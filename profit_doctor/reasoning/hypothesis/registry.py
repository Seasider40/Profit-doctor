"""Retained, explicit proposition contracts. No narrative-based generation."""
from dataclasses import dataclass
from enum import StrEnum


class HypothesisClass(StrEnum):
    EVIDENCE_QUALITY = 'EVIDENCE_QUALITY'
    ECONOMIC_MECHANISM = 'ECONOMIC_MECHANISM'
    NULL_OR_ALTERNATIVE = 'NULL_OR_ALTERNATIVE'


class CandidateRole(StrEnum):
    PRIMARY = 'PRIMARY'
    ALTERNATIVE = 'ALTERNATIVE'
    NULL = 'NULL'


@dataclass(frozen=True)
class HypothesisContract:
    key: str
    hypothesis_class: HypothesisClass
    role: CandidateRole
    findings: tuple[str, ...]
    proposition: str
    requirements: tuple[str, ...]
    disconfirmation: tuple[str, ...]
    version: str = 'HC-2.46.1'


FINDINGS = ('REVENUE_MOVEMENT', 'MARGIN_MOVEMENT', 'CUSTOMER_CONCENTRATION')
CHECKS = ('ORIGIN_CURRENT', 'AUTHORITY', 'LINEAGE', 'SHARED_ANCESTRY',
          'TEMPORAL', 'SEGMENTATION', 'COUNTER_EVIDENCE', 'ALTERNATIVES')

REGISTRY = {
    c.key: c for c in (
        HypothesisContract('INDEPENDENT_CORROBORATION', HypothesisClass.EVIDENCE_QUALITY,
            CandidateRole.PRIMARY, FINDINGS, 'EXACT_CONDITION_INDEPENDENTLY_REPRODUCED',
            ('Two provenance-independent eligible system measurements',
             'Same exact entity, periods, metric/unit/basis and values',
             'No unresolved challenge or contradictory comparable measurement'), CHECKS),
        HypothesisContract('SHARED_CORROBORATION', HypothesisClass.EVIDENCE_QUALITY,
            CandidateRole.ALTERNATIVE, FINDINGS, 'MATCHING_CORROBORATION_INCLUDES_SUBSTANTIALLY_SHARED_ANCESTRY',
            ('At least one eligible exact comparable reproduction',
             'At least one reproduction has SAME_ANCESTRY or SUBSTANTIALLY_SHARED ancestry',
             'Partial overlap remains plausible; unknown ancestry blocks support'), CHECKS),
        HypothesisContract('TEMPORAL_NULL', HypothesisClass.NULL_OR_ALTERNATIVE,
            CandidateRole.NULL, FINDINGS, 'RELATED_SAME_METRIC_EVIDENCE_HAS_NONCOMPARABLE_PERIODS',
            ('An explicit graph relationship to a same-metric eligible Fact',
             'Known periods demonstrably differ; unknown dates are not a mismatch'), CHECKS),
        HypothesisContract('MARGIN_PRICING', HypothesisClass.ECONOMIC_MECHANISM,
            CandidateRole.PRIMARY, ('MARGIN_MOVEMENT',), 'PRICING_CONTRIBUTED_TO_MARGIN_MOVEMENT',
            ('Like-for-like customer-product price history and units',
             'Retained product identity and comparable periods',
             'Qualified segmentation and comparable direct costs'), CHECKS),
        HypothesisContract('MARGIN_COST', HypothesisClass.ECONOMIC_MECHANISM,
            CandidateRole.ALTERNATIVE, ('MARGIN_MOVEMENT',), 'INPUT_COST_CONTRIBUTED_TO_MARGIN_MOVEMENT',
            ('Comparable product direct costs and supplier/input-cost movement',
             'Qualified quantities, comparability and selling-price recovery',
             'Qualified segment-to-aggregate evidence'), CHECKS),
        HypothesisContract('MARGIN_MIX', HypothesisClass.ECONOMIC_MECHANISM,
            CandidateRole.ALTERNATIVE, ('MARGIN_MOVEMENT',), 'MIX_CONTRIBUTED_TO_MARGIN_MOVEMENT',
            ('Comparable customer-product-period margins and revenue shares',
             'Qualified segmentation and portfolio coverage',
             'Separation of mix from new/lost and incomparable products'), CHECKS),
    )
}
