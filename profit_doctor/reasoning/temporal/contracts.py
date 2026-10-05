"""Separate observation, lifecycle, trajectory and interpretation contracts."""
from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from profit_doctor.reasoning.bridge.qualification import Period
from profit_doctor.reasoning.dataset.contracts import DatasetContract, DatasetComparability
from profit_doctor.reasoning.domain.contracts import (
    Contract, ConfidenceProfile, FinancialDecimal, Identifier, LineageReference, now,
)


class ContractKey(StrEnum):
    CONTRIBUTION_0_MARGIN_TRAJECTORY = 'CONTRIBUTION_0_MARGIN_TRAJECTORY'
    REVENUE_DESCRIPTIVE_TRAJECTORY = 'REVENUE_DESCRIPTIVE_TRAJECTORY'
    CASH_TRAPPED_RECEIVABLES_LIFECYCLE = 'CASH_TRAPPED_RECEIVABLES_LIFECYCLE'


class Presence(StrEnum):
    PRESENT = 'PRESENT'
    ABSENT_VERIFIED = 'ABSENT_VERIFIED'
    UNKNOWN = 'UNKNOWN'


class Lifecycle(StrEnum):
    NEW = 'NEW'
    PERSISTENT = 'PERSISTENT'
    RESOLVED = 'RESOLVED'
    RECURRENT = 'RECURRENT'
    INDETERMINATE = 'INDETERMINATE'
    NOT_ASSESSED = 'NOT_ASSESSED'


class Trajectory(StrEnum):
    INCREASING = 'INCREASING'
    DECREASING = 'DECREASING'
    STABLE = 'STABLE'
    MIXED = 'MIXED'
    INDETERMINATE = 'INDETERMINATE'
    NOT_ASSESSED = 'NOT_ASSESSED'


class MovementState(StrEnum):
    POSITIVE = 'POSITIVE'
    NEGATIVE = 'NEGATIVE'
    WITHIN_TOLERANCE = 'WITHIN_TOLERANCE'
    INCOMPARABLE = 'INCOMPARABLE'


class Interpretation(StrEnum):
    IMPROVING = 'IMPROVING'
    WORSENING = 'WORSENING'
    STABLE = 'STABLE'
    INDETERMINATE = 'INDETERMINATE'
    NOT_ASSESSED = 'NOT_ASSESSED'


class Cadence(StrEnum):
    MONTHLY = 'MONTHLY'
    QUARTERLY = 'QUARTERLY'
    ANNUAL = 'ANNUAL'
    UNKNOWN = 'UNKNOWN'


class Window(Contract):
    start: date
    end: date
    cadence: Cadence

    @model_validator(mode='after')
    def ordered(self):
        if self.start > self.end:
            raise ValueError('Assessment window is reversed')
        return self


class AbsenceEvidence(Contract):
    """Explicit condition absence proof; no production provider exists in v2.54.

    These are evidence assertions, not a calculation from a missing/zero Impact.
    A future provider must verify the complete reconciled population and all
    contractual/status classifications before issuing the same evidence shape.
    """
    policy: Literal['AR-ABSENCE-2.54.1'] = 'AR-ABSENCE-2.54.1'
    origin: Literal['SYNTHETIC_QUALIFICATION']
    client_id: Identifier
    as_of: date
    scope_key: str = Field(min_length=1)
    population: str = Field(min_length=1)
    currency: Literal['GBP'] = 'GBP'
    complete_population_verified: Literal[True]
    control_reconciled: Literal[True]
    contractual_and_status_review_complete: Literal[True]
    no_unresolved_classifications: Literal[True]
    condition_absence_verified: Literal[True]
    evidence: tuple[LineageReference, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def scoped(self):
        if any(ref.client_id != self.client_id for ref in self.evidence):
            raise ValueError('Absence proof cannot cross client scope')
        return self


class Observation(Contract):
    observation_id: Identifier
    client_id: Identifier
    run_id: Identifier
    source_kind: Literal['FACT', 'IMPACT', 'ABSENCE', 'UNKNOWN']
    source_id: Identifier
    source_revision: int = Field(default=1, strict=True, ge=1)
    scope_key: str = Field(min_length=1)
    period: Period = Field(default_factory=Period)
    dataset: DatasetContract | None = None
    metric: str
    unit: Literal['PERCENTAGE', 'CURRENCY']
    currency: Literal['GBP'] | None = None
    value: FinancialDecimal | None = None
    presence: Presence = Presence.UNKNOWN
    absence: AbsenceEvidence | None = None
    context_binding_id: Identifier | None = None
    lineage: tuple[LineageReference, ...] = ()
    source_snapshot: str = Field(min_length=1)

    @model_validator(mode='after')
    def scope_and_presence(self):
        if (self.unit == 'CURRENCY') != (self.currency is not None):
            raise ValueError('Currency identity belongs exactly to monetary observations')
        if any(ref.client_id != self.client_id for ref in self.lineage):
            raise ValueError('Observation lineage cannot cross client scope')
        if self.dataset and self.dataset.client_id != self.client_id:
            raise ValueError('Observation Dataset Contract is foreign')
        if self.presence == Presence.PRESENT and (self.source_kind != 'IMPACT' or
                self.metric != 'cash_trapped_receivables' or self.value is None or self.value <= 0 or not self.lineage):
            raise ValueError('Presence requires a qualified positive CASH_TRAPPED Impact premise')
        if (self.presence == Presence.ABSENT_VERIFIED) != (self.absence is not None):
            raise ValueError('Verified absence requires its explicit proof; zero/missing value is insufficient')
        if self.absence:
            proof = self.absence
            if (proof.client_id, proof.scope_key, proof.as_of, proof.currency) != (
                    self.client_id, self.scope_key, self.period.end, self.currency):
                raise ValueError('Absence evidence disagrees with observation scope/date/currency')
            if self.source_kind != 'ABSENCE' or self.metric != 'cash_trapped_receivables':
                raise ValueError('Absence proof belongs only to the named receivables condition')
            if self.dataset is None or self.dataset.population.verified_value != proof.population:
                raise ValueError('Absence proof must bind the verified Dataset Contract population')
            if not set(proof.evidence) <= set(self.lineage):
                raise ValueError('Absence evidence must remain in the observation lineage')
        return self


class TemporalInput(Contract):
    origin: Literal['CANONICAL', 'SYNTHETIC_QUALIFICATION']
    contract_key: ContractKey
    client_id: Identifier
    subject_id: Identifier
    window: Window
    observations: tuple[Observation, ...]

    @model_validator(mode='after')
    def scope(self):
        if any(o.client_id != self.client_id for o in self.observations):
            raise ValueError('Temporal input cannot cross client scope')
        if len({o.observation_id for o in self.observations}) != len(self.observations):
            raise ValueError('Duplicate observation identities are prohibited')
        if self.origin == 'CANONICAL' and any(o.absence for o in self.observations):
            raise ValueError('No production verified-absence provider is qualified in v2.54')
        return self


class Movement(Contract):
    left_id: Identifier
    right_id: Identifier
    state: MovementState
    delta: FinancialDecimal | None = None
    threshold: FinancialDecimal | None = None
    basis: Literal['PERCENTAGE_POINT_CHANGE', 'RELATIVE_PERCENT_CHANGE', 'NOT_ASSESSED']
    reason: str


class Exclusion(Contract):
    observation_id: Identifier
    reason: str


class TemporalResult(Contract):
    schema_version: Literal['TEMPORAL-2.54.1'] = 'TEMPORAL-2.54.1'
    basis: TemporalInput
    policy_version: str
    tolerance_policy: str | None = None
    directionality: Literal['HIGHER_IS_FAVOURABLE', 'NO_DIRECTIONAL_INTERPRETATION']
    included: tuple[Identifier, ...] = ()
    excluded: tuple[Exclusion, ...] = ()
    gaps: tuple[str, ...] = ()
    revisions: tuple[Exclusion, ...] = ()
    comparisons: tuple[DatasetComparability, ...] = ()
    sequence: Literal['QUALIFIED', 'INDETERMINATE', 'NOT_ASSESSED'] = 'NOT_ASSESSED'
    consecutive: bool = False
    lifecycle: Lifecycle = Lifecycle.NOT_ASSESSED
    trajectory: Trajectory = Trajectory.NOT_ASSESSED
    interpretation: Interpretation = Interpretation.NOT_ASSESSED
    movements: tuple[Movement, ...] = ()
    confidence: ConfidenceProfile = Field(default_factory=ConfidenceProfile)
    limitations: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


class Assessment(Contract):
    assessment_id: Identifier
    series_id: Identifier
    subject_id: Identifier
    client_id: Identifier
    run_id: Identifier
    revision: int = Field(strict=True, ge=1)
    supersedes: Identifier | None = None
    created_at: AwareDatetime = Field(default_factory=now)
    result: TemporalResult

    @model_validator(mode='after')
    def envelope(self):
        if (self.subject_id, self.client_id) != (self.result.basis.subject_id, self.result.basis.client_id):
            raise ValueError('Temporal assessment and evidence envelope disagree')
        if (self.revision == 1) != (self.supersedes is None):
            raise ValueError('Every later assessment must retain its explicit predecessor')
        return self
