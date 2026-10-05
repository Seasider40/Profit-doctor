"""Adversarial Dataset Contract and comparability boundary tests."""
import unittest
from datetime import date, datetime, timezone

from profit_doctor.reasoning.bridge.qualification import Coverage, Period, ReportingBasis
from profit_doctor.reasoning.dataset.comparability import assess_dataset_comparability
from profit_doctor.reasoning.dataset.contracts import (AssessmentOutcome, DatasetAssertion,
    DatasetComparability, DatasetContract, DatasetCoverage, DatasetFamily,
    DatasetRevisionRelationship, DimensionState, TemporalEvidenceRole)
from profit_doctor.reasoning.domain.contracts import Actor, LineageReference
from profit_doctor.reasoning.domain.service import ScopeError
from profit_doctor.reasoning.domain.vocabulary import ActorType, LineageKind, SourceAuthority


T = datetime(2026, 10, 1, tzinfo=timezone.utc)


def ref(kind, resource, source_id, client='c1'):
    return LineageReference(kind=kind, store='LEGACY_SQLITE', resource=resource,
        source_id=source_id, client_id=client)


def verified(value, *evidence):
    return DatasetAssertion(verified_value=value, verification_authority=SourceAuthority.SYSTEM_DERIVED,
        verification_evidence=tuple(evidence))


def period(month, *, completeness=Coverage.COMPLETE, basis='source-control-v1'):
    start = date(2026, month, 1)
    if month == 12:
        end = date(2026, 12, 31)
    else:
        from calendar import monthrange
        end = date(2026, month, monthrange(2026, month)[1])
    return DatasetCoverage(period=Period(start=start, end=end, basis=ReportingBasis.MONTHLY,
        convention='CALENDAR_MONTH', nature='FLOW'), completeness=completeness, coverage_basis=basis)


def contract(name, *, client='c1', month=1, coverage_state=Coverage.COMPLETE,
             population='all-uk-sales', selection=None, family=DatasetFamily.SALES_TRANSACTIONS,
             organisation='uk-all-divisions', currency='GBP', unit='MONEY',
             revision=DatasetRevisionRelationship.NEW_OBSERVATION, verified_claims=True,
             observed_rows=10, coverage_basis='source-control-v1', source_provider='northstar'):
    dataset = ref(LineageKind.DATASET, 'dataset', 'ds-'+name, client)
    version = ref(LineageKind.DATASET_VERSION, 'dataset_version', 'version-'+name, client)
    file = ref(LineageKind.SOURCE_FILE, 'source_file', 'file-'+name, client)
    refs = (dataset, version, file)
    make = (lambda value, *ev: DatasetAssertion() if value is None else verified(value, *ev)) if verified_claims else (lambda value, *ev: DatasetAssertion() if value is None else DatasetAssertion(
        declared_value=value, declaration_authority=SourceAuthority.MANAGEMENT_ASSERTION,
        declared_by=Actor(actor_type=ActorType.MANAGEMENT, source_authority=SourceAuthority.MANAGEMENT_ASSERTION,
            actor_id='client-user-1'), declared_at=T))
    values = dict(contract_id='contract-'+name, client_id=client, recorded_run_id='run-'+client,
        source_dataset=dataset, source_version=version, source_file=file, source_file_sha256='a'*64,
        source_capture_id='import-'+name, logical_dataset_key='northstar:transactions',
        source_data_domain='D07_SALES_TRANSACTIONS', source_digest='b'*64, revision=1,
        family=make(str(family), *refs), source_provider=make(source_provider, *refs),
        population=make(population, *refs), inclusion_exclusion=make(selection or {
            'included': ['invoices', 'credit_notes'], 'excluded': [], 'filters': []}, *refs),
        coverage=make(period(month, completeness=coverage_state, basis=coverage_basis).model_dump(mode='json'), *refs),
        definition=make({'key':'sales-transaction-v1','version':'1'}, *refs),
        organisational_scope=make({'entity':'uk-trading','division':organisation}, *refs),
        currency=make(currency, *refs), unit=make(unit, *refs),
        time_basis=make({'date_field':'month','basis':'CALENDAR_MONTH'}, *refs),
        revision_relationship=make(str(revision), *refs), observed_row_count=observed_rows,
        observed_period_from=f'2026-{month:02}-01', observed_period_to=f'2026-{month:02}-28', created_at=T)
    if revision in (DatasetRevisionRelationship.RESTATEMENT, DatasetRevisionRelationship.CORRECTION,
                    DatasetRevisionRelationship.SUPERSESSION, DatasetRevisionRelationship.PARTIAL_REPLACEMENT):
        values['revision_target_contract_id'] = 'prior-'+name
    return DatasetContract(**values)


class DatasetContractV253(unittest.TestCase):
    def assess(self, left=None, right=None):
        return assess_dataset_comparability(left or contract('jan', month=1),
            right or contract('feb', month=2), assessed_at=T)

    def test_verified_same_population_and_definition_can_be_comparable(self):
        result = self.assess()
        self.assertEqual(AssessmentOutcome.COMPARABLE, result.outcome)
        self.assertEqual(TemporalEvidenceRole.NEW_OBSERVATION, result.temporal_evidence_role)
        self.assertEqual(11, len(result.dimensions))

    def test_missing_population_fails_closed_even_when_totals_and_rows_match(self):
        left = contract('jan', month=1, population=None, observed_rows=10)
        right = contract('feb', month=2, population=None, observed_rows=10)
        result = self.assess(left, right)
        self.assertEqual(AssessmentOutcome.INSUFFICIENT_EVIDENCE, result.outcome)
        self.assertEqual('POPULATION_UNKNOWN', result.dimensions['POPULATION'].reason)

    def test_different_divisions_are_not_comparable(self):
        result = self.assess(contract('jan', month=1, organisation='division-a'),
            contract('feb', month=2, organisation='division-b'))
        self.assertEqual(AssessmentOutcome.NOT_COMPARABLE, result.outcome)
        self.assertEqual('ORGANISATIONAL_SCOPE_DIFFERS', result.dimensions['ORGANISATIONAL_SCOPE'].reason)

    def test_complete_and_partial_extracts_are_not_silently_comparable(self):
        result = self.assess(contract('jan', month=1, coverage_state=Coverage.COMPLETE),
            contract('feb', month=2, coverage_state=Coverage.PARTIAL))
        self.assertEqual(AssessmentOutcome.NOT_COMPARABLE, result.outcome)
        self.assertEqual('COMPLETE_AND_PARTIAL_COVERAGE_DIFFER', result.dimensions['COVERAGE'].reason)

    def test_changed_inclusion_filter_is_not_comparable(self):
        result = self.assess(contract('jan', month=1, selection={'include':['invoices','credit_notes'],'exclude':[]}),
            contract('feb', month=2, selection={'include':['invoices'],'exclude':['credit_notes']}))
        self.assertEqual(AssessmentOutcome.NOT_COMPARABLE, result.outcome)

    def test_row_count_and_similar_values_never_supply_population_evidence(self):
        result = self.assess(contract('jan', month=1, population=None, observed_rows=50),
            contract('feb', month=2, population=None, observed_rows=50))
        self.assertNotEqual(AssessmentOutcome.COMPARABLE, result.outcome)

    def test_explicit_restatement_is_not_a_new_temporal_observation(self):
        left = contract('sep-v1', month=9, revision=DatasetRevisionRelationship.NEW_OBSERVATION)
        right = contract('sep-v2', month=9, revision=DatasetRevisionRelationship.RESTATEMENT)
        result = self.assess(left, right)
        self.assertEqual(TemporalEvidenceRole.REVISION_ONLY, result.temporal_evidence_role)
        self.assertEqual('EXPLICIT_REVISION_IS_NOT_A_NEW_TIME_OBSERVATION',
            result.dimensions['REVISION_RELATIONSHIP'].reason)

    def test_unknown_revision_does_not_become_a_new_observation(self):
        left = contract('sep-v1', month=9, revision=DatasetRevisionRelationship.UNKNOWN)
        right = contract('sep-v2', month=9, revision=DatasetRevisionRelationship.UNKNOWN)
        result = self.assess(left, right)
        self.assertEqual(TemporalEvidenceRole.INDETERMINATE, result.temporal_evidence_role)
        self.assertEqual(AssessmentOutcome.INSUFFICIENT_EVIDENCE, result.outcome)

    def test_human_declaration_remains_distinct_from_verification(self):
        left = contract('jan', month=1, verified_claims=False)
        right = contract('feb', month=2, verified_claims=False)
        result = self.assess(left, right)
        self.assertEqual(AssessmentOutcome.COMPARABLE_WITH_LIMITATIONS, result.outcome)
        self.assertIsNone(left.population.verified_value)
        self.assertEqual('all-uk-sales', left.population.declared_value)
        self.assertEqual('client-user-1', left.population.declared_by.actor_id)

    def test_source_evidence_contradicting_declaration_is_retained_and_refused(self):
        left = contract('jan', month=1)
        claim = DatasetAssertion(declared_value='all-uk-sales',
            declaration_authority=SourceAuthority.MANAGEMENT_ASSERTION,
            declared_by=Actor(actor_type=ActorType.MANAGEMENT,source_authority=SourceAuthority.MANAGEMENT_ASSERTION,actor_id='manager-1'),
            declared_at=T, verified_value='division-a-only', verification_authority=SourceAuthority.SOURCE_DATA,
            verification_evidence=(left.source_file,))
        right = contract('feb', month=2)
        left = DatasetContract.from_json(left.model_copy(update={'population':claim}).to_json())
        result = self.assess(left, right)
        self.assertEqual(AssessmentOutcome.NOT_COMPARABLE, result.outcome)
        self.assertEqual('POPULATION_DECLARATION_CONTRADICTED_BY_VERIFIED_EVIDENCE',
            result.dimensions['POPULATION'].reason)

    def test_cross_client_comparison_is_refused(self):
        with self.assertRaises(ScopeError):
            self.assess(contract('jan', month=1, client='c1'), contract('feb', month=2, client='c2'))

    def test_cross_family_is_not_comparable_even_when_measures_are_similar(self):
        result = self.assess(contract('sales', month=1), contract('gl', month=2, family=DatasetFamily.GENERAL_LEDGER))
        self.assertEqual(AssessmentOutcome.NOT_COMPARABLE, result.outcome)

    def test_currency_and_unit_mismatches_are_refused_without_conversion(self):
        result = self.assess(contract('jan', month=1, currency='GBP', unit='MONEY'),
            contract('feb', month=2, currency='EUR', unit='MONEY'))
        self.assertEqual(AssessmentOutcome.NOT_COMPARABLE, result.outcome)
        result = self.assess(contract('jan2', month=1, unit='MONEY'),
            contract('feb2', month=2, unit='COUNT'))
        self.assertEqual(AssessmentOutcome.NOT_COMPARABLE, result.outcome)

    def test_definition_and_coverage_basis_changes_are_explicit(self):
        left = contract('jan', month=1)
        changed = DatasetContract.from_json(left.model_copy(update={'definition':verified({'key':'sales-v2','version':'2'},left.source_file)}).to_json())
        result = self.assess(changed, contract('feb', month=2))
        self.assertEqual(AssessmentOutcome.NOT_COMPARABLE, result.outcome)
        result = self.assess(contract('jan2', month=1, coverage_basis='control-a'),
            contract('feb2', month=2, coverage_basis='control-b'))
        self.assertEqual(AssessmentOutcome.NOT_COMPARABLE, result.outcome)

    def test_source_data_domain_change_is_not_hidden_by_declared_provider(self):
        left = contract('left', month=1, verified_claims=False)
        right = DatasetContract.from_json(contract('right', month=2, verified_claims=False).model_copy(
            update={'source_data_domain':'D01_PNL'}).to_json())
        result = self.assess(left, right)
        self.assertEqual(DimensionState.MISMATCH, result.dimensions['SOURCE_LINEAGE'].state)
        self.assertEqual('SOURCE_DATA_DOMAIN_DIFFERS', result.dimensions['SOURCE_LINEAGE'].reason)

    def test_duplicate_period_is_not_new_time_evidence(self):
        result = self.assess(contract('sep-a', month=9), contract('sep-b', month=9))
        self.assertEqual(TemporalEvidenceRole.INDETERMINATE, result.temporal_evidence_role)
        self.assertIn('SAME_PERIOD', result.dimensions['COVERAGE'].reason)

    def test_serialization_preserves_authority_lineage_and_revision_without_scores(self):
        value = contract('jan', month=1, verified_claims=False)
        copied = DatasetContract.from_json(value.to_json())
        self.assertEqual(value, copied)
        self.assertEqual(value.source_version, copied.source_version)
        self.assertIsNone(copied.population.verified_value)
        result = self.assess()
        self.assertNotIn('score', result.model_dump(mode='json'))
        self.assertEqual(result, DatasetComparability.from_json(result.to_json()))

    def test_declaration_actor_must_be_identified_and_human(self):
        with self.assertRaises(ValueError):
            DatasetAssertion(declared_value='all sales', declaration_authority=SourceAuthority.MANAGEMENT_ASSERTION,
                declared_by=Actor(actor_type=ActorType.MANAGEMENT,source_authority=SourceAuthority.MANAGEMENT_ASSERTION),
                declared_at=T)

    def test_unknown_claim_cannot_smuggle_authority_or_value(self):
        with self.assertRaises(ValueError):
            DatasetAssertion(verified_value='complete', verification_authority=SourceAuthority.SYSTEM_DERIVED)


if __name__ == '__main__':
    unittest.main()
