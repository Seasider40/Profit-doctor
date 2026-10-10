"""Discovery and safety delegation only: no API or PostgreSQL access."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from scripts import qualify_production_postgresql_v255 as runner


def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):yield from flatten(item)
        else:yield item


class ProductionRunnerV255(unittest.TestCase):
    def test_preserves_inherited_520_checks_and_final_gate(self):
        inherited=[t.id() for t in flatten(runner.inherited.build_live_suite())]
        actual=[t.id() for t in flatten(runner.build_live_suite())]
        self.assertEqual(len(inherited),520)
        self.assertEqual(len(actual),len(set(actual)))
        self.assertTrue(set(inherited).issubset(actual))
        tail=[t.id() for t in flatten(unittest.TestSuite(list(runner.inherited.build_live_suite())[-2:]))]
        self.assertEqual(actual[-len(tail):],tail)

    def test_static_discovery_opens_no_connection(self):
        with (patch.dict(os.environ,{},clear=True),patch.object(runner.inherited.cumulative,'neon_api_get',side_effect=AssertionError('API forbidden')),
            contextlib.redirect_stdout(io.StringIO()) as output):
            self.assertEqual(0,runner.main(['--disposable-branch','v2-41-qualification','--expected-host','ep-offline.example',
                '--report','unused.json','--list-checks']))
        self.assertIn('discovered',output.getvalue())

    def test_missing_credentials_refuse_before_database(self):
        with (patch.dict(os.environ,{},clear=True),patch.object(runner.inherited.cumulative,'build_engine',side_effect=AssertionError('Database forbidden')),
            contextlib.redirect_stderr(io.StringIO())):
            with self.assertRaises(SystemExit) as error:runner.main(['--disposable-branch','v2-41-qualification',
                '--expected-host','ep-offline.example','--report','unused.json'])
        self.assertEqual(error.exception.code,2)

    def test_current_head_only_changed_inside_execution(self):
        original=runner.inherited.cumulative.CURRENT_HEAD
        def delegated(args):
            self.assertEqual(runner.inherited.cumulative.CURRENT_HEAD,'0020_engagement_workspace')
            self.assertIs(runner.inherited.cumulative.build_live_suite,runner.build_live_suite)
            return 7
        with patch.object(runner.inherited.cumulative,'main',side_effect=delegated):self.assertEqual(runner.main([]),7)
        self.assertEqual(runner.inherited.cumulative.CURRENT_HEAD,original)
        # Exercise the preserved-fixture PostgreSQL empty-state setup offline.
        # The engine and Alembic command are mocked; no network can be used.
        engine=MagicMock();engine.dialect.name='postgresql'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'tests').mkdir()
            fixture=runner.migrations.ProductionEvidenceMigrationsV255('runTest')
            fixture.target_url='postgresql+psycopg://offline.example/qualification'
            with (patch.object(runner.migrations,'ROOT',root),
                    patch.object(runner.migrations,'build_engine',return_value=engine),
                    patch.object(runner.migrations.command,'downgrade') as downgrade):
                try:fixture.setUp()
                finally:fixture.doCleanups()
            downgrade.assert_called_once_with(fixture.cfg,'base')
            sql=engine.begin.return_value.__enter__.return_value.execute.call_args.args[0]
            self.assertEqual(str(sql),'DROP TABLE IF EXISTS alembic_version')
            engine.dispose.assert_called_once()
