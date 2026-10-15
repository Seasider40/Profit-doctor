"""Host/session conveniences do not weaken local operator authority."""
import unittest
from fastapi.testclient import TestClient
from tests.test_workspace_v256 import WorkspaceFixture
from profit_doctor.workspace.app import create_app
from profit_doctor.workspace.session import OperatorSession


class AdviserSessionV257(WorkspaceFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.time = 10.0
        self.http = TestClient(create_app(self.factory, self.operator, self.store, access_code='test-code',
            session_clock=lambda:self.time), base_url='http://127.0.0.1:8765')
        self.addCleanup(self.http.close)
        self.headers = {'Origin':'http://127.0.0.1:8765'}

    def login(self):
        response = self.http.post('/session', content='test-code', headers=self.headers)
        self.assertEqual(response.status_code,200)
        self.headers['X-CSRF-Token'] = response.json()['csrf']
        return response

    def test_anonymous_introspection_no_client_data(self):
        r=self.http.get('/workspace/session'); self.assertEqual(r.status_code,401)
        self.assertNotIn('client_grants',r.json())

    def test_authenticated_refresh_restores_csrf_not_access_secret(self):
        login=self.login(); resume=self.http.get('/workspace/session')
        self.assertEqual(resume.status_code,200)
        self.assertEqual(resume.json()['csrf'],login.json()['csrf'])
        self.assertNotIn('test-code',resume.text)
        self.assertIn('HttpOnly',login.headers['set-cookie'])
        self.assertIn('SameSite=strict',login.headers['set-cookie'])

    def test_idle_expiry(self):
        self.login(); self.time+=OperatorSession.IDLE
        self.assertEqual(self.http.get('/clients').status_code,401)

    def test_polling_does_not_extend_idle(self):
        self.login(); self.time+=3599
        self.assertEqual(self.http.get('/workspace/session').status_code,200)
        self.time+=1; self.assertEqual(self.http.get('/workspace/session').status_code,401)

    def test_explicit_renewal_and_absolute_expiry(self):
        self.login(); self.time+=3500
        self.assertEqual(self.http.post('/workspace/session/renew',headers=self.headers).status_code,200)
        self.time+=3500; self.assertEqual(self.http.get('/clients').status_code,200)
        self.time=10+OperatorSession.ABSOLUTE
        self.assertEqual(self.http.get('/clients').status_code,401)

    def test_signout_revokes_cookie_and_old_csrf(self):
        self.login(); cookie=self.http.cookies.get('pd_workspace')
        self.assertEqual(self.http.post('/workspace/session/end',headers=self.headers).status_code,200)
        self.http.cookies.set('pd_workspace',cookie)
        self.assertEqual(self.http.get('/workspace/session').status_code,401)

    def test_mutations_need_csrf_and_origin(self):
        self.login()
        self.assertEqual(self.http.post('/workspace/session/end',headers={'Origin':self.headers['Origin']}).status_code,403)
        self.assertEqual(self.http.post('/workspace/session/renew',headers={'X-CSRF-Token':self.headers['X-CSRF-Token']}).status_code,403)
        self.assertEqual(self.http.get('/workspace/session',headers={'Host':'wrong.example'}).status_code,403)

    def test_new_login_invalidates_prior_token(self):
        self.login(); old=self.http.cookies.get('pd_workspace'); self.login()
        self.http.cookies.set('pd_workspace',old)
        self.assertEqual(self.http.get('/clients').status_code,401)

    def test_restart_refuses_old_cookie(self):
        self.login(); other=TestClient(create_app(self.factory,self.operator,self.store,access_code='new-code'),base_url='http://127.0.0.1:8765')
        try:
            other.cookies.set('pd_workspace',self.http.cookies.get('pd_workspace'))
            self.assertEqual(other.get('/clients').status_code,401)
        finally: other.close()

    def test_ungranted_and_foreign_summary_access(self):
        self.login()
        self.assertEqual(self.http.get('/clients/foreign/setup-drafts').status_code,403)
        self.assertEqual(self.http.get('/workspace/home?limit=51').status_code,400)
        self.assertEqual(self.http.get('/clients/c2/setup-drafts/draft-1').status_code,403)

    def test_unicode_filename_preserves_exact_identity(self):
        self.login()
        from urllib.parse import quote
        r=self.http.post('/clients/c1/engagements/e1/receipts',content=b'original',headers=self.headers|{
            'Idempotency-Key':'unicode','X-Filename-Encoded':quote('état-financier.csv')})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['filename'],'état-financier.csv')
        self.assertEqual(r.json()['actor'],self.operator.actor)

    def test_asserted_actor_draft_refused(self):
        self.login()
        r=self.http.post('/clients/c1/setup-drafts',json={'draft_id':'x','fields':{},'expected_revision':0,'actor':'issuer'},headers=self.headers)
        self.assertEqual(r.status_code,422)


    def test_cross_client_refusal_after_rotation(self):
        self.login(); self.login()
        self.assertEqual(self.http.get('/clients/foreign/setup-drafts').status_code,403)


class SessionBindingSafetyV257(unittest.TestCase):
    """Controlled interleavings: no database, network, sleeps or token logging."""
    def setUp(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from profit_doctor.workspace import app as module
        from profit_doctor.workspace.storage import EvidenceStore
        self.time = 10.0
        self.owner = OperatorSession(clock=lambda:self.time)
        def forbidden():
            raise AssertionError('Database access forbidden in session safety tests')
        with patch.object(module,'OperatorSession',return_value=self.owner):
            app=module.create_app(forbidden,SimpleNamespace(actor='synthetic',clients=frozenset({'c1'})),
                object.__new__(EvidenceStore),access_code='synthetic-session-safety')
        self.http=TestClient(app,base_url='http://127.0.0.1:8765')
        self.addCleanup(self.http.close)
        response=self.http.post('/session',content='synthetic-session-safety',headers={'Origin':'http://127.0.0.1:8765'})
        self.assertEqual(response.status_code,200)
        self.token=self.http.cookies.get('pd_workspace')
        self.binding=self.owner.authenticate(self.token)
        self.headers={'Origin':'http://127.0.0.1:8765','X-CSRF-Token':response.json()['csrf']}

    def interrupted(self,path,*,revoke=False):
        from unittest.mock import patch
        original=self.owner.authenticate
        successor=[]
        def interleave(*args,**kwargs):
            bound=original(*args,**kwargs)
            if revoke:self.owner.end(bound)
            else:successor.append(self.owner.login())
            return bound
        with patch.object(self.owner,'authenticate',side_effect=interleave):
            response=self.http.get(path) if path=='/workspace/session' else self.http.post(path,headers=self.headers)
        self.assertEqual(response.status_code,401)
        self.assertNotIn('csrf',response.json())
        self.assertNotIn('client_grants',response.json())
        self.assertNotIn('set-cookie',response.headers)
        if successor:
            self.assertEqual(self.owner.authenticate(successor[0].token),successor[0])
            self.assertNotIn(successor[0].csrf,response.text)
        return response

    def test_rotation_before_metadata(self):self.interrupted('/workspace/session')
    def test_rotation_before_renewal(self):self.interrupted('/workspace/session/renew')
    def test_rotation_before_signout(self):self.interrupted('/workspace/session/end')
    def test_revocation_before_metadata(self):self.interrupted('/workspace/session',revoke=True)
    def test_revocation_before_renewal(self):self.interrupted('/workspace/session/renew',revoke=True)
    def test_revocation_before_signout(self):self.interrupted('/workspace/session/end',revoke=True)

    def test_old_token_after_rotation(self):
        self.owner.login()
        self.assertEqual(self.http.get('/workspace/session').status_code,401)

    def test_old_token_after_signout(self):
        self.owner.end(self.binding)
        self.assertEqual(self.http.get('/workspace/session').status_code,401)

    def test_expired_binding_before_metadata(self):
        self.time+=OperatorSession.IDLE
        self.assertEqual(self.http.get('/workspace/session').status_code,401)

    def test_absolute_expiry_cannot_be_renewed(self):
        self.time+=OperatorSession.ABSOLUTE
        self.assertEqual(self.http.post('/workspace/session/renew',headers=self.headers).status_code,401)

    def test_concurrent_requests_keep_distinct_identities(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from profit_doctor.workspace.session import SessionRefused
        barrier=Barrier(2)
        def old_request():
            binding=self.owner.authenticate(self.token)
            barrier.wait(timeout=10);barrier.wait(timeout=10)
            with self.assertRaises(SessionRefused):self.owner.metadata(binding)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future=executor.submit(old_request)
            barrier.wait(timeout=10)
            successor=self.owner.login()
            barrier.wait(timeout=10);future.result(timeout=10)
        self.assertEqual(self.owner.metadata(successor)['csrf'],successor.csrf)

    def test_csrf_cannot_cross_session_identities(self):
        successor=self.owner.login()
        self.http.cookies.clear();self.http.cookies.set('pd_workspace',successor.token)
        self.assertEqual(self.http.post('/workspace/session/renew',headers=self.headers).status_code,403)
        self.assertEqual(self.owner.authenticate(successor.token),successor)

    def test_successful_bound_operations(self):
        self.assertEqual(self.http.get('/workspace/session').json()['csrf'],self.binding.csrf)
        self.time+=100
        response=self.http.post('/workspace/session/renew',headers=self.headers)
        self.assertEqual(response.status_code,200);self.assertEqual(response.json()['idle_seconds'],3600)
        self.assertEqual(self.http.post('/workspace/session/end',headers=self.headers).status_code,200)
        self.assertEqual(self.http.get('/workspace/session').status_code,401)

    def test_replay_failure_does_not_revoke_successor(self):
        successor=self.owner.login()
        for _ in range(2):
            self.assertEqual(self.http.post('/workspace/session/end',headers=self.headers).status_code,401)
        self.assertEqual(self.owner.authenticate(successor.token),successor)

    def test_copied_binding_cannot_impersonate_authenticated_identity(self):
        from profit_doctor.workspace.session import SessionBinding,SessionRefused
        with self.assertRaises(SessionRefused):self.owner.metadata(SessionBinding(self.binding.token,self.binding.csrf))
