"""Evidence contracts distinguish arithmetic checks from semantic verification."""
from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from profit_doctor.reasoning.bridge.qualification import Period
from profit_doctor.reasoning.domain.contracts import (
    Actor, Contract, FinancialDecimal, Identifier, LineageReference, now,
)


class ReconciliationState(StrEnum):
    MATCH = 'MATCH'
    MISMATCH = 'MISMATCH'
    INSUFFICIENT_EVIDENCE = 'INSUFFICIENT_EVIDENCE'
    NOT_APPLICABLE = 'NOT_APPLICABLE'
    CONFLICTED = 'CONFLICTED'


class ReadinessState(StrEnum):
    VERIFIED = 'VERIFIED'
    DECLARED = 'DECLARED'
    PARTIAL = 'PARTIAL'
    INSUFFICIENT = 'INSUFFICIENT'
    NOT_PROVIDED = 'NOT_PROVIDED'
    CONFLICTED = 'CONFLICTED'


class RecordKind(StrEnum):
    TB_ACTIVITY = 'TB_ACTIVITY'
    TB_CLOSING = 'TB_CLOSING'
    PNL = 'PNL'
    BALANCE_SHEET = 'BALANCE_SHEET'
    SALES = 'SALES'
    RECEIVABLE = 'RECEIVABLE'


class EvidenceScope(Contract):
    client_id: Identifier
    entity_id: Identifier
    ledger_id: Identifier
    population: str = Field(min_length=1)
    period: Period
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    definition: str = Field(min_length=1)


class SourceAmount(Contract):
    """A transported amount, not a complete population or verified measurement."""
    record_id: Identifier
    account_code: str = Field(min_length=1)
    kind: RecordKind
    amount: FinancialDecimal
    scope: EvidenceScope
    lineage: tuple[LineageReference, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def scoped(self):
        if any(ref.client_id != self.scope.client_id for ref in self.lineage):
            raise ValueError('Source amount lineage cannot cross client scope')
        return self


class Reconciliation(Contract):
    schema_version: Literal['RECONCILIATION-2.55.1'] = 'RECONCILIATION-2.55.1'
    reconciliation_id: Identifier
    scope: EvidenceScope
    method: Literal['EXACT_SCOPED_AMOUNTS_1'] = 'EXACT_SCOPED_AMOUNTS_1'
    source_a: tuple[LineageReference, ...]
    source_b: tuple[LineageReference, ...]
    records_a: tuple[Identifier, ...]
    records_b: tuple[Identifier, ...]
    amount_a: FinancialDecimal | None
    amount_b: FinancialDecimal | None
    difference: FinancialDecimal | None
    # This contract has exact arithmetic; it does not introduce a tolerance policy.
    tolerance: Literal['0'] = '0'
    state: ReconciliationState
    authority: Literal['SYSTEM_DERIVED'] = 'SYSTEM_DERIVED'
    reasons: tuple[str, ...]
    limitations: tuple[str, ...] = (
        'Amount agreement does not establish population membership, completeness, '
        'account classification, source authenticity or economic causality.',
    )

    @model_validator(mode='after')
    def scoped(self):
        if any(ref.client_id != self.scope.client_id for ref in (*self.source_a, *self.source_b)):
            raise ValueError('Reconciliation lineage cannot cross client scope')
        return self


class EvidenceDeclaration(Contract):
    """Human context remains separately attributable; never a verified flag."""
    declaration_id: Identifier
    client_id: Identifier
    actor: Actor
    effective_on: date
    recorded_at: AwareDatetime = Field(default_factory=now)
    dimension: Literal['population', 'coverage', 'definition', 'organisational_scope',
        'currency', 'unit', 'time_basis', 'revision_relationship', 'inclusion_exclusion']
    claim: str = Field(min_length=1)
    lineage: tuple[LineageReference, ...] = Field(min_length=1)
    revision: int = Field(strict=True, ge=1)
    supersedes: Identifier | None = None

    @model_validator(mode='after')
    def declared_only(self):
        if self.actor.actor_type not in ('HUMAN', 'MANAGEMENT') or not self.actor.actor_id:
            raise ValueError('Declaration requires an identified human or management actor')
        expected = 'HUMAN_FD_JUDGEMENT' if self.actor.actor_type == 'HUMAN' else 'MANAGEMENT_ASSERTION'
        if self.actor.source_authority != expected:
            raise ValueError('Declaration must retain its human authority')
        if any(ref.client_id != self.client_id for ref in self.lineage):
            raise ValueError('Declaration lineage cannot cross client scope')
        if (self.revision == 1) != (self.supersedes is None):
            raise ValueError('Declaration revision requires its explicit predecessor')
        return self
