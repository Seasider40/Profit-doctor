"""Trusted resolver for the frozen legacy dataset-version owner."""
import hashlib
import json
from pathlib import Path

from profit_doctor.ingestion.northstar import sha256
from profit_doctor.reasoning.domain.service import RevisionConflict, ScopeError, ResolvedScope


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, default=str).encode('utf-8')).hexdigest()


class LegacyDatasetSource:
    """Resolve existing SQLite dataset identity; never infer population policy."""

    def __init__(self, connection, client_id):
        self.connection, self.client_id = connection, client_id

    def capture_sales(self, dataset_version_id):
        if self.connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dataset_version'").fetchone() is None:
            raise ScopeError('Legacy dataset-version owner is unavailable')
        row = self.connection.execute('''SELECT
            d.dataset_id,d.client_id,d.source_file_id AS dataset_source_file_id,d.data_domain,d.logical_dataset_key,d.created_at AS dataset_created_at,
            v.dataset_version_id,v.dataset_id AS version_dataset_id,v.ingestion_job_id,v.source_file_id AS version_source_file_id,
            v.version_number,v.row_count,v.period_from,v.period_to,v.ingestion_status,v.created_at AS version_created_at,
            f.source_file_id,f.client_id AS file_client_id,f.original_filename,f.storage_location,f.file_hash,f.file_size,f.immutable_flag,f.uploaded_at,
            j.client_id AS job_client_id,j.run_id AS ingestion_run_id,j.status AS job_status
            FROM dataset_version v JOIN dataset d ON d.dataset_id=v.dataset_id
            JOIN source_file f ON f.source_file_id=v.source_file_id
            JOIN ingestion_job j ON j.ingestion_job_id=v.ingestion_job_id
            WHERE v.dataset_version_id=?''', (dataset_version_id,)).fetchone()
        if row is None or row['client_id'] != self.client_id or row['file_client_id'] != self.client_id or row['job_client_id'] != self.client_id:
            raise ScopeError('Dataset version, file or capture is missing or belongs to another client')
        value = dict(row)
        if value['data_domain'] != 'D07_SALES_TRANSACTIONS':
            raise ValueError('Only the existing D07 sales-transactions route is qualified')
        if value['version_dataset_id'] != value['dataset_id']:
            raise RevisionConflict('Dataset version is inconsistent with its registered source')
        if value['ingestion_status'] != 'COMPLETED' or value['job_status'] != 'COMPLETED':
            raise ValueError('Dataset contract requires a completed immutable import')
        if value['logical_dataset_key'] != 'northstar:transactions':
            raise ValueError('Unregistered sales provider/dataset key; no generic source inference')
        path = Path(value['storage_location'])
        if not value['immutable_flag'] or not path.is_file() or sha256(path) != value['file_hash']:
            raise RevisionConflict('Retained immutable source file is missing or no longer matches its registered hash')
        observed = self.connection.execute('''SELECT COUNT(*) AS row_count, MIN(transaction_date) AS period_from,
            MAX(transaction_date) AS period_to FROM sales_transaction
            WHERE client_id=? AND dataset_version_id=?''', (self.client_id, dataset_version_id)).fetchone()
        if int(observed['row_count']) != int(value['row_count'] or 0):
            raise RevisionConflict('Imported sales row count disagrees with retained dataset-version metadata')
        value['observed_row_count'] = int(observed['row_count'])
        value['observed_period_from'] = observed['period_from']
        value['observed_period_to'] = observed['period_to']
        # Retain a stable digest of the imported rows, not merely row count and
        # date bounds, so same-shape data edits invalidate a current snapshot.
        rows = self.connection.execute('''SELECT * FROM sales_transaction
            WHERE client_id=? AND dataset_version_id=?
            ORDER BY source_row_reference, sales_transaction_id''',
            (self.client_id, dataset_version_id)).fetchall()
        value['observed_rows_digest'] = digest([dict(row) for row in rows])
        value['snapshot_digest'] = digest(value)
        return value

    def resolve(self, ref):
        if ref.client_id != self.client_id:
            raise ScopeError('Foreign dataset lineage is prohibited')
        if ref.resource == 'dataset_version' and ref.kind.value == 'DATASET_VERSION':
            row = self.connection.execute('''SELECT d.client_id,j.run_id FROM dataset_version v
                JOIN dataset d ON d.dataset_id=v.dataset_id
                JOIN ingestion_job j ON j.ingestion_job_id=v.ingestion_job_id
                WHERE v.dataset_version_id=?''', (ref.source_id,)).fetchone()
        elif ref.resource == 'dataset' and ref.kind.value == 'DATASET':
            row = self.connection.execute('SELECT client_id,NULL AS run_id FROM dataset WHERE dataset_id=?', (ref.source_id,)).fetchone()
        elif ref.resource == 'source_file' and ref.kind.value == 'SOURCE_FILE':
            row = self.connection.execute('SELECT client_id,NULL AS run_id FROM source_file WHERE source_file_id=?', (ref.source_id,)).fetchone()
        else:
            raise ScopeError('Unsupported dataset lineage resource')
        if row is None or row['client_id'] != self.client_id:
            raise ScopeError('Dataset lineage endpoint is missing or foreign')
        return ResolvedScope(row['client_id'], ref.run_id)
