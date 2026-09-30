"""Read authoritative accounting source declarations, never infer missing policy."""
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

from profit_doctor.calc.primitive_engine import ALIASES
from profit_doctor.ingestion.northstar import sha256
from profit_doctor.reasoning.bridge.qualification import Period
from profit_doctor.reasoning.domain.contracts import LineageReference
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from .contracts import MeasurementContext, MeasurementSlot


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def accounting_metric(row):
    selected = {'SELECTED_REVENUE': ('Selected population revenue', 'financial_revenue'),
                'SELECTED_CONTRIBUTION_0': ('Selected population Contribution 0', 'contribution_0')}
    if row['statement_type'] == 'PNL' and row['line_code'] in selected and row['line_name'] == selected[row['line_code']][0]:
        return selected[row['line_code']][1]
    # Explicit additive source measure; never an alias for gross profit.
    if row['statement_type'] == 'PNL' and row['line_code'] == 'CONTRIBUTION_0' and row['line_name'] == 'Contribution 0':
        return 'contribution_0'
    options = (('REVENUE', 'financial_revenue'), ('DIRECT_COST', 'financial_direct_cost'),
               ('GROSS_PROFIT', 'financial_gross_profit'), ('EBITDA', 'financial_ebitda')) if row['statement_type'] == 'PNL' else (
               ('AR', 'bs_accounts_receivable'), ('AP', 'bs_accounts_payable'),
               ('INVENTORY', 'bs_inventory'), ('CASH', 'bs_cash'))
    matches = [metric for key, metric in options if
               row['line_code'].strip().upper() in ALIASES[key] or row['line_name'].strip().upper() in ALIASES[key]]
    if len(matches) != 1:
        raise ValueError('Accounting metric is unknown or ambiguous; no generic mapping')
    return matches[0]


class AccountingContextSource:
    def __init__(self, connection, client_id):
        self.connection, self.client_id = connection, client_id

    def row(self, resource, source_id):
        keys = {'financial_statement_line': 'statement_line_id', 'primitive_result': 'primitive_result_id',
                'signal': 'signal_id', 'source_revision': 'revision_id', 'source_file': 'source_file_id'}
        if resource not in keys:
            raise ValueError('Unsupported owning resource')
        if resource == 'source_revision' and self.connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_revision'").fetchone() is None:
            raise ScopeError('Existing source revision store is unavailable; no revision invented')
        result = self.connection.execute(f'SELECT * FROM {resource} WHERE {keys[resource]}=?', (source_id,)).fetchone()
        if result is None or result['client_id'] != self.client_id:
            raise ScopeError('Measurement source missing or foreign')
        return dict(result)

    def dataset(self, version_id):
        result = self.connection.execute('''SELECT v.*,d.client_id,d.logical_dataset_key,
            f.file_hash,f.storage_location,f.immutable_flag,f.client_id AS file_client
            FROM dataset_version v JOIN dataset d ON d.dataset_id=v.dataset_id
            JOIN source_file f ON f.source_file_id=v.source_file_id
            WHERE v.dataset_version_id=?''', (version_id,)).fetchone()
        if result is None or result['client_id'] != self.client_id or result['file_client'] != self.client_id:
            raise ScopeError('Dataset/source file missing or foreign')
        return dict(result)

    def capture(self, statement_line_id, run_id, *, supersedes=None):
        row = self.row('financial_statement_line', statement_line_id)
        ds = self.dataset(row['dataset_version_id'])
        if ds['ingestion_status'] != 'COMPLETED':
            raise ValueError('Source ingestion is incomplete')
        ref = LineageReference(kind='DATASET_VERSION', store='LEGACY_SQLITE', resource='dataset_version',
            source_id=row['dataset_version_id'], client_id=self.client_id)
        file_ref = LineageReference(kind='SOURCE_FILE', store='LEGACY_SQLITE', resource='source_file',
            source_id=ds['source_file_id'], client_id=self.client_id)
        record_ref = LineageReference(kind='CANONICAL_RECORD', store='LEGACY_SQLITE', resource='financial_statement_line',
            source_id=statement_line_id, client_id=self.client_id)
        declarations = {}
        path = Path(ds['storage_location'])
        retained = path.is_file() and bool(ds['immutable_flag'])
        if retained:
            if sha256(path) != ds['file_hash']:
                raise RevisionConflict('Retained source file hash changed')
            with path.open(newline='', encoding='utf-8-sig') as stream:
                source_rows = list(csv.DictReader(stream))
            index = row['source_row_reference'] - 2
            if not 0 <= index < len(source_rows):
                raise RevisionConflict('Source row reference no longer resolves')
            declarations = source_rows[index]
            if (declarations.get('period_end'), declarations.get('line_code'), declarations.get('line_name')) != (
                    row['period_end'], row['line_code'], row['line_name']) or Decimal(declarations['amount']) != Decimal(row['amount']):
                raise RevisionConflict('Source row and retained measurement disagree')
        def declared(key):
            val = declarations.get(key)
            return val.strip() if val and val.strip() else None
        parent_ref = None
        parent_file = None
        if declared('source_workbook_id'):
            parent_file = self.row('source_file', declared('source_workbook_id'))
            parent_path = Path(parent_file['storage_location'])
            if not parent_path.is_file() or not parent_file['immutable_flag'] or sha256(parent_path) != parent_file['file_hash']:
                raise RevisionConflict('Original workbook is unavailable or changed')
            parent_ref = LineageReference(kind='SOURCE_FILE', store='LEGACY_SQLITE', resource='source_file',
                source_id=parent_file['source_file_id'], client_id=self.client_id)
        stock = row['statement_type'] == 'BALANCE_SHEET'
        # A stock end is an as-of. A flow end does not establish its start.
        period = Period(start=row['period_end'] if stock else declared('period_start'), end=row['period_end'],
            basis=declared('reporting_basis') or ('POINT_IN_TIME' if stock else 'UNKNOWN'),
            convention=declared('reporting_convention'), nature='STOCK' if stock else 'FLOW')
        if stock and period.basis != 'POINT_IN_TIME':
            raise ValueError('Balance-sheet stock cannot claim a flow reporting basis')
        currency = declared('currency')
        if currency not in (None, 'GBP'):
            raise ValueError('Currency unsupported by the frozen numerical accounting path')
        revision = None
        if declared('source_revision_id'):
            revision = self.row('source_revision', declared('source_revision_id'))
            # The file explicitly identifies the existing revision AND its
            # payload hash. This retains a declared association, not proof of
            # accounting comparability between different source vintages.
            if revision['logical_source_key'] != ds['logical_dataset_key'] or revision['content_hash'] != declared('source_revision_content_hash'):
                raise ValueError('Source revision is not explicitly bound to this dataset snapshot')
        snapshot = digest({'row': row, 'dataset': ds, 'source_revision': revision, 'parent_file': parent_file})
        return MeasurementContext(client_id=self.client_id, run_id=run_id,
            origin=MeasurementSlot(store='LEGACY_SQLITE', resource='financial_statement_line', source_id=statement_line_id, slot='amount'),
            origin_digest=snapshot, metric=accounting_metric(row), unit='CURRENCY', currency=currency,
            economic_basis=declared('economic_basis'), segment_scope=declared('segment_scope'), period=period,
            entity_type=declared('entity_type'), entity_id=declared('entity_id'),
            coverage=declared('coverage') or 'UNKNOWN', coverage_basis=declared('coverage_basis'),
            source_version=ref, lineage=(ref, file_ref, record_ref) + ((parent_ref,) if parent_ref else ()), supersedes=supersedes,
            source_locator=declared('source_locator'),
            source_revision_id=revision['revision_id'] if revision else None,
            source_revision_digest=digest(revision) if revision else None,
            revision_state=revision['revision_type'] if revision else 'UNKNOWN_UNBOUND',
            prior_source_revision_id=revision['prior_revision_id'] if revision else None,
            capture_method='ACCOUNTING_CSV_EXPLICIT_V1' if retained else 'RETAINED_ACCOUNTING_V1',
            limitations=() if retained else ('Original source bytes unavailable; declaration backfill withheld.',))
