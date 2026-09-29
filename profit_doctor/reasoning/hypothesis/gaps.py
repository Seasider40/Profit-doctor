"""Investigation requirements, not recommendations or inferred evidence.

A gap records why an assessment cannot establish a proposition. It neither
repairs a source nor authorizes a stronger canonical mapping or graph edge.
"""
from enum import StrEnum

from pydantic import Field, field_validator

from profit_doctor.reasoning.canonical.contracts import ReportingScope
from profit_doctor.reasoning.domain.contracts import Contract, Identifier


class GapBarrier(StrEnum):
    SUPPORT = 'SUPPORT'
    CONTRADICTION = 'CONTRADICTION'
    BOTH = 'BOTH'


class GapKind(StrEnum):
    MISSING_EVIDENCE = 'MISSING_EVIDENCE'
    UNSAFE_SEMANTICS = 'UNSAFE_SEMANTICS'
    INCOMPLETE_LINEAGE = 'INCOMPLETE_LINEAGE'
    SHARED_ANCESTRY = 'SHARED_ANCESTRY'
    UNVERIFIED_AUTHORITY = 'UNVERIFIED_AUTHORITY'
    INCOMPARABLE_PERIODS = 'INCOMPARABLE_PERIODS'
    MISSING_SEGMENTATION = 'MISSING_SEGMENTATION'
    CONFLICTING_EVIDENCE = 'CONFLICTING_EVIDENCE'


class EvidenceGap(Contract):
    """A versioned assessment component with an explicit evidential barrier.

    Identity and client/run ownership belong to its containing assessment.
    Related IDs must be resolved by that assessment's service before persistence;
    this value contract alone makes no endpoint-existence or ownership claim.
    """
    schema_version: str = Field(default='HG-2.46.1', pattern=r'^HG-2\.46\.1$')
    kind: GapKind
    missing_evidence: str = Field(min_length=1)
    reason_required: str = Field(min_length=1)
    dimension: str = Field(min_length=1)
    scope: ReportingScope
    investigation_request: str = Field(min_length=1)
    blocks: GapBarrier
    related_objects: tuple[Identifier, ...] = ()

    @field_validator('missing_evidence', 'reason_required', 'dimension', 'investigation_request')
    @classmethod
    def meaningful_text(cls, value):
        if not value.strip() or any(ord(c) < 32 for c in value):
            raise ValueError('Gap descriptions must be nonblank and free of control characters')
        return value

    @field_validator('related_objects')
    @classmethod
    def stable_references(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('Duplicate evidence references do not add evidence')
        return tuple(sorted(value))
