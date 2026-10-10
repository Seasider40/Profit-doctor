"""Real HTTP boundary/journey tests; browser-supplied actor/client flags confer no authority."""
import unittest
from fastapi.testclient import TestClient
from tests.test_workspace_v256 import WorkspaceFixture
from profit_doctor.workspace.app import create_app


class WorkspaceHTTPV256(WorkspaceFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.http = TestClient(create_app(self.factory, self.operator, self.store, access_code='test-access'), base_url='http://127.0.0.1:8765')
        self.addCleanup(self.http.close)
        self.headers = {'Origin': 'http://127.0.0.1:8765', 'Idempotency-Key': 'http-operation'}

    def login(self):
        result = self.http.post('/session', content='test-access', headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.headers['X-CSRF-Token'] = result.json()['csrf']

    def test_anonymous_client_data_refused(self):
        self.assertEqual(self.http.get('/clients').status_code, 401)
        self.assertEqual(self.http.get('/ui.js').status_code, 200)

    def test_wrong_code_refused(self):
        self.assertEqual(self.http.post('/session', content='wrong', headers=self.headers).status_code, 401)

    def test_origin_and_host_refused(self):
        self.assertEqual(self.http.post('/session', content='test-access').status_code, 403)
        self.assertEqual(self.http.get('/', headers={'Host': 'evil.example'}).status_code, 403)

    def test_csrf_required_for_mutation(self):
        self.login()
        headers = dict(self.headers)
        del headers['X-CSRF-Token']
        self.assertEqual(self.http.post('/clients', json={'client_id': 'c1', 'name': 'One'}, headers=headers).status_code, 403)

    def test_http_multi_file_request_and_reopen_journey(self):
        self.login()
        url = '/clients/c1/engagements/e1'
        receipts = []
        for i in range(2):
            headers = self.headers | {'Idempotency-Key': 'upload-' + str(i), 'X-Filename': f'accounts-{i}.csv'}
            result = self.http.post(url + '/receipts', content=f'original-{i}'.encode(), headers=headers)
            self.assertEqual(result.status_code, 200, result.text)
            receipts.append(result.json())
        request = {'request_id': 'http-request', 'client_id': 'c1', 'engagement_id': 'e1', 'revision': 1,
            'question': 'Provide GL provenance', 'evidence_required': 'Original posting export'}
        result = self.http.post(url + '/requests', json={'value': request, 'expected_revision': 0}, headers=self.headers)
        self.assertEqual(result.status_code, 200, result.text)
        first = self.http.get(url).json()
        self.assertEqual(len(first['inventory']), 2)
        self.assertEqual(len(first['requests']), 1)
        self.assertEqual(self.http.get('/clients/c1/receipts/' + receipts[0]['receipt_id']).content, b'original-0')
        self.assertEqual(self.http.get(url + '/readiness').json()[0]['assessment'], None)
        self.assertEqual(self.http.get(url).json(), first)

    def test_foreign_scope_download_refused(self):
        value = self.receive()
        self.session.commit()
        self.login()
        self.assertEqual(self.http.get('/clients/c2/receipts/' + value.receipt_id).status_code, 403)
        self.assertEqual(self.http.get('/clients/c2/engagements/e1').status_code, 403)

    def test_supplied_actor_and_authority_refused(self):
        self.login()
        value = self.value.model_dump(mode='json')
        result = self.http.post('/clients/c1/engagements', json={'value': value, 'expected_revision': 0,
            'actor': 'trusted-issuer', 'verified': True}, headers=self.headers)
        self.assertEqual(result.status_code, 422)

    def test_untrusted_html_download_is_attachment(self):
        value = self.service.receive('c1', 'e1', 'hostile.html', b'<script>bad()</script>', role='UNKNOWN', key='html')
        self.session.commit()
        self.login()
        response = self.http.get('/clients/c1/receipts/' + value.receipt_id)
        self.assertEqual(response.headers['content-disposition'], 'attachment')
        self.assertEqual(response.headers['content-type'], 'application/octet-stream')
        self.assertEqual(response.headers['cache-control'], 'no-store')
