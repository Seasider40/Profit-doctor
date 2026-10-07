"""Immutable context authority. Caller owns transaction and both stores."""
import json
from decimal import Decimal

from sqlalchemy import insert, select

from profit_doctor.persistence import measurement_schema as tables
from profit_doctor.reasoning.canonical.service import CanonicalService, identity
from profit_doctor.reasoning.canonical.source import LegacySignalSource
from profit_doctor.reasoning.domain.contracts import Actor, now
from profit_doctor.reasoning.domain.service import FoundationService, ScopeError, RevisionConflict
from .contracts import ContextBinding, MeasurementContext, MeasurementSlot
from .source import AccountingContextSource, digest
from profit_doctor.reasoning.bridge.qualification import Period


class MeasurementContextService:
    def __init__(self, session, client_id, run_id, actor, connection):
        self.session, self.client_id, self.run_id = session, client_id, run_id
        self.actor = Actor.from_json(actor.to_json())
        self.source = AccountingContextSource(connection, client_id)
        self.foundation = FoundationService(session, client_id, self.actor)
        self.foundation._run(run_id)
        self.receivables = None
        self.monthly = None
        self.margins = None
        self.workbook_providers = ()
        if run_id is None:
            raise ScopeError('Context capture requires a scoped run')

    def _audit(self, context, binding=None):
        event_id = identity('measurement-audit', context.context_id, binding.binding_id if binding else None)
        document = json.dumps({'event_type': 'OBJECT_CREATED' if binding is None else 'EVIDENCE_LINKED',
            'actor': self.actor.model_dump(mode='json'), 'context_id': context.context_id,
            'binding_id': binding.binding_id if binding else None,
            'supersedes': context.supersedes}, sort_keys=True, separators=(',', ':'))
        self.session.execute(insert(tables.measurement_audit).values(event_id=event_id,
            client_id=self.client_id, context_id=context.context_id,
            binding_id=binding.binding_id if binding else None,
            created_at=now().isoformat(), document=document))

    def get_context(self, context_id, *, current=False):
        row = self.session.execute(select(tables.measurement_context).where(
            tables.measurement_context.c.context_id == context_id,
            tables.measurement_context.c.client_id == self.client_id)).mappings().one_or_none()
        if row is None:
            raise ScopeError('Context missing or foreign')
        value = MeasurementContext.from_json(row['document'])
        if (value.context_id, value.client_id, value.run_id, value.supersedes) != (
                row['context_id'], row['client_id'], row['run_id'], row['supersedes']):
            raise ScopeError('Context payload disagrees with indexed envelope')
        if current:
            reproduced = (self._margin_provider().get_margin(value.origin.source_id, current=True).context if value.capture_method == 'QUALIFIED_C0_MARGIN_V255' else
                          self._monthly_provider().context(value.origin.source_id) if value.capture_method == 'QUALIFIED_MONTHLY_SOURCE_V255' else
                          self._receivable_provider().context(value.origin.source_id) if value.capture_method == 'RECEIVABLE_SNAPSHOT_V1' else
                          self._fact_context(value.origin) if value.capture_method == 'RETAINED_FACT_SLOT_V1' else
                          self.source.capture(value.origin.source_id, value.run_id, supersedes=value.supersedes))
            if reproduced != value:
                raise RevisionConflict('Context no longer matches its retained source snapshot')
        return value

    def capture_accounting(self, statement_line_id, *, supersedes=None):
        value = self.source.capture(statement_line_id, self.run_id, supersedes=supersedes)
        root_row, _, _ = self._owner(value.origin)
        previous_binding = self.session.scalar(select(tables.measurement_binding.c.binding_id).where(
            tables.measurement_binding.c.client_id == self.client_id,
            tables.measurement_binding.c.owner_key == self._owner_key(value.origin),
            tables.measurement_binding.c.owner_digest == digest(root_row)))
        if previous_binding:
            old = self.get_context(self.get_binding(previous_binding).context_id, current=True)
            if old.model_dump(exclude={'run_id'}) != value.model_dump(exclude={'run_id'}):
                raise RevisionConflict('An unchanged source slot already has a different context')
            return old
        if supersedes:
            old = self.get_context(supersedes)
            old_ds = self.source.dataset(old.source_version.source_id)
            new_ds = self.source.dataset(value.source_version.source_id)
            if (old.metric, old.entity_type, old.entity_id, old.origin.slot, old_ds['dataset_id']) != (
                    value.metric, value.entity_type, value.entity_id, value.origin.slot, new_ds['dataset_id']):
                raise ScopeError('Context revision must retain its measurement family and logical source')
            if old.period != value.period:
                raise ValueError('Different reporting period is a new measurement, not a silent restatement')
        return self._persist(value)

    def _persist(self, value):
        exists = self.session.scalar(select(tables.measurement_context.c.context_id).where(
            tables.measurement_context.c.context_id == value.context_id))
        if exists:
            if self.get_context(exists) != value:
                raise RevisionConflict('Existing context identity changed')
        else:
            self.session.execute(insert(tables.measurement_context).values(context_id=value.context_id,
                client_id=self.client_id, run_id=self.run_id, supersedes=value.supersedes, document=value.to_json()))
            self._audit(value)
        self._bind(value, value.origin)
        return value

    def _fact_context(self, owner):
        if owner.resource != 'canonical_fact':
            raise ValueError('Fact backfill requires an exact canonical measurement slot')
        row, _, _ = self._owner(owner)
        from profit_doctor.reasoning.canonical.contracts import CanonicalFact
        fact = CanonicalFact.model_validate(row)
        if fact.run_id != self.run_id:
            raise ScopeError('Fact context backfill requires its originating run')
        refs = tuple(r for r in fact.lineage if r.kind == 'DATASET_VERSION')
        if len(refs) != 1:
            raise ValueError('Fact needs an unambiguous retained dataset version; no ancestry guess')
        self.source.dataset(refs[0].source_id)
        source = LegacySignalSource(self.source.connection, self.client_id)
        for ref in fact.lineage:
            source.resolve(ref)
        measurement = getattr(fact, owner.slot)
        nature = {'revenue': 'FLOW', 'contribution_0': 'FLOW', 'contribution_0_margin': 'RATE',
                  'contribution_0_margin_change': 'RATE', 'revenue_share': 'RATE'}.get(measurement.metric, 'UNKNOWN')
        return MeasurementContext(client_id=self.client_id, run_id=fact.run_id, origin=owner,
            origin_digest=digest(row), metric=measurement.metric, unit=measurement.unit,
            currency=measurement.currency, entity_type=fact.scope.entity_type, entity_id=fact.scope.entity_id,
            period=Period(nature=nature), source_version=refs[0], lineage=fact.lineage,
            capture_method='RETAINED_FACT_SLOT_V1',
            limitations=('Frozen mapped unit/currency retained; source accounting, per-slot period and coverage remain unqualified.',))

    def backfill_fact_slot(self, fact_id, slot):
        owner = MeasurementSlot(store='CANONICAL', resource='canonical_fact', source_id=fact_id, slot=slot)
        return self._persist(self._fact_context(owner))

    def capture_dataset(self, dataset_version_id):
        self.source.dataset(dataset_version_id)
        rows = self.source.connection.execute('SELECT statement_line_id FROM financial_statement_line WHERE client_id=? AND dataset_version_id=? ORDER BY source_row_reference',
            (self.client_id, dataset_version_id)).fetchall()
        return tuple(self.capture_accounting(row[0]) for row in rows)

    def _owner(self, owner):
        owner = MeasurementSlot.from_json(owner.to_json())
        if owner.resource == 'canonical_monthly_c0_margin':
            return self._margin_provider().owner(owner.source_id)
        if owner.resource == 'canonical_monthly_measurement':
            return self._monthly_provider().owner(owner.source_id)
        if owner.resource == 'canonical_receivable_invoice':
            return self._receivable_provider().owner(owner.source_id)
        if owner.store == 'CANONICAL':
            service = CanonicalService(self.session, self.client_id, self.actor,
                LegacySignalSource(self.source.connection, self.client_id))
            fact = service.get_fact(owner.source_id)
            _, _, _, source_digest = service.source.read(fact.source_signal_id)
            if source_digest != fact.source_digest or fact.state != 'OBSERVED':
                raise RevisionConflict('Fact is stale or inactive')
            measurement = getattr(fact, owner.slot)
            if measurement is None:
                raise ValueError('Fact measurement slot is absent')
            return fact.model_dump(mode='json'), measurement.value, measurement.unit.value
        row = self.source.row(owner.resource, owner.source_id)
        if owner.resource in ('primitive_result', 'signal'):
            table, key, order = ('calculation_lineage', 'primitive_result_id', 'lineage_id') if owner.resource == 'primitive_result' else (
                'diagnostic_lineage', 'signal_id', 'diagnostic_lineage_id')
            row['_retained_lineage'] = [dict(r) for r in self.source.connection.execute(
                f'SELECT * FROM {table} WHERE {key}=? ORDER BY {order}', (owner.source_id,)).fetchall()]
        columns = {'amount': 'amount', 'numeric_value': 'numeric_value',
                   'observed': 'observed_value', 'comparison': 'comparison_value', 'derived': 'variance_value'}
        raw = row[columns[owner.slot]]
        if raw is None:
            raise ValueError('Source measurement slot is absent')
        return row, Decimal(raw), row.get('unit', 'GBP')

    def _receivable_provider(self):
        from profit_doctor.reasoning.receivables.service import ReceivablesService
        if not isinstance(self.receivables, ReceivablesService) or self.receivables.contexts is not self:
            raise ScopeError('Registered receivables owner required')
        return self.receivables

    def _monthly_provider(self):
        from profit_doctor.reasoning.production_evidence.service import ProductionEvidenceService
        if not isinstance(self.monthly, ProductionEvidenceService) or self.monthly.contexts is not self:
            raise ScopeError('Registered monthly owner required')
        return self.monthly

    def _margin_provider(self):
        from profit_doctor.reasoning.production_evidence.margin import MarginQualificationService
        if not isinstance(self.margins, MarginQualificationService) or self.margins.contexts is not self:
            raise ScopeError('Registered exact monthly margin owner required')
        return self.margins

    @staticmethod
    def _owner_key(owner):
        return ':'.join((owner.store, owner.resource, owner.source_id, owner.slot))

    def get_binding(self, binding_id):
        row = self.session.execute(select(tables.measurement_binding).where(
            tables.measurement_binding.c.binding_id == binding_id,
            tables.measurement_binding.c.client_id == self.client_id)).mappings().one_or_none()
        if row is None:
            raise ScopeError('Binding missing or foreign')
        value = ContextBinding.from_json(row['document'])
        expected = dict(binding_id=value.binding_id, client_id=value.client_id, run_id=value.run_id,
            context_id=value.context_id, parent_binding_id=value.parent_binding_id,
            owner_key=self._owner_key(value.owner), owner_digest=value.owner_digest, document=value.to_json())
        if dict(row) != expected:
            raise ScopeError('Binding payload disagrees with indexed envelope')
        return value

    def _bind(self, context, owner, parent=None):
        row, _, _ = self._owner(owner)
        if row.get('run_id', self.run_id) != self.run_id:
            raise ScopeError('Binding owner is outside the recording run')
        value = ContextBinding(client_id=self.client_id, run_id=self.run_id, owner=owner,
            owner_digest=digest(row), context_id=context.context_id,
            parent_binding_id=parent.binding_id if parent else None)
        old = self.session.scalar(select(tables.measurement_binding.c.binding_id).where(
            tables.measurement_binding.c.client_id == self.client_id,
            tables.measurement_binding.c.owner_key == self._owner_key(owner),
            tables.measurement_binding.c.owner_digest == value.owner_digest))
        if old:
            if self.get_binding(old) != value:
                raise RevisionConflict('Owner snapshot already has a different authoritative context')
            return value
        self.session.execute(insert(tables.measurement_binding).values(binding_id=value.binding_id,
            client_id=self.client_id, run_id=self.run_id, context_id=context.context_id,
            parent_binding_id=value.parent_binding_id, owner_key=self._owner_key(owner),
            owner_digest=value.owner_digest, document=value.to_json()))
        self._audit(context, value)
        return value

    def lookup(self, owner):
        row, _, _ = self._owner(owner)
        binding_id = self.session.scalar(select(tables.measurement_binding.c.binding_id).where(
            tables.measurement_binding.c.client_id == self.client_id,
            tables.measurement_binding.c.owner_key == self._owner_key(owner),
            tables.measurement_binding.c.owner_digest == digest(row)))
        if binding_id is None:
            raise ScopeError('Current measurement slot is unknown/unbound')
        return self.get_binding(binding_id)

    def resolve_binding(self, binding_id):
        """Validate every pinned dependency before a current-context consumer."""
        value = self.get_binding(binding_id)
        visited = set()
        cursor = value
        while True:
            if cursor.binding_id in visited or cursor.context_id != value.context_id:
                raise ScopeError('Cyclic or inconsistent context propagation chain')
            visited.add(cursor.binding_id)
            row, _, _ = self._owner(cursor.owner)
            if digest(row) != cursor.owner_digest:
                raise RevisionConflict('A measurement in the propagation chain changed')
            if cursor.parent_binding_id is None:
                break
            cursor = self.get_binding(cursor.parent_binding_id)
        context = self.get_context(value.context_id, current=True)
        if cursor.owner != context.origin:
            raise ScopeError('Context chain does not terminate at its captured origin')
        return value, context

    def audit_events(self, context_id):
        self.get_context(context_id)
        rows = self.session.execute(select(tables.measurement_audit).where(
            tables.measurement_audit.c.context_id == context_id,
            tables.measurement_audit.c.client_id == self.client_id).order_by(
            tables.measurement_audit.c.created_at, tables.measurement_audit.c.event_id)).mappings().all()
        return tuple(json.loads(row['document']) for row in rows)

    def propagate(self, parent_binding_id, owner):
        """Only verified one-to-one retained dependency edges, no inferred sums."""
        parent, context = self.resolve_binding(parent_binding_id)
        before, a, au = self._owner(parent.owner)
        if digest(before) != parent.owner_digest:
            raise RevisionConflict('Parent measurement binding is stale')
        after, b, bu = self._owner(owner)
        if a != b or (au.replace('GBP', 'CURRENCY') != bu.replace('GBP', 'CURRENCY')):
            raise ValueError('Propagation cannot change measurement value or unit')
        edge = (parent.owner.resource, owner.resource)
        con = self.source.connection
        if edge == ('financial_statement_line', 'primitive_result'):
            names = {'financial_revenue': 'FIN_REVENUE', 'financial_direct_cost': 'FIN_DIRECT_COST',
                'financial_gross_profit': 'FIN_GROSS_PROFIT', 'financial_ebitda': 'FIN_EBITDA',
                'bs_accounts_receivable': 'BS_ACCOUNTS_RECEIVABLE', 'bs_accounts_payable': 'BS_ACCOUNTS_PAYABLE',
                'bs_inventory': 'BS_INVENTORY', 'bs_cash': 'BS_CASH'}
            refs = con.execute('SELECT source_object_type,source_object_id FROM calculation_lineage WHERE primitive_result_id=?', (owner.source_id,)).fetchall()
            # Restrict to an unambiguous single source line for this metric in
            # the selected dataset. Multi-period aggregation needs its own context.
            from .source import accounting_metric
            source_rows = con.execute('SELECT * FROM financial_statement_line WHERE client_id=? AND dataset_version_id=?',
                (self.client_id, context.source_version.source_id)).fetchall()
            candidates = []
            for row in source_rows:
                try:
                    if accounting_metric(dict(row)) == context.metric:
                        candidates.append(row['statement_line_id'])
                except ValueError:
                    continue
            valid = (after['primitive_id'] == names.get(context.metric) and after['result_status'] == 'VALID'
                and after['period_to'] == before['period_end'] and candidates == [parent.owner.source_id]
                and [(r[0], r[1]) for r in refs] == [('DATASET_VERSION', context.source_version.source_id)])
        elif edge == ('primitive_result', 'signal'):
            refs = con.execute('SELECT source_object_type,source_object_id FROM diagnostic_lineage WHERE signal_id=?', (owner.source_id,)).fetchall()
            valid = (owner.slot == 'observed' and after['status'] == 'ACTIVE' and
                [(r[0], r[1]) for r in refs] == [('PRIMITIVE_RESULT', parent.owner.source_id)]
                and after['source_primitive_id'] == before['primitive_id'])
        elif edge == ('signal', 'canonical_fact'):
            measurement = after[owner.slot]
            valid = (after['source_signal_id'] == parent.owner.source_id and owner.slot == parent.owner.slot
                     and measurement['metric'] == context.metric)
        else:
            valid = False
        if not valid:
            raise ValueError('Unqualified context propagation edge; no generic fallback')
        return self._bind(context, owner, parent)
