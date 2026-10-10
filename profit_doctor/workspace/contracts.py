"""Typed administrative contracts; receipt, review and qualification are distinct."""
from dataclasses import dataclass
from datetime import date
from typing import Literal
from pydantic import Field, model_validator
from profit_doctor.reasoning.domain.contracts import Contract, Identifier


@dataclass(frozen=True)
class Operator:
    actor: str
    clients: frozenset[str]

    def __post_init__(self):
        if not self.actor.strip() or not self.clients or any(not x.strip() for x in self.clients):
            raise ValueError('Identified operator and explicit client grants required')

    def require(self, client_id):
        if client_id not in self.clients:
            raise PermissionError('Client is outside operator grants')


class Scope(Contract):
    entity_id: Identifier
    ledger_id: Identifier
    period_start: date
    period_end: date

    @model_validator(mode='after')
    def ordered(self):
        if self.period_start > self.period_end:
            raise ValueError('Reporting period is reversed')
        return self


class EngagementRevision(Contract):
    engagement_id: Identifier
    client_id: Identifier
    revision: int = Field(strict=True, ge=1)
    title: str = Field(min_length=1, max_length=255)
    scope: Scope
    status: Literal['OPEN', 'CLOSED'] = 'OPEN'
    run_ids: tuple[Identifier, ...] = ()
    readiness_ids: tuple[Identifier, ...] = ()
    readiness_view: Literal['CURRENT', 'HISTORICAL'] = 'CURRENT'
    scope_basis: Literal['ADMINISTRATIVE_DECLARATION'] = 'ADMINISTRATIVE_DECLARATION'


class Receipt(Contract):
    receipt_id: Identifier
    client_id: Identifier
    engagement_id: Identifier
    filename: str = Field(min_length=1, max_length=255)
    sha256: str = Field(pattern='^[a-f0-9]{64}$')
    byte_count: int = Field(strict=True, ge=1)
    source_role: str = Field(min_length=1, max_length=80)
    description: str = Field(max_length=2000)
    received_at: str
    actor: str
    predecessor_id: Identifier | None = None


class InformationRevision(Contract):
    request_id: Identifier
    engagement_id: Identifier
    client_id: Identifier
    revision: int = Field(strict=True, ge=1)
    question: str = Field(min_length=1, max_length=2000)
    evidence_required: str = Field(min_length=1, max_length=2000)
    prerequisite: str | None = Field(default=None, max_length=255)
    due_date: date | None = None
    status: Literal['OPEN', 'EVIDENCE_RECEIVED', 'FULFILMENT_REVIEWED', 'WITHDRAWN'] = 'OPEN'
    receipt_ids: tuple[Identifier, ...] = ()
    review_rationale: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def governed(self):
        if self.status in ('EVIDENCE_RECEIVED', 'FULFILMENT_REVIEWED') and not self.receipt_ids:
            raise ValueError('Evidence receipt required')
        if self.status in ('FULFILMENT_REVIEWED', 'WITHDRAWN') and not (self.review_rationale or '').strip():
            raise ValueError('Attributable review/withdrawal rationale required')
        if len(set(self.receipt_ids)) != len(self.receipt_ids):
            raise ValueError('Duplicate receipt references')
        return self
