"""Governed evidence and prospective cash contracts, never recovery percentages."""
from datetime import date, timedelta
from typing import Literal
from pydantic import Field, model_validator
from profit_doctor.reasoning.domain.contracts import Contract, Identifier, FinancialDecimal, ConfidenceProfile
from profit_doctor.reasoning.canonical.service import identity


class Evidence(Contract):
    reference: str = Field(min_length=1)
    authority: Literal['SOURCE_RECORD', 'MANAGEMENT_ASSERTION', 'HUMAN_FD_JUDGEMENT']
    observed_on: date


class Contact(Contract):
    evidence: Evidence
    outcome: Literal['CONTACTED', 'ACKNOWLEDGED', 'PROMISE_RECEIVED', 'NO_RESPONSE']
    promised_on: date | None = None
    promised_amount: FinancialDecimal | None = Field(default=None, ge=0)


class HistoricalCase(Contract):
    case_id: Identifier
    customer_id: Identifier
    invoice_id: Identifier
    currency: Literal['GBP'] = 'GBP'
    exposure: FinancialDecimal = Field(gt=0)
    days_overdue_at_start: int = Field(strict=True, ge=1)
    terms_days: int = Field(strict=True, ge=0)
    status: Literal['ORDINARY_UNCONSTRAINED']
    intervention: Literal['ORDINARY_COLLECTION', 'COMMERCIAL_INTERVENTION', 'BUSINESS_AS_USUAL']
    started_on: date
    observed_through: date
    cash_received: FinancialDecimal = Field(ge=0)
    invoice_date: date | None = None
    settled_on: date | None = None
    days_to_pay: int | None = Field(default=None, strict=True, ge=0)
    promise_kept: bool | None = None
    evidence: Evidence

    @model_validator(mode='after')
    def valid_outcome(self):
        if self.observed_through <= self.started_on or self.cash_received > self.exposure:
            raise ValueError('Invalid historical observation window or receipt')
        if self.evidence.observed_on < self.observed_through:
            raise ValueError('Outcome evidence predates observation close')
        if self.days_to_pay is not None and (self.invoice_date is None or self.settled_on is None
                or (self.settled_on-self.invoice_date).days != self.days_to_pay):
            raise ValueError('Historical days-to-pay requires consistent original invoice and settlement dates')
        if self.settled_on and (not self.invoice_date or self.settled_on < self.invoice_date or self.settled_on > self.observed_through):
            raise ValueError('Settlement outside evidenced history')
        return self


class MatchedPair(Contract):
    treated: HistoricalCase
    comparison: HistoricalCase
    matching_evidence: Evidence


class CollectionReview(Contract):
    invoice_id: Identifier
    customer_id: Identifier
    addressability: Literal['ORDINARY_COLLECTION', 'COMMERCIAL_INTERVENTION', 'STRATEGIC_CONSTRAINT', 'UNKNOWN'] = 'UNKNOWN'
    authority_evidence: Evidence | None = None
    constraint_basis: str | None = None
    management_approved_flexibility: bool | None = None
    contacts: tuple[Contact, ...] = ()
    initiative: Literal['NO_QUALIFYING_PRIOR_INITIATIVE_EVIDENCED', 'ALREADY_UNDERWAY', 'UNKNOWN'] = 'UNKNOWN'
    initiative_review: Evidence | None = None
    initiative_review_complete: bool = False
    initiative_id: Identifier | None = None
    initiative_started_on: date | None = None
    cohort_pairs: tuple[MatchedPair, ...] = ()
    cohort_coverage: Literal['COMPLETE_INCEPTION_COHORT', 'SELECTED', 'UNKNOWN'] = 'UNKNOWN'
    cohort_manifest: Evidence | None = None
    eligible_pair_count: int | None = Field(default=None, strict=True, ge=0)
    cohort_exclusions: tuple[str, ...] = ()
    comparability_basis: str | None = None
    central_method: Literal['NOT_ASSESSED', 'EMPIRICAL_PAIR_MEAN'] = 'NOT_ASSESSED'


class CollectionEvidence(Contract):
    schema_version: Literal['CE-2.50.1'] = 'CE-2.50.1'
    client_id: Identifier
    run_id: Identifier
    impact_id: Identifier
    assessed_on: date
    horizon_days: int = Field(strict=True, ge=1, le=3660)
    origin: Literal['REAL_SOURCE', 'BLIND_QUALIFICATION']
    coverage: Literal['COMPLETE', 'PARTIAL']
    source_version: str = Field(min_length=1)
    dataset_version_id: Identifier
    reviews: tuple[CollectionReview, ...] = ()

    @property
    def evidence_id(self): return identity('collection-evidence', self.to_json())

    @model_validator(mode='after')
    def unique_reviews(self):
        keys = [(r.customer_id, r.invoice_id) for r in self.reviews]
        if len(keys) != len(set(keys)): raise ValueError('Duplicate collection review')
        for r in self.reviews:
            evidence = [r.authority_evidence, r.initiative_review, r.cohort_manifest]
            evidence += [c.evidence for c in r.contacts]
            for pair in r.cohort_pairs:
                evidence += [pair.matching_evidence, pair.treated.evidence, pair.comparison.evidence]
            if any(e and e.observed_on > self.assessed_on for e in evidence):
                raise ValueError('Future evidence cannot enter assessment')
            if r.initiative_started_on and r.initiative_started_on > self.assessed_on:
                raise ValueError('Future initiative is not already underway')
        return self


class Candidate(Contract):
    candidate_id: Identifier
    client_id: Identifier
    run_id: Identifier
    impact_id: Identifier
    effect_id: Identifier
    source_candidate_id: Identifier
    source_revision: int = Field(strict=True, ge=1)
    mechanism: Literal['RECEIVABLES_COLLECTION_ACCELERATION'] = 'RECEIVABLES_COLLECTION_ACCELERATION'
    contract: Literal['MATCHED_COLLECTION_OUTCOMES_1'] = 'MATCHED_COLLECTION_OUTCOMES_1'
    assessed_on: date
    horizon_days: int = Field(strict=True, ge=1, le=3660)
    origin: Literal['REAL_SOURCE', 'BLIND_QUALIFICATION']
    scope: str
    source_amount: FinancialDecimal = Field(gt=0)
    source_document: str

    @property
    def horizon_end(self): return self.assessed_on + timedelta(days=self.horizon_days)


class Portion(Contract):
    invoice_id: Identifier
    customer_id: Identifier
    amount: FinancialDecimal = Field(ge=0)
    state: Literal['ADDRESSABLE', 'EXCLUDED_CONSTRAINT', 'EXCLUDED_PRIOR_INITIATIVE', 'UNRESOLVED']
    reason: str
    low: FinancialDecimal | None = Field(default=None, ge=0)
    high: FinancialDecimal | None = Field(default=None, ge=0)
    central: FinancialDecimal | None = Field(default=None, ge=0)
    sample_pairs: int = Field(default=0, strict=True, ge=0)

    @model_validator(mode='after')
    def bounds(self):
        if (self.low is None) != (self.high is None): raise ValueError('Both empirical bounds required')
        if self.low is not None and (self.state != 'ADDRESSABLE' or not 0 <= self.low <= self.high <= self.amount):
            raise ValueError('Bounds outside addressable population')
        if self.central is not None and (self.low is None or not self.low <= self.central <= self.high):
            raise ValueError('Central estimate must remain inside empirical range')
        return self


class Assessment(Contract):
    schema_version: Literal['OQ-2.50.1'] = 'OQ-2.50.1'
    candidate: Candidate
    revision: int = Field(strict=True, ge=1)
    evidence_id: Identifier | None
    outcome: Literal['QUALIFIED', 'PARTIALLY_QUALIFIED', 'UNRESOLVED', 'NOT_ADDRESSABLE', 'REJECTED', 'INSUFFICIENT_EVIDENCE']
    opportunity_id: Identifier | None = None
    portions: tuple[Portion, ...]
    addressable: FinancialDecimal
    excluded: FinancialDecimal
    unresolved: FinancialDecimal
    capture_unresolved: FinancialDecimal
    low: FinancialDecimal | None = None
    high: FinancialDecimal | None = None
    central: FinancialDecimal | None = None
    dimension: Literal['CASH'] = 'CASH'
    currency: Literal['GBP'] = 'GBP'
    confidence: ConfidenceProfile = Field(default_factory=ConfidenceProfile)
    limitations: tuple[str, ...]

    @model_validator(mode='after')
    def partition(self):
        from decimal import localcontext
        from profit_doctor.reasoning.impact.contracts import precision
        with localcontext() as ctx:
            ctx.prec = precision([v for p in self.portions for v in (p.amount,p.low,p.high,p.central) if v is not None])
            keys=[(p.customer_id,p.invoice_id) for p in self.portions]
            if len(keys)!=len(set(keys)):raise ValueError('Duplicate Opportunity population')
            if self.addressable + self.excluded + self.unresolved != self.candidate.source_amount:
                raise ValueError('Opportunity partition must preserve source Impact')
            amounts = {'ADDRESSABLE': self.addressable, 'UNRESOLVED': self.unresolved}
            for state, amount in amounts.items():
                if sum(p.amount for p in self.portions if p.state == state) != amount:
                    raise ValueError('Partition disagrees with invoice evidence')
            if sum(p.amount for p in self.portions if p.state.startswith('EXCLUDED')) != self.excluded:
                raise ValueError('Exclusion mismatch')
            if self.capture_unresolved != sum(p.amount for p in self.portions if p.state == 'ADDRESSABLE' and p.high is None):
                raise ValueError('Unresolved capture must remain explicit within addressable population')
            positive = self.outcome in ('QUALIFIED', 'PARTIALLY_QUALIFIED')
            if self.outcome=='QUALIFIED' and (self.unresolved or self.capture_unresolved):
                raise ValueError('Incomplete qualification must remain partial')
            if positive != (self.opportunity_id is not None): raise ValueError('Only qualified portions have Opportunity identity')
            if positive:
                if self.low is None or self.high is None or not 0 <= self.low <= self.high <= self.addressable or self.high <= 0:
                    raise ValueError('Invalid prospective capture range')
                if self.low != sum(p.low for p in self.portions if p.low is not None) or self.high != sum(p.high for p in self.portions if p.high is not None):
                    raise ValueError('Range disagrees with qualified portions')
                contributors=[p for p in self.portions if p.high is not None]
                expected_central=sum(p.central for p in contributors) if all(p.central is not None for p in contributors) else None
                if self.central != expected_central:raise ValueError('Central must derive from every contributing cohort, never a midpoint')
            elif self.low is not None or self.high is not None:
                raise ValueError('Unqualified assessment cannot carry capture value')
            elif self.central is not None:raise ValueError('Unqualified central value')
        return self
