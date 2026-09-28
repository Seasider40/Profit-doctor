"""Evidence characteristics, never an opaque evidence or causal score."""
from enum import StrEnum
from typing import Literal
from pydantic import AwareDatetime, Field, model_validator
from profit_doctor.reasoning.domain.contracts import Contract, Identifier, ConfidenceProfile, now
from profit_doctor.reasoning.canonical.contracts import ReportingScope
from profit_doctor.reasoning.domain.vocabulary import SourceAuthority


class Independence(StrEnum):
    SAME_ANCESTRY = 'SAME_ANCESTRY'
    SUBSTANTIALLY_SHARED = 'SUBSTANTIALLY_SHARED'
    PARTIALLY_SHARED = 'PARTIALLY_SHARED'
    INDEPENDENT = 'INDEPENDENT'
    INDETERMINATE = 'INDETERMINATE'


class Temporal(StrEnum):
    PRECEDES = 'PRECEDES'
    FOLLOWS = 'FOLLOWS'
    OVERLAPS = 'OVERLAPS'
    SAME_COMPARABLE_PERIOD = 'SAME_COMPARABLE_PERIOD'
    NOT_COMPARABLE = 'NOT_COMPARABLE'
    INSUFFICIENT_PERIOD_INFORMATION = 'INSUFFICIENT_PERIOD_INFORMATION'


class Ancestry(Contract):
    # Existing store/resource/key tuples serialized as stable strings. These are
    # references, never replacements for owning-store identities.
    references: tuple[str, ...] = ()
    datasets: tuple[str, ...] = ()
    source_files: tuple[str, ...] = ()
    primitives: tuple[str, ...] = ()
    records: tuple[str, ...] = ()
    diagnostic_families: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    complete: bool = False


class Node(Contract):
    object_id: Identifier
    revision: int
    run_id: Identifier
    object_type: Literal['FACT', 'FINDING', 'SIGNAL']
    authority: SourceAuthority
    scope: ReportingScope
    ancestry: Ancestry
    confidence: ConfidenceProfile
    eligible: bool


class Characteristics(Contract):
    schema_version: Literal['EG-2.45.1'] = 'EG-2.45.1'
    independence: Independence
    independence_basis: str
    shared_references: tuple[str, ...]
    shared_datasets: tuple[str, ...]
    shared_source_files: tuple[str, ...]
    source_authorities: tuple[str, str]
    lineage_complete: tuple[bool, bool]
    temporal: Temporal
    contradiction_present: bool = False
    data_confidence: tuple[str | None, str | None]


class SeriesBasis(Contract):
    """Aligned Fact IDs, not caller-invented numeric observations."""
    source_facts: tuple[Identifier, ...] = Field(min_length=4)
    target_facts: tuple[Identifier, ...] = Field(min_length=4)
    slot: Literal['observed', 'comparison', 'derived'] = 'observed'
    method: Literal['ALIGNED_NONZERO_DIRECTION-1'] = 'ALIGNED_NONZERO_DIRECTION-1'

    @model_validator(mode='after')
    def aligned(self):
        if len(self.source_facts) != len(self.target_facts):
            raise ValueError('Series lengths differ')
        if len(set(self.source_facts)) != len(self.source_facts) or len(set(self.target_facts)) != len(self.target_facts):
            raise ValueError('Repeated observations are not a time series')
        return self


class GraphRecord(Contract):
    schema_version: Literal['EG-2.45.1'] = 'EG-2.45.1'
    revision: int = Field(default=1, strict=True, ge=1)
    created_at: AwareDatetime = Field(default_factory=now)
    link_id: Identifier
    client_id: Identifier
    run_id: Identifier
    source_id: Identifier
    target_id: Identifier
    relationship: Literal['SUPPORTS', 'CONTRADICTS', 'QUANTIFIES', 'CONTEXTUALISES',
                          'TEMPORALLY_PRECEDES', 'CO_MOVES_WITH', 'MITIGATES']
    source_revision: int
    target_revision: int
    rationale: str = Field(min_length=1)
    characteristics: Characteristics
    series: SeriesBasis | None = None
    source_snapshot: Node
    target_snapshot: Node

    @model_validator(mode='after')
    def coherent(self):
        if self.source_id == self.target_id or not self.rationale.strip():
            raise ValueError('Self-link or empty rationale')
        if (self.source_id, self.source_revision) != (self.source_snapshot.object_id, self.source_snapshot.revision):
            raise ValueError('Source snapshot disagrees with endpoint')
        if (self.target_id, self.target_revision) != (self.target_snapshot.object_id, self.target_snapshot.revision):
            raise ValueError('Target snapshot disagrees with endpoint')
        if (self.series is not None) != (self.relationship == 'CO_MOVES_WITH'):
            raise ValueError('Co-movement requires a typed series basis')
        if self.characteristics.source_authorities != (self.source_snapshot.authority, self.target_snapshot.authority):
            raise ValueError('Characteristics disagree with retained authorities')
        if self.characteristics.lineage_complete != (self.source_snapshot.ancestry.complete, self.target_snapshot.ancestry.complete):
            raise ValueError('Characteristics disagree with retained ancestry')
        return self
