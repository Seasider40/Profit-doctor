"""Explainable dimensions and immutable assessments, independent of decisions."""
from typing import Literal
from pydantic import AwareDatetime, Field, model_validator
from profit_doctor.reasoning.domain.contracts import (
    Actor, Contract, ConfidenceProfile, MaterialityProfile, Identifier, FinancialDecimal, now,
)

Level = Literal['NOT_ASSESSED', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
Classification = Literal['INSUFFICIENT_EVIDENCE', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
Choice = Literal['INVESTIGATE', 'ACCEPT', 'REJECT']


class Dimension(Contract):
    state: str = 'NOT_ASSESSED'
    evidence: tuple[str, ...] = ()
    reason: str = Field(min_length=1)

    @model_validator(mode='after')
    def supported(self):
        if self.state != 'NOT_ASSESSED' and (not self.evidence or any(not x.strip() for x in self.evidence)):
            raise ValueError('Assessed dimension requires explicit evidence references')
        if not self.reason.strip():
            raise ValueError('Nonblank reason required')
        return self


class EconomicBasis(Contract):
    kind: Literal['UNQUANTIFIED', 'OBSERVED_MEASUREMENTS', 'INDICATIVE_CAPTURE_RANGE',
                  'RECURRING_LEAKAGE', 'HISTORICAL_COST', 'EXPOSURE']
    amount: FinancialDecimal | None = None
    low: FinancialDecimal | None = None
    high: FinancialDecimal | None = None
    central: FinancialDecimal | None = None
    currency: Literal['GBP'] | None = None
    dimension: Literal['CASH', 'PROFIT_PNL', 'EXPOSURE', 'MEASUREMENT', 'UNKNOWN'] = 'UNKNOWN'
    horizon_days: int | None = Field(default=None, strict=True, gt=0)
    evidence: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    @model_validator(mode='after')
    def exact(self):
        values = (self.amount, self.low, self.high, self.central)
        if any(v is not None for v in values) and (self.currency is None or not self.evidence):
            raise ValueError('Financial values require currency and evidence')
        if (self.low is None) != (self.high is None) or self.low is not None and self.low > self.high:
            raise ValueError('A complete ordered range is required')
        if self.central is not None and (self.low is None or not self.low <= self.central <= self.high):
            raise ValueError('Central must lie inside an explicit range')
        if self.amount is not None and self.low is not None:
            raise ValueError('Point and range are separate economic representations')
        if self.kind in ('UNQUANTIFIED', 'OBSERVED_MEASUREMENTS') and any(v is not None for v in values):
            raise ValueError('Measurements cannot be promoted to an economic valuation')
        return self


def unknown(reason):
    return Dimension(reason=reason)


class PriorityBasis(Contract):
    schema_version: Literal['PD-2.51.1'] = 'PD-2.51.1'
    origin: Literal['CANONICAL', 'SYNTHETIC_QUALIFICATION']
    materiality: Dimension = Field(default_factory=lambda: unknown('No qualified relative materiality assessment'))
    evidence_strength: Dimension = Field(default_factory=lambda: unknown('No qualified confidence calibration'))
    urgency: Dimension = Field(default_factory=lambda: unknown('No qualified timing-consequence evidence'))
    controllability: Dimension = Field(default_factory=lambda: unknown('No qualified management-control assessment'))
    persistence: Dimension = Field(default_factory=lambda: unknown('No qualified recurrence assessment'))
    economic: EconomicBasis
    confidence: ConfidenceProfile = Field(default_factory=ConfidenceProfile)
    materiality_profile: MaterialityProfile = Field(default_factory=MaterialityProfile)
    source_snapshot: str = Field(min_length=1)
    limitations: tuple[str, ...] = ()

    @model_validator(mode='after')
    def vocabulary(self):
        allowed = {
            'materiality': {'NOT_ASSESSED', 'LOW', 'MEDIUM', 'HIGH'},
            'evidence_strength': {'NOT_ASSESSED', 'WEAK', 'CONFLICTED', 'STRONG'},
            'urgency': {'NOT_ASSESSED', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'},
            'controllability': {'NOT_ASSESSED', 'DIRECT', 'PARTIAL', 'EXTERNAL'},
            'persistence': {'NOT_ASSESSED', 'RECURRING', 'STRUCTURAL', 'WORSENING', 'INTERMITTENT', 'ISOLATED', 'HISTORICAL_ONLY'},
        }
        for name, vocabulary in allowed.items():
            if getattr(self, name).state not in vocabulary:
                raise ValueError('Invalid '+name+' vocabulary')
        return self


class PriorityResult(Contract):
    policy_version: Literal['ATTENTION-2.51.1'] = 'ATTENTION-2.51.1'
    classification: Classification
    rule: str
    reasons: tuple[str, ...]
    gaps: tuple[str, ...]
    basis: PriorityBasis


class Assessment(Contract):
    subject_id: Identifier
    client_id: Identifier
    run_id: Identifier
    revision: int = Field(strict=True, ge=1)
    created_at: AwareDatetime = Field(default_factory=now)
    result: PriorityResult


class AdviserRequest(Contract):
    request_id: Identifier
    choice: Choice
    actor: Actor
    rationale: str = Field(min_length=1)
    provenance: str = Field(min_length=1)
    questions: tuple[str, ...] = ()
    required_evidence: tuple[str, ...] = ()

    @model_validator(mode='after')
    def human(self):
        if (self.actor.actor_type != 'HUMAN' or self.actor.source_authority != 'HUMAN_FD_JUDGEMENT'
                or not self.actor.actor_id or not self.actor.actor_id.strip()):
            raise ValueError('An identified human adviser is required')
        if not self.rationale.strip() or not self.provenance.strip():
            raise ValueError('Rationale and decision provenance must be nonblank')
        if any(not s.strip() for s in (*self.questions, *self.required_evidence)):
            raise ValueError('Investigation details must be nonblank')
        if self.choice == 'INVESTIGATE' and (not self.questions or not self.required_evidence):
            raise ValueError('Investigation requires questions and required evidence')
        return self


class Decision(Contract):
    subject_id: Identifier
    client_id: Identifier
    revision: int = Field(strict=True, ge=1)
    assessment_revision: int = Field(strict=True, ge=1)
    created_at: AwareDatetime = Field(default_factory=now)
    request: AdviserRequest
