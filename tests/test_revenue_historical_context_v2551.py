"""Registered synthetic-source regressions; no private finance-pack material."""
from decimal import Decimal
import unittest
from sqlalchemy import select, func

from tests.test_component_margin_v255 import ComponentFixture
from profit_doctor.persistence import production_history_schema as tables
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.production_evidence.temporal import ProductionTemporalService
from profit_doctor.reasoning.production_evidence.assessments import ProductionAssessmentService
from profit_doctor.reasoning.temporal.contracts import ContractKey, Window

REV = ContractKey.REVENUE_DESCRIPTIVE_TRAJECTORY
C0 = ContractKey.CONTRIBUTION_0_MARGIN_TRAJECTORY


class RevenueHistoricalContextV2551(ComponentFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.temporal = ProductionTemporalService(self.service, self.margin_service)
        self.assessments = ProductionAssessmentService(self.service, monthly=self.temporal)

    def restate(self, old, amount):
        x = self.fx.fx
        period = old.context.period
        changes = {'period_start': period.start.isoformat(), 'period_end': period.end.isoformat(),
                   'definition': old.semantic.manifest.scope.definition}
        records = x.amounts('s1', amount, changes=changes)
        controls = x.amounts('control-rev', amount, changes=changes)
        manifest = old.semantic.manifest.model_copy(update={
            'record_version_id': records, 'predecessor_version_id': old.semantic.contract.source_version.source_id,
            'change_kind': 'RESTATEMENT', 'change_reference': 'source-supported synthetic report correction'})
        result = self.service.qualify_monthly(records, controls, x.document(manifest, 'manifest'),
            mapping_version=old.semantic.source_versions[3], family='REVENUE')
        self.assertEqual(result.outcome, 'QUALIFIED')
        return result.value

    def six_months(self):
        ids = [self.revenue.measurement_id]
        for month, amount in enumerate(('105', '110', '120', '126', '132.3'), 2):
            self.components(amount, '40', month)
            ids.append(self.revenue.measurement_id)
            if month == 3:
                original = self.revenue
        revised = self.restate(original, '112.5')
        ids[2] = revised.measurement_id
        return ids, original, revised, Window(start='2026-01-01', end='2026-06-30', cadence='MONTHLY')

    def test_current_context_resolves_normally(self):
        value = self.revenue
        binding = self.service.contexts.lookup(value.context.origin)
        self.assertEqual(self.service.contexts.resolve_binding(binding.binding_id)[1], value.context)

    def test_explicit_historical_context_retains_original_owner(self):
        old = self.revenue
        new = self.restate(old, '112.5')
        binding = self.service.contexts.lookup(old.context.origin, current=False)
        resolved, context = self.service.contexts.resolve_binding(binding.binding_id, current=False)
        self.assertEqual((resolved.owner, context), (old.context.origin, old.context))
        self.assertEqual(self.service.context(old.measurement_id, current=False), old.context)
        self.assertEqual(self.service.owner(old.measurement_id, current=False)[1], Decimal('100'))
        self.assertEqual(self.service.get_monthly(new.measurement_id, current=True), new)
        self.assertEqual(new.supersedes, old.measurement_id)

    def test_current_only_historical_owner_binding_and_context_refuse(self):
        old = self.revenue
        binding = self.service.contexts.lookup(old.context.origin)
        self.restate(old, '112.5')
        for read in (lambda: self.service.get_monthly(old.measurement_id, current=True),
                     lambda: self.service.owner(old.measurement_id),
                     lambda: self.service.context(old.measurement_id),
                     lambda: self.service.contexts.lookup(old.context.origin),
                     lambda: self.service.contexts.resolve_binding(binding.binding_id),
                     lambda: self.service.contexts.get_context(old.context.context_id, current=True)):
            with self.subTest(read=read), self.assertRaises(RevisionConflict):
                read()

    def test_temporal_restatement_has_six_economic_observations(self):
        ids, old, new, window = self.six_months()
        result = self.temporal.evaluate(REV, window, monthly_ids=ids)
        self.assertEqual((result.sequence, result.trajectory, result.interpretation),
                         ('QUALIFIED', 'INCREASING', 'NOT_ASSESSED'))
        self.assertEqual(len(result.included), 6)
        self.assertEqual(len(result.basis.observations), 7)
        self.assertIn(new.measurement_id, result.included)
        self.assertNotIn(old.measurement_id, result.included)
        self.assertEqual([m.threshold for m in result.movements],
                         [Decimal(x) for x in ('5', '5.25', '5.625', '6', '6.3')])
        values = {o.source_id: o.value for o in result.basis.observations}
        self.assertEqual((values[old.measurement_id], values[new.measurement_id]),
                         (Decimal('110'), Decimal('112.5')))
        self.assertEqual(self.service.get_monthly(old.measurement_id), old)

    def test_multiple_same_period_revisions_preserve_traversal(self):
        old = self.revenue
        second = self.restate(old, '105')
        third = self.restate(second, '110')
        self.components('120', '40', 2); february = self.revenue
        self.components('130', '40', 3); march = self.revenue
        result = self.temporal.evaluate(REV, Window(start='2026-01-01', end='2026-03-31', cadence='MONTHLY'),
            monthly_ids=(third.measurement_id, february.measurement_id, march.measurement_id))
        self.assertEqual(len(result.included), 3)
        self.assertEqual(len(result.basis.observations), 5)
        self.assertEqual(second.supersedes, old.measurement_id)
        self.assertEqual(third.supersedes, second.measurement_id)

    def test_durable_restatement_replay_retains_history(self):
        ids, old, new, window = self.six_months()
        before_ids = [old.measurement_id if x == new.measurement_id else x for x in ids]
        with self.assertRaises(RevisionConflict):
            self.assessments.assess(REV, window, monthly_ids=before_ids)
        value = self.assessments.assess(REV, window, monthly_ids=ids)
        self.assertEqual(self.assessments.get(value.assessment_id, current=True), value)
        self.assertEqual(self.assessments.assess(REV, window, monthly_ids=ids), value)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.temporal)), 1)
        self.assertEqual(self.service.get_monthly(old.measurement_id).context, old.context)

    def test_prior_assessment_survives_restatement(self):
        ids = [self.revenue.measurement_id]
        self.components('105', '40', 2); ids.append(self.revenue.measurement_id)
        self.components('110', '40', 3); ids.append(self.revenue.measurement_id)
        old = self.revenue
        window = Window(start='2026-01-01', end='2026-03-31', cadence='MONTHLY')
        previous = self.assessments.assess(REV, window, monthly_ids=ids)
        current = self.restate(old, '112.5'); ids[2] = current.measurement_id
        revised = self.assessments.assess(REV, window, monthly_ids=ids)
        self.assertEqual((revised.revision, revised.supersedes), (2, previous.assessment_id))
        self.assertEqual(self.assessments.get(previous.assessment_id), previous)

    def test_cross_client_historical_context_refuses(self):
        old = self.revenue
        self.restate(old, '112.5')
        # Change the canonical reader scope, as in the frozen ownership tests.
        # Foreign ownership must refuse before consulting the source/context.
        self.service.client_id = 'c2'
        with self.assertRaises(ScopeError):
            self.service.contexts.lookup(old.context.origin, current=False)

    def test_unresolved_source_revision_authority_still_refuses(self):
        old = self.revenue
        x = self.fx.fx
        records = x.amounts('s1', '112.5')
        controls = x.amounts('control-rev', '112.5')
        manifest = old.semantic.manifest.model_copy(update={'record_version_id': records})
        result = self.service.qualify_monthly(records, controls, x.document(manifest, 'manifest'),
            mapping_version=old.semantic.source_versions[3], family='REVENUE')
        self.assertEqual(result.outcome, 'REFUSED')
        self.assertTrue(result.blockers)
        self.assertEqual(self.service.get_monthly(old.measurement_id), old)
        with self.assertRaises(RevisionConflict):
            self.service.get_monthly(old.measurement_id, current=True)

    def test_arbitrary_stale_request_remains_refused(self):
        old = self.revenue
        self.restate(old, '112.5')
        with self.assertRaises(RevisionConflict):
            self.temporal.evaluate(REV, Window(start='2026-01-01', end='2026-01-31', cadence='MONTHLY'),
                monthly_ids=(old.measurement_id,))

    def test_historical_margin_binding_uses_its_own_context(self):
        binding = self.bind()
        old = self.margin_service.qualify(binding.binding_id)
        self.components('100', '39', 2)
        february = self.margin_service.qualify(self.bind().binding_id)
        self.components('100', '38', 3)
        march = self.margin_service.qualify(self.bind().binding_id)
        proof = binding.proof.model_copy(update={'revision': 2, 'predecessor_version_id': binding.proof_version_id,
            'change_kind': 'CORRECTION', 'change_reference': 'authoritative source relationship corrected'})
        revised = self.margin_service.qualify(self.bind(proof).binding_id)
        result = self.temporal.evaluate(C0, Window(start='2026-01-01', end='2026-03-31', cadence='MONTHLY'),
            margin_ids=(revised.margin_id, february.margin_id, march.margin_id))
        self.assertEqual(len(result.included), 3)
        self.assertEqual(result.interpretation, 'IMPROVING')
        historical = self.service.contexts.lookup(old.context.origin, current=False)
        self.assertEqual(self.service.contexts.resolve_binding(historical.binding_id, current=False)[1], old.context)
        with self.assertRaises(RevisionConflict):
            self.service.contexts.lookup(old.context.origin)
