"""Eight explicit requirements; none has a production positive writer in v2.49."""
from dataclasses import dataclass
from profit_doctor.reasoning.domain.vocabulary import ImpactType


@dataclass(frozen=True)
class ImpactContract:
    category: ImpactType
    required_evidence: str
    counterfactual: str
    period: str
    version: str = 'IC-2.49.1'
    production_qualified: bool = False
    overlap: str = 'Unknown until governed; distinct analytical paths do not establish independence'


REGISTRY = {c.category: c for c in (
    ImpactContract(ImpactType.OBSERVED_LOSS, 'Evidence of actual value lost, not movement or residual', 'Defensible loss comparison where needed', 'Observed loss interval'),
    ImpactContract(ImpactType.RUN_RATE_LEAKAGE, 'Underperformance, persistence and seasonality qualification', 'Governed expected performance and periodisation; never one month times twelve', 'Observation and run-rate windows separately'),
    ImpactContract(ImpactType.CASH_TRAPPED, 'Governed excess/trapped balance relative to required position', 'Defensible operational, contractual or comparable required balance; stock growth is insufficient', 'Matched as-of stock and required-position date'),
    ImpactContract(ImpactType.AVOIDABLE_COST, 'Evidence of avoidability, not merely increased cost', 'Supported alternative cost state', 'Comparable cost interval'),
    ImpactContract(ImpactType.CAPITAL_AT_RISK, 'Identified capital and supported risk, not concentration alone', 'Supported exposure basis; not realised loss', 'Capital as-of and risk horizon'),
    ImpactContract(ImpactType.FUTURE_EXPOSURE, 'Governed prospective scenario and downside evidence', 'Explicit supported alternative scenario', 'Future horizon'),
    ImpactContract(ImpactType.VALUE_CREATION_POTENTIAL, 'Supported economic upside, not revenue growth', 'Defensible alternative economic state', 'Explicit future horizon'),
    ImpactContract(ImpactType.REALISED_BENEFIT, 'Observed improvement with qualified benefit attribution', 'Qualified attribution baseline; later integration deferred', 'Realisation window'),
)}

# The generic identity/Bridge registry above remains insufficient. Positive
# authority is confined to this versioned, source-specific production provider.
PROVIDER_CONTRACTS = {
    'OVERDUE_RECEIVABLES_1': ImpactContract(ImpactType.CASH_TRAPPED,
        'Retained invoice snapshot, contractual dates, current unconstrained source reviews and scoped CMC bindings',
        'Contractual settlement by due date; within-terms position and blocked overdue retained separately',
        'Single reporting-date outstanding stock', production_qualified=True),
}
