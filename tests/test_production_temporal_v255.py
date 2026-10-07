"""Production admission, precision gaps and frozen-kernel refusal parity."""
import unittest
from decimal import Decimal

from tests import test_component_margin_v255 as fixture
from profit_doctor.reasoning.production_evidence.temporal import ProductionTemporalService, ProductionTemporalResult
from profit_doctor.reasoning.temporal.contracts import ContractKey, Window
from profit_doctor.reasoning.domain.service import ScopeError


REV = ContractKey.REVENUE_DESCRIPTIVE_TRAJECTORY
C0 = ContractKey.CONTRIBUTION_0_MARGIN_TRAJECTORY


class ProductionTemporalV255(fixture.ComponentFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.temporal = ProductionTemporalService(self.service, self.margin_service)
        self.window = Window(start='2026-01-01', end='2026-03-31', cadence='MONTHLY')

    def revenue_series(self, values=('105', '110.25')):
        owners = [self.revenue.measurement_id]
        for month, value in enumerate(values, 2):
            self.components(value, '40', month)
            owners.append(self.revenue.measurement_id)
        return owners

    def margin_series(self, costs=('39', '38')):
        owners = [self.margin_service.qualify(self.bind().binding_id).margin_id]
        for month, cost in enumerate(costs, 2):
            self.components('100', cost, month)
            owners.append(self.margin_service.qualify(self.bind().binding_id).margin_id)
        return owners

    def test_three_production_revenue_observations_qualify(self):
        ids = self.revenue_series()
        result = self.temporal.evaluate(REV, self.window, monthly_ids=ids)
        self.assertEqual((result.sequence, result.trajectory, result.interpretation), ('QUALIFIED', 'INCREASING', 'NOT_ASSESSED'))
        self.assertEqual(result.basis.origin, 'QUALIFIED_PRODUCTION_V255')
        self.assertEqual([o.source_kind for o in result.basis.observations], ['MONTHLY_REVENUE'] * 3)
        self.assertNotIn('SYNTHETIC_QUALIFICATION', result.to_json())
        self.assertEqual(len(result.comparisons), 2)
        self.assertTrue(all(len(c.dimensions) == 11 for c in result.comparisons))

    def test_revenue_equality_is_material(self):
        result = self.temporal.evaluate(REV, self.window, monthly_ids=self.revenue_series())
        self.assertEqual([m.state for m in result.movements], ['POSITIVE', 'POSITIVE'])
        self.assertEqual(result.movements[0].threshold, Decimal('5'))
        self.assertEqual(result.movements[1].threshold, Decimal('5.25'))

    def test_revenue_below_threshold_is_stable(self):
        result = self.temporal.evaluate(REV, self.window, monthly_ids=self.revenue_series(('104.99', '105')))
        self.assertEqual(result.trajectory, 'STABLE')
        self.assertEqual(result.interpretation, 'NOT_ASSESSED')

    def test_revenue_decrease_remains_descriptive(self):
        result = self.temporal.evaluate(REV, self.window, monthly_ids=self.revenue_series(('90', '80')))
        self.assertEqual((result.trajectory, result.interpretation), ('DECREASING', 'NOT_ASSESSED'))

    def test_three_exact_monthly_margins_improve(self):
        result = self.temporal.evaluate(C0, self.window, margin_ids=self.margin_series())
        self.assertEqual((result.sequence, result.trajectory, result.interpretation), ('QUALIFIED', 'INCREASING', 'IMPROVING'))
        self.assertEqual([m.threshold for m in result.movements], [Decimal('1'), Decimal('1')])
        self.assertEqual([m.delta for m in result.movements], [Decimal('1'), Decimal('1')])
        self.assertEqual(result.basis.origin, 'QUALIFIED_PRODUCTION_V255')

    def test_margin_decrease_worsens(self):
        result = self.temporal.evaluate(C0, self.window, margin_ids=self.margin_series(('41', '42')))
        self.assertEqual((result.trajectory, result.interpretation), ('DECREASING', 'WORSENING'))

    def test_margin_below_threshold_stable(self):
        result = self.temporal.evaluate(C0, self.window, margin_ids=self.margin_series(('39.01', '39')))
        self.assertEqual((result.trajectory, result.interpretation), ('STABLE', 'STABLE'))

    def test_monetary_c0_cannot_enter_margin_contract(self):
        with self.assertRaises(ScopeError):
            self.temporal.evaluate(C0, self.window, monthly_ids=(self.contribution.measurement_id,))

    def test_monetary_c0_cannot_enter_revenue_contract(self):
        with self.assertRaises(ScopeError):
            self.temporal.evaluate(REV, self.window, monthly_ids=(self.contribution.measurement_id,))

    def test_unknown_owner_refuses(self):
        with self.assertRaises(ScopeError):
            self.temporal.evaluate(REV, self.window, monthly_ids=('REV-01',))

    def test_missing_month_is_indeterminate(self):
        first = self.revenue.measurement_id
        self.components('115', '40', 3)
        result = self.temporal.evaluate(REV, self.window, monthly_ids=(first, self.revenue.measurement_id))
        self.assertEqual(result.gaps, ('2026-02',))
        self.assertEqual(result.trajectory, 'INDETERMINATE')

    def test_non_terminating_margin_does_not_complete_sequence(self):
        first = self.margin_service.qualify(self.bind().binding_id).margin_id
        self.components('3', '2')
        second = self.margin_service.qualify(self.bind().binding_id).margin_id
        self.components('100', '38', 3)
        third = self.margin_service.qualify(self.bind().binding_id).margin_id
        result = self.temporal.evaluate(C0, self.window, margin_ids=(first, second, third))
        self.assertEqual(result.sequence, 'NOT_ASSESSED')
        self.assertEqual(result.trajectory, 'NOT_ASSESSED')
        self.assertIn('MISSING_CANONICAL_MEASUREMENT_EVIDENCE', result.reasons)
        self.assertTrue(any(o.value is None for o in result.basis.observations))

    def test_two_months_only_have_movement(self):
        first = self.revenue.measurement_id
        self.components('105', '40')
        window = Window(start='2026-01-01', end='2026-02-28', cadence='MONTHLY')
        result = self.temporal.evaluate(REV, window, monthly_ids=(first, self.revenue.measurement_id))
        self.assertEqual(result.sequence, 'QUALIFIED')
        self.assertEqual(len(result.movements), 1)
        self.assertEqual(result.trajectory, 'NOT_ASSESSED')

    def test_partial_window_cannot_invent_month(self):
        window = Window(start='2026-01-02', end='2026-03-31', cadence='MONTHLY')
        result = self.temporal.evaluate(REV, window, monthly_ids=self.revenue_series())
        self.assertNotEqual(result.sequence, 'QUALIFIED')

    def test_no_favourable_subwindow_selection(self):
        ids = self.revenue_series(('90', '110'))
        result = self.temporal.evaluate(REV, self.window, monthly_ids=ids)
        self.assertEqual(result.trajectory, 'MIXED')
        self.assertEqual(result.basis.window, self.window)

    def test_duplicate_request_refuses(self):
        with self.assertRaises(ValueError):
            self.temporal.evaluate(REV, self.window, monthly_ids=(self.revenue.measurement_id,) * 2)

    def test_unknown_contract_refuses(self):
        with self.assertRaises(ValueError):
            self.temporal.evaluate('ARBITRARY', self.window)

    def test_no_arbitrary_value_injection(self):
        with self.assertRaises(TypeError):
            self.temporal.evaluate(REV, self.window, value='100')

    def test_serialization_retains_truthful_owner_lineage(self):
        result = self.temporal.evaluate(C0, self.window, margin_ids=self.margin_series())
        self.assertEqual(ProductionTemporalResult.from_json(result.to_json()), result)
        self.assertTrue(all(o.context_binding_id for o in result.basis.observations))
        self.assertTrue(all('canonical_c0_component_binding' in o.source_snapshot for o in result.basis.observations))

    def test_provider_must_be_registered(self):
        with self.assertRaises(ScopeError):
            ProductionTemporalService(object())

    def test_ar_route_refuses_without_qualified_dataset_provider(self):
        with self.assertRaisesRegex(ScopeError, 'SOURCE_SUPPORTED_AR_DATASET_PROVIDER_REQUIRED'):
            self.temporal.evaluate(ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE, self.window, absence_ids=('absence',))

    def test_qualified_impact_identity_cannot_bypass_ar_dataset_boundary(self):
        with self.assertRaisesRegex(ScopeError, 'SOURCE_SUPPORTED_AR_DATASET_PROVIDER_REQUIRED'):
            self.temporal.evaluate(ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE, self.window, impact_ids=('impact',))
