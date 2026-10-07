"""Adversarial authenticated population binding and exact finite-margin ownership."""
from decimal import Decimal, localcontext
import unittest

from sqlalchemy import select, func, insert
from sqlalchemy.exc import IntegrityError

from tests import test_production_ownership_service_v255 as ownership
from profit_doctor.persistence import production_qualification_schema as tables, measurement_schema
from profit_doctor.reasoning.production_evidence.component import ComponentManifest, ComponentRecordPair
from profit_doctor.reasoning.production_evidence.margin import MarginQualificationService, MarginOwner
from profit_doctor.reasoning.production_evidence.precision import exact_percentage, NON_TERMINATING
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.bridge.qualification import Period
from profit_doctor.reasoning.production_evidence.contracts import EvidenceDeclaration


class ComponentFixture(ownership.OwnershipFixture):
    def setUp(self):
        super().setUp()
        self.margin_service = MarginQualificationService(self.service)
        self.revenue = self.qualify().value
        self.fx.fx.c0()
        x = self.fx.fx
        self.contribution = self.service.qualify_monthly(x.records, x.controls, x.document(x.manifest, 'manifest'),
            mapping_version=x.document(x.mapping, 'mapping', 'HUMAN_FD_JUDGEMENT'), family='CONTRIBUTION_0').value
        self.proof = ComponentManifest(scope=self.revenue.semantic.manifest.scope,
            revenue_owner_id=self.revenue.measurement_id, contribution_owner_id=self.contribution.measurement_id,
            revenue_version_id=self.revenue.semantic.contract.source_version.source_id,
            contribution_version_id=self.contribution.semantic.contract.source_version.source_id,
            source_system_id='source-system1', economic_observation_reference='entity-e1-ledger-l1-2026-01',
            relationship_reference='source-issued-cross-export-component-manifest-1', population_relationship='EXACT_EQUIVALENT',
            revenue_definition='NET_REVENUE', revenue_population=self.revenue.semantic.manifest.scope.population,
            contribution_population=self.contribution.semantic.manifest.scope.population,
            revenue_inclusion_exclusion=self.revenue.semantic.manifest.inclusion_exclusion,
            contribution_inclusion_exclusion=self.contribution.semantic.manifest.inclusion_exclusion,
            pairs=(ComponentRecordPair(revenue_record_id='s1', contribution_record_id='s1', underlying_source_record='source-system1:posting:posting-1'),),
            revision=1, change_kind='ORIGINAL', change_reference='authenticated initial source relationship')

    def bind(self, proof=None, authority='SOURCE_DATA'):
        version = self.fx.fx.document(proof or self.proof, 'c0-component-manifest', authority)
        return self.margin_service.bind(version)

    def refused(self, update, reason):
        binding = self.bind(self.proof.model_copy(update=update))
        self.assertEqual(binding.status, 'REFUSED')
        self.assertIn(reason, binding.reasons)
        margin = self.margin_service.qualify(binding.binding_id)
        self.assertEqual(margin.status, 'REFUSED')
        self.assertIsNone(margin.measurement)
        self.assertIsNone(margin.context)

    def components(self, revenue_amount, cost, month=2):
        x = self.fx.fx
        from calendar import monthrange
        start = f'2026-{month:02d}-01'
        end = f'2026-{month:02d}-{monthrange(2026, month)[1]}'
        period = Period(start=start, end=end, basis='MONTHLY', nature='FLOW')
        scope = self.revenue.semantic.manifest.scope.model_copy(update={'period': period})
        changes = {'period_start': start, 'period_end': end, 'definition': 'NET_REVENUE'}
        rv = x.amounts('s1', revenue_amount, changes=changes)
        control = x.amounts('control-rev', revenue_amount, changes=changes)
        manifest = self.revenue.semantic.manifest.model_copy(update={'scope': scope, 'record_version_id': rv,
            'extraction_start': period.start, 'extraction_end': period.end})
        chart = self.revenue.semantic.chart.model_copy(update={'scope': scope})
        mapping = self.revenue.semantic.mapping.model_copy(update={'scope': scope, 'source_chart_version': x.document(chart, 'chart')})
        self.revenue = self.service.qualify_monthly(rv, control, x.document(manifest, 'manifest'),
            mapping_version=x.document(mapping, 'mapping', 'HUMAN_FD_JUDGEMENT'), family='REVENUE').value
        cscope = scope.model_copy(update={'definition': 'REVENUE_MINUS_DIRECT_COST'})
        changes['definition'] = 'REVENUE_MINUS_DIRECT_COST'
        cv = x.amounts('s1', revenue_amount, changes=changes, extras=({'record_id': 's2', 'account_code': '5000', 'amount': cost},))
        cc = x.amounts('control-rev', revenue_amount, changes=changes, extras=({'record_id': 'control-cost', 'account_code': '5000', 'amount': cost},))
        cm = self.contribution.semantic.manifest.model_copy(update={'scope': cscope, 'record_version_id': cv,
            'extraction_start': period.start, 'extraction_end': period.end})
        chart = self.contribution.semantic.chart.model_copy(update={'scope': cscope})
        mapping = self.contribution.semantic.mapping.model_copy(update={'scope': cscope, 'source_chart_version': x.document(chart, 'chart')})
        self.contribution = self.service.qualify_monthly(cv, cc, x.document(cm, 'manifest'),
            mapping_version=x.document(mapping, 'mapping', 'HUMAN_FD_JUDGEMENT'), family='CONTRIBUTION_0').value
        self.proof = self.proof.model_copy(update={'scope': scope, 'revenue_owner_id': self.revenue.measurement_id,
            'contribution_owner_id': self.contribution.measurement_id, 'revenue_version_id': rv, 'contribution_version_id': cv,
            'economic_observation_reference': f'entity-e1-ledger-l1-2026-{month:02d}'})


class ComponentMarginV255(ComponentFixture, unittest.TestCase):
    def test_authenticated_exact_population_qualifies(self):
        binding = self.bind()
        self.assertEqual(binding.status, 'QUALIFIED')
        margin = self.margin_service.qualify(binding.binding_id)
        self.assertEqual(margin.measurement.value, Decimal('60'))
        self.assertEqual(margin.context.unit, 'PERCENTAGE')
        self.assertEqual(margin.context.period.nature, 'RATE')
        self.assertNotEqual(margin.margin_id, self.contribution.measurement_id)
        self.assertEqual(self.margin_service.get_margin(margin.margin_id, current=True), margin)

    def test_equal_amounts_without_authenticated_proof_cannot_bind(self):
        binding = self.bind(authority='HUMAN_FD_JUDGEMENT')
        self.assertEqual(binding.status, 'REFUSED')
        self.assertIn('SOURCE_AUTHORITATIVE_COMPONENT_RELATIONSHIP_REQUIRED', binding.reasons)

    def test_same_record_ids_across_exports_without_authority_cannot_bind(self):
        binding = self.bind(authority=None)
        self.assertEqual(binding.status, 'REFUSED')

    def test_same_client_period_alone_cannot_bind(self):
        self.refused({'pairs': ()}, 'EXACT_SOURCE_RECORD_RELATIONSHIP_REQUIRED')

    def test_same_account_codes_alone_cannot_bind(self):
        self.refused({'population_relationship': 'UNKNOWN'}, 'EXACT_REVENUE_POPULATION_EQUIVALENCE_REQUIRED')

    def test_exact_record_relationship_retained(self):
        binding = self.bind()
        restored = self.margin_service.get_binding(binding.binding_id, current=True)
        self.assertEqual(restored.proof.pairs[0].underlying_source_record, 'source-system1:posting:posting-1')
        self.assertIn(binding.proof_version_id, [r.source_id for r in restored.lineage])

    def test_subset_refuses(self):
        self.refused({'population_relationship': 'SUBSET'}, 'EXACT_REVENUE_POPULATION_EQUIVALENCE_REQUIRED')

    def test_superset_refuses(self):
        self.refused({'population_relationship': 'SUPERSET'}, 'EXACT_REVENUE_POPULATION_EQUIVALENCE_REQUIRED')

    def test_partial_overlap_refuses(self):
        self.refused({'population_relationship': 'PARTIAL_OVERLAP'}, 'EXACT_REVENUE_POPULATION_EQUIVALENCE_REQUIRED')

    def test_unknown_relationship_refuses(self):
        self.refused({'population_relationship': 'UNKNOWN'}, 'EXACT_REVENUE_POPULATION_EQUIVALENCE_REQUIRED')

    def test_contradictory_relationship_refuses(self):
        self.refused({'population_relationship': 'CONTRADICTORY'}, 'EXACT_REVENUE_POPULATION_EQUIVALENCE_REQUIRED')

    def test_different_revenue_definition_refuses(self):
        self.refused({'revenue_definition': 'UNKNOWN'}, 'QUALIFIED_NET_REVENUE_DEFINITION_REQUIRED')

    def test_different_organisation_refuses(self):
        scope = self.proof.scope.model_copy(update={'ledger_id': 'other'})
        self.refused({'scope': scope}, 'COMPONENT_SCOPE_PERIOD_OR_CURRENCY_MISMATCH')

    def test_different_client_refuses(self):
        proof = self.proof.model_copy(update={'scope': self.proof.scope.model_copy(update={'client_id': 'c2'})})
        with self.assertRaises(ScopeError):
            self.bind(proof)

    def test_different_period_refuses(self):
        scope = self.proof.scope.model_copy(update={'period': self.proof.scope.period.model_copy(update={'start': '2026-02-01', 'end': '2026-02-28'})})
        self.refused({'scope': scope}, 'COMPONENT_SCOPE_PERIOD_OR_CURRENCY_MISMATCH')

    def test_insufficient_record_lineage_refuses(self):
        pair = self.proof.pairs[0].model_copy(update={'contribution_record_id': 'not-in-export'})
        self.refused({'pairs': (pair,)}, 'COMPONENT_RECORD_MEMBERSHIP_MISMATCH')

    def test_untrusted_source_refuses(self):
        self.assertEqual(self.bind(authority=None).status, 'REFUSED')

    def test_management_declaration_cannot_establish_binding(self):
        self.assertEqual(self.bind(authority='MANAGEMENT_ASSERTION').status, 'REFUSED')

    def test_contradictory_declaration_retained_and_refused(self):
        declaration = EvidenceDeclaration(declaration_id='relationship-assertion-1', client_id='c1',
            actor=self.fx.fx.actor, effective_on='2026-01-31', dimension='population', claim='SUBSET',
            lineage=self.revenue.lineage, revision=1)
        self.refused({'declarations': (declaration,)}, 'CONTRADICTORY_COMPONENT_DECLARATION')

    def test_unchanged_replay_is_idempotent(self):
        binding = self.bind()
        self.assertEqual(self.bind(), binding)
        margin = self.margin_service.qualify(binding.binding_id)
        self.assertEqual(self.margin_service.qualify(binding.binding_id), margin)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.binding)), 1)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.margin)), 1)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.audit)), 2)

    def test_source_revision_reassessed_without_new_period(self):
        old = self.bind()
        first = self.margin_service.qualify(old.binding_id)
        proof = self.proof.model_copy(update={'revision': 2, 'predecessor_version_id': old.proof_version_id,
            'change_kind': 'CORRECTION', 'change_reference': 'source relationship reissued'})
        new = self.bind(proof)
        self.assertEqual(new.status, 'QUALIFIED')
        second = self.margin_service.qualify(new.binding_id)
        self.assertEqual(second.supersedes, first.margin_id)
        self.assertEqual(second.context.period, first.context.period)
        self.assertEqual(self.margin_service.get_margin(first.margin_id), first)
        with self.assertRaises(RevisionConflict):
            self.margin_service.get_margin(first.margin_id, current=True)

    def test_unresolved_revision_refuses(self):
        self.bind()
        self.refused({'relationship_reference': 'unrelated-second-manifest'}, 'COMPONENT_REVISION_AUTHORITY_REQUIRED')

    def test_competing_registered_original_proofs_refuse(self):
        other = self.proof.model_copy(update={'relationship_reference': 'second-original-root'})
        self.fx.fx.document(other, 'c0-component-manifest')
        self.refused({}, 'COMPONENT_SOURCE_ROOT_AMBIGUOUS')

    def test_new_ambiguous_source_proof_invalidates_current_binding(self):
        value = self.bind()
        self.fx.fx.document(self.proof.model_copy(update={'relationship_reference': 'unresolved-second-root'}), 'c0-component-manifest')
        with self.assertRaises(RevisionConflict):
            self.margin_service.get_binding(value.binding_id, current=True)

    def test_binding_foreign_component_fk_refuses(self):
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.execute(insert(tables.binding).values(binding_id='b', series_id='s', client_id='c2', run_id='r2',
                revision=1, revenue_owner_id=self.revenue.measurement_id, contribution_owner_id=self.contribution.measurement_id, document='{}'))

    def test_caller_owned_rollback(self):
        self.session.commit()
        binding = self.bind()
        self.margin_service.qualify(binding.binding_id)
        self.session.rollback()
        for table in (tables.binding, tables.margin, tables.audit):
            self.assertEqual(self.session.scalar(select(func.count()).select_from(table)), 0)

    def test_audit_and_serialization_preserve_binding(self):
        value = self.margin_service.qualify(self.bind().binding_id)
        self.assertEqual(MarginOwner.from_json(value.to_json()), value)
        self.assertIn(value.binding_id, value.to_json())
        self.assertIn('source-evidence-owner', self.session.scalar(select(tables.audit.c.document).where(tables.audit.c.margin_id == value.margin_id)))

    def test_margin_context_resolves_separate_owner(self):
        value = self.margin_service.qualify(self.bind().binding_id)
        binding = self.service.contexts.lookup(value.context.origin)
        self.assertEqual(self.service.contexts.resolve_binding(binding.binding_id)[1], value.context)

    def test_expired_proof_authority_refuses_current_margin(self):
        binding = self.bind()
        value = self.margin_service.qualify(binding.binding_id)
        self.fx.fx.grants.pop(binding.proof_version_id)
        with self.assertRaises(RevisionConflict):
            self.margin_service.get_margin(value.margin_id, current=True)

    def test_non_terminating_refusal_persisted_without_approximation(self):
        self.components('3', '2')
        value = self.margin_service.qualify(self.bind().binding_id)
        self.assertEqual(value.status, 'REFUSED')
        self.assertEqual(value.reasons, (NON_TERMINATING,))
        self.assertIsNone(value.measurement)
        self.assertIsNone(value.context)
        self.assertEqual(self.margin_service.get_margin(value.margin_id, current=True), value)
        self.assertIsNone(self.session.scalar(select(tables.margin.c.context_id)))
        self.assertEqual(self.session.scalar(select(func.count()).select_from(measurement_schema.measurement_context)), 4)

    def test_production_finite_25_percent(self):
        self.components('100', '75')
        self.assertEqual(self.margin_service.qualify(self.bind().binding_id).measurement.value, Decimal('25'))

    def test_production_finite_12_5_percent(self):
        self.components('8', '7')
        self.assertEqual(self.margin_service.qualify(self.bind().binding_id).measurement.value, Decimal('12.5'))

    def test_production_negative_finite_ratio(self):
        self.components('8', '9')
        self.assertEqual(self.margin_service.qualify(self.bind().binding_id).measurement.value, Decimal('-12.5'))

    def test_production_zero_revenue_refuses(self):
        self.components('0', '1')
        value = self.margin_service.qualify(self.bind().binding_id)
        self.assertEqual(value.reasons, ('POSITIVE_REVENUE_REQUIRED',))
        self.assertIsNone(value.measurement)

    def test_production_nonpositive_revenue_refuses(self):
        self.components('-8', '1')
        value = self.margin_service.qualify(self.bind().binding_id)
        self.assertEqual(value.reasons, ('POSITIVE_REVENUE_REQUIRED',))
        self.assertIsNone(value.measurement)

    def test_production_negative_non_terminating_refuses(self):
        self.components('3', '4')
        value = self.margin_service.qualify(self.bind().binding_id)
        self.assertEqual(value.reasons, (NON_TERMINATING,))
        self.assertIsNone(value.measurement)

    def test_wrong_owner_family_refuses(self):
        self.refused({'contribution_owner_id': self.revenue.measurement_id,
            'contribution_version_id': self.revenue.semantic.contract.source_version.source_id},
            'SEPARATE_QUALIFIED_COMPONENT_OWNERS_REQUIRED')

    def test_component_restatement_requires_new_binding_and_preserves_history(self):
        old_binding = self.bind()
        old_margin = self.margin_service.qualify(old_binding.binding_id)
        x = self.fx.fx
        old_r, old_c = self.revenue, self.contribution
        for old, family in ((old_r, 'REVENUE'), (old_c, 'CONTRIBUTION_0')):
            changes = {'definition': old.semantic.manifest.scope.definition}
            extras = ({'record_id': 's2', 'account_code': '5000', 'amount': '40'},) if family == 'CONTRIBUTION_0' else ()
            version = x.amounts('s1', '104', changes=changes, extras=extras)
            controls = x.amounts('control-rev', '104', changes=changes,
                extras=({'record_id': 'control-cost', 'account_code': '5000', 'amount': '40'},) if extras else ())
            manifest = old.semantic.manifest.model_copy(update={'record_version_id': version,
                'predecessor_version_id': old.semantic.contract.source_version.source_id, 'change_kind': 'RESTATEMENT',
                'change_reference': 'source monthly report restated'})
            new = self.service.qualify_monthly(version, controls, x.document(manifest, 'manifest'),
                mapping_version=old.semantic.source_versions[3], family=family).value
            if family == 'REVENUE':
                self.revenue = new
            else:
                self.contribution = new
        with self.assertRaises(RevisionConflict):
            self.margin_service.get_binding(old_binding.binding_id, current=True)
        proof = self.proof.model_copy(update={'revenue_owner_id': self.revenue.measurement_id,
            'contribution_owner_id': self.contribution.measurement_id,
            'revenue_version_id': self.revenue.semantic.contract.source_version.source_id,
            'contribution_version_id': self.contribution.semantic.contract.source_version.source_id,
            'revision': 2, 'predecessor_version_id': old_binding.proof_version_id,
            'change_kind': 'RESTATEMENT', 'change_reference': 'source component relationship reassessed'})
        binding = self.bind(proof)
        self.assertEqual(binding.status, 'QUALIFIED')
        self.assertEqual(binding.supersedes, old_binding.binding_id)
        # 64/104 = 8/13: revised evidence is valid but exact margin is unavailable.
        new_margin = self.margin_service.qualify(binding.binding_id)
        self.assertEqual(new_margin.reasons, (NON_TERMINATING,))
        self.assertEqual(new_margin.supersedes, old_margin.margin_id)
        self.assertEqual(self.margin_service.get_margin(old_margin.margin_id), old_margin)

    def test_foreign_currency_refuses(self):
        self.refused({'scope': self.proof.scope.model_copy(update={'currency': 'USD'})},
            'COMPONENT_SCOPE_PERIOD_OR_CURRENCY_MISMATCH')

    def test_inclusion_exclusion_contradiction_refuses(self):
        self.refused({'revenue_inclusion_exclusion': 'only one chosen customer'},
            'COMPONENT_SOURCE_POPULATION_OR_INCLUSION_MISMATCH')

    def test_authenticated_proof_does_not_override_missing_membership(self):
        pair = self.proof.pairs[0].model_copy(update={'revenue_record_id': 'unknown'})
        self.refused({'pairs': (pair,)}, 'COMPONENT_RECORD_MEMBERSHIP_MISMATCH')

    def test_duplicate_underlying_relationship_rejected(self):
        pair = self.proof.pairs[0].model_copy(update={'revenue_record_id': 's-other', 'contribution_record_id': 'c-other'})
        with self.assertRaisesRegex(ValueError, 'one-to-one'):
            ComponentManifest.from_json(self.proof.model_copy(update={'pairs': (*self.proof.pairs, pair)}).to_json())

    def test_caller_precomputed_margin_not_accepted(self):
        with self.assertRaises(TypeError):
            self.margin_service.qualify('binding', percentage='60')

    def test_unregistered_component_provider_refuses(self):
        with self.assertRaisesRegex(ScopeError, 'Registered production evidence owner'):
            MarginQualificationService(object())

    def test_frozen_facts_and_temporal_owners_not_created(self):
        self.margin_service.qualify(self.bind().binding_id)
        from profit_doctor.persistence import Base
        for name in ('canonical_fact_v244', 'canonical_temporal_assessment'):
            self.assertEqual(self.session.scalar(select(func.count()).select_from(Base.metadata.tables[name])), 0)


class ExactMarginPrecisionV255(unittest.TestCase):
    def test_exact_25_percent(self):
        self.assertEqual(exact_percentage(Decimal('25'), Decimal('100')), Decimal('25'))

    def test_exact_12_5_percent(self):
        self.assertEqual(exact_percentage(Decimal('1'), Decimal('8')), Decimal('12.5'))

    def test_multiple_decimal_places(self):
        self.assertEqual(exact_percentage(Decimal('1'), Decimal('128')), Decimal('0.78125'))

    def test_negative_finite_sign(self):
        self.assertEqual(exact_percentage(Decimal('-1'), Decimal('8')), Decimal('-12.5'))

    def test_high_precision(self):
        numerator = Decimal('0.123456789012345678901234567890123456789')
        self.assertEqual(exact_percentage(numerator, Decimal('100')), numerator)

    def test_very_large_values(self):
        self.assertEqual(exact_percentage(Decimal('1E+10000'), Decimal('8E+10000')), Decimal('12.5'))

    def test_one_third_refuses(self):
        with self.assertRaisesRegex(ValueError, NON_TERMINATING):
            exact_percentage(Decimal('1'), Decimal('3'))

    def test_two_thirds_refuses(self):
        with self.assertRaisesRegex(ValueError, NON_TERMINATING):
            exact_percentage(Decimal('2'), Decimal('3'))

    def test_one_sixth_refuses(self):
        with self.assertRaisesRegex(ValueError, NON_TERMINATING):
            exact_percentage(Decimal('1'), Decimal('6'))

    def test_both_signs_non_terminating(self):
        for n in ('1', '-1'):
            with self.subTest(n=n), self.assertRaisesRegex(ValueError, NON_TERMINATING):
                exact_percentage(Decimal(n), Decimal('7'))

    def test_context_does_not_change_outcome(self):
        for precision in (1, 7, 28, 100):
            with self.subTest(precision=precision), localcontext() as context:
                context.prec = precision
                self.assertEqual(exact_percentage(Decimal('1'), Decimal('128')), Decimal('0.78125'))
                with self.assertRaisesRegex(ValueError, NON_TERMINATING):
                    exact_percentage(Decimal('1'), Decimal('3'))

    def test_zero_revenue_refuses(self):
        with self.assertRaisesRegex(ValueError, 'POSITIVE_REVENUE_REQUIRED'):
            exact_percentage(Decimal('1'), Decimal('0'))

    def test_negative_revenue_refuses(self):
        with self.assertRaisesRegex(ValueError, 'POSITIVE_REVENUE_REQUIRED'):
            exact_percentage(Decimal('1'), Decimal('-8'))

    def test_binary_float_refuses(self):
        with self.assertRaises(TypeError):
            exact_percentage(1.0, Decimal('8'))
