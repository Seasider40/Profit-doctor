"""Offline cumulative discovery, inherited coverage and safety delegation."""
import contextlib
import io
import os
import unittest
from unittest.mock import patch
from scripts import qualify_temporal_postgresql_v254 as runner


def tests(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):yield from tests(item)
        else:yield item


class TemporalRunnerV254(unittest.TestCase):
    def test_preserves_every_inherited_check_once_and_keeps_v241_last(self):
        inherited=[t.id() for t in tests(runner._inherited_suite())]
        current=[t.id() for t in tests(runner.build_live_suite())]
        self.assertEqual(472,len(inherited))
        self.assertEqual(len(current),len(set(current)))
        self.assertEqual(set(inherited),set(inherited)&set(current))
        self.assertTrue(any('TemporalMigrationsV254' in name for name in current))
        inherited_tail=[t.id() for t in tests(unittest.TestSuite(list(runner._inherited_suite())[-2:]))]
        self.assertEqual(inherited_tail,current[-len(inherited_tail):])

    def test_offline_discovery_requires_no_api_or_database(self):
        with patch.dict(os.environ,{},clear=True),patch.object(runner.cumulative,'neon_api_get',side_effect=AssertionError('No API')),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0,runner.main(['--disposable-branch',runner.cumulative.BRANCH_NAME,
                '--expected-host','ep-offline.example','--report','unused.json','--list-checks']))
        self.assertIn('"discovered"',output.getvalue())

    def test_missing_credentials_refuse_before_database(self):
        with patch.dict(os.environ,{},clear=True),patch.object(runner.cumulative,'build_engine',side_effect=AssertionError('No database')),contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                runner.main(['--disposable-branch',runner.cumulative.BRANCH_NAME,'--expected-host','ep-offline.example','--report','unused.json'])
        self.assertEqual(2,error.exception.code)

    def test_live_execution_uses_existing_failfast_and_safety_main(self):
        with patch.object(runner.cumulative,'main',return_value=7) as main:
            self.assertEqual(7,runner.main(['test-arguments']))
            main.assert_called_once_with(['test-arguments'])
        self.assertEqual('0019_production_history',runner.cumulative.CURRENT_HEAD)
