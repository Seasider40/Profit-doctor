"""Read-only owning-store adapter. Never consumes legacy Fact text or status.

SQLite connections are caller-owned. Source evidence is read in the caller's
transaction; canonical persistence does not establish a distributed transaction.
"""
import hashlib
import json

from profit_doctor.reasoning.domain.contracts import LineageReference
from profit_doctor.reasoning.domain.service import ResolvedScope, ScopeError


class LegacySignalSource:
    def __init__(self, connection, client_id):
        self.connection = connection
        self.client_id = client_id

    def read(self, signal_id):
        row = self.connection.execute('SELECT * FROM signal WHERE signal_id=? AND client_id=?',
                                      (signal_id, self.client_id)).fetchone()
        if row is None:
            raise ScopeError('Source Signal missing or outside client scope')
        value = dict(row)
        execution = self.connection.execute('SELECT * FROM test_execution WHERE test_execution_id=? AND client_id=? AND run_id=? AND test_id=?',
            (value['test_execution_id'], self.client_id, value['run_id'], value['test_id'])).fetchone()
        if execution is None:
            raise ScopeError('Signal lacks a matching diagnostic execution')
        ancestry = [dict(r) for r in self.connection.execute(
            'SELECT * FROM diagnostic_lineage WHERE signal_id=? ORDER BY diagnostic_lineage_id', (signal_id,))]
        refs = [self.ref('DERIVED_ANCESTOR', 'signal', signal_id, value['run_id']),
                self.ref('DIAGNOSTIC', 'test_execution', value['test_execution_id'], value['run_id'])]
        refs.extend(self.ref('DIAGNOSTIC_LINEAGE', 'diagnostic_lineage', r['diagnostic_lineage_id'], value['run_id']) for r in ancestry)
        for item in ancestry:
            if item['source_object_type'] == 'DATASET_VERSION':
                refs.append(self.ref('DATASET_VERSION', 'dataset_version', item['source_object_id'], None))
            elif item['source_object_type'] == 'PRIMITIVE_RESULT':
                refs.append(self.ref('PRIMITIVE_RESULT', 'primitive_result', item['source_object_id'], value['run_id']))
        snapshot = {'signal': value, 'execution': dict(execution), 'ancestry': ancestry}
        digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        return value, dict(execution), tuple(refs), digest

    def ref(self, kind, resource, identity, run):
        return LineageReference(kind=kind, store='LEGACY_SQLITE', resource=resource,
                                source_id=identity, client_id=self.client_id, run_id=run)

    def resolve(self, ref):
        if ref.store != 'LEGACY_SQLITE':
            raise ScopeError('Wrong owning store')
        if (ref.kind, ref.resource) == ('DERIVED_ANCESTOR', 'signal'):
            row = self.connection.execute('SELECT client_id,run_id FROM signal WHERE signal_id=?', (ref.source_id,)).fetchone()
        elif (ref.kind, ref.resource) == ('DIAGNOSTIC', 'test_execution'):
            row = self.connection.execute('SELECT client_id,run_id FROM test_execution WHERE test_execution_id=?', (ref.source_id,)).fetchone()
        elif (ref.kind, ref.resource) == ('DIAGNOSTIC_LINEAGE', 'diagnostic_lineage'):
            row = self.connection.execute('SELECT s.client_id,s.run_id FROM diagnostic_lineage d JOIN signal s ON s.signal_id=d.signal_id WHERE d.diagnostic_lineage_id=?', (ref.source_id,)).fetchone()
        elif (ref.kind, ref.resource) == ('DATASET_VERSION', 'dataset_version'):
            row = self.connection.execute('SELECT d.client_id,NULL AS run_id FROM dataset_version v JOIN dataset d ON d.dataset_id=v.dataset_id WHERE v.dataset_version_id=?', (ref.source_id,)).fetchone()
        elif (ref.kind, ref.resource) == ('PRIMITIVE_RESULT', 'primitive_result'):
            row = self.connection.execute('SELECT client_id,run_id FROM primitive_result WHERE primitive_result_id=?', (ref.source_id,)).fetchone()
        else:
            raise ScopeError('Unsupported source reference')
        if row is None or row['client_id'] != self.client_id:
            raise ScopeError('Source reference missing or foreign')
        return ResolvedScope(row['client_id'], row['run_id'])
