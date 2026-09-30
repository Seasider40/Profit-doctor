"""Exact matched-exposure empirical envelope; not a causal probability model."""
from decimal import Decimal, localcontext
from fractions import Fraction
from profit_doctor.reasoning.receivables.contracts import Snapshot, population
from profit_doctor.reasoning.impact.contracts import precision
from profit_doctor.reasoning.canonical.service import identity
from .contracts import Assessment, Portion

CONTRACT = {
    'id': 'MATCHED_COLLECTION_OUTCOMES_1',
    'impact_contract': 'OVERDUE_RECEIVABLES_1',
    'method': 'Observed matched-pair cash difference, identical exposure, no proportional scaling',
    'minimum_pairs': 3,
    'range': 'Minimum and maximum nonnegative treated-minus-comparison receipts',
    'central': 'Optional equal-weight empirical paired-difference mean, only if exactly representable as Decimal; never a predictive probability or midpoint',
    'limitations': (
        'Empirical scenario envelope, not a guaranteed range or statistical confidence interval.',
        'Matching is source-declared and must cover customer, exposure, ageing, terms, window and intervention.',
        'No causal attribution or future recovery guarantee; matching does not remove unobserved confounding.',
        'Three pairs is a conservative eligibility floor, not evidence of statistical representativeness.',
        'Prospective incremental cash only; not profit, realised benefit, priority or an Action Plan.',
    ),
}


def age_band(days):
    return '1_30' if days <= 30 else '31_60' if days <= 60 else '61_90' if days <= 90 else 'OVER_90'


def capture(invoice, review, candidate):
    pairs = review.cohort_pairs
    if invoice.terms is None: return None, 'Historical comparability requires governed contractual terms'
    if (review.cohort_coverage != 'COMPLETE_INCEPTION_COHORT' or not review.cohort_manifest
            or review.cohort_manifest.authority != 'SOURCE_RECORD' or not review.comparability_basis
            or review.cohort_exclusions or review.eligible_pair_count != len(pairs)):
        return None, 'Complete inception cohort and retained inclusion denominator required'
    if len(pairs) < CONTRACT['minimum_pairs']: return None, 'Insufficient comparable matched pairs'
    keys = []; differences = []
    for pair in pairs:
        a, b = pair.treated, pair.comparison
        if pair.matching_evidence.authority != 'SOURCE_RECORD': return None, 'Matching evidence is not a source record'
        for case, intervention in ((a, review.addressability), (b, 'BUSINESS_AS_USUAL')):
            keys.append((case.customer_id, case.invoice_id))
            if (case.customer_id != invoice.customer_id or case.exposure != invoice.outstanding
                    or case.terms_days != invoice.terms.days or case.currency != invoice.currency
                    or age_band(case.days_overdue_at_start) != age_band(invoice.days_overdue)
                    or case.intervention != intervention or case.evidence.authority != 'SOURCE_RECORD'
                    or (case.observed_through-case.started_on).days != candidate.horizon_days
                    or case.observed_through > candidate.assessed_on):
                return None, 'Incomparable customer/exposure/age/terms/intervention/window/authority'
        if a.started_on != b.started_on or a.observed_through != b.observed_through:
            return None, 'Matched cases require the same historical observation window'
        if a.cash_received < b.cash_received:
            return None, 'Contradictory outcome: comparison outperformed intervention; no positive-only selection'
        differences.append(a.cash_received-b.cash_received)
    if len(keys) != len(set(keys)): return None, 'Historical invoice reused within cohort'
    if any(key == (invoice.customer_id, invoice.invoice_id) for key in keys):
        return None, 'Current invoice cannot serve as its own historical outcome'
    central=None
    if review.central_method=='EMPIRICAL_PAIR_MEAN':
        mean=sum((Fraction(d) for d in differences),Fraction(0))/len(differences)
        denominator=mean.denominator
        for prime in (2,5):
            while denominator % prime == 0:denominator//=prime
        if denominator==1:
            with localcontext() as ctx:
                # Decimal digit length of the denominator underestimates the
                # expansion of powers of two. Bit length safely bounds the
                # number of terminating fractional places without rounding.
                ctx.prec=max(60,len(str(abs(mean.numerator)))+mean.denominator.bit_length()+4)
                central=Decimal(mean.numerator)/Decimal(mean.denominator)
    return (min(differences), max(differences), central), 'Complete matched outcomes; incremental empirical cash envelope'


def assess(candidate, evidence, revision):
    from profit_doctor.reasoning.impact.contracts import Qualification
    q = Qualification.from_json(candidate.source_document)
    snapshot = Snapshot.from_json(q.source_document)
    invoices = population(snapshot)['QUALIFYING_OVERDUE']
    reviews = {(r.customer_id, r.invoice_id): r for r in evidence.reviews} if evidence else {}
    keys = {(i.customer_id, i.invoice_id) for i in invoices}
    if set(reviews)-keys: raise ValueError('Collection evidence includes invoices outside qualified Impact population')
    if evidence and evidence.coverage == 'COMPLETE' and set(reviews) != keys:
        raise ValueError('Complete collection review omits qualified Impact invoices')
    portions = []
    with localcontext() as ctx:
        ctx.prec = precision([i.outstanding for i in invoices] +
            [c.cash_received for r in reviews.values() for p in r.cohort_pairs for c in (p.treated,p.comparison)])
        for i in invoices:
            r = reviews.get((i.customer_id,i.invoice_id))
            state, reason, bounds = 'UNRESOLVED', 'Collection authority and incrementality not established', None
            if r and r.authority_evidence and r.authority_evidence.observed_on == candidate.assessed_on:
                if r.addressability == 'STRATEGIC_CONSTRAINT' and r.constraint_basis:
                    state, reason = 'EXCLUDED_CONSTRAINT', r.constraint_basis
                elif r.initiative == 'ALREADY_UNDERWAY' and r.initiative_review and r.initiative_id and r.initiative_started_on and r.initiative_started_on < candidate.assessed_on:
                    state, reason = 'EXCLUDED_PRIOR_INITIATIVE', 'Existing recovery context; no newly claimed value'
                elif (r.addressability in ('ORDINARY_COLLECTION','COMMERCIAL_INTERVENTION')
                        and r.initiative == 'NO_QUALIFYING_PRIOR_INITIATIVE_EVIDENCED'
                        and r.initiative_review_complete and r.initiative_review
                        and r.initiative_review.observed_on == candidate.assessed_on
                        and r.initiative_id is None and r.initiative_started_on is None):
                    state = 'ADDRESSABLE'
                    bounds, reason = capture(i,r,candidate)
            portions.append(Portion(invoice_id=i.invoice_id,customer_id=i.customer_id,amount=i.outstanding,
                state=state,reason=reason,low=bounds[0] if bounds else None,high=bounds[1] if bounds else None,
                central=bounds[2] if bounds else None,
                sample_pairs=len(r.cohort_pairs) if r else 0))
        addressable = sum((p.amount for p in portions if p.state == 'ADDRESSABLE'),Decimal(0))
        excluded = sum((p.amount for p in portions if p.state.startswith('EXCLUDED')),Decimal(0))
        unresolved = sum((p.amount for p in portions if p.state == 'UNRESOLVED'),Decimal(0))
        low = sum((p.low for p in portions if p.low is not None),Decimal(0))
        high = sum((p.high for p in portions if p.high is not None),Decimal(0))
        contributors=[p for p in portions if p.high is not None]
        central=sum((p.central for p in contributors),Decimal(0)) if contributors and all(p.central is not None for p in contributors) else None
        qualified = high > 0
        complete_capture = all(p.state.startswith('EXCLUDED') or p.high is not None for p in portions)
        outcome = ('QUALIFIED' if complete_capture and not unresolved else 'PARTIALLY_QUALIFIED') if qualified else (
            'NOT_ADDRESSABLE' if excluded == candidate.source_amount else 'INSUFFICIENT_EVIDENCE' if evidence is None else 'UNRESOLVED')
        return Assessment(candidate=candidate,revision=revision,evidence_id=evidence.evidence_id if evidence else None,
            outcome=outcome,opportunity_id=identity('qualified-opportunity',candidate.candidate_id,revision) if qualified else None,
            portions=tuple(portions),addressable=addressable,excluded=excluded,unresolved=unresolved,
            capture_unresolved=sum((p.amount for p in portions if p.state=='ADDRESSABLE' and p.high is None),Decimal(0)),
            low=low if qualified else None,high=high if qualified else None,
            central=central if qualified else None,
            confidence={'rationale':{'method':CONTRACT['id'],'origin':candidate.origin,'calibration':'Not assessed'}},
            limitations=CONTRACT['limitations'])
