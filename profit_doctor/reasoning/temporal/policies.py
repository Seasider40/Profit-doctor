"""Explicit temporal policies, independently qualified on synthetic evidence.

The numbers coincide with SIGNIFICANCE-2.44.1; their temporal semantics are
separately versioned here. They apply to adjacent complete calendar-month
observations of an unchanged verified population/definition, never broad Signal
windows. Equality is material (>=), matching the governed significance boundary.
"""
from dataclasses import dataclass
from decimal import Decimal, localcontext

from .contracts import ContractKey, Movement, MovementState


@dataclass(frozen=True)
class TemporalPolicy:
    key: ContractKey
    version: str
    metric: str
    unit: str
    movement_basis: str
    tolerance_version: str | None
    directionality: str
    minimum_trajectory: int = 3
    minimum_persistence: int = 2


POLICIES = {
    ContractKey.CONTRIBUTION_0_MARGIN_TRAJECTORY: TemporalPolicy(
        ContractKey.CONTRIBUTION_0_MARGIN_TRAJECTORY, 'C0-TEMPORAL-2.54.1',
        'contribution_0_margin', 'PERCENTAGE', 'PERCENTAGE_POINT_CHANGE',
        'C0-ADJACENT-1PP-2.54.1', 'HIGHER_IS_FAVOURABLE'),
    ContractKey.REVENUE_DESCRIPTIVE_TRAJECTORY: TemporalPolicy(
        ContractKey.REVENUE_DESCRIPTIVE_TRAJECTORY, 'REVENUE-TEMPORAL-2.54.1',
        'revenue', 'CURRENCY', 'RELATIVE_PERCENT_CHANGE',
        'REVENUE-ADJACENT-5PCT-2.54.1', 'NO_DIRECTIONAL_INTERPRETATION'),
    ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE: TemporalPolicy(
        ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE, 'AR-LIFECYCLE-2.54.1',
        'cash_trapped_receivables', 'CURRENCY', 'NOT_ASSESSED', None,
        'NO_DIRECTIONAL_INTERPRETATION'),
}


def movement(policy, left, right):
    missing = left.value is None or right.value is None
    if missing or policy.tolerance_version is None or (
            policy.key == ContractKey.REVENUE_DESCRIPTIVE_TRAJECTORY and left.value <= 0):
        return Movement(left_id=left.observation_id, right_id=right.observation_id,
            state=MovementState.INCOMPARABLE, basis=policy.movement_basis,
            reason='No qualified magnitude tolerance, missing value, or nonpositive revenue base')
    # Exact subtraction/multiplication: precision covers disparate exponents.
    numbers = (left.value, right.value)
    max_adjusted = max(v.adjusted() for v in numbers)
    min_exponent = min(v.as_tuple().exponent for v in numbers)
    with localcontext() as ctx:
        ctx.prec = max(28, max_adjusted - min_exponent + 12)
        delta = right.value - left.value
        threshold = (Decimal('1') if policy.key == ContractKey.CONTRIBUTION_0_MARGIN_TRAJECTORY
                     else left.value * Decimal('0.05'))
        state = (MovementState.WITHIN_TOLERANCE if abs(delta) < threshold else
                 MovementState.POSITIVE if delta > 0 else MovementState.NEGATIVE)
    return Movement(left_id=left.observation_id, right_id=right.observation_id,
        state=state, delta=delta, threshold=threshold, basis=policy.movement_basis,
        reason='Equality is material; below the explicit threshold is within tolerance')
