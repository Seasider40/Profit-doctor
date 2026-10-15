"""Administrative draft adversaries; all evidence and accounting remain frozen."""
import unittest
from unittest.mock import patch
from sqlalchemy import insert, select, func
from sqlalchemy.exc import IntegrityError
from tests.test_workspace_v256 import WorkspaceFixture
from profit_doctor.workspace.setup import SetupService, SetupFields, SetupDraft
from profit_doctor.persistence import workspace_schema as w, setup_schema as t
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict


class AdviserSetupV257(WorkspaceFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.setup = SetupService(self.service)
        self.fields = SetupFields(title='Business review', entity_id='entity-1', ledger_id='ledger-1',
            period_start='2027-01-01', period_end='2027-03-31')

    def save(self, fields=None, **kw):
        return self.setup.save('c1', 'draft-1', fields or {}, expected_revision=kw.pop('expected_revision', 0),
            key=kw.pop('key', 'draft-save'), **kw)

    def materialise(self):
        self.save(self.fields)
        return self.save(self.fields, expected_revision=1, key='materialise', action='CREATE_REVIEW')

    def test_partial_draft_has_no_formal_review(self):
        value = self.save()
        self.assertEqual(value.lifecycle, 'DRAFT')
        self.assertIsNone(value.engagement_id)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(w.engagement)), 1)

    def test_partial_fields_round_trip_and_history(self):
        first = self.save({'title': 'Partial'})
        second = self.save(self.fields, expected_revision=1, key='more-fields')
        self.assertEqual(self.setup.get('c1', 'draft-1', 1), first)
        self.assertEqual(SetupDraft.from_json(second.to_json()), second)

    def test_empty_client_or_foreign_draft_refused(self):
        self.save()
        with self.assertRaises(ScopeError): self.setup.get('c2', 'draft-1')
        with self.assertRaises(PermissionError): self.setup.save('foreign', 'x', {}, expected_revision=0, key='x')

    def test_replay_one_revision_and_one_review(self):
        first = self.materialise()
        replay = self.save(self.fields, expected_revision=1, key='materialise', action='CREATE_REVIEW')
        self.assertEqual(first, replay)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(t.link)), 1)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(t.revision)), 2)

    def test_changed_replay_payload_refused(self):
        self.save()
        with self.assertRaises(RevisionConflict): self.save({'title': 'Different'})

    def test_stale_revision_refused(self):
        self.save()
        self.save(self.fields, expected_revision=1, key='revision-2')
        with self.assertRaises(RevisionConflict): self.save({}, expected_revision=1, key='stale')

    def test_incomplete_scope_cannot_create_review(self):
        self.save()
        with self.assertRaises(ValueError): self.save({}, expected_revision=1, key='incomplete', action='CREATE_REVIEW')
        self.assertEqual(self.session.scalar(select(func.count()).select_from(t.link)), 0)

    def test_create_requires_saved_draft(self):
        with self.assertRaises(ValueError): self.save(self.fields, action='CREATE_REVIEW')

    def test_fixed_scope_cannot_be_retargeted(self):
        self.materialise()
        with self.assertRaises(RevisionConflict):
            self.save(self.fields.model_copy(update={'ledger_id': 'other'}), expected_revision=2, key='retarget')

    def test_complete_is_only_administrative(self):
        created = self.materialise()
        complete = self.save(self.fields, expected_revision=2, key='complete', action='COMPLETE', step=3)
        self.assertEqual(complete.lifecycle, 'COMPLETE')
        self.assertEqual(self.service.engagement('c1', created.engagement_id).status, 'OPEN')
        self.assertTrue(all(x['assessment'] is None for x in self.service.readiness('c1', created.engagement_id)))

    def test_complete_requires_review_and_final_step(self):
        self.save()
        with self.assertRaises(ValueError): self.save({}, expected_revision=1, key='complete', action='COMPLETE', step=3)

    def test_terminal_draft_not_mutated(self):
        self.save()
        self.save({}, expected_revision=1, key='cancel', action='CANCEL')
        with self.assertRaises(RevisionConflict): self.save({}, expected_revision=2, key='edit-cancel')

    def test_back_keeps_original_receipts_and_fixed_scope(self):
        created = self.materialise()
        receipt = self.service.receive('c1', created.engagement_id, 'original.csv', b'original', role='SOURCE', key='upload')
        back = self.save(self.fields, expected_revision=2, key='back', step=1)
        self.assertEqual(back.engagement_id, created.engagement_id)
        self.assertEqual(self.service.receipt('c1', receipt.receipt_id).engagement_id, created.engagement_id)

    def test_caller_rollback_removes_draft_review_and_audits(self):
        self.materialise()
        self.session.rollback()
        for table in t.TABLES: self.assertEqual(self.session.scalar(select(func.count()).select_from(table)), 0)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(w.engagement)), 1)
        self.assertEqual(len(self.service.history('c1', 'e1')), 1)

    def test_atomic_materialisation_failure_keeps_saved_draft(self):
        self.save(self.fields)
        with patch.object(self.service, '_audit', side_effect=ValueError('forced failure')):
            with self.assertRaises(ValueError): self.save(self.fields, expected_revision=1, key='failed', action='CREATE_REVIEW')
        self.assertEqual(self.setup.get('c1', 'draft-1').revision, 1)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(t.link)), 0)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(w.engagement)), 1)

    def test_list_bounded_and_client_scoped(self):
        self.save()
        self.assertEqual(self.setup.list('c2'), [])
        self.assertEqual(len(self.setup.list('c1')), 1)
        with self.assertRaises(ValueError): self.setup.list('c1', limit=51)

    def test_cross_client_link_database_refuses(self):
        self.save()
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.execute(insert(t.link).values(draft_id='draft-1', client_id='c2', engagement_id='e1', created_at='now', actor='test'))

    def test_revision_predecessor_database_refuses(self):
        self.save()
        for previous in (None, 2):
            with self.subTest(previous=previous), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.session.execute(insert(t.revision).values(revision_id='bad', draft_id='draft-1', client_id='c1', revision=3,
                    previous_revision=previous, created_at='now', actor='test', event_type='SAVE', request_key='bad', digest='0'*64, document='{}'))

    def test_history_attribution_and_cross_client_refusal(self):
        created = self.materialise()
        history = self.setup.review_history('c1', created.engagement_id)
        self.assertEqual([r['revision'] for r in history], [1, 2])
        self.assertTrue(all(r['actor'] == self.operator.actor for r in history))
        self.assertEqual(history[1]['previous_revision'], 1)
        with self.assertRaises(ScopeError): self.setup.review_history('c2', created.engagement_id)

    def test_invalid_fields_and_asserted_authority_rejected(self):
        for fields in ({'authenticated': True}, {'period_start': '2027-04-01', 'period_end': '2027-03-01'}):
            with self.subTest(fields=fields), self.assertRaises(ValueError): self.save(fields)

    def test_restart_owns_draft_and_immutable_history(self):
        first = self.materialise()
        self.session.commit(); self.session.close(); self.engine.dispose()
        session = self.factory()
        try:
            from profit_doctor.workspace.service import WorkspaceService
            owner = SetupService(WorkspaceService(session, self.operator, self.store))
            self.assertEqual(owner.get('c1', 'draft-1'), first)
            self.assertEqual(owner.get('c1', 'draft-1', 1).lifecycle, 'DRAFT')
        finally: session.close()
