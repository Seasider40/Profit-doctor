"""Reusable context contracts, independent of Bridge comparability policies."""
from typing import Literal

from pydantic import Field, model_validator

from profit_doctor.reasoning.bridge.qualification import Coverage, Period
from profit_doctor.reasoning.canonical.registry import Unit
from profit_doctor.reasoning.domain.contracts import Contract, Identifier, LineageReference
from profit_doctor.reasoning.canonical.service import identity


class MeasurementSlot(Contract):
    store: Literal['LEGACY_SQLITE', 'CANONICAL']
    resource: Literal['financial_statement_line', 'primitive_result', 'signal', 'canonical_fact', 'canonical_receivable_invoice']
    source_id: Identifier
    slot: Literal['amount', 'numeric_value', 'observed', 'comparison', 'derived']

    @model_validator(mode='after')
    def valid_slot(self):
        slots = {'financial_statement_line': ('amount',), 'primitive_result': ('numeric_value',),
                 'signal': ('observed', 'comparison', 'derived'),
                 'canonical_fact': ('observed', 'comparison', 'derived'), 'canonical_receivable_invoice': ('amount',)}
        if self.slot not in slots[self.resource] or (self.store == 'CANONICAL') != (self.resource in ('canonical_fact', 'canonical_receivable_invoice')):
            raise ValueError('Invalid owning store/resource/measurement slot')
        return self


class MeasurementContext(Contract):
    schema_version: Literal['CMC-2.48.1'] = 'CMC-2.48.1'
    client_id: Identifier
    run_id: Identifier
    origin: MeasurementSlot
    origin_digest: str = Field(pattern='^[a-f0-9]{64}$')
    metric: str = Field(min_length=1)
    unit: Unit
    currency: Literal['GBP'] | None = None
    economic_basis: str | None = Field(default=None, min_length=1)
    entity_type: str | None = None
    entity_id: str | None = None
    segment_scope: str | None = Field(default=None, min_length=1)
    period: Period = Field(default_factory=Period)
    coverage: Coverage = Coverage.UNKNOWN
    coverage_basis: str | None = Field(default=None, min_length=1)
    source_version: LineageReference
    lineage: tuple[LineageReference, ...]
    source_locator: str | None = None
    # Existing source_revision identity only; no separate source revision chain.
    source_revision_id: Identifier | None = None
    source_revision_digest: str | None = Field(default=None, pattern='^[a-f0-9]{64}$')
    revision_state: Literal['UNKNOWN_UNBOUND', 'ORIGINAL', 'RESTATEMENT'] = 'UNKNOWN_UNBOUND'
    prior_source_revision_id: Identifier | None = None
    supersedes: Identifier | None = None
    capture_method: Literal['ACCOUNTING_CSV_EXPLICIT_V1', 'RETAINED_ACCOUNTING_V1', 'RETAINED_FACT_SLOT_V1', 'RECEIVABLE_SNAPSHOT_V1']
    limitations: tuple[str, ...] = ()

    @property
    def context_id(self):
        return identity('measurement-context', self.to_json())

    @model_validator(mode='after')
    def governed_context(self):
        if (self.entity_type is None) != (self.entity_id is None):
            raise ValueError('Entity kind and identity must be retained together')
        money = self.unit in (Unit.CURRENCY, Unit.CURRENCY_PER_UNIT, Unit.CURRENCY_PER_FTE)
        if not money and self.currency is not None:
            raise ValueError('Nonmonetary context cannot carry currency')
        if not self.lineage or self.source_version not in self.lineage:
            raise ValueError('Existing dataset version must be retained in lineage')
        if self.source_version.kind != 'DATASET_VERSION' or self.source_version.resource != 'dataset_version' or self.source_version.store != 'LEGACY_SQLITE':
            raise ValueError('Existing owning-store dataset version is required')
        if any(r.client_id != self.client_id for r in self.lineage):
            raise ValueError('Foreign context lineage')
        if self.coverage != Coverage.UNKNOWN and self.coverage_basis is None:
            raise ValueError('Assessed coverage needs an explicit scoped basis')
        bound = self.source_revision_id is not None
        if bound != (self.source_revision_digest is not None) or bound != (self.revision_state != 'UNKNOWN_UNBOUND'):
            raise ValueError('Revision identity, snapshot and state must agree')
        if self.revision_state == 'ORIGINAL' and self.prior_source_revision_id is not None:
            raise ValueError('Original source revision has no predecessor')
        if self.revision_state == 'RESTATEMENT' and self.prior_source_revision_id is None:
            raise ValueError('Restatement requires its existing predecessor')
        return self


class ContextBinding(Contract):
    schema_version: Literal['MCB-2.48.1'] = 'MCB-2.48.1'
    client_id: Identifier
    run_id: Identifier
    owner: MeasurementSlot
    owner_digest: str = Field(pattern='^[a-f0-9]{64}$')
    context_id: Identifier
    parent_binding_id: Identifier | None = None

    @property
    def binding_id(self):
        return identity('measurement-binding', self.to_json())
