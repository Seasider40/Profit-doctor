"""Evidence-gap value contracts cannot fill missing analytical semantics."""
import json
import unittest

from profit_doctor.reasoning.canonical.contracts import ReportingScope
from profit_doctor.reasoning.hypothesis.gaps import EvidenceGap, GapBarrier, GapKind


class HypothesisGapsV246(unittest.TestCase):
    def gap(self, **changes):
        values = dict(kind='MISSING_SEGMENTATION', missing_evidence='Customer-product identity',
            reason_required='Customer identity alone cannot establish like-for-like price movement',
            dimension='CUSTOMER_PRODUCT_PERIOD', scope=ReportingScope(
                entity_type='CUSTOMER', entity_id='customer-a',
                period_basis='Exact comparison windows not retained'),
            investigation_request='Provide identified customer-product price and quantity history for comparable windows',
            blocks='BOTH', related_objects=('fact-b', 'fact-a'))
        values.update(changes)
        return EvidenceGap(**values)

    def test_gap_round_trip_preserves_explicit_unknown_period_and_scope(self):
        gap = self.gap()
        self.assertEqual(gap, EvidenceGap.from_json(gap.to_json()))
        self.assertEqual('customer-a', gap.scope.entity_id)
        self.assertIsNone(gap.scope.period_from)
        self.assertIsNone(gap.scope.period_to)
        self.assertEqual(('fact-a', 'fact-b'), gap.related_objects)

    def test_support_and_contradiction_barriers_remain_distinct(self):
        for barrier in GapBarrier:
            with self.subTest(barrier=barrier):
                self.assertEqual(barrier, self.gap(blocks=barrier).blocks)
        self.assertNotEqual(self.gap(blocks='SUPPORT'), self.gap(blocks='CONTRADICTION'))

    def test_all_governed_gap_kinds_round_trip(self):
        for kind in GapKind:
            with self.subTest(kind=kind):
                gap = self.gap(kind=kind)
                self.assertEqual(kind, EvidenceGap.from_json(gap.to_json()).kind)

    def test_unknown_vocabulary_and_schema_are_rejected(self):
        for changes in ({'kind': 'ROOT_CAUSE'}, {'blocks': 'NONE'}, {'schema_version': 'future'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.gap(**changes)

    def test_missing_or_blank_explanation_is_rejected(self):
        for field in ('missing_evidence', 'reason_required', 'dimension', 'investigation_request'):
            for value in ('', '   ', '\t', 'hidden\x00text'):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.gap(**{field: value})
            document = json.loads(self.gap().to_json())
            del document[field]
            with self.assertRaises(ValueError):
                EvidenceGap.from_json(json.dumps(document))

    def test_no_invented_confidence_financial_value_or_action_fields(self):
        for field in ('score', 'confidence', 'financial_impact', 'action_plan', 'verified'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.gap(**{field: 'invented'})

    def test_references_are_unique_and_serialization_order_is_deterministic(self):
        self.assertEqual(self.gap().to_json(), self.gap(related_objects=('fact-a', 'fact-b')).to_json())
        with self.assertRaises(ValueError):
            self.gap(related_objects=('fact-a', 'fact-a'))

    def test_scope_requires_paired_entity_and_ordered_period(self):
        for values in ({'entity_type': 'PRODUCT'},
                       {'period_from': '2026-02-01', 'period_to': '2026-01-01'}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.gap(scope={'period_basis': 'Captured windows', **values})


if __name__ == '__main__':
    unittest.main()
