"""Explicit registered CSV transport; no completeness or authority promotion."""
import csv
from datetime import date
from pathlib import Path

from profit_doctor.ingestion.northstar import sha256
from profit_doctor.reasoning.bridge.qualification import Period
from profit_doctor.reasoning.domain.contracts import LineageReference
from profit_doctor.reasoning.domain.service import RevisionConflict, ScopeError
from .contracts import EvidenceScope, SourceAmount


FIELDS = ('record_id', 'account_code', 'record_kind', 'amount', 'entity_id', 'ledger_id',
          'population', 'period_start', 'period_end', 'time_basis', 'currency', 'definition')
DOMAIN = 'PRODUCTION_ACCOUNTING_RECORDS_V255'
PROVIDER = 'production-evidence:accounting-records-1'


class RegisteredAccountingSource:
    """Read retained raw records through the existing ingestion registry.

    Caller owns the legacy connection. Registration/import commits remain with
    its existing owner. No new source identity store or caller verification flag.
    Population/definition fields are transported labels, not verified claims.
    """

    def __init__(self, connection, client_id):
        self.connection, self.client_id = connection, client_id

    def read(self, version_id):
        row = self.connection.execute('''SELECT d.client_id, d.data_domain, d.logical_dataset_key,
            v.dataset_version_id, v.row_count, v.ingestion_status,
            f.source_file_id, f.client_id AS file_client, f.storage_location, f.file_hash,
            f.immutable_flag, j.client_id AS job_client, j.status AS job_status
            FROM dataset_version v JOIN dataset d ON d.dataset_id=v.dataset_id
            JOIN source_file f ON f.source_file_id=v.source_file_id
            JOIN ingestion_job j ON j.ingestion_job_id=v.ingestion_job_id
            WHERE v.dataset_version_id=?''', (version_id,)).fetchone()
        if row is None or any(row[key] != self.client_id for key in ('client_id', 'file_client', 'job_client')):
            raise ScopeError('Registered accounting source is missing or foreign')
        if (row['data_domain'], row['logical_dataset_key']) != (DOMAIN, PROVIDER):
            raise ScopeError('Unregistered source profile; no filename or fuzzy mapping fallback')
        if row['ingestion_status'] != 'COMPLETED' or row['job_status'] != 'COMPLETED':
            raise ScopeError('Accounting source requires completed registration')
        path = Path(row['storage_location'])
        if not row['immutable_flag'] or not path.is_file() or sha256(path) != row['file_hash']:
            raise RevisionConflict('Retained accounting file is absent, mutable or changed')
        refs = (
            LineageReference(kind='DATASET_VERSION', store='LEGACY_SQLITE', resource='dataset_version',
                source_id=version_id, client_id=self.client_id),
            LineageReference(kind='SOURCE_FILE', store='LEGACY_SQLITE', resource='source_file',
                source_id=row['source_file_id'], client_id=self.client_id),
        )
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != FIELDS:
                raise ValueError('ACCOUNTING_RECORDS_1 requires its exact ordered schema')
            raw = list(reader)
        if len(raw) != row['row_count']:
            raise RevisionConflict('Retained accounting row count differs from registration')
        records = []
        for data in raw:
            if None in data or any(v is None or v == '' for v in data.values()):
                raise ValueError('Malformed or missing accounting field; no implicit defaults')
            start, end = date.fromisoformat(data['period_start']), date.fromisoformat(data['period_end'])
            kind = data['record_kind']
            stock = kind in ('TB_CLOSING', 'BALANCE_SHEET', 'RECEIVABLE')
            if data['time_basis'] != ('POINT_IN_TIME' if stock else 'MONTHLY'):
                raise ValueError('Source record kind conflicts with reporting basis')
            records.append(SourceAmount(record_id=data['record_id'], account_code=data['account_code'],
                kind=kind, amount=data['amount'], scope=EvidenceScope(client_id=self.client_id,
                    entity_id=data['entity_id'], ledger_id=data['ledger_id'], population=data['population'],
                    period=Period(start=start, end=end, basis=data['time_basis'], nature='STOCK' if stock else 'FLOW'),
                    currency=data['currency'], definition=data['definition']), lineage=refs))
        if len({r.record_id for r in records}) != len(records):
            raise ValueError('Duplicate accounting record identity')
        # Also catch changes during read; this is freshness, not source authenticity.
        if sha256(path) != row['file_hash']:
            raise RevisionConflict('Retained accounting source changed during read')
        return tuple(records)
