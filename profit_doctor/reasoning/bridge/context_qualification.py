"""BIQ-2.48.2 consumes authoritative contexts; never overwrites their semantics.

The original BIQ-2.48.1 descriptor policy remains unchanged/readable. This policy
supports calendar totals without daily normalisation and point-in-time stocks.
It establishes endpoint comparability only, not a Bridge or causal decomposition.
"""
from calendar import monthrange
from typing import Literal

from profit_doctor.reasoning.domain.contracts import Contract, Identifier
from profit_doctor.reasoning.canonical.service import identity
from .qualification import BridgeFamily, Outcome


class ContextQualification(Contract):
    contract_version: Literal['BIQ-2.48.2'] = 'BIQ-2.48.2'
    family: BridgeFamily
    opening_binding_id: Identifier
    closing_binding_id: Identifier
    opening_context_id: Identifier
    closing_context_id: Identifier
    outcome: Outcome
    gaps: tuple[str, ...]
    version_basis: Literal['SAME_IMMUTABLE_DATASET_SNAPSHOT', 'UNKNOWN']

    @property
    def assessment_id(self):
        return identity('context-qualification', self.to_json())


METRICS = {
    BridgeFamily.REVENUE_BRIDGE: {'financial_revenue'},
    BridgeFamily.MARGIN_OR_PROFIT_BRIDGE: {'financial_gross_profit', 'financial_ebitda'},
    # Individual stock endpoints only. A composite working-capital Bridge still
    # requires all selected components and an explicit coverage/sign contract.
    BridgeFamily.WORKING_CAPITAL_BRIDGE: {'bs_accounts_receivable', 'bs_inventory', 'bs_accounts_payable'},
}


def qualify_contexts(service, family, opening_binding_id, closing_binding_id):
    family = BridgeFamily(family)
    resolved = [service.resolve_binding(key) for key in (opening_binding_id, closing_binding_id)]
    contexts = [context for binding, context in resolved]
    a, b = contexts
    mismatch, missing, partial = [], [], []
    if family not in METRICS or a.metric not in METRICS[family] or b.metric not in METRICS[family]:
        missing.append('FAMILY_MEASURE_CONTRACT_UNQUALIFIED')
    if (a.client_id, a.metric, a.unit, a.currency, a.entity_type, a.entity_id, a.segment_scope) != (
            b.client_id, b.metric, b.unit, b.currency, b.entity_type, b.entity_id, b.segment_scope):
        mismatch.append('MEASUREMENT_SCOPE_OR_UNIT_MISMATCH')
    if a.economic_basis != b.economic_basis:
        mismatch.append('ECONOMIC_BASIS_MISMATCH')
    if a.coverage_basis is not None and b.coverage_basis is not None and a.coverage_basis != b.coverage_basis:
        mismatch.append('COVERAGE_BASIS_MISMATCH')
    for ctx in contexts:
        if ctx.currency is None or ctx.economic_basis is None or ctx.segment_scope is None:
            missing.append('REQUIRED_MEASUREMENT_CONTEXT_UNKNOWN')
        if ctx.coverage == 'UNKNOWN' or not ctx.coverage_basis:
            missing.append('COVERAGE_UNKNOWN')
        elif ctx.coverage == 'PARTIAL':
            partial.append('PARTIAL_COVERAGE')
        if ctx.limitations:
            partial.append('SOURCE_LIMITATIONS')
        p = ctx.period
        if p.start is None or p.end is None or p.convention is None:
            missing.append('PERIOD_CONTEXT_UNKNOWN')
        elif p.nature == 'STOCK':
            if p.basis != 'POINT_IN_TIME' or p.start != p.end:
                mismatch.append('STOCK_PERIOD_MISMATCH')
        elif p.nature == 'FLOW' and p.basis in ('MONTHLY', 'QUARTERLY', 'ANNUAL'):
            months = {'MONTHLY': 1, 'QUARTERLY': 3, 'ANNUAL': 12}[p.basis]
            if (p.start.day != 1 or (p.start.month - 1) % months or
                    p.end.year != p.start.year or p.end.month != p.start.month + months - 1 or
                    p.end.day != monthrange(p.end.year, p.end.month)[1]):
                mismatch.append('CALENDAR_INTERVAL_MISMATCH')
        else:
            missing.append('REPORTING_POLICY_UNQUALIFIED')
    if (a.period.basis, a.period.convention, a.period.nature) != (b.period.basis, b.period.convention, b.period.nature):
        mismatch.append('REPORTING_BASIS_MISMATCH')
    if a.period.end and b.period.start and a.period.end >= b.period.start:
        mismatch.append('PERIOD_CHRONOLOGY_MISMATCH')
    same_snapshot = (a.source_version, a.source_revision_id, a.revision_state) == (
        b.source_version, b.source_revision_id, b.revision_state)
    if not same_snapshot:
        missing.append('CROSS_VERSION_COMPATIBILITY_UNQUALIFIED')
    outcome = (Outcome.INCOMPARABLE if mismatch else Outcome.INSUFFICIENT_EVIDENCE if missing
               else Outcome.PARTIALLY_QUALIFIED if partial else Outcome.QUALIFIED)
    return ContextQualification(family=family, opening_binding_id=opening_binding_id,
        closing_binding_id=closing_binding_id, opening_context_id=a.context_id, closing_context_id=b.context_id,
        outcome=outcome, gaps=tuple(sorted(set(mismatch + missing + partial))),
        version_basis='SAME_IMMUTABLE_DATASET_SNAPSHOT' if same_snapshot else 'UNKNOWN')
