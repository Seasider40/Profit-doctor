"""Production reads owning services; no caller evidence/result injection route."""
import json
from sqlalchemy import insert, select

from profit_doctor.persistence import dataset_schema, temporal_schema as tables
from profit_doctor.reasoning.canonical.service import CanonicalService, identity
from profit_doctor.reasoning.dataset.service import DatasetContractService
from profit_doctor.reasoning.domain.contracts import LineageReference, now
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.measurement.contracts import MeasurementSlot
from profit_doctor.reasoning.measurement.service import MeasurementContextService
from profit_doctor.reasoning.impact.service import ImpactService
from profit_doctor.reasoning.receivables.contracts import Snapshot
from profit_doctor.reasoning.bridge.qualification import Period
from .contracts import Assessment, ContractKey, Observation, TemporalInput, Window
from .engine import evaluate
from .policies import POLICIES


class TemporalService:
    """Caller owns session/transaction; writes append revisions and one audit.

    The frozen providers cannot verify every temporal prerequisite. Production
    results therefore remain refused. A future independently qualified provider
    can supply the same observation/comparability architecture without rewriting
    downstream objects or these temporal contracts.
    """
    def __init__(self, canonical, datasets, contexts=None, impacts=None):
        if not isinstance(canonical, CanonicalService) or not isinstance(datasets, DatasetContractService):
            raise ScopeError('Canonical and Dataset Contract owners are required')
        self.canonical, self.datasets = canonical, datasets
        self.session, self.client_id, self.run_id = canonical.session, canonical.client_id, datasets.run_id
        self.foundation = canonical.foundation
        self.foundation._run(self.run_id)
        for owner, cls in ((datasets, DatasetContractService), (contexts, MeasurementContextService), (impacts, ImpactService)):
            if owner is not None and (not isinstance(owner, cls) or owner.session is not self.session or owner.client_id != self.client_id):
                raise ScopeError('Temporal owners must share session and client scope')
        self.contexts, self.impacts = contexts, impacts

    def _dataset(self, version_id):
        if version_id is None:
            return None
        key = self.session.scalar(select(dataset_schema.dataset_contract.c.contract_id).where(
            dataset_schema.dataset_contract.c.client_id == self.client_id,
            dataset_schema.dataset_contract.c.source_version_id == version_id
        ).order_by(dataset_schema.dataset_contract.c.revision.desc()).limit(1))
        return self.datasets.get_contract(key, current=True) if key else None

    def _fact(self, source_id, policy):
        fact = self.canonical.get_fact(source_id)
        if fact.state != 'OBSERVED' or self.canonical.source.read(fact.source_signal_id)[3] != fact.source_digest:
            raise RevisionConflict('Temporal Fact is inactive or its source changed')
        measurement = fact.observed
        expected = ('GM-01', 'CONTRIBUTION_MARGIN_CHANGE') if policy.metric == 'contribution_0_margin' else ('REV-01', 'COMPARABLE_REVENUE_CHANGE')
        if (fact.diagnostic, fact.signal_type) != expected or measurement is None or measurement.metric != policy.metric:
            raise ScopeError('Fact is outside the exact temporal contract catalogue')
        versions = {ref.source_id for ref in fact.lineage if ref.kind == 'DATASET_VERSION'}
        ds = self._dataset(next(iter(versions))) if len(versions) == 1 else None
        period, binding = Period(), None
        if self.contexts:
            owner = MeasurementSlot(store='CANONICAL', resource='canonical_fact', source_id=source_id, slot='observed')
            try:
                binding = self.contexts.lookup(owner)
            except ScopeError:
                # An unknown/unbound slot remains unknown; no date inference.
                binding = None
            if binding:
                _, context = self.contexts.resolve_binding(binding.binding_id)
                period = context.period
        scope = json.dumps([fact.scope.entity_type, fact.scope.entity_id], separators=(',', ':'))
        return Observation(observation_id=identity('temporal-observation', fact.to_json()),
            client_id=fact.client_id, run_id=fact.run_id, source_kind='FACT', source_id=fact.object_id,
            source_revision=fact.revision, scope_key=scope, period=period, dataset=ds,
            metric=measurement.metric, unit=measurement.unit.value, currency=measurement.currency,
            value=measurement.value, context_binding_id=binding.binding_id if binding else None,
            lineage=fact.lineage, source_snapshot=fact.to_json())

    def _impact(self, candidate_id):
        if self.impacts is None:
            raise ScopeError('Qualified Impact owner required')
        q = self.impacts.get(candidate_id)
        if q.domain != 'PRODUCTION' or q.source.kind != 'RECEIVABLES' or q.category != 'CASH_TRAPPED':
            raise ScopeError('Only production receivables CASH_TRAPPED qualification is eligible')
        snapshot = Snapshot.from_json(q.source_document)
        if snapshot.origin != 'REAL_SOURCE':
            raise ScopeError('Blind/synthetic qualification sources cannot become production temporal claims')
        version = LineageReference(kind='DATASET_VERSION', store='LEGACY_SQLITE',
            resource='dataset_version', source_id=snapshot.dataset_version_id, client_id=self.client_id)
        refs = (version,)
        if q.impact:
            refs += (LineageReference(kind='DERIVED_ANCESTOR', store='CANONICAL',
                resource='reasoning_object_v243', source_id=q.impact.impact_id,
                client_id=self.client_id, run_id=q.run_id),)
        return Observation(observation_id=identity('temporal-observation', q.to_json()),
            client_id=q.client_id, run_id=q.run_id, source_kind='IMPACT' if q.impact else 'UNKNOWN',
            source_id=candidate_id, source_revision=q.revision,
            scope_key=json.dumps([snapshot.ledger_id, snapshot.entity, snapshot.scope, snapshot.currency], separators=(',', ':')),
            period=Period(start=snapshot.as_of, end=snapshot.as_of, basis='POINT_IN_TIME', nature='STOCK'),
            dataset=self._dataset(snapshot.dataset_version_id), metric='cash_trapped_receivables',
            unit='CURRENCY', currency='GBP', value=q.impact.amount.value if q.impact else None,
            presence='PRESENT' if q.impact else 'UNKNOWN', lineage=refs, source_snapshot=q.to_json())

    def _basis(self, subject_id, contract_key, window, source_ids):
        key = ContractKey(contract_key)
        window = Window.from_json(window.to_json())
        subject = self.foundation.get_object(subject_id)
        self.foundation._run(subject.run_id)
        if len(set(source_ids)) != len(source_ids):
            raise ValueError('Duplicate requested source identities')
        source_ids = tuple(sorted(source_ids))
        if key == ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE:
            if subject.object_type != 'ECONOMIC_IMPACT' or subject.impact_type != 'CASH_TRAPPED':
                raise ScopeError('Receivables lifecycle must attach to a CASH_TRAPPED Impact')
            rows = tuple(self._impact(source_id) for source_id in source_ids)
            if not any(subject_id in {ref.source_id for ref in o.lineage} for o in rows):
                raise ScopeError('Requested history does not contain its assessed Impact')
        else:
            finding = self.canonical.get_finding(subject_id)
            expected_type = 'MARGIN_MOVEMENT' if key == ContractKey.CONTRIBUTION_0_MARGIN_TRAJECTORY else 'REVENUE_MOVEMENT'
            if subject.object_type != 'FINDING' or finding.finding_type != expected_type:
                raise ScopeError('Trajectory must attach to the exact canonical Finding family')
            allowed = {o.fact_id for o in finding.observations}
            if not set(source_ids) <= allowed:
                raise ScopeError('Requested Fact is not an observation of this Finding')
            rows = tuple(self._fact(source_id, POLICIES[key]) for source_id in source_ids)
        if len({o.scope_key for o in rows}) > 1:
            raise ScopeError('Observation history contains a different entity/population scope')
        return TemporalInput(origin='CANONICAL', contract_key=key, client_id=self.client_id,
            subject_id=subject_id, window=window, observations=rows)

    def _row(self, series_id, revision=None):
        query = select(tables.assessment).where(tables.assessment.c.series_id == series_id,
            tables.assessment.c.client_id == self.client_id)
        if revision is not None:
            query = query.where(tables.assessment.c.revision == revision)
        return self.session.execute(query.order_by(tables.assessment.c.revision.desc()).limit(1)).mappings().one_or_none()

    def assess(self, subject_id, contract_key, window, source_ids, *, expected_revision=None):
        basis = self._basis(subject_id, contract_key, window, tuple(source_ids))
        result = evaluate(basis)
        series_id = identity('temporal-series-2.54.1', self.client_id, subject_id,
            basis.contract_key.value, window.model_dump(mode='json'))
        row = self._row(series_id)
        old = self.get(series_id) if row else None
        if old and old.result == result and old.run_id == self.run_id:
            return old
        if expected_revision != (old.revision if old else None):
            raise RevisionConflict('Changed temporal evidence requires its explicit predecessor revision')
        revision = old.revision + 1 if old else 1
        value = Assessment(assessment_id=identity('temporal-assessment', series_id, revision, result.to_json(), self.run_id),
            series_id=series_id, subject_id=subject_id, client_id=self.client_id, run_id=self.run_id,
            revision=revision, supersedes=old.assessment_id if old else None, result=result)
        connection = self.session.connection()
        if connection.dialect.name == 'sqlite' and not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql('BEGIN')
        with self.session.begin_nested():
            self.session.execute(insert(tables.assessment).values(assessment_id=value.assessment_id,
                series_id=value.series_id, subject_id=value.subject_id, client_id=value.client_id,
                run_id=value.run_id, revision=value.revision, supersedes=value.supersedes,
                created_at=value.created_at.isoformat(), document=value.to_json()))
            document = json.dumps({'event': 'TEMPORAL_ASSESSED',
                'actor': self.foundation.actor.model_dump(mode='json'),
                'previous': old.to_json() if old else None, 'new': value.to_json()}, sort_keys=True, separators=(',', ':'))
            self.session.execute(insert(tables.audit).values(event_id=identity('temporal-audit', value.assessment_id),
                assessment_id=value.assessment_id, client_id=self.client_id,
                created_at=value.created_at.isoformat(), document=document))
        return value

    def get(self, series_id, revision=None, *, current=False):
        row = self._row(series_id, revision)
        if row is None:
            raise ScopeError('Missing or foreign temporal assessment')
        value = Assessment.from_json(row['document'])
        if (value.assessment_id, value.series_id, value.subject_id, value.client_id, value.run_id,
                value.revision, value.supersedes, value.created_at.isoformat()) != (
                row['assessment_id'], row['series_id'], row['subject_id'], row['client_id'], row['run_id'],
                row['revision'], row['supersedes'], row['created_at']):
            raise ScopeError('Temporal indexed envelope disagrees with its document')
        if value.result.basis.origin != 'CANONICAL' or evaluate(value.result.basis) != value.result:
            raise ScopeError('Synthetic or unqualified temporal result in production persistence')
        self.foundation.get_object(value.subject_id)
        self.foundation._run(value.run_id)
        if current:
            basis = value.result.basis
            if self._row(series_id)['revision'] != value.revision or value.run_id != self.run_id or self._basis(
                    value.subject_id, basis.contract_key, basis.window,
                    tuple(o.source_id for o in basis.observations)) != basis:
                raise RevisionConflict('Temporal assessment is historical or its evidence changed')
        return value

    def history(self, series_id):
        self.get(series_id)
        return tuple(self.get(series_id, revision) for revision in self.session.scalars(
            select(tables.assessment.c.revision).where(tables.assessment.c.series_id == series_id,
                tables.assessment.c.client_id == self.client_id).order_by(tables.assessment.c.revision)))

    def audit_events(self, series_id):
        self.get(series_id)
        query = select(tables.audit.c.document).join(tables.assessment,
            tables.audit.c.assessment_id == tables.assessment.c.assessment_id).where(
            tables.assessment.c.series_id == series_id, tables.audit.c.client_id == self.client_id)
        return tuple(json.loads(document) for document in self.session.scalars(query.order_by(tables.assessment.c.revision)))
