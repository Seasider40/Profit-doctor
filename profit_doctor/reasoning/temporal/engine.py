"""Explicit-window deterministic qualification; no inference from dates alone."""
from calendar import monthrange
from datetime import date, datetime, timezone

from profit_doctor.reasoning.dataset.comparability import assess_dataset_comparability
from .contracts import (ContractKey, Exclusion, Interpretation, Lifecycle,
    MovementState, Presence, TemporalInput, TemporalResult, Trajectory)
from .policies import POLICIES, movement


def _next_month(value):
    return date(value.year + (value.month == 12), value.month % 12 + 1, 1)


def _month_end(value):
    return date(value.year, value.month, monthrange(value.year, value.month)[1])


def _period_valid(observation, cash):
    period = observation.period
    if period.start is None or period.end is None:
        return False
    if cash:
        return (period.basis == 'POINT_IN_TIME' and period.nature == 'STOCK' and
                period.start == period.end == _month_end(period.start))
    return (period.basis == 'MONTHLY' and period.start.day == 1 and
            period.end == _month_end(period.start) and
            period.nature == ('RATE' if observation.metric == 'contribution_0_margin' else 'FLOW'))


def _resolved_period(rows):
    """Choose a linear, source-verified replacement chain; competing tips refuse."""
    if len(rows) == 1:
        # A lone claimed restatement has no supplied applicable predecessor.
        relation = rows[0].dataset.revision_relationship.verified_value if rows[0].dataset else None
        return (None, ()) if relation in ('RESTATEMENT', 'CORRECTION', 'SUPERSESSION', 'PARTIAL_REPLACEMENT') else (rows[0], ())
    by_contract = {o.dataset.contract_id: o for o in rows if o.dataset}
    if len(by_contract) != len(rows):
        return None, ()
    children = {}
    for o in rows:
        ds = o.dataset
        if ds.revision_target_contract_id is not None:
            if ds.revision_relationship.verified_value not in ('RESTATEMENT', 'CORRECTION', 'SUPERSESSION'):
                return None, ()
            target = by_contract.get(ds.revision_target_contract_id)
            if target is None or target.scope_key != o.scope_key:
                return None, ()
            # Replacement authority cannot conceal a changed population,
            # definition, unit, coverage or source data domain.
            c = assess_dataset_comparability(target.dataset, ds,
                assessed_at=datetime(2000, 1, 1, tzinfo=timezone.utc))
            if any(v.state not in ('MATCH', 'LIMITED_MATCH') or
                   (k != 'REVISION_RELATIONSHIP' and v.state != 'MATCH')
                   for k, v in c.dimensions.items()):
                return None, ()
            if target.observation_id in children:
                return None, ()
            children[target.observation_id] = o.observation_id
    roots = [o for o in rows if o.dataset.revision_target_contract_id is None]
    if len(roots) != 1 or roots[0].dataset.revision_relationship.verified_value != 'NEW_OBSERVATION':
        return None, ()
    ids = {o.observation_id: o for o in rows}
    cursor, seen = roots[0], set()
    while cursor.observation_id in children:
        if cursor.observation_id in seen:
            return None, ()
        seen.add(cursor.observation_id)
        cursor = ids[children[cursor.observation_id]]
    if len(seen) != len(rows) - 1:
        return None, ()
    return cursor, tuple(Exclusion(observation_id=o.observation_id,
        reason='SOURCE_VERIFIED_SAME_PERIOD_REPLACEMENT') for o in rows if o != cursor)


def _lifecycle(rows):
    states = [o.presence for o in rows]
    if not states or Presence.UNKNOWN in states:
        return Lifecycle.INDETERMINATE
    if states[-1] == Presence.ABSENT_VERIFIED:
        return Lifecycle.RESOLVED if Presence.PRESENT in states[:-1] else Lifecycle.INDETERMINATE
    # A complete resolution gap must follow a positive and precede the current
    # positive. Unknown/missing periods never reach this rule.
    prior_present = False
    resolved = False
    for state in states[:-1]:
        if state == Presence.PRESENT:
            prior_present = True
        elif prior_present and state == Presence.ABSENT_VERIFIED:
            resolved = True
    if resolved:
        return Lifecycle.RECURRENT
    if len(states) >= 2 and states[-2] == Presence.PRESENT:
        return Lifecycle.PERSISTENT
    return Lifecycle.NEW


def evaluate(value: TemporalInput) -> TemporalResult:
    """Pure evidence evaluation; application callers use the owning service.

    Synthetic inputs are explicitly marked qualification premises. Canonical
    production input cannot acquire positive temporal claims in this release.
    """
    value = TemporalInput.from_json(value.to_json())
    policy = POLICIES[value.contract_key]
    cash = value.contract_key == ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE
    window = value.window
    excluded, revisions, included, problems, comparisons = [], [], [], [], []
    grouped = {}
    for observation in value.observations:
        p = observation.period
        if p.start is None or p.end is None:
            excluded.append(Exclusion(observation_id=observation.observation_id, reason='UNKNOWN_PERIOD'))
            problems.append('UNKNOWN_PERIOD')
        elif p.end < window.start or p.start > window.end:
            excluded.append(Exclusion(observation_id=observation.observation_id, reason='OUTSIDE_REQUESTED_WINDOW'))
        elif not _period_valid(observation, cash) or p.start < window.start or p.end > window.end:
            excluded.append(Exclusion(observation_id=observation.observation_id, reason='UNQUALIFIED_PERIOD_OR_PARTIAL_WINDOW'))
            problems.append('UNQUALIFIED_PERIOD_OR_PARTIAL_WINDOW')
        else:
            grouped.setdefault((p.start, p.end), []).append(observation)
    for key, rows in sorted(grouped.items()):
        selected, replaced = _resolved_period(rows)
        if selected is None:
            problems.append('UNRESOLVED_DUPLICATE_OR_RESTATEMENT')
            excluded.extend(Exclusion(observation_id=o.observation_id,
                reason='UNRESOLVED_DUPLICATE_OR_RESTATEMENT') for o in rows)
        else:
            included.append(selected)
            revisions.extend(replaced)
            excluded.extend(replaced)
    resolved_replacements = {o.observation_id for o in included if any(
        r.observation_id in {p.observation_id for p in grouped[(o.period.start, o.period.end)]}
        for r in revisions)}
    expected = []
    if window.cadence != 'MONTHLY' or window.start.day != 1 or window.end != _month_end(window.end):
        problems.append('NO_QUALIFIED_CADENCE_OR_WINDOW_POLICY')
    else:
        cursor = window.start
        while cursor <= window.end:
            expected.append(cursor.strftime('%Y-%m'))
            cursor = _next_month(cursor)
    present_months = {o.period.start.strftime('%Y-%m') for o in included}
    gaps = tuple(month for month in expected if month not in present_months)
    if gaps:
        problems.append('MISSING_REQUIRED_MONTHS')
    if len({o.scope_key for o in included}) > 1:
        problems.append('OBSERVATION_SCOPE_MISMATCH')
    for o in included:
        if (o.metric, o.unit) != (policy.metric, policy.unit):
            problems.append('MEASUREMENT_SEMANTICS_MISMATCH')
        if not cash and (o.source_kind != 'FACT' or o.value is None or not o.lineage):
            problems.append('MISSING_CANONICAL_MEASUREMENT_EVIDENCE')
        ds = o.dataset
        if ds is None:
            problems.append('DATASET_CONTRACT_UNAVAILABLE')
            continue
        if ds.family.verified_value != ('GENERAL_LEDGER' if cash else 'SALES_TRANSACTIONS'):
            problems.append('DATASET_FAMILY_OUTSIDE_CONTRACT')
        if ds.revision_relationship.verified_value != 'NEW_OBSERVATION' and o.observation_id not in resolved_replacements:
            problems.append('NEW_OBSERVATION_OR_RESOLVED_REVISION_NOT_VERIFIED')
        if any(claim.verified_value is None or (claim.declared_value is not None and
                claim.declared_value != claim.verified_value) for claim in ds.claims()):
            problems.append('UNVERIFIED_OR_CONTRADICTED_DATASET_DIMENSION')
        coverage = ds.coverage.verified_value
        if not isinstance(coverage, dict) or coverage.get('completeness') != 'COMPLETE':
            problems.append('COMPLETE_DATASET_COVERAGE_NOT_VERIFIED')
        else:
            p = coverage.get('period', {})
            if (p.get('start'), p.get('end'), p.get('basis')) != (
                    o.period.start.isoformat(), o.period.end.isoformat(), o.period.basis.value):
                problems.append('MEASUREMENT_PERIOD_NOT_BOUND_TO_DATASET')
        if ds.unit.verified_value != ('PERCENTAGE' if policy.unit == 'PERCENTAGE' else 'MONEY') or ds.currency.verified_value != ('GBP' if policy.unit == 'CURRENCY' else 'N/A'):
            problems.append('DATASET_MEASUREMENT_UNIT_OR_CURRENCY_MISMATCH')
    for left, right in zip(included, included[1:]):
        if left.dataset and right.dataset:
            comparison = assess_dataset_comparability(left.dataset, right.dataset,
                assessed_at=datetime(2000, 1, 1, tzinfo=timezone.utc))
            comparisons.append(comparison)
            allowed_replacement = left.observation_id in resolved_replacements or right.observation_id in resolved_replacements
            for dimension, result in comparison.dimensions.items():
                if result.state != 'MATCH' and not (dimension == 'REVISION_RELATIONSHIP' and
                        result.state == 'LIMITED_MATCH' and allowed_replacement):
                    problems.append('DATASET_COMPARABILITY_'+result.state.value)
    base = dict(basis=value, policy_version=policy.version, tolerance_policy=policy.tolerance_version,
        directionality=policy.directionality, included=tuple(o.observation_id for o in included),
        excluded=tuple(excluded), revisions=tuple(revisions), gaps=gaps, comparisons=tuple(comparisons),
        limitations=('Assessment is restricted to the requested window; NEW never means never previously occurred.',
                     'No automatic downstream state, confidence uplift, seasonality or causal claim.'))
    if value.origin == 'CANONICAL':
        return TemporalResult(**base, reasons=tuple(sorted(set(problems))) + (
            'PRODUCTION_TEMPORAL_PREREQUISITES_NOT_VERIFIED',
            'No production temporal/absence verification provider is qualified in v2.54.'))
    if problems or not included:
        indeterminate = bool(gaps) or 'UNRESOLVED_DUPLICATE_OR_RESTATEMENT' in problems
        state = 'INDETERMINATE' if indeterminate else 'NOT_ASSESSED'
        return TemporalResult(**base, sequence=state,
            lifecycle=Lifecycle.INDETERMINATE if cash and indeterminate else Lifecycle.NOT_ASSESSED,
            trajectory=Trajectory.INDETERMINATE if not cash and indeterminate else Trajectory.NOT_ASSESSED,
            reasons=tuple(sorted(set(problems))) or ('NO_INCLUDED_OBSERVATIONS',))
    base.update(sequence='QUALIFIED', consecutive=True)
    if cash:
        return TemporalResult(**base, lifecycle=_lifecycle(included),
            reasons=('Presence/explicit verified absence assessed independently of magnitude.',))
    movements = tuple(movement(policy, a, b) for a, b in zip(included, included[1:]))
    trajectory = Trajectory.NOT_ASSESSED
    if any(m.state == MovementState.INCOMPARABLE for m in movements):
        trajectory = Trajectory.INDETERMINATE
    elif len(included) >= policy.minimum_trajectory:
        signs = {m.state for m in movements}
        trajectory = (Trajectory.MIXED if {'POSITIVE', 'NEGATIVE'} <= signs else
                      Trajectory.INCREASING if 'POSITIVE' in signs else
                      Trajectory.DECREASING if 'NEGATIVE' in signs else Trajectory.STABLE)
    interpretation = Interpretation.NOT_ASSESSED
    if policy.directionality == 'HIGHER_IS_FAVOURABLE':
        interpretation = {Trajectory.INCREASING: Interpretation.IMPROVING,
            Trajectory.DECREASING: Interpretation.WORSENING, Trajectory.STABLE: Interpretation.STABLE,
            Trajectory.MIXED: Interpretation.INDETERMINATE,
            Trajectory.INDETERMINATE: Interpretation.INDETERMINATE}.get(trajectory, Interpretation.NOT_ASSESSED)
    return TemporalResult(**base, movements=movements, trajectory=trajectory,
        interpretation=interpretation, reasons=('Two observations describe movement only; trajectory requires at least three.',))
