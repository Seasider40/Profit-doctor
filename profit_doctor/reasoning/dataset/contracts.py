"""Immutable claims about dataset meaning, provenance and comparability."""
from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, JsonValue, model_validator

from profit_doctor.reasoning.bridge.qualification import Coverage, Period, ReportingBasis
from profit_doctor.reasoning.domain.contracts import Actor, Contract, Identifier, LineageReference
from profit_doctor.reasoning.domain.vocabulary import SourceAuthority


class DatasetFamily(StrEnum):
    SALES_TRANSACTIONS = 'SALES_TRANSACTIONS'
    GENERAL_LEDGER = 'GENERAL_LEDGER'


class DatasetRevisionRelationship(StrEnum):
    NEW_OBSERVATION = 'NEW_OBSERVATION'
    RESTATEMENT = 'RESTATEMENT'
    CORRECTION = 'CORRECTION'
    SUPERSESSION = 'SUPERSESSION'
    PARTIAL_REPLACEMENT = 'PARTIAL_REPLACEMENT'
    UNKNOWN = 'UNKNOWN'


class AssessmentOutcome(StrEnum):
    COMPARABLE = 'COMPARABLE'
    COMPARABLE_WITH_LIMITATIONS = 'COMPARABLE_WITH_LIMITATIONS'
    NOT_COMPARABLE = 'NOT_COMPARABLE'
    INSUFFICIENT_EVIDENCE = 'INSUFFICIENT_EVIDENCE'


class DimensionState(StrEnum):
    MATCH = 'MATCH'
    LIMITED_MATCH = 'LIMITED_MATCH'
    MISMATCH = 'MISMATCH'
    INSUFFICIENT_EVIDENCE = 'INSUFFICIENT_EVIDENCE'


class ComparabilityDimension(StrEnum):
    DATASET_FAMILY = 'DATASET_FAMILY'
    POPULATION = 'POPULATION'
    INCLUSION_EXCLUSION = 'INCLUSION_EXCLUSION'
    COVERAGE = 'COVERAGE'
    DEFINITION = 'DEFINITION'
    ORGANISATIONAL_SCOPE = 'ORGANISATIONAL_SCOPE'
    CURRENCY = 'CURRENCY'
    UNIT = 'UNIT'
    TIME_BASIS = 'TIME_BASIS'
    SOURCE_LINEAGE = 'SOURCE_LINEAGE'
    REVISION_RELATIONSHIP = 'REVISION_RELATIONSHIP'


class TemporalEvidenceRole(StrEnum):
    NEW_OBSERVATION = 'NEW_OBSERVATION'
    REVISION_ONLY = 'REVISION_ONLY'
    INDETERMINATE = 'INDETERMINATE'


class DatasetAssertion(Contract):
    """A declaration and any independent verification remain separate values."""

    declared_value: JsonValue = None
    declaration_authority: SourceAuthority | None = None
    declared_by: Actor | None = None
    declared_at: datetime | None = None
    verified_value: JsonValue = None
    verification_authority: SourceAuthority | None = None
    verification_evidence: tuple[LineageReference, ...] = ()

    @model_validator(mode='after')
    def authority_and_value(self):
        declared = self.declared_value is not None
        declaration_parts = (self.declaration_authority, self.declared_by, self.declared_at)
        if declared != all(x is not None for x in declaration_parts):
            raise ValueError('A declaration requires its authority, identified actor and timestamp')
        if declared:
            if self.declaration_authority not in (SourceAuthority.MANAGEMENT_ASSERTION, SourceAuthority.HUMAN_FD_JUDGEMENT):
                raise ValueError('Human declarations retain human source authority')
            if self.declared_by.actor_id is None or self.declared_by.actor_type.value not in ('HUMAN', 'MANAGEMENT'):
                raise ValueError('Dataset declarations require an identified human or management actor')
        verified = self.verified_value is not None
        if verified != (self.verification_authority is not None) or verified != bool(self.verification_evidence):
            raise ValueError('Verified values require authority and retained evidence')
        if verified and self.verification_authority not in (SourceAuthority.SYSTEM_DERIVED, SourceAuthority.SOURCE_DATA):
            raise ValueError('Verification must retain system or source authority')
        if not verified and self.verification_authority is not None:
            raise ValueError('Unknown verification cannot carry verification authority')
        if self.declared_at is not None and self.declared_at.tzinfo is None:
            raise ValueError('Declaration timestamp must include a timezone')
        return self


class DatasetCoverage(Contract):
    period: Period
    completeness: Coverage
    coverage_basis: str | None = Field(default=None, min_length=1)

    @model_validator(mode='after')
    def coverage_evidence(self):
        if self.completeness != Coverage.UNKNOWN and self.coverage_basis is None:
            raise ValueError('Declared completeness requires an explicit coverage basis')
        if self.completeness != Coverage.UNKNOWN and (self.period.start is None or self.period.end is None
                                                       or self.period.basis == ReportingBasis.UNKNOWN):
            raise ValueError('Assessed coverage requires a period and reporting basis')
        return self


class DatasetContract(Contract):
    schema_version: Literal['DSC-2.53.1'] = 'DSC-2.53.1'
    contract_id: Identifier
    client_id: Identifier
    recorded_run_id: Identifier
    source_dataset: LineageReference
    source_version: LineageReference
    source_file: LineageReference
    source_file_sha256: str = Field(pattern='^[a-f0-9]{64}$')
    source_capture_id: Identifier
    logical_dataset_key: str = Field(min_length=1, max_length=255)
    source_data_domain: str = Field(min_length=1, max_length=80)
    source_provider: DatasetAssertion = Field(default_factory=DatasetAssertion)
    source_digest: str = Field(pattern='^[a-f0-9]{64}$')
    revision: int = Field(strict=True, ge=1)
    supersedes: Identifier | None = None
    family: DatasetAssertion = Field(default_factory=DatasetAssertion)
    population: DatasetAssertion = Field(default_factory=DatasetAssertion)
    inclusion_exclusion: DatasetAssertion = Field(default_factory=DatasetAssertion)
    coverage: DatasetAssertion = Field(default_factory=DatasetAssertion)
    definition: DatasetAssertion = Field(default_factory=DatasetAssertion)
    organisational_scope: DatasetAssertion = Field(default_factory=DatasetAssertion)
    currency: DatasetAssertion = Field(default_factory=DatasetAssertion)
    unit: DatasetAssertion = Field(default_factory=DatasetAssertion)
    time_basis: DatasetAssertion = Field(default_factory=DatasetAssertion)
    revision_relationship: DatasetAssertion = Field(default_factory=DatasetAssertion)
    revision_target_contract_id: Identifier | None = None
    observed_row_count: int = Field(strict=True, ge=0)
    observed_period_from: str | None = None
    observed_period_to: str | None = None
    created_at: datetime

    @model_validator(mode='after')
    def ownership_and_revision(self):
        if self.created_at.tzinfo is None:
            raise ValueError('Dataset contract creation time must include a timezone')
        refs = (self.source_dataset, self.source_version, self.source_file)
        if any(r.client_id != self.client_id for r in refs):
            raise ValueError('Dataset contract cannot retain foreign-client source lineage')
        if (self.source_dataset.kind.value, self.source_dataset.resource) != ('DATASET', 'dataset'):
            raise ValueError('Dataset identity must use the existing dataset source')
        if (self.source_version.kind.value, self.source_version.resource) != ('DATASET_VERSION', 'dataset_version'):
            raise ValueError('Dataset contract must retain the existing dataset version')
        if (self.source_file.kind.value, self.source_file.resource) != ('SOURCE_FILE', 'source_file'):
            raise ValueError('Dataset contract must retain the immutable source file')
        for claim in self.claims():
            if claim.declared_by and claim.declared_by.source_authority != claim.declaration_authority:
                raise ValueError('Declaration actor authority disagrees with the declaration')
            if claim.declared_at and claim.declared_at.astimezone(timezone.utc) > self.created_at.astimezone(timezone.utc):
                raise ValueError('Declaration timestamp cannot follow its contract revision')
            if any(ref.client_id != self.client_id for ref in claim.verification_evidence):
                raise ValueError('Verification evidence cannot cross client scope')
        relation = self.revision_relationship.verified_value or self.revision_relationship.declared_value
        if relation is not None:
            relationship = DatasetRevisionRelationship(relation)
            if relationship == DatasetRevisionRelationship.UNKNOWN and self.revision_target_contract_id:
                raise ValueError('Unknown revision relationship cannot claim a predecessor')
            if relationship not in (DatasetRevisionRelationship.UNKNOWN, DatasetRevisionRelationship.NEW_OBSERVATION) and not self.revision_target_contract_id:
                raise ValueError('Restatement/correction/supersession requires an explicit prior contract')
        elif self.revision_target_contract_id is not None:
            raise ValueError('Revision target requires an explicit revision relationship')
        return self

    def claims(self) -> tuple[DatasetAssertion, ...]:
        return (self.family, self.source_provider, self.population, self.inclusion_exclusion, self.coverage,
                self.definition, self.organisational_scope, self.currency, self.unit,
                self.time_basis, self.revision_relationship)


class DimensionResult(Contract):
    state: DimensionState
    reason: str = Field(min_length=1)
    left_evidence: tuple[LineageReference, ...] = ()
    right_evidence: tuple[LineageReference, ...] = ()
    limitations: tuple[str, ...] = ()


class DatasetComparability(Contract):
    schema_version: Literal['DCA-2.53.1'] = 'DCA-2.53.1'
    assessment_id: Identifier
    client_id: Identifier
    run_id: Identifier
    left_contract_id: Identifier
    right_contract_id: Identifier
    policy_version: str = 'DATASET-COMPARABILITY-2.53.1'
    outcome: AssessmentOutcome
    temporal_evidence_role: TemporalEvidenceRole
    dimensions: dict[ComparabilityDimension, DimensionResult]
    limitations: tuple[str, ...] = ()
    assessed_at: datetime

    @model_validator(mode='after')
    def scope_and_dimensions(self):
        if self.left_contract_id == self.right_contract_id:
            raise ValueError('A dataset contract cannot be compared with itself')
        if self.assessed_at.tzinfo is None:
            raise ValueError('Assessment timestamp must include a timezone')
        required = set(ComparabilityDimension)
        if set(self.dimensions) != required:
            raise ValueError('Every governed comparability dimension must be explained')
        return self


def json_value(value: Any) -> JsonValue:
    """Convert a governed Pydantic value to its deterministic JSON representation."""
    if hasattr(value, 'model_dump'):
        return value.model_dump(mode='json')
    return value
