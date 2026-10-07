"""Exact scoped reconciliation only; MATCH never certifies semantic completeness."""
from decimal import Decimal, localcontext

from profit_doctor.reasoning.canonical.service import identity
from .contracts import EvidenceScope, Reconciliation, SourceAmount


def exact_sum(amounts):
    amounts = tuple(amounts)
    if not amounts:
        return Decimal(0)
    # Cover disparate exponents and growth from summing many values, without rounding.
    with localcontext() as context:
        context.prec = max(28, max(a.adjusted() for a in amounts) -
                           min(a.as_tuple().exponent for a in amounts) +
                           len(str(len(amounts))) + 4)
        return sum(amounts, Decimal(0))


def reconcile(scope: EvidenceScope, source_a, source_b) -> Reconciliation:
    """Pure calculation over transported records, not a production verification writer.

    Application qualification must resolve and revalidate the underlying records.
    Neither caller-constructed records nor this result establish source authority.
    """
    scope = EvidenceScope.from_json(scope.to_json())
    a, b = tuple(SourceAmount.from_json(r.to_json()) for r in source_a), tuple(
        SourceAmount.from_json(r.to_json()) for r in source_b)
    if any(r.scope.client_id != scope.client_id for r in (*a, *b)):
        raise ValueError('Reconciliation refuses cross-client records')
    # Record identity is owner-qualified: copied rows cannot silently be summed twice.
    for rows in (a, b):
        keys = [(r.record_id, tuple(r.lineage)) for r in rows]
        if len(set(keys)) != len(keys):
            raise ValueError('Duplicate source record in reconciliation')
    reasons = []
    if not a or not b:
        reasons.append('SOURCE_AMOUNT_RECORDS_NOT_PROVIDED')
    if any(r.scope != scope for r in (*a, *b)):
        reasons.append('SOURCE_SCOPE_PERIOD_CURRENCY_POPULATION_OR_DEFINITION_MISMATCH')
    valid = not reasons
    amount_a = exact_sum(r.amount for r in a) if valid else None
    amount_b = exact_sum(r.amount for r in b) if valid else None
    difference = exact_sum((amount_a, amount_b.copy_negate())) if valid else None
    state = ('MATCH' if difference == 0 else 'MISMATCH') if valid else (
        'CONFLICTED' if any(r.scope != scope for r in (*a, *b)) else 'INSUFFICIENT_EVIDENCE')
    refs_a = tuple(dict.fromkeys(ref for r in a for ref in r.lineage))
    refs_b = tuple(dict.fromkeys(ref for r in b for ref in r.lineage))
    fingerprint = [scope.to_json(), [r.to_json() for r in sorted(a, key=lambda r: r.to_json())],
                   [r.to_json() for r in sorted(b, key=lambda r: r.to_json())]]
    return Reconciliation(reconciliation_id=identity('reconciliation-2.55.1', *fingerprint),
        scope=scope, source_a=refs_a, source_b=refs_b,
        records_a=tuple(sorted(r.record_id for r in a)), records_b=tuple(sorted(r.record_id for r in b)),
        amount_a=amount_a, amount_b=amount_b, difference=difference, state=state,
        reasons=tuple(reasons) or ('EXACT_AMOUNT_AGREEMENT' if difference == 0 else 'NONZERO_CONTROL_DIFFERENCE',))
