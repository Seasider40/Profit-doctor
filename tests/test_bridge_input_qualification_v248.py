"""Synthetic policy proofs are distinct from real resolver qualification.

No test fabricates a qualified application Bridge or repairs frozen source rows
to manufacture missing production semantics. There is no Bridge writer yet.
"""
import unittest
from datetime import date
from decimal import Decimal
from sqlalchemy import event, text

from profit_doctor.reasoning.bridge.qualification import (
    ComparisonInput, Endpoint, Period, Qualification, qualify,
)
from profit_doctor.reasoning.bridge.source import BridgeInputResolver
from profit_doctor.reasoning.canonical.contracts import Measurement
from profit_doctor.reasoning.domain.contracts import LineageReference
from profit_doctor.reasoning.domain.service import RevisionConflict, ScopeError
from tests import test_evidence_graph_v245 as graph_tests


def changed(original, **updates):
    fields = original.model_dump(mode='python')
    fields.update(updates)
    return type(original).model_validate(fields)


def synthetic_input():
    """Explicit hypothetical evidence; not a source resolver/certificate."""
    ref = LineageReference(kind='DATASET_VERSION', store='LEGACY_SQLITE',
        resource='dataset_version', source_id='v1', client_id='c1')
    a = Endpoint(fact_id='a', client_id='c1', run_id='r1',
        measurement=Measurement(metric='revenue', value='100.00000000000000000001',
            unit='CURRENCY', currency='GBP', basis='prior comparable window'),
        segment_basis='complete business sales', economic_basis='net sales; same recognition policy',
        period=Period(start='2025-01-01', end='2025-01-31', basis='MONTHLY',
            convention='calendar month, inclusive dates', nature='FLOW'),
        coverage='COMPLETE', coverage_evidence=(ref,), source_versions=('v1',),
        lineage=(ref,), lineage_complete=True, source_snapshot='a'*64, eligible=True)
    b = changed(a, fact_id='b', run_id='r2',
        measurement=changed(a.measurement, value='120.0000', basis='current comparable window'),
        period=changed(a.period, start=date(2025, 3, 1), end=date(2025, 3, 31)))
    return ComparisonInput(family='REVENUE_BRIDGE', opening=a, closing=b,
        version_relationship='COMPATIBLE', version_evidence=(ref,), version_basis='Synthetic retained common source version')


class BridgeInputPolicyV248(unittest.TestCase):
    def test_explicit_comparable_periods_qualify_without_score(self):
        result = qualify(synthetic_input())
        self.assertEqual('QUALIFIED', result.outcome)
        self.assertEqual((), result.gaps)
        self.assertEqual(31, result.input.opening.period.duration_days)
        self.assertNotIn('score', type(result).model_fields)

    def test_same_dates_different_reporting_basis_blocked(self):
        value = synthetic_input()
        b = changed(value.closing, period=changed(value.opening.period, basis='YTD'))
        result = qualify(changed(value, closing=b))
        self.assertEqual('INCOMPARABLE', result.outcome)
        self.assertIn('REPORTING_BASIS_MISMATCH', result.gaps)

    def test_equal_duration_different_entity_blocked(self):
        value = synthetic_input()
        result = qualify(changed(value, closing=changed(value.closing, entity_type='CUSTOMER', entity_id='other')))
        self.assertEqual('INCOMPARABLE', result.outcome)

    def test_stock_cannot_silently_replace_flow(self):
        value = synthetic_input()
        result = qualify(changed(value, closing=changed(value.closing, period=changed(value.closing.period, nature='STOCK'))))
        self.assertEqual('INCOMPARABLE', result.outcome)
        self.assertIn('METRIC_UNIT_OR_STOCK_FLOW_NOT_ALLOWED', result.gaps)

    def test_unknown_restatement_blocks_even_same_source_version(self):
        result = qualify(changed(synthetic_input(), version_relationship='UNKNOWN'))
        self.assertEqual('INSUFFICIENT_EVIDENCE', result.outcome)
        self.assertIn('VERSION_RESTATEMENT_BASIS_NOT_ESTABLISHED', result.gaps)

    def test_restated_requires_evidence_and_explicit_policy(self):
        value = changed(synthetic_input(), version_relationship='RESTATED_COMPATIBLE')
        self.assertEqual('QUALIFIED', qualify(value).outcome)
        self.assertEqual('INSUFFICIENT_EVIDENCE', qualify(changed(value, version_basis=None)).outcome)
        self.assertEqual('INSUFFICIENT_EVIDENCE', qualify(changed(value, version_evidence=())).outcome)
        self.assertEqual('INCOMPARABLE', qualify(changed(value, version_relationship='SUPERSEDED')).outcome)

    def test_partial_coverage_retained_not_company_complete(self):
        value = synthetic_input()
        result = qualify(changed(value, closing=changed(value.closing, coverage='PARTIAL')))
        self.assertEqual('PARTIALLY_QUALIFIED', result.outcome)
        self.assertEqual('PARTIAL', result.input.closing.coverage)

    def test_complete_label_without_coverage_evidence_blocks(self):
        value = synthetic_input()
        result = qualify(changed(value, opening=changed(value.opening, coverage_evidence=())))
        self.assertEqual('INSUFFICIENT_EVIDENCE', result.outcome)

    def test_lineage_alone_does_not_establish_basis(self):
        value = synthetic_input()
        result = qualify(changed(value, opening=changed(value.opening, economic_basis=None)))
        self.assertEqual('INSUFFICIENT_EVIDENCE', result.outcome)
        self.assertIn('ECONOMIC_BASIS_UNKNOWN', result.gaps)

    def test_duration_and_chronology_no_implicit_normalisation(self):
        value = synthetic_input()
        for start, end in [('2025-02-01', '2025-02-28'), ('2024-01-01', '2024-01-31')]:
            with self.subTest(start=start):
                b = changed(value.closing, period=changed(value.closing.period, start=start, end=end))
                self.assertEqual('INCOMPARABLE', qualify(changed(value, closing=b)).outcome)

    def test_currency_metric_and_segment_mismatch(self):
        value = synthetic_input()
        for b in [changed(value.closing, segment_basis='selected products'),
                  changed(value.closing, measurement=changed(value.closing.measurement, metric='gross_profit')),
                  changed(value.closing, economic_basis='cash basis')]:
            self.assertEqual('INCOMPARABLE', qualify(changed(value, closing=b)).outcome)
        with self.assertRaises(ValueError):
            changed(value.closing.measurement, currency='USD')  # frozen canonical GBP boundary

    def test_contribution_zero_not_gross_profit(self):
        value = synthetic_input()
        a = changed(value.opening, measurement=changed(value.opening.measurement, metric='contribution_0'))
        b = changed(value.closing, measurement=changed(value.closing.measurement, metric='gross_profit'))
        result = qualify(changed(value, family='MARGIN_OR_PROFIT_BRIDGE', opening=a, closing=b))
        self.assertEqual('INCOMPARABLE', result.outcome)

    def test_no_generic_family_fallback(self):
        for family in ('WORKING_CAPITAL_BRIDGE', 'PROFIT_TO_CASH_BRIDGE', 'COST_TO_OUTPUT_BRIDGE'):
            self.assertEqual('INSUFFICIENT_EVIDENCE', qualify(changed(synthetic_input(), family=family)).outcome)
        with self.assertRaises(ValueError):
            changed(synthetic_input(), family='OTHER')

    def test_precision_serialization_replay_and_changed_evidence_identity(self):
        value = synthetic_input()
        result = qualify(value)
        self.assertEqual(result, Qualification.from_json(result.to_json()))
        self.assertEqual(Decimal('100.00000000000000000001'), result.input.opening.measurement.value)
        self.assertEqual(result.assessment_id, qualify(value).assessment_id)
        revised = qualify(changed(value, closing=changed(value.closing, source_snapshot='b'*64)))
        self.assertNotEqual(result.assessment_id, revised.assessment_id)
        self.assertEqual('a'*64, result.input.closing.source_snapshot)

    def test_invalid_structures_and_floating_finance_rejected(self):
        with self.assertRaises(ValueError):
            Period(start='2025-02-01', end='2025-01-01')
        with self.assertRaises(ValueError):
            Period(start='2025-01-01', end='2025-01-31', basis='POINT_IN_TIME')
        with self.assertRaises(ValueError):
            changed(synthetic_input().opening.measurement, value=1.1)
        with self.assertRaises(ValueError):
            changed(synthetic_input(), contract_version='BIQ-UNKNOWN')

    def test_forged_qualification_outcome_rejected_on_read(self):
        result = qualify(changed(synthetic_input(), version_relationship='UNKNOWN'))
        with self.assertRaises(ValueError):
            changed(result, outcome='QUALIFIED', gaps=())

    def test_calendar_label_cannot_qualify_arbitrary_equal_intervals(self):
        value = synthetic_input()
        a = changed(value.opening, period=changed(value.opening.period, start='2025-01-02'))
        b = changed(value.closing, period=changed(value.closing.period, start='2025-03-02'))
        result = qualify(changed(value, opening=a, closing=b))
        self.assertEqual('INCOMPARABLE', result.outcome)
        self.assertIn('PERIOD_NOT_FULL_CALENDAR_INTERVAL', result.gaps)

    def test_invalid_endpoints_cannot_be_repaired_with_components(self):
        value = synthetic_input()
        self.assertEqual('INVALID', qualify(changed(value, closing=changed(value.closing, eligible=False))).outcome)
        with self.assertRaises(ValueError):
            changed(value, components=['complete-looking decomposition'])


class BridgeInputSourceV248(unittest.TestCase):
    target_url = graph_tests.EvidenceGraphV245.target_url
    prepare_target = graph_tests.EvidenceGraphV245.prepare_target
    signal = graph_tests.EvidenceGraphV245.signal
    fact = graph_tests.EvidenceGraphV245.fact

    def setUp(self):
        graph_tests.EvidenceGraphV245.setUp(self)

    def revenue_fact(self):
        return self.fact('bridge', test='REV-01', typ='COMPARABLE_REVENUE_CHANGE', entity=None,
            entity_id=None, observed='120.0000', comparison='100.0000', variance='20.0000',
            period_from='2023-01-31', period_to='2025-01-31')

    def resolver(self):
        return BridgeInputResolver(self.session, 'c1', 'r1', self.actor, self.source)

    def test_actual_retained_ancestry_cannot_supply_missing_semantics(self):
        fact = self.revenue_fact()
        result = self.resolver().assess('REVENUE_BRIDGE', fact.object_id)
        self.assertEqual('INSUFFICIENT_EVIDENCE', result.outcome)
        self.assertTrue(result.input.opening.lineage_complete)
        self.assertIsNone(result.input.opening.period.start)
        self.assertEqual('UNKNOWN', result.input.opening.coverage)
        self.assertIn('VERSION_RESTATEMENT_BASIS_NOT_ESTABLISHED', result.gaps)
        self.assertIn('PERIOD_BASIS_NOT_ESTABLISHED', result.gaps)
        self.assertIn('COVERAGE_NOT_ESTABLISHED', result.gaps)

    def test_read_only_source_and_canonical_no_new_audits(self):
        fact = self.revenue_fact()
        self.session.commit()
        before = self.legacy.total_changes
        audit_before = self.session.execute(text('SELECT COUNT(*) FROM reasoning_audit_event_v243')).scalar_one()
        statements = []
        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement.lstrip().split()[0].upper())
        event.listen(self.engine, 'before_cursor_execute', record)
        self.legacy.execute('PRAGMA query_only=ON')
        try:
            result = self.resolver().assess('REVENUE_BRIDGE', fact.object_id)
            self.assertEqual('INSUFFICIENT_EVIDENCE', result.outcome)
            self.assertEqual(before, self.legacy.total_changes)
            self.assertFalse(self.session.new)
            self.assertFalse(self.session.dirty)
            self.assertEqual(audit_before, self.session.execute(text('SELECT COUNT(*) FROM reasoning_audit_event_v243')).scalar_one())
            self.assertTrue(statements)
            self.assertEqual({'SELECT'}, set(statements))
        finally:
            self.legacy.execute('PRAGMA query_only=OFF')
            event.remove(self.engine, 'before_cursor_execute', record)

    def test_replay_and_source_metadata_change_preserve_old_snapshot(self):
        fact = self.revenue_fact()
        resolver = self.resolver()
        old = resolver.assess('REVENUE_BRIDGE', fact.object_id)
        self.assertEqual(old, resolver.assess('REVENUE_BRIDGE', fact.object_id))
        self.legacy.execute("UPDATE dataset_version SET row_count=9 WHERE dataset_version_id='va'")
        new = resolver.assess('REVENUE_BRIDGE', fact.object_id)
        self.assertNotEqual(old.assessment_id, new.assessment_id)
        self.assertEqual('INSUFFICIENT_EVIDENCE', new.outcome)
        self.assertEqual(old, Qualification.from_json(old.to_json()))

    def test_stale_signal_rejected_without_semantic_repair(self):
        fact = self.revenue_fact()
        self.legacy.execute("UPDATE signal SET observed_value='999' WHERE signal_id='bridge'")
        with self.assertRaises(RevisionConflict):
            self.resolver().assess('REVENUE_BRIDGE', fact.object_id)

    def test_foreign_client_and_wrong_closing_run_rejected(self):
        fact = self.revenue_fact()
        with self.assertRaises(ScopeError):
            BridgeInputResolver(self.session, 'c2', 'r2', self.actor, self.source)
        with self.assertRaises(ScopeError):
            BridgeInputResolver(self.session, 'c1', 'r3', self.actor, self.source).assess('REVENUE_BRIDGE', fact.object_id)

    def test_no_caller_assertion_override(self):
        fact = self.revenue_fact()
        with self.assertRaises(TypeError):
            self.resolver().assess('REVENUE_BRIDGE', fact.object_id, coverage='COMPLETE')

    def test_shared_ancestry_retained_without_independence_claim(self):
        fact = self.revenue_fact()
        result = self.resolver().assess('REVENUE_BRIDGE', fact.object_id)
        self.assertEqual(result.input.opening.lineage, result.input.closing.lineage)
        self.assertEqual(('LEGACY_SQLITE:dataset_version:va',), result.input.opening.source_versions)
        self.assertNotEqual('QUALIFIED', result.outcome)

    def test_dataset_dates_retained_but_not_assigned_to_measurement_windows(self):
        fact = self.revenue_fact()
        self.legacy.execute("UPDATE dataset_version SET period_from='2023-01-01',period_to='2025-01-31' WHERE dataset_version_id='va'")
        result = self.resolver().assess('REVENUE_BRIDGE', fact.object_id)
        source = result.input.opening.retained_sources[0]
        self.assertEqual(date(2023, 1, 1), source.period_from)
        self.assertEqual(1, source.version_number)
        self.assertEqual('COMPLETED', source.ingestion_status)
        self.assertIsNone(result.input.opening.period.start)
        self.assertEqual('INSUFFICIENT_EVIDENCE', result.outcome)
