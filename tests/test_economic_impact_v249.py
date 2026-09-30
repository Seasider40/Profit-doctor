"""Explicit synthetic positives and adversarial production qualification boundaries."""
from decimal import Decimal
import json
from pathlib import Path
import unittest
from sqlalchemy import select, insert, update, func
from sqlalchemy.exc import IntegrityError

from profit_doctor.persistence import impact_schema as tables, reasoning_schema as rd
from profit_doctor.reasoning.domain.contracts import ReasoningObject, EffectOverlap
from profit_doctor.reasoning.domain.service import FoundationService, ScopeError, RevisionConflict
from profit_doctor.reasoning.domain.vocabulary import ImpactType, OverlapType
from profit_doctor.reasoning.impact.contracts import (
    Source, SyntheticBasis, Qualification, QualifiedImpact, Dimension, DIMENSIONS,
)
from profit_doctor.reasoning.impact.registry import REGISTRY
from profit_doctor.reasoning.impact.service import ImpactService
from tests import test_canonical_facts_findings_v244 as canonical
from tests import test_economic_bridge_v248b as bridge_tests

FIXTURE = Path(__file__).parent / 'fixtures/impact_v249/excess_wc.json'


class EconomicImpactV249(unittest.TestCase):
    target_url = canonical.CanonicalV244.target_url
    prepare_target = canonical.CanonicalV244.prepare_target

    def setUp(self):
        canonical.CanonicalV244.setUp(self)
        self.foundation = FoundationService(self.session, 'c1', self.actor)
        self.bases = {'operational-wc-a': SyntheticBasis.from_json(FIXTURE.read_text())}
        self.relationships = {}
        self.impacts = ImpactService(self.foundation, 'r1', synthetic_resolver=self.bases.__getitem__,
                                     synthetic_overlap_resolver=self.relationships.get)

    def candidate(self, key='operational-wc-a', category='CASH_TRAPPED', **kwargs):
        return self.impacts.assess(Source(kind='SYNTHETIC', source_id=key), category, **kwargs)

    def other(self, key='other', **updates):
        data = self.bases['operational-wc-a'].model_dump(mode='json')
        data.update(fixture_key=key, consequence_key=key)
        data.update(updates)
        data['counterfactual'].update(scope=data['scope'], as_of=data['as_of'])
        self.bases[key] = SyntheticBasis.model_validate(data)
        return self.candidate(key)

    def total(self, *records, **kwargs):
        opts = dict(domain='SYNTHETIC', dimension='CASH', category='CASH_TRAPPED')
        opts.update(kwargs)
        return self.impacts.aggregate([q.candidate_id for q in records], **opts)

    def overlap(self, a, b, kind):
        relation = self.foundation.relate_effects(EffectOverlap(client_id='c1', run_id='r1',
            source_effect_id=a.impact.effect_id, target_effect_id=b.impact.effect_id,
            overlap_type=kind, metadata={'basis': 'Explicit synthetic relationship axiom only'}))
        self.relationships[relation.overlap_id] = relation
        return relation

    def count(self, table):
        return self.session.scalar(select(func.count()).select_from(table))

    def test_synthetic_positive_precision_counterfactual_and_roundtrip(self):
        q = self.candidate()
        self.assertEqual('QUALIFIED_IMPACT', q.outcome)
        self.assertEqual(Decimal('200.00000000000000000001'), q.impact.amount.value)
        self.assertEqual('COUNTERFACTUAL_EXCESS_STOCK', q.impact.amount.basis)
        self.assertEqual('SYNTHETIC', q.domain)
        self.assertEqual(q, Qualification.from_json(q.to_json()))
        self.session.commit()
        self.assertEqual(q, self.impacts.get(q.candidate_id, current=True))

    def test_independent_confidence_materiality_no_opportunity_fields(self):
        i = self.candidate().impact
        self.assertEqual('NOT_ASSESSED', i.confidence.attribution_confidence)
        self.assertEqual('NOT_ASSESSED', i.confidence.opportunity_confidence)
        self.assertEqual('NOT_ASSESSED', i.materiality.controllability)
        self.assertIsNone(i.materiality.percentage_of_gross_profit)
        for field in ('score', 'recoverability', 'addressability', 'opportunity_value'):
            self.assertNotIn(field, type(i).model_fields)

    def test_no_positive_production_category_is_enabled(self):
        self.assertEqual(set(ImpactType), set(REGISTRY))
        self.assertFalse(any(c.production_qualified for c in REGISTRY.values()))
        obj = self.foundation.create_object(ReasoningObject(client_id='c1', run_id='r1',
            object_type='FINDING', source_authority='SYSTEM_DERIVED'))
        for category in ImpactType:
            q = self.impacts.assess(Source(kind='REASONING', source_id=obj.object_id), category)
            self.assertIsNone(q.impact)
            self.assertEqual('INSUFFICIENT_EVIDENCE', q.outcome)
        self.assertEqual(0, self.count(tables.impact))

    def test_management_assertion_held_not_verified(self):
        obj = self.foundation.create_object(ReasoningObject(client_id='c1', run_id='r1',
            object_type='FACT', source_authority='MANAGEMENT_ASSERTION'))
        q = self.impacts.assess(Source(kind='REASONING', source_id=obj.object_id), 'CASH_TRAPPED')
        self.assertEqual('HELD', q.outcome)
        self.assertIn('SOURCE_AUTHORITY_NOT_VERIFIED', q.blockers)
        self.assertIsNone(q.impact)

    def test_unknown_category_and_source_kind_rejected(self):
        with self.assertRaises(ValueError): self.candidate(category='FINANCIAL_IMPACT')
        with self.assertRaises(ValueError): Source(kind='RAW_WORKBOOK', source_id='a')

    def test_fake_qualified_outcome_and_domain_rejected(self):
        data = self.candidate().model_dump(mode='json')
        for patch in ({'domain': 'PRODUCTION'}, {'impact': None}, {'blockers': ['missing']}):
            with self.assertRaises(ValueError): Qualification.model_validate({**data, **patch})
        with self.assertRaises(ValueError): QualifiedImpact.model_validate({**data['impact'], 'category': 'OBSERVED_LOSS'})

    def test_float_and_missing_counterfactual_rejected(self):
        data = self.bases['operational-wc-a'].model_dump(mode='json')
        with self.assertRaises(ValueError): SyntheticBasis.model_validate({**data, 'observed': 1200.1})
        with self.assertRaises(ValueError): SyntheticBasis.model_validate({**data, 'counterfactual': None})

    def test_counterfactual_must_match_scope_and_date(self):
        data = self.bases['operational-wc-a'].model_dump(mode='json')
        for patch in ({'as_of': '2025-12-31'}, {'scope': 'unrelated'}):
            with self.assertRaises(ValueError): SyntheticBasis.model_validate({**data, **patch})

    def test_precision_not_limited_by_default_decimal_context(self):
        q = self.other(observed='100000000000000000000000000000000000000000000000000000000000000000.00000000000000000001')
        self.assertEqual(Decimal('99999999999999999999999999999999999999999999999999999999999999000.00000000000000000001'), q.impact.amount.value)
        self.assertEqual(q.impact.amount.value, self.total(q).total)

    def test_contradictory_equivalence_and_independence_blocks(self):
        a, b, c = self.candidate(), self.other('b'), self.other('c')
        self.overlap(a, b, 'SAME_EFFECT'); self.overlap(b, c, 'SAME_EFFECT')
        self.overlap(a, c, 'INDEPENDENT')
        self.assertEqual('NOT_SAFELY_AGGREGATABLE', self.total(a, b, c).status)

    def test_unsupported_benchmark_and_one_month_run_rate_refused(self):
        data = self.bases['operational-wc-a'].model_dump(mode='json')
        data['counterfactual']['basis'] = 'BEST_EVER_MARGIN'
        with self.assertRaises(ValueError): SyntheticBasis.model_validate(data)
        q = self.candidate(category='RUN_RATE_LEAKAGE')
        self.assertIsNone(q.impact)
        self.assertIn('periodisation', q.required_counterfactual)

    def test_future_risk_profit_cash_potential_benefit_dimensions_separate(self):
        self.assertEqual(6, len(set(DIMENSIONS.values())))
        self.assertNotEqual(DIMENSIONS[ImpactType.FUTURE_EXPOSURE], DIMENSIONS[ImpactType.OBSERVED_LOSS])
        with self.assertRaises(ValueError): self.total(self.candidate(), dimension='PROFIT_PNL')

    def test_synthetic_cannot_enter_production_totals(self):
        result = self.total(self.candidate(), domain='PRODUCTION')
        self.assertEqual('NOT_SAFELY_AGGREGATABLE', result.status)
        self.assertIsNone(result.total)

    def test_synthetic_foundation_identity_cannot_reenter_as_production_candidate(self):
        q = self.candidate()
        with self.assertRaises(ScopeError):
            self.impacts.assess(Source(kind='REASONING', source_id=q.impact.impact_id), 'CASH_TRAPPED')
        self.assertEqual(1, self.count(tables.qualification))

    def test_neutral_or_negative_excess_has_no_impact(self):
        for value in ('1000', '900'):
            q = self.other('case'+value, observed=value)
            self.assertEqual('NOT_APPLICABLE', q.outcome)
            self.assertIsNone(q.impact)
            self.assertEqual('EMPTY', self.total(q).status)

    def test_partial_coverage_preserved_without_extrapolation(self):
        q = self.other(coverage='PARTIAL')
        self.assertEqual('PARTIAL', q.impact.amount.coverage)
        self.assertEqual(Decimal('200.00000000000000000001'), self.total(q).total)

    def test_replay_does_not_duplicate_candidates_effects_impacts_or_audits(self):
        a = self.candidate()
        counts = [self.count(t) for t in (tables.qualification, tables.impact, tables.audit, rd.economic_effect, rd.audit_event)]
        self.assertEqual(a, self.candidate())
        self.assertEqual(counts, [self.count(t) for t in (tables.qualification, tables.impact, tables.audit, rd.economic_effect, rd.audit_event)])

    def test_revision_requires_expected_version_preserves_history_and_effect(self):
        a = self.candidate()
        data = self.bases['operational-wc-a'].model_dump(mode='json')
        data['observed'] = '1300'
        self.bases['operational-wc-a'] = SyntheticBasis.model_validate(data)
        with self.assertRaises(RevisionConflict): self.total(a)
        with self.assertRaises(RevisionConflict): self.candidate()
        b = self.candidate(expected_revision=1)
        self.assertEqual(2, b.revision)
        self.assertEqual(a.impact.effect_id, b.impact.effect_id)
        self.assertEqual(a, self.impacts.get(a.candidate_id, 1))
        self.assertEqual(Decimal('300'), self.total(b).total)
        with self.assertRaises(RevisionConflict): self.impacts.get(a.candidate_id, 1, current=True)

    def test_loss_of_qualification_removes_previous_impact_from_current_totals(self):
        a = self.candidate()
        data = self.bases['operational-wc-a'].model_dump(mode='json'); data['observed'] = '1000'
        self.bases['operational-wc-a'] = SyntheticBasis.model_validate(data)
        b = self.candidate(expected_revision=1)
        self.assertEqual('EMPTY', self.total(b).status)
        self.assertIsNotNone(self.impacts.get(a.candidate_id, 1).impact)

    def test_two_analytical_paths_share_effect_without_double_count(self):
        a = self.candidate()
        b = self.other(consequence_key=self.bases['operational-wc-a'].consequence_key)
        self.assertEqual(a.impact.effect_id, b.impact.effect_id)
        self.assertEqual(a.impact.amount.value, self.total(a, b, a).total)
        self.assertEqual(1, self.count(rd.economic_effect))

    def test_same_effect_declared_alias_deduplicates(self):
        a, b = self.candidate(), self.other()
        self.overlap(a, b, 'SAME_EFFECT')
        self.assertEqual(a.impact.amount.value, self.total(a, b).total)

    def test_partial_overlap_blocks_total(self):
        a, b = self.candidate(), self.other(); self.overlap(a, b, 'PARTIAL_OVERLAP')
        self.assertIsNone(self.total(a, b).total)

    def test_unqualified_independence_declaration_is_not_proof(self):
        a, b = self.candidate(), self.other()
        self.overlap(a, b, 'INDEPENDENT')
        self.relationships.clear()
        self.assertIsNone(self.total(a, b).total)

    def test_supersession_and_invalidation_lifecycle(self):
        a = self.candidate()
        self.assertEqual('QUANTIFIED', self.impacts.lifecycle(a.candidate_id))
        self.bases['operational-wc-a'] = SyntheticBasis.model_validate({**self.bases['operational-wc-a'].model_dump(), 'observed': '1000'})
        self.candidate(expected_revision=1)
        self.assertEqual('INVALIDATED', self.impacts.lifecycle(a.candidate_id, 1))
        self.assertEqual('CANDIDATE', self.impacts.lifecycle(a.candidate_id))

    def test_parent_child_blocks_total(self):
        a, b = self.candidate(), self.other(); self.overlap(a, b, 'PARENT_CHILD')
        self.assertEqual('NOT_SAFELY_AGGREGATABLE', self.total(a, b).status)

    def test_unknown_overlap_explicit_and_absent_block_total(self):
        a, b = self.candidate(), self.other()
        self.assertIsNone(self.total(a, b).total)
        self.overlap(a, b, 'UNKNOWN_OVERLAP')
        self.assertIsNone(self.total(a, b).total)

    def test_independent_effects_sum_only_compatible_values(self):
        a, b = self.candidate(), self.other(); self.overlap(a, b, 'INDEPENDENT')
        self.assertEqual(Decimal('400.00000000000000000002'), self.total(a, b).total)

    def test_same_effect_conflicting_values_block_total(self):
        a = self.candidate()
        b = self.other(consequence_key=self.bases['operational-wc-a'].consequence_key, observed='1300')
        self.assertIsNone(self.total(a, b).total)

    def test_different_dates_scopes_and_coverage_block_total(self):
        a = self.candidate()
        for idx, patch in enumerate(({'as_of':'2025-12-31'}, {'scope':'other population'}, {'coverage':'PARTIAL'})):
            b = self.other('variant'+str(idx), **patch)
            self.overlap(a, b, 'INDEPENDENT')
            self.assertIsNone(self.total(a, b).total)

    def test_caller_rollback_removes_all_new_state(self):
        self.candidate()
        self.session.rollback()
        for table in (tables.qualification, tables.impact, tables.audit, rd.reasoning_object, rd.economic_effect, rd.effect_reference, rd.audit_event):
            self.assertEqual(0, self.count(table), table.name)

    def test_cross_client_and_wrong_run_rejected(self):
        q = self.candidate()
        foreign = ImpactService(FoundationService(self.session, 'c2', self.actor), 'r2')
        with self.assertRaises(ScopeError): foreign.get(q.candidate_id)
        with self.assertRaises(ScopeError): ImpactService(self.foundation, 'r2')
        with self.assertRaises(ScopeError): ImpactService(self.foundation, 'r3', synthetic_resolver=self.bases.__getitem__).assess(q.source, q.category)

    def test_missing_endpoints_and_default_synthetic_resolver_rejected(self):
        with self.assertRaises(ScopeError): self.impacts.assess(Source(kind='REASONING', source_id='missing'), 'CASH_TRAPPED')
        with self.assertRaises(ScopeError): ImpactService(self.foundation, 'r1').assess(Source(kind='SYNTHETIC', source_id='operational-wc-a'), 'CASH_TRAPPED')

    def test_fk_cross_client_and_missing_effect_enforced(self):
        q = self.candidate(); self.session.commit()
        for client, effect in (('c2', q.impact.effect_id), ('c1', 'missing')):
            with self.assertRaises(IntegrityError):
                with self.session.begin_nested():
                    self.session.execute(update(tables.impact).where(tables.impact.c.impact_id == q.impact.impact_id).values(client_id=client, effect_id=effect))

    def test_corrupt_indexed_source_and_document_rejected(self):
        q = self.candidate()
        self.session.execute(update(tables.qualification).values(run_id='r3'))
        with self.assertRaises(ScopeError): self.impacts.get(q.candidate_id)

    def test_duplicate_revision_database_uniqueness(self):
        q = self.candidate()
        row = dict(self.session.execute(select(tables.qualification)).mappings().one())
        with self.assertRaises(IntegrityError):
            with self.session.begin_nested(): self.session.execute(insert(tables.qualification).values(**row))

    def test_audit_records_source_counterfactual_previous_and_actor(self):
        q = self.candidate()
        entry = json.loads(self.session.scalar(select(tables.audit.c.document)))
        self.assertIsNone(entry['previous'])
        self.assertEqual(self.actor.actor_id, entry['actor']['actor_id'])
        self.assertEqual(q, Qualification.from_json(entry['new']))
        self.assertTrue(self.foundation.audit_events(object_id=q.impact.impact_id))


class GoldenImpactV249(unittest.TestCase):
    target_url = bridge_tests.EconomicBridgeV248B.target_url
    prepare_target = bridge_tests.EconomicBridgeV248B.prepare_target
    signal = bridge_tests.EconomicBridgeV248B.signal
    fact = bridge_tests.EconomicBridgeV248B.fact
    inputs = bridge_tests.EconomicBridgeV248B.inputs
    create = bridge_tests.EconomicBridgeV248B.create

    def setUp(self):
        bridge_tests.EconomicBridgeV248B.setUp(self)
        self.impacts = ImpactService(FoundationService(self.session, 'c1', self.actor), 'r1', bridges=self.bridges)

    def test_golden_three_candidates_zero_impacts_and_no_totals(self):
        categories = ('CASH_TRAPPED', 'VALUE_CREATION_POTENTIAL', 'OBSERVED_LOSS')
        families = ('WORKING_CAPITAL_BRIDGE', 'REVENUE_BRIDGE', 'MARGIN_OR_PROFIT_BRIDGE')
        records = []
        for family, category in zip(families, categories):
            b = self.create(family).bridge
            q = self.impacts.assess(Source(kind='BRIDGE', source_id=b.snapshot_id), category)
            records.append(q)
            self.assertEqual('INSUFFICIENT_EVIDENCE', q.outcome)
            self.assertIsNone(q.impact)
            total = self.impacts.aggregate([q.candidate_id], domain='PRODUCTION', dimension=DIMENSIONS[ImpactType(category)], category=category)
            self.assertEqual('EMPTY', total.status); self.assertIsNone(total.total)
        wc = self.bridges.get(records[0].source.source_id)
        self.assertEqual(Decimal('700000'), wc.closing-wc.opening)
        self.assertIn('required balance', records[0].required_counterfactual)
        self.assertEqual(3, self.session.scalar(select(func.count()).select_from(tables.qualification)))
        self.assertEqual(0, self.session.scalar(select(func.count()).select_from(tables.impact)))

    def test_residuals_partial_coverage_exact_c0_remain_source_evidence(self):
        for family, residual in (('REVENUE_BRIDGE','-225000'), ('MARGIN_OR_PROFIT_BRIDGE','-88250')):
            b = self.create(family).bridge
            q = self.impacts.assess(Source(kind='BRIDGE',source_id=b.snapshot_id), 'RUN_RATE_LEAKAGE')
            self.assertIsNone(q.impact)
            source = json.loads(q.source_document)
            self.assertEqual(Decimal(residual), Decimal(source['residual']))
            self.assertEqual('PARTIAL', source['components'][0]['coverage'])
            if family == 'MARGIN_OR_PROFIT_BRIDGE': self.assertEqual('contribution_0', source['metric'])

    def test_refused_bridges_cannot_be_resolved_as_sources(self):
        for family in ('PROFIT_TO_CASH_BRIDGE', 'COST_TO_OUTPUT_BRIDGE'):
            self.assertIsNone(self.bridges.create(family,2025,2026,(),()).bridge)
            with self.assertRaises(ScopeError): self.impacts.assess(Source(kind='BRIDGE',source_id=family), 'OBSERVED_LOSS')

    def test_stale_bridge_is_held_and_requires_explicit_reassessment(self):
        b = self.create('WORKING_CAPITAL_BRIDGE').bridge
        source = Source(kind='BRIDGE', source_id=b.snapshot_id)
        q = self.impacts.assess(source, 'CASH_TRAPPED')
        self.legacy.execute("UPDATE financial_statement_line SET amount='1' WHERE line_code='AR'")
        with self.assertRaises(RevisionConflict): self.impacts.assess(source, 'CASH_TRAPPED')
        held = self.impacts.assess(source, 'CASH_TRAPPED', expected_revision=1)
        self.assertEqual('HELD', held.outcome)
        self.assertEqual(q, self.impacts.get(q.candidate_id, 1))
