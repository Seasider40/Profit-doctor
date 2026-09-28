"""Temporary read-only compatibility envelope; no automatic semantic conversion."""
from typing import Literal
from pydantic import Field, JsonValue
from .contracts import Contract, LineageReference
from .vocabulary import SourceAuthority


class LegacyObservation(Contract):
    """Retains legacy evidence verbatim. This is NOT a canonical reasoning object.

    No canonical status, confidence vector or materiality vector is inferred.
    Retire this envelope per semantic slice once a qualified migration exists.
    """
    schema_version: Literal['LEGACY-OBSERVATION-2.43'] = 'LEGACY-OBSERVATION-2.43'
    source: LineageReference
    legacy_type: str
    legacy_status: str | None = None
    legacy_confidence: str | None = None
    legacy_materiality: str | None = None
    source_authority: Literal[SourceAuthority.LEGACY_UNCLASSIFIED] = SourceAuthority.LEGACY_UNCLASSIFIED
    original_fields: dict[str, JsonValue] = Field(default_factory=dict)
    conversion_state: Literal['UNRESOLVED'] = 'UNRESOLVED'
