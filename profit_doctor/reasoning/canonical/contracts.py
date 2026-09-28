"""Structured propositions and assessments, extending the v2.43 identity boundary."""
from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from profit_doctor.reasoning.domain.contracts import (
    Contract, ConfidenceProfile, FinancialDecimal, Identifier, LineageReference,
    MaterialityProfile, ReferenceId,
)
from .registry import MAPPING_VERSIONS, ZERO_DENOMINATOR_GUARDS, Unit


class FactState(StrEnum):
    OBSERVED = 'OBSERVED'
    SUPERSEDED = 'SUPERSEDED'
    INVALIDATED = 'INVALIDATED'


class AssessmentOutcome(StrEnum):
    FINDING_CREATED = 'FINDING_CREATED'
    NOT_SIGNIFICANT = 'NOT_SIGNIFICANT'
    INSUFFICIENT_EVIDENCE = 'INSUFFICIENT_EVIDENCE'
    HELD_LIMITED = 'HELD_LIMITED'


class Measurement(Contract):
    metric: str = Field(min_length=1)
    value: FinancialDecimal
    unit: Unit
    currency: Literal['GBP'] | None = None
    basis: str = Field(min_length=1)

    @model_validator(mode='after')
    def units(self):
        money = self.unit in (Unit.CURRENCY, Unit.CURRENCY_PER_FTE, Unit.CURRENCY_PER_UNIT)
        if money != (self.currency is not None):
            raise ValueError('Currency identity belongs exactly to monetary measurements')
        if self.unit == Unit.COUNT and (self.value < 0 or self.value != self.value.to_integral_value()):
            raise ValueError('Counts are nonnegative integers')
        return self


class ReportingScope(Contract):
    entity_type: str | None = None
    # Frozen dimension keys (e.g. department names) may contain spaces. These
    # are source scope labels, not new UUID/lineage endpoint identities.
    entity_id: str | None = Field(default=None, min_length=1, max_length=128)
    period_from: date | None = None
    period_to: date | None = None
    period_basis: str

    @model_validator(mode='after')
    def valid_scope(self):
        if (self.entity_type is None) != (self.entity_id is None):
            raise ValueError('Entity type and identity must be retained together')
        if self.entity_id is not None and (not self.entity_id.strip() or any(ord(c) < 32 for c in self.entity_id)):
            raise ValueError('Scope labels must be nonblank and free of control characters')
        if self.period_from and self.period_to and self.period_from > self.period_to:
            raise ValueError('Reversed reporting period')
        return self


class CanonicalFact(Contract):
    schema_version: Literal['CFF-2.44'] = 'CFF-2.44'
    object_id: Identifier
    client_id: Identifier
    run_id: Identifier
    source_signal_id: ReferenceId
    source_digest: str = Field(pattern='^[a-f0-9]{64}$')
    diagnostic: str
    signal_type: str
    mapping_version: str
    family: Literal['MEASUREMENT', 'MEASUREMENT_SET', 'COMPARATIVE', 'RECONCILIATION']
    scope: ReportingScope
    observed: Measurement | None = None
    comparison: Measurement | None = None
    derived: Measurement | None = None
    source_authority: Literal['SYSTEM_DERIVED'] = 'SYSTEM_DERIVED'
    eligibility: str
    limitations: tuple[str, ...] = ()
    lineage: tuple[LineageReference, ...]
    confidence: ConfidenceProfile = Field(default_factory=ConfidenceProfile)
    state: FactState = FactState.OBSERVED
    revision: int = Field(default=1, strict=True, ge=1)
    supersedes: Identifier | None = None

    @model_validator(mode='after')
    def typed_semantics(self):
        mapping = MAPPING_VERSIONS.get((self.diagnostic, self.signal_type, self.mapping_version))
        if mapping is None or mapping.version != self.mapping_version or mapping.family != self.family:
            raise ValueError('A retained, known mapping version is required')
        if self.scope.entity_type != mapping.entity_type or self.scope.period_basis != mapping.period_basis:
            raise ValueError('Reporting scope disagrees with governed mapping')
        for spec, value in zip(mapping.slots, (self.observed, self.comparison, self.derived)):
            if spec is None:
                if value is not None:
                    raise ValueError('Unmapped populated slot')
            elif value is None:
                if spec.required:
                    raise ValueError('Required measurement missing')
            elif (value.metric, value.unit, value.basis) != (spec.metric, spec.unit, spec.basis):
                raise ValueError('Measurement semantics disagree with mapping')
        if not self.lineage or any(r.client_id != self.client_id for r in self.lineage):
            raise ValueError('Scoped source lineage is required')
        guarded = ZERO_DENOMINATOR_GUARDS.get((self.diagnostic, self.signal_type))
        measurement = getattr(self, guarded) if guarded else None
        if measurement is not None and measurement.value.is_zero():
            raise ValueError('Zero may be an undefined-denominator sentinel; source semantics insufficient')
        if self.confidence != ConfidenceProfile():
            raise ValueError('This mapping version does not establish assessed confidence dimensions')
        return self


class CanonicalisationResult(Contract):
    outcome: Literal['CREATED', 'REPLAYED', 'UNMAPPED', 'REFUSED']
    reason: str
    fact: CanonicalFact | None = None


class FindingAssessment(Contract):
    outcome: AssessmentOutcome
    policy_version: Literal['SIGNIFICANCE-2.44.1'] = 'SIGNIFICANCE-2.44.1'
    rationale: str
    materiality: MaterialityProfile = Field(default_factory=MaterialityProfile)
    confidence: ConfidenceProfile = Field(default_factory=ConfidenceProfile)
    finding_id: Identifier | None = None


class FindingObservation(Contract):
    run_id: Identifier
    fact_id: Identifier
    scope: ReportingScope


class CanonicalFinding(Contract):
    schema_version: Literal['CFF-2.44'] = 'CFF-2.44'
    object_id: Identifier
    client_id: Identifier
    finding_type: Literal['REVENUE_MOVEMENT', 'MARGIN_MOVEMENT', 'CUSTOMER_CONCENTRATION']
    semantic_key: str
    first_seen_run: Identifier
    latest_seen_run: Identifier
    observations: tuple[FindingObservation, ...]
    contradictory_evidence: tuple[Identifier, ...] = ()
    mitigating_evidence: tuple[Identifier, ...] = ()
    assessment: FindingAssessment
    temporal_state: Literal['FIRST_OBSERVATION', 'REPEATED_OBSERVATION', 'PREVIOUS_COMPARABLE_PERIOD', 'INSUFFICIENT_TEMPORAL_EVIDENCE']
    status: Literal['DETECTED'] = 'DETECTED'
    revision: int = Field(default=1, strict=True, ge=1)


def render_fact(fact: CanonicalFact) -> str:
    """No computed values, inferred calendar dates, causal verbs or recommendations."""
    fact = CanonicalFact.from_json(fact.to_json())
    scope = fact.scope
    subject = f'{scope.entity_type} {scope.entity_id}' if scope.entity_id else 'BUSINESS'
    dates = f'{scope.period_from or "unknown"} to {scope.period_to or "unknown"}'
    parts = []
    for value in (fact.observed, fact.comparison, fact.derived):
        if value is not None:
            unit = {Unit.PERCENTAGE: '%', Unit.PERCENTAGE_POINTS: 'percentage points'}.get(value.unit, value.unit.value)
            parts.append(f'{value.metric} = {value.value} {value.currency + " " if value.currency else ""}{unit} ({value.basis})')
    limits = '; '.join(fact.limitations) or 'none recorded'
    return f'{subject}; {fact.state.value}; eligibility {fact.eligibility}; limitations: {limits}; recorded scope {dates}; {scope.period_basis}: ' + '; '.join(parts)
