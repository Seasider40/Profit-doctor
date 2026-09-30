"""Source assertions, contractual dates and point-in-time balances; no recoverability."""
from datetime import date, timedelta
from decimal import Decimal, localcontext
from typing import Literal
from pydantic import Field, model_validator
from profit_doctor.reasoning.domain.contracts import Contract, Identifier, FinancialDecimal
from profit_doctor.reasoning.impact.contracts import precision
from profit_doctor.reasoning.canonical.service import identity


class Terms(Contract):
    reference: str = Field(min_length=1)
    days: int = Field(strict=True, ge=0)
    effective_from: date
    effective_to: date
    basis: Literal['CALENDAR_DAYS_AFTER_INVOICE'] = 'CALENDAR_DAYS_AFTER_INVOICE'


class StatusEvidence(Contract):
    status: Literal['NONE_RECORDED', 'AGREED_PAYMENT_PLAN', 'ACTIVE_DISPUTE',
                    'CREDIT_NOTE_PENDING', 'UNKNOWN'] = 'UNKNOWN'
    reviewed_at: date | None = None
    authority: Literal['SOURCE_RECORD', 'MANAGEMENT_ASSERTION', 'UNKNOWN'] = 'UNKNOWN'
    reference: str | None = None
    # This contract covers the entire invoice outstanding balance, not an inferred subset.
    scope: Literal['ENTIRE_OUTSTANDING_BALANCE'] = 'ENTIRE_OUTSTANDING_BALANCE'


class Invoice(Contract):
    invoice_id: Identifier
    customer_id: Identifier
    invoice_date: date | None = None
    explicit_due: date | None = None
    terms: Terms | None = None
    outstanding: FinancialDecimal = Field(ge=0)
    original_amount: FinancialDecimal | None = Field(default=None, ge=0)
    currency: Literal['GBP'] = 'GBP'
    as_of: date
    status: StatusEvidence = Field(default_factory=StatusEvidence)
    source_reference: str = Field(min_length=1)

    @property
    def due(self):
        derived = self.invoice_date + timedelta(days=self.terms.days) if self.terms and self.invoice_date else None
        return self.explicit_due or derived

    @property
    def days_overdue(self):
        return None if self.due is None else max(0, (self.as_of-self.due).days)

    @model_validator(mode='after')
    def dates(self):
        if self.invoice_date and self.invoice_date > self.as_of:
            raise ValueError('Invoice postdates snapshot')
        if self.terms:
            if self.invoice_date is None or not self.terms.effective_from <= self.invoice_date <= self.terms.effective_to:
                raise ValueError('Terms require an invoice date within their effective interval')
            derived = self.invoice_date + timedelta(days=self.terms.days)
            if self.explicit_due and self.explicit_due != derived:
                raise ValueError('Explicit due date and contractual terms disagree')
        if self.explicit_due and self.invoice_date and self.explicit_due < self.invoice_date:
            raise ValueError('Due date precedes invoice')
        if self.status.reviewed_at and self.status.reviewed_at > self.as_of:
            raise ValueError('Status review postdates snapshot')
        return self


class Snapshot(Contract):
    schema_version: Literal['AR-2.49.1'] = 'AR-2.49.1'
    client_id: Identifier
    run_id: Identifier
    ledger_id: Identifier
    entity: str = Field(min_length=1)
    as_of: date
    currency: Literal['GBP'] = 'GBP'
    scope: str = Field(min_length=1)
    coverage: Literal['COMPLETE', 'PARTIAL']
    coverage_basis: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    # Qualification data may exercise a production contract without becoming real client data.
    origin: Literal['REAL_SOURCE', 'BLIND_QUALIFICATION']
    invoices: tuple[Invoice, ...] = Field(min_length=1)
    control_amount: FinancialDecimal | None = Field(default=None, ge=0)
    control_reference: str | None = None
    dataset_version_id: Identifier
    workbook_source_id: Identifier | None = None

    @property
    def total(self):
        with localcontext() as ctx:
            ctx.prec = precision(i.outstanding for i in self.invoices)
            return sum((i.outstanding for i in self.invoices), Decimal(0))

    @property
    def series_id(self):
        return identity('ar-series', self.client_id, self.run_id, self.ledger_id,
                        self.as_of.isoformat(), self.scope, self.origin)

    @property
    def snapshot_id(self): return identity('ar-snapshot', self.to_json())

    @property
    def reconciliation_difference(self):
        if self.control_amount is None: return None
        with localcontext() as ctx:
            ctx.prec = precision((self.total, self.control_amount))
            return self.total-self.control_amount

    @model_validator(mode='after')
    def consistent(self):
        keys = [(i.customer_id, i.invoice_id) for i in self.invoices]
        if len(set(keys)) != len(keys): raise ValueError('Duplicate customer/invoice reference')
        if any((i.as_of, i.currency) != (self.as_of, self.currency) for i in self.invoices):
            raise ValueError('Invoice currency or reporting date differs from snapshot')
        if (self.control_amount is None) != (self.control_reference is None):
            raise ValueError('Control amount requires its source reference')
        return self


def population(snapshot):
    """Partition exactly. Unknown/stale/asserted status never qualifies."""
    groups = {}
    for invoice in snapshot.invoices:
        status = invoice.status
        if invoice.due is None: reason = 'DUE_DATE_UNKNOWN'
        elif invoice.due >= snapshot.as_of: reason = 'WITHIN_TERMS'
        elif status.authority != 'SOURCE_RECORD' or status.reviewed_at != snapshot.as_of or not status.reference:
            reason = 'STATUS_UNVERIFIED'
        elif status.status != 'NONE_RECORDED': reason = status.status
        else: reason = 'QUALIFYING_OVERDUE'
        groups.setdefault(reason, []).append(invoice)
    return groups
