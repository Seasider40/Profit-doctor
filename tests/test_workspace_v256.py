"""Scoped workflow, durable receipt and negative governance regressions."""
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from sqlalchemy import insert, select, func
from sqlalchemy.exc import IntegrityError
from alembic import command
from profit_doctor.persistence import DatabaseConfig, build_engine, session_factory, EngineRun, workspace_schema as t
from tests.test_postgresql_live_qualification_v218 import alembic_config
from profit_doctor.workspace.contracts import Operator, Scope, EngagementRevision, InformationRevision
from profit_doctor.workspace.service import WorkspaceService
from profit_doctor.workspace.storage import EvidenceStore
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict


class WorkspaceFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.url = getattr(self, 'target_url', None) or 'sqlite+pysqlite:///' + (self.root / 'workspace.db').as_posix()
        command.upgrade(alembic_config(self.url), 'head')
        self.engine = build_engine(DatabaseConfig(self.url))
        self.addCleanup(self.engine.dispose)
        self.factory = session_factory(self.engine)
        self.session = self.factory()
        self.addCleanup(self.session.close)
        self.store = EvidenceStore(self.root / 'evidence')
        self.operator = Operator('local-adviser', frozenset({'c1', 'c2'}))
        self.service = WorkspaceService(self.session, self.operator, self.store)
        self.service.create_client('c1', 'One')
        self.service.create_client('c2', 'Two')
        self.scope = Scope(entity_id='entity-1', ledger_id='ledger-1', period_start='2027-01-01', period_end='2027-03-31')
        self.value = EngagementRevision(engagement_id='e1', client_id='c1', revision=1, title='Review', scope=self.scope)
        self.service.save_engagement(self.value, expected_revision=0, key='create')
        self.session.commit()

    def receive(self, **kwargs):
        return self.service.receive('c1', 'e1', 'accounts.csv', b'record,value\nA,123.45\n',
            role='ACCOUNTING_PACK', key=kwargs.pop('key', 'receipt'), **kwargs)

    def request(self, **kwargs):
        value = InformationRevision(request_id='request-1', engagement_id='e1', client_id='c1', revision=1,
            question='Which records establish the population?', evidence_required='Source-supported membership manifest', **kwargs)
        return self.service.save_information(value, expected_revision=0, key='request')


class WorkspaceV256(WorkspaceFixture, unittest.TestCase):
    def test_engagement_round_trip_and_declared_scope(self):
        self.assertEqual(self.service.engagement('c1', 'e1'), self.value)
        self.assertEqual(self.value.scope_basis, 'ADMINISTRATIVE_DECLARATION')
        self.assertEqual(EngagementRevision.from_json(self.value.to_json()), self.value)

    def test_client_authorisation_not_request_actor(self):
        owner = WorkspaceService(self.session, Operator('other', frozenset({'c2'})), self.store)
        with self.assertRaises(PermissionError):
            owner.engagement('c1', 'e1')

    def test_foreign_engagement_hidden(self):
        with self.assertRaises(ScopeError):
            self.service.engagement('c2', 'e1')

    def test_scope_cannot_change_in_place(self):
        changed = self.value.model_copy(update={'revision': 2, 'scope': self.scope.model_copy(update={'ledger_id': 'other'})})
        with self.assertRaises(RevisionConflict):
            self.service.save_engagement(changed, expected_revision=1, key='scope')

    def test_close_reopen_retains_history(self):
        closed = self.value.model_copy(update={'revision': 2, 'status': 'CLOSED'})
        self.service.save_engagement(closed, expected_revision=1, key='close')
        with self.assertRaises(RevisionConflict):
            self.receive()
        self.service.save_engagement(closed.model_copy(update={'revision': 3, 'status': 'OPEN'}), expected_revision=2, key='reopen')
        self.assertEqual(self.service.engagement('c1', 'e1', revision=1), self.value)
        self.assertEqual(len(self.service.history('c1', 'e1')), 3)

    def test_stale_revision_refused(self):
        changed = self.value.model_copy(update={'revision': 2, 'title': 'Updated'})
        self.service.save_engagement(changed, expected_revision=1, key='update')
        with self.assertRaises(RevisionConflict):
            self.service.save_engagement(changed, expected_revision=1, key='stale')

    def test_engagement_replay_idempotent(self):
        result = self.service.save_engagement(self.value, expected_revision=0, key='create')
        self.assertEqual(result, self.value)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(t.engagement_revision)), 1)

    def test_changed_replay_payload_refused(self):
        with self.assertRaises(RevisionConflict):
            self.service.save_engagement(self.value.model_copy(update={'title': 'Different'}), expected_revision=0, key='create')

    def test_missing_or_foreign_run_refused(self):
        self.session.add(EngineRun(run_id='r2', client_id='c2', run_type='BASELINE', started_at='2027-01-01', status='COMPLETE', engine_version='test'))
        self.session.flush()
        for key in ('missing', 'r2'):
            with self.subTest(key=key), self.assertRaises(ScopeError):
                self.service.save_engagement(self.value.model_copy(update={'revision': 2, 'run_ids': (key,)}), expected_revision=1, key=key)

    def test_readiness_missing_has_no_score_or_qualified_state(self):
        rows = self.service.readiness('c1', 'e1')
        self.assertEqual(len(rows), 9)
        self.assertTrue(all(r['assessment'] is None for r in rows))
        self.assertNotIn('VERIFIED', str(rows))
        self.assertNotIn('score', str(rows))

    def test_asserted_readiness_cannot_be_selected(self):
        with self.assertRaises(ScopeError):
            self.service.save_engagement(self.value.model_copy(update={'revision': 2, 'readiness_ids': ('fake',)}), expected_revision=1, key='fake')

    def test_receipt_bytes_preserved_and_no_qualification_uplift(self):
        receipt = self.receive()
        self.assertEqual(self.store.read(receipt.sha256, receipt.byte_count), b'record,value\nA,123.45\n')
        item = self.service.inventory('c1', 'e1')[0]
        self.assertEqual(item['registrations'], [])
        self.assertEqual(item['qualification'], 'NOT_ESTABLISHED_BY_RECEIPT')

    def test_receipt_replay_has_one_owner(self):
        self.assertEqual(self.receive(), self.receive())
        self.assertEqual(self.session.scalar(select(func.count()).select_from(t.receipt)), 1)

    def test_replacement_retains_original(self):
        a = self.receive()
        b = self.service.receive('c1', 'e1', 'new.csv', b'new', role='ACCOUNTING_PACK', predecessor=a.receipt_id, key='new')
        self.assertEqual(b.predecessor_id, a.receipt_id)
        self.assertEqual(len(self.service.inventory('c1', 'e1')), 2)

    def test_corrupt_storage_fails_not_missing_evidence_state(self):
        value = self.receive()
        self.store.path(value.sha256).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            self.service.inventory('c1', 'e1')

    def test_unsafe_original_filenames_refused(self):
        for name in ('../x', '..\\x', 'C:x', '<bad>\x00', '.', ''):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.store.filename(name)

    def test_empty_and_oversize_bytes_refused(self):
        with self.assertRaises(ValueError):
            self.store.put(b'')
        with patch.object(self.store, 'LIMIT', 2), self.assertRaises(ValueError):
            self.store.put(b'123')

    def test_request_receipt_review_does_not_qualify(self):
        a = self.request()
        receipt = self.receive()
        b = self.service.save_information(a.model_copy(update={'revision': 2, 'status': 'EVIDENCE_RECEIVED', 'receipt_ids': (receipt.receipt_id,)}), expected_revision=1, key='received')
        c = self.service.save_information(b.model_copy(update={'revision': 3, 'status': 'FULFILMENT_REVIEWED', 'review_rationale': 'Manifest supplied; source authority remains unresolved'}), expected_revision=2, key='reviewed')
        self.assertEqual(c.status, 'FULFILMENT_REVIEWED')
        self.assertEqual(self.service.inventory('c1', 'e1')[0]['authority'], 'NOT_ESTABLISHED_BY_RECEIPT')
        self.assertEqual(len(self.service.requests('c1', 'e1')), 1)

    def test_request_new_must_start_open(self):
        with self.assertRaises(ValueError):
            self.request(status='WITHDRAWN', review_rationale='No longer required')

    def test_missing_review_rationale_refused(self):
        with self.assertRaises(ValueError):
            InformationRevision(request_id='r', engagement_id='e1', client_id='c1', revision=1,
                question='q', evidence_required='e', status='FULFILMENT_REVIEWED', receipt_ids=('receipt',))

    def test_request_cross_engagement_receipt_refused(self):
        a = self.request()
        other = self.value.model_copy(update={'engagement_id': 'e2'})
        self.service.save_engagement(other, expected_revision=0, key='other')
        receipt = self.service.receive('c1', 'e2', 'x.csv', b'X', role='ACCOUNTING', key='other-file')
        with self.assertRaises(ScopeError):
            self.service.save_information(a.model_copy(update={'revision': 2, 'status': 'EVIDENCE_RECEIVED', 'receipt_ids': (receipt.receipt_id,)}), expected_revision=1, key='foreign')

    def test_save_reopen_after_engine_disposal(self):
        value = self.receive()
        self.request()
        self.session.commit()
        self.session.close()
        self.engine.dispose()
        session = self.factory()
        try:
            owner = WorkspaceService(session, self.operator, EvidenceStore(self.root / 'evidence'))
            self.assertEqual(owner.receipt('c1', value.receipt_id), value)
            self.assertEqual(len(owner.requests('c1', 'e1')), 1)
        finally:
            session.close()

    def test_caller_rollback_removes_receipt_and_audit_with_detectable_orphan(self):
        value = self.receive()
        self.session.rollback()
        self.assertEqual(self.session.scalar(select(func.count()).select_from(t.receipt)), 0)
        self.assertEqual(self.store.unreferenced(set()), [value.sha256])
        self.assertEqual(len(self.service.history('c1', 'e1')), 1)

    def test_database_rejects_cross_client_receipt_parent(self):
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.execute(insert(t.receipt).values(receipt_id='bad', engagement_id='e1', client_id='c2', document='{}'))

    def test_invalid_status_and_extra_asserted_authority_refused(self):
        for changes in ({'status': 'VERIFIED'}, {'authenticated': True}):
            data = self.value.model_dump(mode='json') | changes
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                EngagementRevision.model_validate(data)
