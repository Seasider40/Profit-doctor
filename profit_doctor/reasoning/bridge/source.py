"""Read-only BIQ resolver over existing canonical/owning-store identities.

No coverage/restatement certificate is bound to these canonical source slots.
Those fields deliberately remain unknown. FULL diagnostic eligibility, file
immutability and successful ingestion are not substitutes for these certificates.
The caller owns both transactions, Session and connections.
"""
import hashlib
import json

from profit_doctor.reasoning.canonical.contracts import CanonicalFact
from profit_doctor.reasoning.domain.service import ScopeError
from profit_doctor.reasoning.graph.service import EvidenceGraph
from .qualification import (BridgeFamily, ComparisonInput, Coverage, Endpoint,
                            Period, RetainedSource, qualify)


class BridgeInputResolver:
    def __init__(self, session, client_id, run_id, actor, source):
        with session.no_autoflush:
            self.graph = EvidenceGraph(session, client_id, run_id, actor, source)
        self.session, self.source, self.run_id = session, source, run_id

    def _snapshot(self, fact, node):
        """Digest actual retained lineage rows, including primitive dates.

        Dataset metadata dates describe the dataset, not the two measurement
        windows. Source paths/narrative are never parsed into semantic evidence.
        Materialise results before validation to release SQLite cursor resources.
        """
        keys = {'signal': 'signal_id', 'test_execution': 'test_execution_id',
                'diagnostic_lineage': 'diagnostic_lineage_id',
                'calculation_lineage': 'lineage_id', 'primitive_result': 'primitive_result_id',
                'dataset_version': 'dataset_version_id', 'dataset': 'dataset_id',
                'source_file': 'source_file_id', 'sales_transaction': 'sales_transaction_id'}
        snapshots, semantics = [], []
        for ref in node.ancestry.references:
            store, table, key = ref.split(':', 2)
            if store != 'LEGACY_SQLITE' or table not in keys:
                continue
            row = self.source.connection.execute(
                f'SELECT * FROM {table} WHERE {keys[table]}=?', (key,)).fetchone()
            if row is None:
                raise ScopeError('Retained ancestry disappeared during qualification')
            item = dict(row)
            if 'client_id' in item and item['client_id'] != self.source.client_id:
                raise ScopeError('Foreign qualification ancestry')
            snapshots.append((ref, item))
            if table in ('dataset_version', 'primitive_result'):
                fields = {name: item[name] for name in RetainedSource.model_fields if name in item}
                semantics.append(RetainedSource(reference=ref, **fields))
        payload = {'fact': json.loads(fact.to_json()), 'ancestry': node.ancestry.model_dump(mode='json'),
                   'retained_sources': snapshots}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        return digest, tuple(semantics)

    def _endpoint(self, fact: CanonicalFact, node, slot, snapshot):
        measurement = getattr(fact, slot)
        if measurement is None:
            raise ValueError('Required endpoint measurement is absent')
        # Do not copy the combined Signal or dataset interval into a slot period.
        # Source metric conventions establish nature only, not dates/coverage.
        nature = {'revenue': 'FLOW', 'contribution_0': 'FLOW',
                  'contribution_0_margin': 'RATE', 'bs_accounts_receivable': 'STOCK',
                  'bs_accounts_payable': 'STOCK', 'bs_inventory': 'STOCK'}.get(measurement.metric, 'UNKNOWN')
        versions = tuple(r for r in node.ancestry.datasets if r.startswith('LEGACY_SQLITE:dataset_version:'))
        return Endpoint(fact_id=fact.object_id, client_id=fact.client_id, run_id=fact.run_id,
            measurement=measurement, entity_type=fact.scope.entity_type, entity_id=fact.scope.entity_id,
            period=Period(nature=nature),
            coverage=Coverage.PARTIAL if fact.eligibility.startswith('PARTIAL') else Coverage.UNKNOWN,
            source_versions=versions, lineage=fact.lineage, lineage_complete=node.ancestry.complete,
            source_snapshot=snapshot[0], retained_sources=snapshot[1], eligible=node.eligible,
            limitations=fact.limitations + ('Separate measurement periods, coverage and accounting/restatement basis are unqualified.',))

    def assess(self, family, opening_fact_id, closing_fact_id=None):
        """Resolve comparison/observed slots (same Fact) or observed slots (pair).

        There is intentionally no caller override for period, completeness,
        restatement or economic basis. No SQL writes, flush, commit or cleanup.
        """
        family = BridgeFamily(family)
        closing_fact_id = closing_fact_id or opening_fact_id
        with self.session.no_autoflush:
            a = self.graph.canonical.get_fact(opening_fact_id)
            b = self.graph.canonical.get_fact(closing_fact_id)
            na = self.graph.node(a.object_id)
            nb = self.graph.node(b.object_id)
            if b.run_id != self.run_id:
                raise ScopeError('Closing Fact is outside the qualification run')
            sa, sb = self._snapshot(a, na), self._snapshot(b, nb)
            opening = self._endpoint(a, na, 'comparison' if a.object_id == b.object_id else 'observed', sa)
            closing = self._endpoint(b, nb, 'observed', sb)
            return qualify(ComparisonInput(family=family, opening=opening, closing=closing))
