"""Read existing owning-store lineage; never infer source rows from prose."""
from .contracts import Ancestry
from profit_doctor.reasoning.domain.service import ScopeError


class AncestryReader:
    def __init__(self, source):
        self.source = source
        self.connection = source.connection

    def read(self, refs):
        seen, active, unresolved = set(), set(), set()
        datasets, files, primitives, records, families = set(), set(), set(), set(), set()

        def row(table, key, value):
            # All table/column names below are program-owned constants.
            result = self.connection.execute(f'SELECT * FROM {table} WHERE {key}=?', (value,)).fetchone()
            if result is None:
                return None
            result = dict(result)
            if 'client_id' in result and result['client_id'] != self.source.client_id:
                raise ScopeError('Foreign ancestry endpoint')
            return result

        def visit(resource, key):
            token = f'LEGACY_SQLITE:{resource}:{key}'
            if token in active:
                unresolved.add('cycle:' + token)
                return
            if token in seen:
                return
            seen.add(token)
            active.add(token)
            keys = {'signal': 'signal_id', 'test_execution': 'test_execution_id',
                    'diagnostic_lineage': 'diagnostic_lineage_id', 'primitive_result': 'primitive_result_id',
                    'dataset_version': 'dataset_version_id', 'source_file': 'source_file_id',
                    'dataset': 'dataset_id', 'sales_transaction': 'sales_transaction_id'}
            item = row(resource, keys[resource], key) if resource in keys else None
            if item is None:
                unresolved.add(token)
            elif resource == 'source_file':
                files.add(token)
                if not item['file_hash'] or not item['immutable_flag']:
                    unresolved.add('unverified-source:' + token)
            elif resource == 'dataset':
                datasets.add(token)
                visit('source_file', item['source_file_id'])
            elif resource == 'dataset_version':
                datasets.add(token)
                visit('dataset', item['dataset_id'])
                visit('source_file', item['source_file_id'])
            elif resource == 'sales_transaction':
                records.add(token)
                visit('dataset_version', item['dataset_version_id'])
            elif resource == 'test_execution':
                families.add(item['test_id'].split('-')[0])
            elif resource == 'signal':
                visit('test_execution', item['test_execution_id'])
                children = self.connection.execute('SELECT diagnostic_lineage_id FROM diagnostic_lineage WHERE signal_id=? ORDER BY diagnostic_lineage_id', (key,)).fetchall()
                if not children:
                    unresolved.add('no-ancestry:' + token)
                for child in children:
                    visit('diagnostic_lineage', child[0])
            elif resource == 'diagnostic_lineage':
                owner = row('signal', 'signal_id', item['signal_id'])
                if owner is None:
                    unresolved.add('missing-owner:' + token)
                follow(item)
            elif resource == 'primitive_result':
                primitives.add(token)
                children = self.connection.execute('SELECT * FROM calculation_lineage WHERE primitive_result_id=? ORDER BY lineage_id', (key,)).fetchall()
                if not children:
                    unresolved.add('no-ancestry:' + token)
                for child in children:
                    seen.add('LEGACY_SQLITE:calculation_lineage:' + child['lineage_id'])
                    follow(dict(child))
            active.remove(token)

        def follow(item):
            resources = {'DATASET_VERSION': 'dataset_version', 'SOURCE_FILE': 'source_file',
                         'PRIMITIVE_RESULT': 'primitive_result', 'SIGNAL': 'signal',
                         'SALES_TRANSACTION': 'sales_transaction', 'DATASET': 'dataset'}
            resource = resources.get(item['source_object_type'])
            if resource:
                visit(resource, item['source_object_id'])
            else:
                unresolved.add(item['source_object_type'] + ':' + item['source_object_id'])

        for ref in refs:
            if ref.client_id != self.source.client_id:
                raise ScopeError('Foreign lineage reference')
            if ref.store != 'LEGACY_SQLITE':
                unresolved.add(f'{ref.store}:{ref.resource}:{ref.source_id}')
            else:
                visit(ref.resource, ref.source_id)
        if not files:
            unresolved.add('no-resolved-source-evidence')
        return Ancestry(references=tuple(sorted(seen)), datasets=tuple(sorted(datasets)),
            source_files=tuple(sorted(files)), primitives=tuple(sorted(primitives)),
            records=tuple(sorted(records)), diagnostic_families=tuple(sorted(families)),
            unresolved=tuple(sorted(unresolved)), complete=not unresolved)


def combine(items):
    names = ('references', 'datasets', 'source_files', 'primitives', 'records', 'diagnostic_families', 'unresolved')
    return Ancestry(**{name: tuple(sorted({x for item in items for x in getattr(item, name)})) for name in names},
                    complete=bool(items) and all(item.complete for item in items))
