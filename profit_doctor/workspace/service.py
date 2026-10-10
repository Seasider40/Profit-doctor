"""Caller-owned workflow transactions; no diagnostic or qualification writes."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from uuid import uuid4
from sqlalchemy import insert, select
from profit_doctor.persistence import Client, EngineRun, workspace_schema as t
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from .contracts import EngagementRevision, InformationRevision, Receipt


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier():
    return str(uuid4())


def document(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


class WorkspaceService:
    def __init__(self, session, operator, store, *, reader=None):
        self.session, self.operator, self.store, self.reader = session, operator, store, reader

    @contextmanager
    def atomic(self):
        # SQLite SAVEPOINT must not inadvertently become the outer transaction.
        connection = self.session.connection()
        if connection.dialect.name == 'sqlite' and not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql('BEGIN')
        with self.session.begin_nested():
            yield

    def client(self, client_id):
        self.operator.require(client_id)
        value = self.session.get(Client, client_id)
        if value is None:
            raise ScopeError('Client not found')
        return value

    def clients(self):
        return [{'client_id': c.client_id, 'client_name': c.client_name} for c in self.session.scalars(
            select(Client).where(Client.client_id.in_(self.operator.clients)).order_by(Client.client_id))]

    def create_client(self, client_id, name, currency='GBP'):
        self.operator.require(client_id)
        if not name.strip() or len(name) > 255 or len(currency) != 3 or not currency.isalpha() or not currency.isupper():
            raise ValueError('Client name and uppercase currency required')
        existing = self.session.get(Client, client_id)
        if existing:
            if (existing.client_name, existing.base_currency) != (name, currency):
                raise RevisionConflict('Client identity exists with different metadata')
            return
        self.session.add(Client(client_id=client_id, client_name=name, base_currency=currency, created_at=now()))
        self.session.flush()

    def _row(self, table, key, value, client_id):
        self.client(client_id)
        row = self.session.execute(select(table).where(table.c[key] == value,
            table.c.client_id == client_id)).mappings().one_or_none()
        if row is None:
            raise ScopeError('Workflow object missing or foreign')
        return row

    def _latest(self, table, owner, value, client_id):
        self.client(client_id)
        return self.session.execute(select(table).where(table.c[owner] == value,
            table.c.client_id == client_id).order_by(table.c.revision.desc()).limit(1)).mappings().one()

    def engagement(self, client_id, engagement_id, revision=None):
        self._row(t.engagement, 'engagement_id', engagement_id, client_id)
        if revision is None:
            row = self._latest(t.engagement_revision, 'engagement_id', engagement_id, client_id)
        else:
            row = self.session.execute(select(t.engagement_revision).where(
                t.engagement_revision.c.engagement_id == engagement_id,
                t.engagement_revision.c.client_id == client_id,
                t.engagement_revision.c.revision == revision)).mappings().one_or_none()
            if row is None:
                raise ScopeError('Engagement revision unavailable')
        return EngagementRevision.from_json(row['document'])

    def engagements(self, client_id):
        self.client(client_id)
        ids = self.session.scalars(select(t.engagement.c.engagement_id).where(
            t.engagement.c.client_id == client_id).order_by(t.engagement.c.created_at))
        return [self.engagement(client_id, key).model_dump(mode='json') for key in ids]

    def _open(self, client_id, engagement_id):
        value = self.engagement(client_id, engagement_id)
        if value.status != 'OPEN':
            raise RevisionConflict('Closed engagement requires explicit reopening')
        return value

    def _replay(self, client_id, key, payload):
        if not isinstance(key, str) or not 1 <= len(key) <= 64:
            raise ValueError('Bounded idempotency key required')
        self.client(client_id)
        digest = hashlib.sha256(document(payload).encode()).hexdigest()
        row = self.session.execute(select(t.audit.c.document).where(
            t.audit.c.client_id == client_id, t.audit.c.request_key == key)).scalar_one_or_none()
        if row:
            event = json.loads(row)
            if event['digest'] != digest or event['actor'] != self.operator.actor:
                raise RevisionConflict('Idempotency key reused for a different request')
            return digest, event['result']
        return digest, None

    def _audit(self, client_id, engagement_id, key, digest, kind, result, previous=None):
        self.session.execute(insert(t.audit).values(event_id=identifier(), client_id=client_id,
            engagement_id=engagement_id, created_at=now(), request_key=key,
            document=document({'actor': self.operator.actor, 'event': kind, 'digest': digest,
                'previous': previous, 'result': result, 'boundary': 'ADMINISTRATIVE_WORKFLOW_ONLY'})))

    def save_engagement(self, value, *, expected_revision, key):
        value = EngagementRevision.model_validate(value.model_dump(mode='json') if isinstance(value, EngagementRevision) else value)
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError('Non-negative expected revision required')
        payload = {'operation': 'engagement', 'value': value.model_dump(mode='json'), 'expected': expected_revision}
        digest, replay = self._replay(value.client_id, key, payload)
        if replay is not None:
            return EngagementRevision.model_validate(replay)
        previous = None
        if expected_revision:
            previous = self.engagement(value.client_id, value.engagement_id)
            if previous.revision != expected_revision:
                raise RevisionConflict('Engagement changed since it was opened')
            if previous.scope != value.scope:
                raise RevisionConflict('Engagement scope is fixed; create a separate scoped engagement')
        if value.revision != expected_revision + 1:
            raise RevisionConflict('Sequential engagement revision required')
        if len(set(value.run_ids)) != len(value.run_ids) or len(set(value.readiness_ids)) != len(value.readiness_ids):
            raise ValueError('Duplicate selections')
        for run_id in value.run_ids:
            run = self.session.get(EngineRun, run_id)
            if run is None or run.client_id != value.client_id:
                raise ScopeError('Run missing or foreign')
        for ready_id in value.readiness_ids:
            if self.reader is None:
                raise ScopeError('Owned readiness reader not configured; no inferred current result')
            self.reader.readiness(value, ready_id, current=value.readiness_view == 'CURRENT')
        with self.atomic():
            if expected_revision == 0:
                self.session.execute(insert(t.engagement).values(engagement_id=value.engagement_id,
                    client_id=value.client_id, created_at=now()))
            self.session.execute(insert(t.engagement_revision).values(revision_id=identifier(),
                engagement_id=value.engagement_id, client_id=value.client_id,
                revision=value.revision, document=value.to_json()))
            self._audit(value.client_id, value.engagement_id, key, digest, 'ENGAGEMENT_REVISED',
                value.model_dump(mode='json'), previous.model_dump(mode='json') if previous else None)
        return value

    def receipt(self, client_id, receipt_id):
        row = self._row(t.receipt, 'receipt_id', receipt_id, client_id)
        value = Receipt.from_json(row['document'])
        if (value.receipt_id, value.client_id, value.engagement_id, value.predecessor_id) != (
                row['receipt_id'], row['client_id'], row['engagement_id'], row['predecessor_id']):
            raise ScopeError('Receipt indexed ownership differs')
        return value

    def receive(self, client_id, engagement_id, filename, data, *, role, description='', predecessor=None, key):
        self._open(client_id, engagement_id)
        filename = self.store.filename(filename)
        sha = hashlib.sha256(data).hexdigest()
        payload = {'operation': 'receipt', 'engagement': engagement_id, 'filename': filename,
            'sha256': sha, 'role': role, 'description': description, 'predecessor': predecessor}
        digest, replay = self._replay(client_id, key, payload)
        if replay is not None:
            value = Receipt.model_validate(replay)
            self.store.read(value.sha256, value.byte_count)
            return value
        if predecessor and self.receipt(client_id, predecessor).engagement_id != engagement_id:
            raise ScopeError('Receipt predecessor belongs to another engagement')
        value = Receipt(receipt_id=identifier(), client_id=client_id, engagement_id=engagement_id,
            filename=filename, sha256=sha, byte_count=len(data), source_role=role,
            description=description, predecessor_id=predecessor, received_at=now(), actor=self.operator.actor)
        self.store.put(data)  # Durable bytes first. Caller rollback may leave an identifiable orphan.
        with self.atomic():
            self.session.execute(insert(t.receipt).values(receipt_id=value.receipt_id, client_id=client_id,
                engagement_id=engagement_id, predecessor_id=predecessor, document=value.to_json()))
            self._audit(client_id, engagement_id, key, digest, 'EVIDENCE_RECEIVED', value.model_dump(mode='json'))
        return value

    def inventory(self, client_id, engagement_id):
        self.engagement(client_id, engagement_id)
        rows = self.session.execute(select(t.receipt).where(t.receipt.c.client_id == client_id,
            t.receipt.c.engagement_id == engagement_id)).mappings().all()
        values = []
        for row in rows:
            value = self.receipt(client_id, row['receipt_id'])
            self.store.read(value.sha256, value.byte_count)  # Integrity failure stays an error.
            registrations = [json.loads(x) for x in self.session.scalars(select(t.registration.c.document).where(
                t.registration.c.client_id == client_id, t.registration.c.receipt_id == value.receipt_id))]
            for reference in registrations:
                if self.reader is None:
                    raise ScopeError('Retained registration requires its owned reader')
                current = self.reader.registration(self.engagement(client_id, engagement_id), value,
                    reference['registration']['dataset_version_id'])
                if current != reference['registration']:
                    raise RevisionConflict('Registered source changed; historical association cannot appear current')
            values.append({'receipt': value.model_dump(mode='json'), 'received': True,
                'registrations': registrations, 'authority': 'NOT_ESTABLISHED_BY_RECEIPT',
                'reconciliation': 'NOT_ESTABLISHED_BY_RECEIPT', 'qualification': 'NOT_ESTABLISHED_BY_RECEIPT'})
        return values

    def associate_registration(self, client_id, engagement_id, receipt_id, version_id, *, key):
        engagement = self._open(client_id, engagement_id)
        receipt = self.receipt(client_id, receipt_id)
        if receipt.engagement_id != engagement_id or self.reader is None:
            raise ScopeError('Scoped registered-source reader required')
        payload = {'operation': 'registration', 'engagement': engagement_id, 'receipt': receipt_id, 'version': version_id}
        digest, replay = self._replay(client_id, key, payload)
        if replay is not None:
            return replay
        self.store.read(receipt.sha256, receipt.byte_count)
        owned = self.reader.registration(engagement, receipt, version_id)
        result = {'reference_id': identifier(), 'receipt_id': receipt_id, 'registration': owned}
        with self.atomic():
            self.session.execute(insert(t.registration).values(reference_id=result['reference_id'],
                client_id=client_id, engagement_id=engagement_id, receipt_id=receipt_id, document=document(result)))
            self._audit(client_id, engagement_id, key, digest, 'REGISTRATION_LINKED', result)
        return result

    def information(self, client_id, request_id):
        self._row(t.request, 'request_id', request_id, client_id)
        return InformationRevision.from_json(self._latest(t.request_revision, 'request_id', request_id, client_id)['document'])

    def save_information(self, value, *, expected_revision, key):
        value = InformationRevision.model_validate(value.model_dump(mode='json') if isinstance(value, InformationRevision) else value)
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError('Non-negative expected revision required')
        self._open(value.client_id, value.engagement_id)
        digest, replay = self._replay(value.client_id, key, {'operation': 'request',
            'value': value.model_dump(mode='json'), 'expected': expected_revision})
        if replay is not None:
            return InformationRevision.model_validate(replay)
        previous = self.information(value.client_id, value.request_id) if expected_revision else None
        if previous and (previous.revision != expected_revision or previous.engagement_id != value.engagement_id):
            raise RevisionConflict('Request changed or belongs to another engagement')
        if value.revision != expected_revision + 1:
            raise RevisionConflict('Sequential request revision required')
        if previous is None and value.status != 'OPEN':
            raise ValueError('New information requests start OPEN')
        allowed = {'OPEN': {'OPEN', 'EVIDENCE_RECEIVED', 'WITHDRAWN'},
            'EVIDENCE_RECEIVED': {'OPEN', 'EVIDENCE_RECEIVED', 'FULFILMENT_REVIEWED', 'WITHDRAWN'},
            'FULFILMENT_REVIEWED': {'OPEN', 'FULFILMENT_REVIEWED', 'WITHDRAWN'}, 'WITHDRAWN': {'WITHDRAWN'}}
        if previous and value.status not in allowed[previous.status]:
            raise ValueError('Invalid administrative request transition')
        for receipt_id in value.receipt_ids:
            if self.receipt(value.client_id, receipt_id).engagement_id != value.engagement_id:
                raise ScopeError('Request evidence belongs to another engagement')
        with self.atomic():
            if expected_revision == 0:
                self.session.execute(insert(t.request).values(request_id=value.request_id, client_id=value.client_id,
                    engagement_id=value.engagement_id, created_at=now()))
            self.session.execute(insert(t.request_revision).values(revision_id=identifier(), request_id=value.request_id,
                client_id=value.client_id, engagement_id=value.engagement_id, revision=value.revision, document=value.to_json()))
            self._audit(value.client_id, value.engagement_id, key, digest, 'INFORMATION_REQUEST_REVISED',
                value.model_dump(mode='json'), previous.model_dump(mode='json') if previous else None)
        return value

    def requests(self, client_id, engagement_id):
        self.engagement(client_id, engagement_id)
        return [self.information(client_id, key).model_dump(mode='json') for key in self.session.scalars(
            select(t.request.c.request_id).where(t.request.c.client_id == client_id,
                t.request.c.engagement_id == engagement_id))]

    def history(self, client_id, engagement_id):
        self.engagement(client_id, engagement_id)
        return [dict(row, document=json.loads(row['document'])) for row in self.session.execute(
            select(t.audit).where(t.audit.c.client_id == client_id, t.audit.c.engagement_id == engagement_id)
            .order_by(t.audit.c.created_at, t.audit.c.event_id)).mappings()]

    def readiness(self, client_id, engagement_id, *, historical=None):
        value = self.engagement(client_id, engagement_id)
        if historical is None:
            historical = value.readiness_view == 'HISTORICAL'
        if not value.readiness_ids:
            from profit_doctor.reasoning.production_evidence.readiness import ReadinessDomain
            return [{'domain': domain.value, 'assessment': None, 'message': 'No governed assessment available',
                'evidence': 'NOT_PROVIDED_TO_WORKSPACE'} for domain in ReadinessDomain]
        if self.reader is None:
            raise ScopeError('Owned readiness reader unavailable')
        return [self.reader.readiness(value, key, current=not historical) for key in value.readiness_ids]

    def coverage(self, client_id, engagement_id):
        value = self.engagement(client_id, engagement_id)
        if self.reader is None or not value.run_ids:
            return {'basis': 'LEGACY_DIAGNOSTIC_COVERAGE_NOT_GOVERNED_READINESS',
                'available': False, 'reason': 'No selected existing run/legacy registry'}
        return {'available': True, 'runs': [self.reader.legacy_coverage(value, key) for key in value.run_ids]}
