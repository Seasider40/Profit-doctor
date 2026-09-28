"""Versioned foundation contracts; no analytical behaviour or status promotion."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import json
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import (AwareDatetime, BaseModel, BeforeValidator, ConfigDict,
                      Field, JsonValue, field_validator, model_validator)

from .vocabulary import (
    ActionStatus, ActorType, AssessmentLevel, AuditEventType, BenefitStatus,
    ConfidenceLevel, EvidenceRole, ExplanationStatus, FindingStatus, ImpactBasis,
    ImpactType, LineageKind, ObjectType, OpportunityStatus, OverlapType,
    RelationshipType, SourceAuthority, StoryStatus,
)

Identifier = Annotated[str, Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_.:-]+$')]
ReferenceId = Annotated[str, Field(min_length=1, max_length=128, pattern=r'^\S+$')]


def _decimal(value):
    if isinstance(value, (float, bool)):
        raise ValueError('Use Decimal or a decimal string, never binary floating point')
    return value


FinancialDecimal = Annotated[Decimal, BeforeValidator(_decimal), Field(allow_inf_nan=False)]


def now():
    return datetime.now(timezone.utc)


def new_id():
    return 'rd_' + uuid4().hex


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, validate_default=True,
                              revalidate_instances='always', allow_inf_nan=False)

    def to_json(self) -> str:
        """Stable key order; Decimal values are lossless JSON strings."""
        return json.dumps(self.model_dump(mode='json'), sort_keys=True,
                          separators=(',', ':'), ensure_ascii=False, allow_nan=False)

    @classmethod
    def from_json(cls, value: str):
        # Reject duplicate keys instead of silently accepting the last value.
        def unique(pairs):
            result = {}
            for key, item in pairs:
                if key in result:
                    raise ValueError(f'Duplicate JSON key: {key}')
                result[key] = item
            return result
        return cls.model_validate(json.loads(value, object_pairs_hook=unique))


class LineageReference(Contract):
    """An existing identity in its owning store, not a replacement source object.

    Cross-store references require a trusted resolver at the persistence boundary.
    Recording a reference alone is never verification of its contents.
    """
    kind: LineageKind
    store: Literal['LEGACY_SQLITE', 'SQLALCHEMY', 'CANONICAL']
    resource: Annotated[str, Field(min_length=1, max_length=64, pattern=r'^[a-zA-Z0-9_]+$')]
    source_id: ReferenceId
    client_id: Identifier
    run_id: Identifier | None = None


class ConfidenceProfile(Contract):
    data_confidence: ConfidenceLevel | None = ConfidenceLevel.NOT_ASSESSED
    attribution_confidence: ConfidenceLevel | None = ConfidenceLevel.NOT_ASSESSED
    interpretation_confidence: ConfidenceLevel | None = ConfidenceLevel.NOT_ASSESSED
    quantification_confidence: ConfidenceLevel | None = ConfidenceLevel.NOT_ASSESSED
    opportunity_confidence: ConfidenceLevel | None = ConfidenceLevel.NOT_ASSESSED
    benefit_attribution_confidence: ConfidenceLevel | None = ConfidenceLevel.NOT_ASSESSED
    rationale: dict[str, JsonValue] = Field(default_factory=dict)


class MaterialityProfile(Contract):
    # None means unknown, not zero. Percentages are in percentage points.
    absolute_economic_magnitude: FinancialDecimal | None = None
    percentage_of_revenue: FinancialDecimal | None = None
    percentage_of_gross_profit: FinancialDecimal | None = None
    percentage_of_ebitda: FinancialDecimal | None = None
    cash_impact: FinancialDecimal | None = None
    currency: Annotated[str, Field(pattern=r'^[A-Z]{3}$')] | None = None
    persistence: AssessmentLevel | None = AssessmentLevel.NOT_ASSESSED
    trend_velocity: AssessmentLevel | None = AssessmentLevel.NOT_ASSESSED
    concentration: AssessmentLevel | None = AssessmentLevel.NOT_ASSESSED
    strategic_relevance: AssessmentLevel | None = AssessmentLevel.NOT_ASSESSED
    risk_severity: AssessmentLevel | None = AssessmentLevel.NOT_ASSESSED
    urgency: AssessmentLevel | None = AssessmentLevel.NOT_ASSESSED
    controllability: AssessmentLevel | None = AssessmentLevel.NOT_ASSESSED
    rationale: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode='after')
    def money_has_currency(self):
        if (self.absolute_economic_magnitude is not None or self.cash_impact is not None) and self.currency is None:
            raise ValueError('Monetary dimensions require a currency')
        return self


class ScopedIdentity(Contract):
    schema_version: Literal['RDF-2.43'] = 'RDF-2.43'
    client_id: Identifier
    run_id: Identifier | None = None
    entity: LineageReference | None = None
    period_from: date | None = None
    period_to: date | None = None
    created_at: AwareDatetime = Field(default_factory=now)
    lineage: tuple[LineageReference, ...] = ()

    @field_validator('created_at')
    @classmethod
    def utc(cls, value):
        return value.astimezone(timezone.utc)

    @model_validator(mode='after')
    def scope(self):
        if self.period_from and self.period_to and self.period_from > self.period_to:
            raise ValueError('Period start must not follow its end')
        if self.entity and self.entity.kind != LineageKind.ENTITY:
            raise ValueError('Entity scope requires an ENTITY reference')
        for ref in (*self.lineage, *((self.entity,) if self.entity else ())):
            if ref.client_id != self.client_id:
                raise ValueError('Cross-client lineage is prohibited')
        # An ancestor may legitimately belong to an earlier run of this client.
        return self


STATUS_FAMILIES = {
    ObjectType.FINDING: FindingStatus,
    ObjectType.HYPOTHESIS: ExplanationStatus,
    ObjectType.INTERPRETATION: ExplanationStatus,
    ObjectType.ECONOMIC_STORY: StoryStatus,
    ObjectType.OPPORTUNITY_CANDIDATE: OpportunityStatus,
    ObjectType.VALIDATED_OPPORTUNITY: OpportunityStatus,
    ObjectType.ACTION: ActionStatus,
    ObjectType.BENEFIT_RECORD: BenefitStatus,
}


class ReasoningObject(ScopedIdentity):
    """Typed identity contract only, not an untyped analytical payload.

    Future semantic slices extend this contract with their own versioned models.
    No fact text, causal claim or economic calculation is manufactured here.
    """
    object_id: Identifier = Field(default_factory=new_id)
    object_type: ObjectType
    source_authority: SourceAuthority
    revision: Annotated[int, Field(strict=True, ge=1)] = 1
    updated_at: AwareDatetime | None = None
    status: str | None = None
    confidence: ConfidenceProfile = Field(default_factory=ConfidenceProfile)
    materiality: MaterialityProfile = Field(default_factory=MaterialityProfile)
    impact_type: ImpactType | None = None
    impact_basis: ImpactBasis | None = None

    @field_validator('updated_at')
    @classmethod
    def updated_utc(cls, value):
        return value.astimezone(timezone.utc) if value else None

    @model_validator(mode='after')
    def meaning(self):
        if self.updated_at and self.updated_at < self.created_at:
            raise ValueError('Update predates creation')
        if self.status is not None:
            family = STATUS_FAMILIES.get(self.object_type)
            if family is None or self.status not in family._value2member_map_:
                raise ValueError('Status does not belong to this object family')
        if self.object_type != ObjectType.ECONOMIC_IMPACT and (self.impact_type or self.impact_basis):
            raise ValueError('Impact vocabulary belongs only to ECONOMIC_IMPACT')
        return self


class EvidenceLink(ScopedIdentity):
    link_id: Identifier = Field(default_factory=new_id)
    source_id: Identifier
    target_id: Identifier
    relationship_type: RelationshipType
    evidence_role: EvidenceRole | None = None
    source_authority: SourceAuthority
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode='after')
    def endpoints(self):
        if self.source_id == self.target_id:
            raise ValueError('Self-links are prohibited for all evidence relationships')
        return self


class EconomicEffect(ScopedIdentity):
    effect_id: Identifier = Field(default_factory=new_id)


class EffectReference(ScopedIdentity):
    reference_id: Identifier = Field(default_factory=new_id)
    object_id: Identifier
    effect_id: Identifier


class EffectOverlap(ScopedIdentity):
    overlap_id: Identifier = Field(default_factory=new_id)
    source_effect_id: Identifier
    target_effect_id: Identifier
    overlap_type: OverlapType
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode='after')
    def endpoints(self):
        if self.source_effect_id == self.target_effect_id:
            raise ValueError('Self-overlap is prohibited; use the same effect identity')
        return self


class Actor(Contract):
    actor_type: ActorType
    source_authority: SourceAuthority
    actor_id: ReferenceId | None = None


class AuditEvent(ScopedIdentity):
    event_id: Identifier = Field(default_factory=new_id)
    object_id: Identifier | None = None
    effect_id: Identifier | None = None
    event_type: AuditEventType
    actor: Actor
    previous: JsonValue = None
    new: JsonValue = None
    rationale: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode='after')
    def authority(self):
        if (self.object_id is None) == (self.effect_id is None):
            raise ValueError('Audit event requires exactly one object or effect identity')
        if (self.event_type == AuditEventType.MANAGEMENT_ASSERTION_RECORDED
                and self.actor.source_authority != SourceAuthority.MANAGEMENT_ASSERTION):
            raise ValueError('Management assertion events retain management authority')
        if (self.event_type == AuditEventType.HUMAN_OVERRIDE_RECORDED
                and self.actor.actor_type not in (ActorType.HUMAN, ActorType.MANAGEMENT)):
            raise ValueError('Human override requires a human or management actor')
        return self
