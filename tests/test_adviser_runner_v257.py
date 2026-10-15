"""Offline cumulative registration and execution boundary."""
import unittest
from unittest.mock import patch
from scripts import qualify_adviser_postgresql_v257 as runner


def ids(suite):
    for t in suite:
        if isinstance(t,unittest.TestSuite):yield from ids(t)
        else:yield t.id()


class AdviserRunnerV257(unittest.TestCase):
    def test_inherited_ids_and_tail_retained(self):
        old=list(ids(runner.inherited.build_live_suite())); new=list(ids(runner.build_live_suite()))
        self.assertEqual(len(old),784)
        self.assertTrue(set(old)<=set(new)); self.assertEqual(len(new),len(set(new)))
        tail=list(ids(unittest.TestSuite(list(runner.inherited.build_live_suite())[-2:])))
        self.assertEqual(new[-len(tail):],tail)

    def test_discovery_has_no_external_access(self):
        cumulative=runner.inherited.inherited.inherited.cumulative
        with patch.object(cumulative,'neon_api_get',side_effect=AssertionError('API forbidden')),patch.object(cumulative,'build_engine',side_effect=AssertionError('Database forbidden')):
            self.assertEqual(len(list(ids(runner.build_live_suite()))),784+sum(unittest.defaultTestLoader.loadTestsFromTestCase(c).countTestCases() for c in runner.LIVE_CLASSES))

    def test_current_head_only_patched_during_main(self):
        cumulative=runner.inherited.inherited.inherited.cumulative
        original=cumulative.CURRENT_HEAD
        def delegated(argv):
            self.assertEqual(cumulative.CURRENT_HEAD,'0021_adviser_setup'); self.assertIs(cumulative.build_live_suite,runner.build_live_suite)
            return 7
        with patch.object(cumulative,'main',side_effect=delegated):self.assertEqual(runner.main([]),7)
        self.assertEqual(cumulative.CURRENT_HEAD,original)


class EndpointSafetyV257(unittest.TestCase):
    """Every unsafe metadata shape refuses before engine creation."""
    HOST='ep-synthetic.neon.tech'

    def rows(self):
        from tests.test_dataset_qualification_runner_v253 import api_rows
        return api_rows(endpoint_host=self.HOST)

    def refuse(self,rows,*,host=None,stage='endpoint'):
        from contextlib import redirect_stderr
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import Mock,call
        cumulative=runner.inherited.inherited.inherited.cumulative
        host=host or self.HOST
        engine=Mock(side_effect=AssertionError('Unsafe metadata reached database engine'))
        api=Mock(side_effect=lambda path,token:rows[path])
        reasons={
            'endpoint':'The direct host must map uniquely to an enabled read-write endpoint on the verified branch',
            'flags':'Neon branch must explicitly report primary=False and default=False',
            'state':'Neon qualification branch must explicitly report READY state',
            'direct':'The URL must match the expected direct, non-pooler host',
        }
        paths=[f'/projects/{cumulative.PROJECT_ID}',
            f'/projects/{cumulative.PROJECT_ID}/branches/{cumulative.BRANCH_ID}',
            f'/projects/{cumulative.PROJECT_ID}/endpoints']
        expected_calls={'endpoint':3,'flags':2,'state':2,'direct':0}[stage]
        stderr=StringIO()
        with TemporaryDirectory(prefix='pd-endpoint-v257-') as root:
            report=Path(root)/'refusal.json'
            self.assertFalse(report.exists())
            with patch.object(cumulative,'verify_neon_target',wraps=cumulative.verify_neon_target) as verify,\
                    patch.object(cumulative,'reset_qualification_schema',side_effect=AssertionError('Reset forbidden')) as reset:
                with patch.dict('os.environ',{'PROFIT_DOCTOR_POSTGRES_TEST_URL':'postgresql://synthetic@'+host+'/synthetic',
                        'NEON_API_KEY':'synthetic-offline-token','NEON_API_TOKEN':''}),redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as caught:
                        cumulative.main(['--disposable-branch','v2-41-qualification','--expected-host',host,
                            '--report',str(report)],api_get=api,engine_factory=engine)
                verify.assert_called_once()
                reset.assert_not_called()
            self.assertFalse(report.exists())
        self.assertEqual(caught.exception.code,2)
        self.assertIn('error: '+reasons[stage],stderr.getvalue())
        self.assertEqual(api.call_args_list,[call(path,'synthetic-offline-token') for path in paths[:expected_calls]])
        engine.assert_not_called()

    def endpoints(self,rows):
        cumulative=runner.inherited.inherited.inherited.cumulative
        return rows[f'/projects/{cumulative.PROJECT_ID}/endpoints']['endpoints']

    def branch(self,rows):
        cumulative=runner.inherited.inherited.inherited.cumulative
        return rows[f'/projects/{cumulative.PROJECT_ID}/branches/{cumulative.BRANCH_ID}']['branch']

    def test_one_correct_endpoint(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import Mock,call
        cumulative=runner.inherited.inherited.inherited.cumulative;rows=self.rows()
        result=cumulative.verify_neon_target('postgresql://synthetic@'+self.HOST+'/synthetic',self.HOST,'synthetic',
            api_get=lambda path,token:rows[path])
        self.assertEqual(result['host'],self.HOST)
        self.assertEqual(result['project_id'],cumulative.PROJECT_ID)
        self.assertEqual(result['branch_id'],cumulative.BRANCH_ID)
        self.assertEqual(result['branch_name'],cumulative.BRANCH_NAME)
        self.assertEqual(result['endpoint_id'],'ep-qualification')
        self.assertEqual(result['branch_state'],'READY')
        paths=[f'/projects/{cumulative.PROJECT_ID}',
            f'/projects/{cumulative.PROJECT_ID}/branches/{cumulative.BRANCH_ID}',
            f'/projects/{cumulative.PROJECT_ID}/endpoints']
        api=Mock(side_effect=lambda path,token:rows[path])
        class VerifiedEngineBoundary(RuntimeError):pass
        def stop_before_engine(config):
            self.assertEqual(api.call_args_list,[call(path,'synthetic-offline-token') for path in paths])
            self.assertEqual(config.url,'postgresql+psycopg://synthetic@'+self.HOST+'/synthetic')
            raise VerifiedEngineBoundary()
        engine=Mock(side_effect=stop_before_engine)
        with TemporaryDirectory(prefix='pd-endpoint-v257-') as root:
            report=Path(root)/'positive.json'
            self.assertFalse(report.exists())
            with patch.object(cumulative,'verify_neon_target',wraps=cumulative.verify_neon_target) as verify,\
                    patch.object(cumulative,'reset_qualification_schema',side_effect=AssertionError('Reset forbidden')) as reset:
                with patch.dict('os.environ',{'PROFIT_DOCTOR_POSTGRES_TEST_URL':'postgresql://synthetic@'+self.HOST+'/synthetic',
                        'NEON_API_KEY':'synthetic-offline-token','NEON_API_TOKEN':''}):
                    with self.assertRaises(VerifiedEngineBoundary):
                        cumulative.main(['--disposable-branch',cumulative.BRANCH_NAME,'--expected-host',self.HOST,
                            '--report',str(report)],api_get=api,engine_factory=engine)
                verify.assert_called_once();engine.assert_called_once();reset.assert_not_called()
            self.assertFalse(report.exists())

    def test_two_write_endpoints_different_hosts(self):
        rows=self.rows();endpoints=self.endpoints(rows)
        endpoints.append(endpoints[0]|{'id':'another','host':'other.neon.tech'})
        self.refuse(rows)

    def test_duplicate_matching_endpoints(self):
        rows=self.rows();endpoints=self.endpoints(rows);endpoints.append(dict(endpoints[0]));self.refuse(rows)
    def test_no_endpoints(self):
        rows=self.rows();self.endpoints(rows).clear();self.refuse(rows)
    def test_read_only(self):
        rows=self.rows();self.endpoints(rows)[0]['type']='read_only';self.refuse(rows)
    def test_disabled(self):
        rows=self.rows();self.endpoints(rows)[0]['disabled']=True;self.refuse(rows)
    def test_wrong_branch(self):
        rows=self.rows();self.endpoints(rows)[0]['branch_id']='foreign';self.refuse(rows)
    def test_wrong_project(self):
        rows=self.rows();self.endpoints(rows)[0]['project_id']='foreign';self.refuse(rows)
    def test_wrong_direct_host(self):
        rows=self.rows();self.endpoints(rows)[0]['host']='foreign.neon.tech';self.refuse(rows)
    def test_pooled_host(self):self.refuse(self.rows(),host='ep-synthetic-pooler.neon.tech',stage='direct')
    def test_missing_primary(self):
        rows=self.rows();del self.branch(rows)['primary'];self.refuse(rows,stage='flags')
    def test_missing_default(self):
        rows=self.rows();del self.branch(rows)['default'];self.refuse(rows,stage='flags')
    def test_primary(self):
        rows=self.rows();self.branch(rows)['primary']=True;self.refuse(rows,stage='flags')
    def test_default(self):
        rows=self.rows();self.branch(rows)['default']=True;self.refuse(rows,stage='flags')
    def test_not_ready(self):
        rows=self.rows();self.branch(rows)['current_state']='init';self.refuse(rows,stage='state')
    def test_ambiguous_host_ownership(self):
        rows=self.rows();endpoints=self.endpoints(rows);endpoints.append(endpoints[0]|{'branch_id':'foreign'});self.refuse(rows)
    def test_unknown_disabled_state(self):
        rows=self.rows();del self.endpoints(rows)[0]['disabled'];self.refuse(rows)
