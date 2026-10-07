"""Positive evidence of absence under the frozen CASH_TRAPPED population rules."""
import csv
from datetime import date
from pathlib import Path
from typing import Literal
from pydantic import Field, model_validator

from profit_doctor.ingestion.northstar import sha256
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import Contract, FinancialDecimal, Identifier, LineageReference
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.receivables.contracts import Invoice, Snapshot, population
from .reconciliation import exact_sum
from .semantics import RegisteredSemanticSource


class ARScope(Contract):
    client_id: Identifier
    entity_id: Identifier
    ledger_id: Identifier
    as_of: date
    currency: Literal['GBP'] = 'GBP'
    population: str = Field(min_length=1)


class InvoiceReview(Contract):
    customer_id: Identifier
    invoice_id: Identifier
    reviewed_at: date
    source_reference: str = Field(min_length=1)
    dispute: Literal['NONE_RECORDED','PRESENT','UNKNOWN'] = 'UNKNOWN'
    payment_plan: Literal['NONE_RECORDED','PRESENT','UNKNOWN'] = 'UNKNOWN'
    pending_credit: Literal['NONE_RECORDED','PRESENT','UNKNOWN'] = 'UNKNOWN'


class ARExport(Contract):
    schema_version: Literal['AR-EXPORT-2.55.1'] = 'AR-EXPORT-2.55.1'
    scope: ARScope
    system_id: Identifier
    report_id: Identifier
    invoices: tuple[Invoice, ...]
    reviews: tuple[InvoiceReview, ...] = ()

    @model_validator(mode='after')
    def scoped(self):
        keys = [(i.customer_id,i.invoice_id) for i in self.invoices]
        if len(keys) != len(set(keys)):
            raise ValueError('Duplicate open item identity')
        review_keys=[(r.customer_id,r.invoice_id) for r in self.reviews]
        if len(review_keys) != len(set(review_keys)) or not set(review_keys) <= set(keys):
            raise ValueError('Review identity duplicated or outside retained population')
        if any((i.as_of,i.currency) != (self.scope.as_of,self.scope.currency) for i in self.invoices):
            raise ScopeError('Invoice reporting date/currency differs')
        return self


class ARManifest(Contract):
    schema_version: Literal['AR-MANIFEST-2.55.1'] = 'AR-MANIFEST-2.55.1'
    scope: ARScope
    system_id: Identifier
    report_id: Identifier
    record_version_id: Identifier
    open_items: tuple[tuple[Identifier,Identifier], ...] | None = None
    extraction_boundary: str = Field(min_length=1)
    extraction_query: str = Field(min_length=1)
    extraction_as_of: date
    excluded_items: tuple[tuple[Identifier,Identifier], ...] = ()
    change_kind: Literal['ORIGINAL','RESTATEMENT','CORRECTION','SUPERSESSION','UNKNOWN'] = 'UNKNOWN'
    change_reference: str | None = None
    predecessor_version_id: Identifier | None = None

    @model_validator(mode='after')
    def identities(self):
        if self.predecessor_version_id == self.record_version_id:
            raise ValueError('AR source version cannot supersede itself')
        if self.open_items is not None and len(self.open_items) != len(set(self.open_items)):
            raise ValueError('Manifest has duplicate open items')
        if set(self.open_items or ()) & set(self.excluded_items):
            raise ValueError('Included/excluded open item identities overlap')
        return self


class ARControl(Contract):
    schema_version: Literal['AR-CONTROL-2.55.1'] = 'AR-CONTROL-2.55.1'
    scope: ARScope
    amount: FinancialDecimal = Field(ge=0)
    source_reference: str = Field(min_length=1)
    basis: Literal['AR_OPEN_ITEM_CONTROL','UNKNOWN']


class AbsenceAssessment(Contract):
    qualification_contract: Literal['CASH_TRAPPED_ABSENCE_1'] = 'CASH_TRAPPED_ABSENCE_1'
    assessment_id: Identifier
    series_id: Identifier
    client_id: Identifier
    run_id: Identifier
    outcome: Literal['ABSENT_VERIFIED','QUALIFYING_BALANCE_PRESENT','NOT_ASSESSED']
    blockers: tuple[str, ...]
    scope: ARScope
    total: FinancialDecimal
    qualifying: FinancialDecimal | None
    difference: FinancialDecimal
    export: ARExport
    manifest: ARManifest
    control: ARControl
    source_versions: tuple[Identifier,Identifier,Identifier]
    zero_population_id: Identifier | None = None
    zero_source_version_id: Identifier | None = None
    evidence_digest: str
    lineage: tuple[LineageReference, ...]
    revision: int = Field(strict=True, ge=1)
    supersedes: Identifier | None = None
    limitations: tuple[str, ...] = ('Absence of qualifying overdue unconstrained balances, not absence of overdue receivables.',
        'Presence remains owned by the existing CASH_TRAPPED Impact route; no recoverability or temporal assessment.')

    @model_validator(mode='after')
    def ownership(self):
        if self.scope.client_id != self.client_id or any(value.scope != self.scope for value in (self.export,self.manifest,self.control)):
            raise ScopeError('Absence assessment and evidence scopes differ')
        if self.manifest.record_version_id != self.source_versions[0] or not self.lineage or any(
                r.client_id != self.client_id for r in self.lineage):
            raise ScopeError('Absence source identity/lineage differs')
        if (self.zero_population_id is None)!=(self.zero_source_version_id is None):
            raise ValueError('Zero population ownership and source evidence must both remain explicit')
        if self.outcome == 'ABSENT_VERIFIED' and (self.blockers or self.qualifying != 0 or self.difference != 0 or (
                not self.export.invoices and self.zero_population_id is None)):
            raise ValueError('Verified absence requires complete positive evidence, never empty/missing shortcuts')
        if self.outcome == 'QUALIFYING_BALANCE_PRESENT' and (self.blockers or self.qualifying is None or self.qualifying <= 0):
            raise ValueError('Presence indication requires a positive qualified population')
        return self


class ReceivablesAbsenceService:
    """Registered identities only. Empty exports never prove absence in this contract."""
    def __init__(self, connection, client_id, run_id, authority_resolver=None):
        self.sources = RegisteredSemanticSource(connection,client_id,authority_resolver)
        self.connection,self.client_id,self.run_id = connection,client_id,run_id
        row = connection.execute('SELECT client_id FROM engine_run WHERE run_id=?',(run_id,)).fetchone()
        if row is None or row[0] != client_id:
            raise ScopeError('Absence assessment requires a scoped run')

    def _document(self, version, kind):
        profile = 'production-evidence:'+kind+'-1'
        meta = self.sources.metadata(version,profile)
        with Path(meta['storage_location']).open(encoding='utf-8-sig',newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ['evidence']:
                raise ValueError('Exact evidence column required')
            rows = list(reader)
        if len(rows) != 1 or meta['row_count'] != 1 or set(rows[0]) != {'evidence'}:
            raise ValueError('Exactly one registered evidence document required')
        if kind=='ar-zero':
            from .zero import ZeroAREvidence
            model=ZeroAREvidence
        else:
            model = {'ar-export':ARExport,'ar-manifest':ARManifest,'ar-control':ARControl}[kind]
        value = model.from_json(rows[0]['evidence'])
        if value.scope.client_id != self.client_id:
            raise ScopeError('Foreign receivables evidence')
        if sha256(Path(meta['storage_location'])) != meta['file_hash']:
            raise RevisionConflict('Evidence changed during read')
        authority = self.sources.authority_resolver(self.client_id,version,profile,meta['file_hash'])
        return value,meta,authority

    def assess(self, export_version, manifest_version, control_version, *, previous=None, zero_version=None):
        export,em,ea = self._document(export_version,'ar-export')
        manifest,mm,ma = self._document(manifest_version,'ar-manifest')
        control,cm,ca = self._document(control_version,'ar-control')
        if export.scope != manifest.scope or export.scope != control.scope:
            raise ScopeError('AR manifest/export/control scope differs')
        if (manifest.record_version_id,manifest.system_id,manifest.report_id) != (export_version,export.system_id,export.report_id):
            raise ScopeError('Manifest does not identify the registered export')
        blockers = []
        zero=None
        if zero_version is not None:
            from .zero import ZeroARSourceQualifier
            zero=ZeroARSourceQualifier(self.connection,self.client_id,self.run_id,self.sources.authority_resolver).qualify(zero_version)
            if (zero.proof.export_version_id,zero.proof.manifest_version_id,zero.proof.control_version_id)!=(
                    export_version,manifest_version,control_version) or zero.scope!=export.scope:
                raise ScopeError('Zero AR proof does not own this absence population')
        if (ea,ma,ca) != ('SOURCE_DATA','SOURCE_DATA','SOURCE_DATA'):
            blockers.append('SOURCE_AUTHORITY_INSUFFICIENT')
        ids = {(i.customer_id,i.invoice_id) for i in export.invoices}
        if not export.invoices and zero is None:
            blockers.append('EMPTY_EXPORT_IS_NOT_ABSENCE')
        if manifest.open_items is None or set(manifest.open_items) != ids or manifest.excluded_items:
            blockers.append('COMPLETE_OPEN_ITEM_MEMBERSHIP_NOT_PROVEN')
        if manifest.extraction_boundary != export.scope.population or manifest.extraction_as_of != export.scope.as_of:
            blockers.append('EXTRACTION_BOUNDARY_OR_DATE_UNVERIFIED')
        if control.basis != 'AR_OPEN_ITEM_CONTROL' or em['file_hash'] == cm['file_hash']:
            blockers.append('INDEPENDENT_AR_CONTROL_REQUIRED')
        total = exact_sum(i.outstanding for i in export.invoices)
        difference = exact_sum((total,control.amount.copy_negate()))
        if difference != 0:
            blockers.append('AR_CONTROL_MISMATCH')
        for invoice in export.invoices:
            # Require complete source review even within terms: frozen population
            # short-circuiting within-terms is not a proof of status completeness.
            s = invoice.status
            if invoice.due is None:
                blockers.append('DUE_DATE_UNKNOWN:'+invoice.invoice_id)
            if s.authority != 'SOURCE_RECORD' or s.reviewed_at != export.scope.as_of or not s.reference or s.status == 'UNKNOWN':
                blockers.append('STATUS_REVIEW_INCOMPLETE:'+invoice.invoice_id)
            review=next((r for r in export.reviews if (r.customer_id,r.invoice_id)==(invoice.customer_id,invoice.invoice_id)),None)
            if review is None or review.reviewed_at != export.scope.as_of or 'UNKNOWN' in (
                    review.dispute,review.payment_plan,review.pending_credit):
                blockers.append('CONSTRAINT_REVIEW_INCOMPLETE:'+invoice.invoice_id)
            else:
                present={status for field,status in (('dispute','ACTIVE_DISPUTE'),('payment_plan','AGREED_PAYMENT_PLAN'),
                    ('pending_credit','CREDIT_NOTE_PENDING')) if getattr(review,field)=='PRESENT'}
                if s.status not in (present or {'NONE_RECORDED'}):
                    blockers.append('CONSTRAINT_REVIEW_CONTRADICTS_FROZEN_STATUS:'+invoice.invoice_id)
        roots = set()
        rows = self.connection.execute('''SELECT v.dataset_version_id FROM dataset_version v JOIN dataset d
            ON d.dataset_id=v.dataset_id WHERE d.client_id=? AND d.logical_dataset_key=? AND v.ingestion_status='COMPLETED' ''',
            (self.client_id,'production-evidence:ar-manifest-1')).fetchall()
        for (version,) in rows:
            candidate,_,_ = self._document(version,'ar-manifest')
            if candidate.scope == manifest.scope and candidate.system_id == manifest.system_id and candidate.predecessor_version_id is None:
                roots.add(candidate.record_version_id)
        revision_ok = bool(manifest.change_reference) and manifest.change_kind == 'ORIGINAL' and not manifest.predecessor_version_id and len(roots)==1
        if previous:
            previous = AbsenceAssessment.from_json(previous.to_json())
            if previous.client_id != self.client_id or previous.scope != export.scope or previous.export.system_id != export.system_id or previous.export.report_id != export.report_id:
                raise ScopeError('Absence revision belongs to another snapshot scope')
            revision_ok = bool(manifest.change_reference) and manifest.change_kind in ('RESTATEMENT','CORRECTION','SUPERSESSION') and manifest.predecessor_version_id == previous.source_versions[0]
        refs = tuple(r for v,m in ((export_version,em),(manifest_version,mm),(control_version,cm)) for r in self.sources.refs(v,m))
        if zero:refs=tuple(dict.fromkeys((*refs,*zero.lineage)))
        digest = identity('ar-evidence-2.55.1',export.to_json(),manifest.to_json(),control.to_json(),
            ea,ma,ca,sorted(roots),export_version,manifest_version,control_version,*((zero.to_json(),) if zero else ()))
        if previous and previous.evidence_digest == digest:
            return previous
        if not revision_ok:
            blockers.append('SNAPSHOT_REVISION_AUTHORITY_UNRESOLVED')
        qualifying = None
        if not blockers and zero is not None:
            qualifying=exact_sum(())
        elif not blockers:
            snapshot = Snapshot(client_id=self.client_id,run_id=self.run_id,ledger_id=export.scope.ledger_id,
                entity=export.scope.entity_id,as_of=export.scope.as_of,scope=export.scope.population,
                coverage='COMPLETE',coverage_basis=manifest.extraction_boundary,source_version=export_version,
                origin='REAL_SOURCE',invoices=export.invoices,control_amount=control.amount,
                control_reference=control.source_reference,dataset_version_id=export_version)
            qualifying = exact_sum(i.outstanding for i in population(snapshot).get('QUALIFYING_OVERDUE',()))
        series = identity('ar-absence-owner-2.55.1',export.scope.to_json())
        revision = previous.revision+1 if previous else 1
        return AbsenceAssessment(assessment_id=identity('ar-absence-2.55.1',series,digest,revision),series_id=series,
            client_id=self.client_id,run_id=self.run_id,
            outcome='NOT_ASSESSED' if blockers else 'ABSENT_VERIFIED' if qualifying == 0 else 'QUALIFYING_BALANCE_PRESENT',
            blockers=tuple(blockers),scope=export.scope,total=total,qualifying=qualifying,difference=difference,
            export=export,manifest=manifest,control=control,source_versions=(export_version,manifest_version,control_version),
            zero_population_id=zero.zero_id if zero else None,zero_source_version_id=zero_version,
            evidence_digest=digest,lineage=refs,revision=revision,supersedes=previous.assessment_id if previous else None)
