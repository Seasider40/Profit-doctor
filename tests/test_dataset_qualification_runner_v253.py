"""Offline safety and discovery checks for the destructive v2.53 PG runner."""
from io import StringIO
from pathlib import Path
import shutil
from types import SimpleNamespace
from unittest import TestCase
from unittest import TestCase as BaseTestCase, mock
from unittest.mock import patch
import unittest

from scripts import qualify_dataset_postgresql_v253 as runner
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.migration import MigrationContext
from sqlalchemy import inspect
from profit_doctor.persistence import Base, DatabaseConfig, build_engine


HOST = 'ep-disposable.example.neon.tech'
URL = f'postgresql://qualification@{HOST}/app'


def api_rows(*, primary=False, default=False, endpoint_branch=runner.BRANCH_ID,
             endpoint_host=HOST, endpoint_type='read_write', disabled=False):
    return {
        f'/projects/{runner.PROJECT_ID}': {'project': {'id': runner.PROJECT_ID}},
        f'/projects/{runner.PROJECT_ID}/branches/{runner.BRANCH_ID}': {
            'branch': {
                'id': runner.BRANCH_ID, 'project_id': runner.PROJECT_ID,
                'name': runner.BRANCH_NAME, 'primary': primary,
                'default': default, 'current_state': 'ready',
            },
        },
        f'/projects/{runner.PROJECT_ID}/endpoints': {
            'endpoints': [{
                'id': 'ep-qualification', 'project_id': runner.PROJECT_ID,
                'branch_id': endpoint_branch, 'host': endpoint_host,
                'type': endpoint_type, 'disabled': disabled,
            }],
        },
    }


class DatasetQualificationRunnerV253(TestCase):
    def test_discovery_is_nonzero_and_contains_inherited_and_v253_checks(self):
        suite = runner.build_live_suite()
        names = [test.id() for test in iter_tests(suite)]
        self.assertEqual(472, len(names))
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(any('DatasetContractMigrationsV253' in name for name in names))
        self.assertTrue(any('PostgreSQLLiveQualificationV218' in name for name in names))
        self.assertTrue(any('LiveFoundation' in name for name in names))
        self.assertTrue(any('LiveAttention' in name for name in names))

    def test_historical_v243_migrations_run_at_frozen_checkpoint_and_restore_current(self):
        events = []
        frozen = SimpleNamespace(metadata=object())
        reset = mock.Mock(side_effect=lambda engine, url: events.append(('checkpoint', url)))
        restore = mock.Mock(side_effect=lambda url: events.append(('current', url)))
        upgrade = mock.Mock(side_effect=lambda config, revision: events.append(('upgrade', revision)))

        class Probe(BaseTestCase):
            def runTest(self):
                self.assertIs(runner.v243.Base, frozen)
                runner.v243.reset_qualification_schema('engine', 'qualification-url')
                runner.v243.command.upgrade('config', 'head')

        original_base = runner.v243.Base
        original_reset = runner.v243.reset_qualification_schema
        with patch.object(runner.v243.command, 'upgrade', upgrade):
            result = unittest.TextTestRunner(stream=StringIO()).run(
                runner.V243HistoricalMigrationSuite(
                    [Probe()], url='qualification-url', checkpoint_reset=reset,
                    restore_current=restore, frozen_base=frozen))
        self.assertTrue(result.wasSuccessful())
        self.assertEqual([('checkpoint', 'qualification-url'),
                          ('upgrade', runner.V243_HEAD),
                          ('current', 'qualification-url')], events)
        self.assertIs(runner.v243.Base, original_base)
        self.assertIs(runner.v243.reset_qualification_schema, original_reset)

    def test_current_repository_head_is_v253(self):
        config = Config(str(runner.ROOT / 'alembic.ini'))
        self.assertEqual(runner.CURRENT_HEAD, ScriptDirectory.from_config(config).get_current_head())

    def test_frozen_v243_migration_assertions_pass_then_current_head_is_restored(self):
        root = runner.ROOT / 'tests' / '.v253_runner_checkpoint_tmp'
        if root.exists():
            self.fail(f'Refusing to reuse existing checkpoint temp path: {root}')
        root.mkdir()
        database = root / 'v243-checkpoint.db'
        url = 'sqlite+pysqlite:///' + database.as_posix()
        previous_url = runner.v243.URL
        runner.v243.URL = url
        try:
            historical_suite = runner.V243HistoricalMigrationSuite(
                unittest.defaultTestLoader.loadTestsFromTestCase(runner.v243.LiveMigrations),
                url=url)
            result = unittest.TextTestRunner(stream=StringIO(), failfast=True).run(historical_suite)
            self.assertEqual(2, result.testsRun)
            self.assertTrue(result.wasSuccessful(), str(result.failures + result.errors))
            engine = build_engine(DatabaseConfig(url))
            try:
                with engine.connect() as connection:
                    context = MigrationContext.configure(connection)
                    self.assertEqual((runner.CURRENT_HEAD,), context.get_current_heads())
                    self.assertEqual(set(Base.metadata.tables),
                                     set(inspect(engine).get_table_names())
                                     - {'alembic_version'})
            finally:
                engine.dispose()
        finally:
            runner.v243.URL = previous_url
            for path in root.rglob('*'):
                if path.is_file():
                    path.chmod(0o666)
            shutil.rmtree(root)

    def test_historical_suite_failure_remains_fail_fast_and_restores_current(self):
        later_ran = []
        restore = mock.Mock()

        class Fails(BaseTestCase):
            def runTest(self):
                self.fail('injected failure')

        class Later(BaseTestCase):
            def runTest(self):
                later_ran.append(True)

        suite = runner.V243HistoricalMigrationSuite(
            [Fails(), Later()], url='qualification-url',
            checkpoint_reset=mock.Mock(), restore_current=restore,
            frozen_base=SimpleNamespace(metadata=object()))
        result = unittest.TextTestRunner(stream=StringIO(), failfast=True).run(suite)
        self.assertEqual(1, result.testsRun)
        self.assertEqual(1, len(result.failures))
        self.assertEqual([], later_ran)
        restore.assert_called_once_with('qualification-url')

    def test_missing_postgres_url_refuses_before_any_api_or_database_access(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(SystemExit) as error:
                runner.main(['--disposable-branch', runner.BRANCH_NAME,
                             '--expected-host', HOST, '--report', 'unused.json'])
        self.assertEqual(2, error.exception.code)

    def test_missing_neon_token_refuses_before_api_or_database_access(self):
        with patch.dict('os.environ', {'PROFIT_DOCTOR_POSTGRES_TEST_URL': URL}, clear=True):
            with self.assertRaises(SystemExit) as error:
                runner.main(['--disposable-branch', runner.BRANCH_NAME,
                             '--expected-host', HOST, '--report', 'unused.json'])
        self.assertEqual(2, error.exception.code)

    def test_direct_target_verifies_identity_and_endpoint(self):
        responses = api_rows()
        target = runner.verify_neon_target(URL, HOST, 'token',
                                           api_get=lambda path, token: responses[path])
        self.assertEqual(runner.PROJECT_ID, target['project_id'])
        self.assertEqual(runner.BRANCH_ID, target['branch_id'])
        self.assertEqual('ep-qualification', target['endpoint_id'])

    def test_primary_or_default_branch_is_refused(self):
        for flags in ({'primary': True}, {'default': True}):
            with self.subTest(flags=flags):
                responses = api_rows(**flags)
                with self.assertRaises(runner.UnsafeQualificationTarget):
                    runner.verify_neon_target(URL, HOST, 'token',
                        api_get=lambda path, token: responses[path])

    def test_main_refuses_primary_branch_before_postgres_engine_creation(self):
        responses = api_rows(primary=True)
        def make_engine(_config):
            self.fail('PostgreSQL engine must not be created for a primary branch')
        with patch.dict('os.environ', {
            'PROFIT_DOCTOR_POSTGRES_TEST_URL': URL,
            'NEON_API_TOKEN': 'unit-test-token',
        }, clear=True):
            with self.assertRaises(SystemExit) as error:
                runner.main(
                    ['--disposable-branch', runner.BRANCH_NAME, '--expected-host', HOST,
                     '--report', 'unused.json'],
                    api_get=lambda path, token: responses[path],
                    engine_factory=make_engine,
                )
        self.assertEqual(2, error.exception.code)

    def test_wrong_branch_or_host_endpoint_is_refused(self):
        for values in ({'endpoint_branch': 'br-other'}, {'endpoint_host': 'elsewhere.example'}):
            with self.subTest(values=values):
                responses = api_rows(**values)
                with self.assertRaises(runner.UnsafeQualificationTarget):
                    runner.verify_neon_target(URL, HOST, 'token',
                        api_get=lambda path, token: responses[path])

    def test_pooled_disabled_or_read_only_endpoint_is_refused(self):
        cases = [
            (f'postgresql://qualification@ep-disposable-pooler.example.neon.tech/app', HOST, {}),
            (URL, HOST, {'disabled': True}),
            (URL, HOST, {'endpoint_type': 'read_only'}),
        ]
        for url, expected, values in cases:
            with self.subTest(values=values, url_host=url.split('@')[-1].split('/')[0]):
                responses = api_rows(**values)
                with self.assertRaises(runner.UnsafeQualificationTarget):
                    runner.verify_neon_target(url, expected, 'token',
                        api_get=lambda path, token: responses[path])


def iter_tests(suite):
    for item in suite:
        if isinstance(item, __import__('unittest').TestSuite):
            yield from iter_tests(item)
        else:
            yield item
