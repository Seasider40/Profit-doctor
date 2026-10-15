"""Home is an administrative, bounded, grant-scoped projection."""
import unittest
from unittest.mock import patch
from sqlalchemy import insert, update
from tests.test_workspace_v256 import WorkspaceFixture
from profit_doctor.workspace.home import reviews
from profit_doctor.workspace.contracts import Operator, EngagementRevision
from profit_doctor.workspace.service import WorkspaceService
from profit_doctor.persistence import workspace_schema as t
from profit_doctor.reasoning.domain.service import ScopeError


class AdviserHomeV257(WorkspaceFixture, unittest.TestCase):
    def test_home_does_not_hash_originals_or_create_assessments(self):
        self.receive(); self.request()
        with patch.object(self.store,'read',side_effect=AssertionError('Home cannot hash originals')):
            result=reviews(self.service)
        self.assertEqual(result[0]['outstanding_information'],1)
        self.assertEqual(result[0]['review'],self.value.model_dump(mode='json'))

    def test_latest_review_revision_and_status(self):
        self.service.save_engagement(self.value.model_copy(update={'revision':2,'status':'CLOSED'}),expected_revision=1,key='close')
        self.assertEqual(reviews(self.service)[0]['review']['status'],'CLOSED')
        self.assertEqual(len(reviews(self.service)),1)

    def test_only_granted_clients_in_summaries(self):
        owner=WorkspaceService(self.session,Operator('other',frozenset({'c2'})),self.store)
        self.assertEqual(reviews(owner),[])

    def test_pagination_bound_and_empty_state(self):
        self.assertEqual(reviews(self.service,offset=1),[])
        for args in ({'limit':0},{'limit':51},{'offset':-1}):
            with self.subTest(args=args),self.assertRaises(ValueError):reviews(self.service,**args)

    def test_withdrawn_request_is_not_outstanding_or_reviewed(self):
        r=self.request()
        self.service.save_information(r.model_copy(update={'revision':2,'status':'WITHDRAWN','review_rationale':'Not required'}),expected_revision=1,key='withdraw')
        self.assertEqual(reviews(self.service)[0]['outstanding_information'],0)

    def test_document_scope_corruption_refuses(self):
        value=self.value.model_copy(update={'client_id':'c2'})
        self.session.execute(update(t.engagement_revision).where(t.engagement_revision.c.engagement_id=='e1').values(document=value.to_json()))
        with self.assertRaises(ScopeError):reviews(self.service)
