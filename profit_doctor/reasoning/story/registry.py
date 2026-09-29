"""The reviewed SC-2.47.1 catalogue. Unknown families have no fallback."""
from dataclasses import dataclass
from enum import StrEnum


class Resolution(StrEnum):
    CONDITION_STORY = 'CONDITION_STORY'
    MECHANISM_RESOLVED_STORY = 'MECHANISM_RESOLVED_STORY'


@dataclass(frozen=True)
class StoryContract:
    key: str
    finding_type: str
    title: str
    condition: str
    measure_slot: str
    version: str = 'SC-2.47.1'
    minimum: str = 'One significant Finding and an exact independently corroborated canonical observation'
    temporal: str = 'Known identical reporting intervals and governed reporting basis for corroboration'
    scope: str = 'Exact entity, client and analytical run; no inferred segment-to-business relationship'
    contradiction: str = 'Any unresolved relevant contradiction/mitigation prevents new support'
    confidence: str = 'FULL eligible, current system evidence with complete retained ancestry; confidence dimensions remain NOT_ASSESSED'
    mechanism: str = 'UNRESOLVED; no current qualified economic-mechanism support exists'


REGISTRY = {c.key: c for c in (
    StoryContract('MARGIN_COMPRESSION', 'MARGIN_MOVEMENT', 'Contribution 0 margin compression',
        'Contribution 0 margin decreased by at least one percentage point.', 'derived'),
    StoryContract('CUSTOMER_CONCENTRATION_DEPENDENCY', 'CUSTOMER_CONCENTRATION', 'Customer revenue concentration',
        'The largest customer accounts for at least 15% of observed revenue.', 'observed'),
)}

DEFERRED = {
    'LOW_QUALITY_GROWTH': 'Qualified comparable revenue/margin reporting bases and an explicit cross-metric condition contract are required.',
    'PROFIT_TO_CASH_DISCONNECT': 'A governed profit-to-cash Finding/reconciliation with matched periods and coverage is required.',
    'COST_GROWTH_OUTPACING_ECONOMIC_OUTPUT': 'A qualified cost/output Finding with comparable windows, units and coverage is required.',
}
