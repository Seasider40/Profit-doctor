"""Production contract: dated unconstrained overdue stocks, never recoverable value."""
from decimal import Decimal, localcontext
from sqlalchemy import select
from profit_doctor.persistence import reasoning_schema as tables
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import EconomicEffect, EffectOverlap
from profit_doctor.reasoning.receivables.contracts import Snapshot, population
from .contracts import ReceivablesAmount, ReceivablesImpact, precision


def qualify(document, candidate_id, revision):
    s = Snapshot.from_json(document)
    if s.control_amount is not None and s.total > s.control_amount:
        return dict(outcome='HELD',blockers=('AR_POPULATION_EXCEEDS_CONTROL',),missing=('Reconciled population boundary',))
    if s.coverage == 'COMPLETE' and (s.control_amount is None or s.reconciliation_difference != 0):
        return dict(outcome='HELD',blockers=('COMPLETE_AR_RECONCILIATION_NOT_ESTABLISHED',),
                    missing=('Complete AR control reconciliation',))
    groups = population(s)
    with localcontext() as ctx:
        ctx.prec = precision(i.outstanding for i in s.invoices)
        amounts = {k:sum((i.outstanding for i in v),Decimal(0)) for k,v in groups.items()}
        amount = amounts.get('QUALIFYING_OVERDUE',Decimal(0))
        within = amounts.get('WITHIN_TERMS',Decimal(0))
        excluded = s.total-within-amount
    if amount <= 0:
        return dict(outcome='INSUFFICIENT_EVIDENCE' if any(k in groups for k in ('UNKNOWN','DUE_DATE_UNKNOWN','STATUS_UNVERIFIED')) else 'NOT_APPLICABLE',
                    blockers=('NO_QUALIFYING_UNCONSTRAINED_OVERDUE',),missing=())
    # A population effect is independent of the report/run describing it. Unknown
    # relationships between different populations remain blocking in aggregation.
    effect = identity('overdue-ar-effect',s.origin,s.client_id,s.ledger_id,s.as_of.isoformat(),
                      sorted((i.customer_id,i.invoice_id) for i in groups['QUALIFYING_OVERDUE']))
    i = ReceivablesImpact(impact_id=identity('qualified-impact',candidate_id,revision,document),
        candidate_id=candidate_id,revision=revision,client_id=s.client_id,run_id=s.run_id,effect_id=effect,
        amount=ReceivablesAmount(value=amount,as_of=s.as_of,scope=s.scope,coverage=s.coverage,
            observed=s.total,required_position=within,excluded_constrained=excluded,
            snapshot_document=document,qualification_origin=s.origin),
        materiality={'absolute_economic_magnitude':amount,'cash_impact':amount,'currency':'GBP',
                    'rationale':{'evidence_origin':s.origin}},
        confidence={'rationale':{'evidence_origin':s.origin,'basis':'Contractual dates and dated source status; collection probability not assessed'}},
        limitations=('Cash tied up in contractually overdue receivables without evidenced blocking statuses at the reporting date.',
            'No recoverability, collection guarantee or Opportunity value established.',
            'Only the supplied population; no extrapolation. Origin: '+s.origin))
    return dict(outcome='QUALIFIED_IMPACT',impact=i,effect_ids=(effect,),missing=(),blockers=(),
        available=('Retained invoice balances, contractual dates, current structured status and CMC bindings',),
        required_counterfactual='Contractual settlement by due date; current within-terms position retained separately from constrained overdue exclusions')


def link_aggregate(foundation, impact):
    s = Snapshot.from_json(impact.amount.snapshot_document)
    parent_id = identity('aggregate-ar-stock',s.origin,s.client_id,s.ledger_id,s.as_of.isoformat(),s.currency)
    if foundation.session.scalar(select(tables.economic_effect.c.effect_id).where(tables.economic_effect.c.effect_id == parent_id)) is None:
        foundation.create_effect(EconomicEffect(effect_id=parent_id,client_id=s.client_id,
            period_from=s.as_of,period_to=s.as_of))
    pair = '|'.join(sorted((parent_id,impact.effect_id)))
    old = foundation.session.scalar(select(tables.effect_overlap.c.overlap_id).where(
        tables.effect_overlap.c.client_id == s.client_id, tables.effect_overlap.c.pair_key == pair))
    if old:
        existing = foundation.get_effect_overlap(old)
        if (existing.source_effect_id,existing.target_effect_id,existing.overlap_type) != (parent_id,impact.effect_id,'PARENT_CHILD'):
            raise ValueError('Aggregate AR relationship conflicts with retained ownership')
        return
    foundation.relate_effects(EffectOverlap(client_id=s.client_id,run_id=s.run_id,source_effect_id=parent_id,
        target_effect_id=impact.effect_id,overlap_type='PARENT_CHILD',
        metadata={'basis':'Invoice overdue population belongs to this aggregate AR stock; not independent working-capital value',
                  'ledger_id':s.ledger_id,'as_of':s.as_of.isoformat(),'origin':s.origin}))
