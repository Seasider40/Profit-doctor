"""Canonical snapshot owner; existing source registry and CMC remain authorities."""
import csv
import json
from pathlib import Path
from sqlalchemy import insert, select
from profit_doctor.persistence import receivables_schema as tables
from profit_doctor.ingestion.northstar import register_dataset_version, id4, now, sha256
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import LineageReference
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.measurement.contracts import MeasurementContext, MeasurementSlot
from profit_doctor.reasoning.measurement.source import digest
from .contracts import Snapshot, Invoice


class ReceivablesService:
    def __init__(self, contexts):
        self.contexts = contexts
        self.session = contexts.session
        self.client_id, self.run_id = contexts.client_id, contexts.run_id
        contexts.receivables = self

    def _scope(self, snapshot):
        if (snapshot.client_id, snapshot.run_id) != (self.client_id, self.run_id):
            raise ScopeError('Snapshot outside caller client/run')

    def latest(self, series_id):
        row = self.session.execute(select(tables.snapshot).where(
            tables.snapshot.c.client_id == self.client_id, tables.snapshot.c.series_id == series_id)
            .order_by(tables.snapshot.c.revision.desc()).limit(1)).mappings().one_or_none()
        if row is None: raise ScopeError('Receivables series missing or foreign')
        return self.get(row['snapshot_id'])

    @staticmethod
    def read_csv(path):
        with Path(path).open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ['snapshot']: raise ValueError('Expected governed snapshot document CSV')
            rows = list(reader)
        if len(rows) != 1: raise ValueError('Exactly one scoped snapshot per source document')
        return Snapshot.from_json(rows[0]['snapshot'])

    def ingest_csv(self, path, storage_root, *, expected_previous=None):
        supplied = self.read_csv(path)
        self._scope(supplied)
        con = self.contexts.source.connection
        job = id4('job')
        # The existing owning source registry commits ingestion independently.
        # Canonical evidence, CMC and Impact writes remain in the caller transaction.
        with con:
            con.execute('INSERT INTO ingestion_job VALUES (?,?,?,?,?,?,?)',
                        (job, self.run_id, self.client_id, now(), None, 'RUNNING', None))
            dvid, _, _, _ = register_dataset_version(con, self.client_id, job, path, 'D04_AR_SNAPSHOT',
                'receivables:'+supplied.series_id, storage_root)
            con.execute("UPDATE dataset_version SET ingestion_status='COMPLETED' WHERE dataset_version_id=?", (dvid,))
            con.execute("UPDATE ingestion_job SET status='COMPLETED',completed_at=? WHERE ingestion_job_id=?", (now(),job))
        value = Snapshot.model_validate({**supplied.model_dump(), 'dataset_version_id':dvid})
        existing = self.session.scalar(select(tables.snapshot.c.snapshot_id).where(tables.snapshot.c.snapshot_id == value.snapshot_id))
        if existing: return self.get(existing)
        rows = self.session.execute(select(tables.snapshot).where(tables.snapshot.c.client_id == self.client_id,
            tables.snapshot.c.series_id == value.series_id).order_by(tables.snapshot.c.revision.desc()).limit(1)).mappings().one_or_none()
        if (rows['snapshot_id'] if rows else None) != expected_previous:
            raise RevisionConflict('Snapshot revision requires explicit predecessor')
        connection = self.session.connection()
        if connection.dialect.name == 'sqlite' and not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql('BEGIN')
        with self.session.begin_nested():
            self.session.execute(insert(tables.snapshot).values(snapshot_id=value.snapshot_id, client_id=self.client_id,
                run_id=self.run_id, series_id=value.series_id, revision=rows['revision']+1 if rows else 1,
                previous_id=expected_previous, document=value.to_json()))
            for invoice in value.invoices:
                owner_id = self.owner_id(value, invoice)
                self.session.execute(insert(tables.invoice).values(owner_id=owner_id, snapshot_id=value.snapshot_id,
                    client_id=self.client_id, document=invoice.to_json()))
                self.contexts._persist(self.context(owner_id))
            self.session.execute(insert(tables.audit).values(event_id=identity('ar-audit',value.snapshot_id),
                snapshot_id=value.snapshot_id,client_id=self.client_id,created_at=now(),
                document=json.dumps({'actor':self.contexts.actor.model_dump(mode='json'),
                    'previous':expected_previous,'new':value.snapshot_id,'event_type':'OBJECT_SUPERSEDED' if rows else 'OBJECT_CREATED'},sort_keys=True)))
        return value

    def get(self, snapshot_id):
        row = self.session.execute(select(tables.snapshot).where(tables.snapshot.c.snapshot_id == snapshot_id,
            tables.snapshot.c.client_id == self.client_id)).mappings().one_or_none()
        if row is None: raise ScopeError('Snapshot missing or foreign')
        value = Snapshot.from_json(row['document'])
        self._scope(value)
        if (value.snapshot_id,value.series_id,value.client_id,value.run_id) != (snapshot_id,row['series_id'],row['client_id'],row['run_id']):
            raise ScopeError('Snapshot indexed envelope mismatch')
        ds = self.contexts.source.dataset(value.dataset_version_id)
        path = Path(ds['storage_location'])
        if ds['ingestion_status'] != 'COMPLETED' or not ds['immutable_flag'] or not path.is_file() or sha256(path) != ds['file_hash']:
            raise RevisionConflict('Retained snapshot source changed or unavailable')
        supplied = self.read_csv(path)
        if Snapshot.model_validate({**supplied.model_dump(),'dataset_version_id':value.dataset_version_id}) != value:
            raise RevisionConflict('Canonical snapshot disagrees with retained source')
        if value.workbook_source_id:
            original = self.contexts.source.row('source_file', value.workbook_source_id)
            if not original['immutable_flag'] or not Path(original['storage_location']).is_file() or sha256(original['storage_location']) != original['file_hash']:
                raise RevisionConflict('Original workbook changed or unavailable')
        return value

    @staticmethod
    def owner_id(snapshot, invoice):
        return identity('ar-invoice-owner', snapshot.snapshot_id, invoice.customer_id, invoice.invoice_id)

    def _invoice(self, owner_id):
        row = self.session.execute(select(tables.invoice).where(tables.invoice.c.owner_id == owner_id,
            tables.invoice.c.client_id == self.client_id)).mappings().one_or_none()
        if row is None: raise ScopeError('Invoice owner missing or foreign')
        snapshot = self.get(row['snapshot_id'])
        invoice = Invoice.from_json(row['document'])
        if invoice not in snapshot.invoices or self.owner_id(snapshot,invoice) != owner_id:
            raise ScopeError('Invoice owner disagrees with immutable snapshot')
        return snapshot, invoice

    def owner(self, owner_id):
        snapshot, invoice = self._invoice(owner_id)
        return {'snapshot_id':snapshot.snapshot_id,'run_id':snapshot.run_id,'invoice':invoice.model_dump(mode='json')}, invoice.outstanding, 'CURRENCY'

    def context(self, owner_id):
        snapshot, invoice = self._invoice(owner_id)
        ds = self.contexts.source.dataset(snapshot.dataset_version_id)
        source = LineageReference(kind='DATASET_VERSION',store='LEGACY_SQLITE',resource='dataset_version',
            source_id=snapshot.dataset_version_id,client_id=self.client_id)
        file = LineageReference(kind='SOURCE_FILE',store='LEGACY_SQLITE',resource='source_file',
            source_id=ds['source_file_id'],client_id=self.client_id)
        lineage = (source,file)
        if snapshot.workbook_source_id:
            lineage += (LineageReference(kind='SOURCE_FILE',store='LEGACY_SQLITE',resource='source_file',
                source_id=snapshot.workbook_source_id,client_id=self.client_id),)
        return MeasurementContext(client_id=self.client_id,run_id=self.run_id,
            origin=MeasurementSlot(store='CANONICAL',resource='canonical_receivable_invoice',source_id=owner_id,slot='amount'),
            origin_digest=digest(self.owner(owner_id)[0]),metric='invoice_outstanding_balance',unit='CURRENCY',currency=invoice.currency,
            economic_basis='Outstanding carrying balance; original invoice amount may be unknown',
            entity_type='CUSTOMER',entity_id=invoice.customer_id,segment_scope=invoice.invoice_id,
            period={'start':snapshot.as_of,'end':snapshot.as_of,'basis':'POINT_IN_TIME','nature':'STOCK','convention':'Reporting-date stock'},
            coverage=snapshot.coverage,coverage_basis=snapshot.coverage_basis,source_version=source,lineage=lineage,
            source_locator=invoice.source_reference,capture_method='RECEIVABLE_SNAPSHOT_V1',
            limitations=('Origin: '+snapshot.origin,'Contract/status evidence belongs to the retained snapshot; no collection forecast.'))
