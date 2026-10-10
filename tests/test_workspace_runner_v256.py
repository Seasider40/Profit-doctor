"""Offline discovery and unchanged disposable verification; never connects."""
import contextlib
import io
import os
import unittest
from unittest.mock import patch
from scripts import qualify_workspace_postgresql_v256 as runner


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


class WorkspaceRunnerV256(unittest.TestCase):
    def test_all_inherited_ids_present_and_resource_gate_last(self):
        prior = [x.id() for x in flatten(runner.inherited.build_live_suite())]
        actual = [x.id() for x in flatten(runner.build_live_suite())]
        self.assertEqual(len(prior), 743)
        self.assertEqual(len(actual), len(set(actual)))
        self.assertTrue(set(prior).issubset(actual))
        tail = [x.id() for x in flatten(unittest.TestSuite(list(runner.inherited.build_live_suite())[-2:]))]
        self.assertEqual(actual[-len(tail):], tail)
        added = sum(unittest.defaultTestLoader.loadTestsFromTestCase(cls).countTestCases() for cls in runner.LIVE_CLASSES)
        self.assertEqual(len(actual), 743 + added)

    def test_discovery_no_api_or_database(self):
        cumulative = runner.inherited.inherited.cumulative
        with (patch.dict(os.environ, {}, clear=True), patch.object(cumulative, 'neon_api_get', side_effect=AssertionError('API forbidden')),
                patch.object(cumulative, 'build_engine', side_effect=AssertionError('Database forbidden')),
                contextlib.redirect_stdout(io.StringIO()) as output):
            self.assertEqual(runner.main(['--disposable-branch', 'v2-41-qualification', '--expected-host', 'ep-offline.example',
                '--report', 'unused.json', '--list-checks']), 0)
        self.assertIn('discovered', output.getvalue())

    def test_missing_credentials_refuse(self):
        cumulative = runner.inherited.inherited.cumulative
        with (patch.dict(os.environ, {}, clear=True), patch.object(cumulative, 'build_engine', side_effect=AssertionError('Database forbidden')),
                contextlib.redirect_stderr(io.StringIO())):
            with self.assertRaises(SystemExit) as error:
                runner.main(['--disposable-branch', 'v2-41-qualification', '--expected-host', 'ep-offline.example', '--report', 'unused.json'])
        self.assertEqual(error.exception.code, 2)

    def test_current_head_patch_restored_and_fail_fast_delegated(self):
        cumulative = runner.inherited.inherited.cumulative
        original = cumulative.CURRENT_HEAD
        def delegated(args):
            self.assertEqual(cumulative.CURRENT_HEAD, '0020_engagement_workspace')
            self.assertIs(cumulative.build_live_suite, runner.build_live_suite)
            return 1
        with patch.object(cumulative, 'main', side_effect=delegated):
            self.assertEqual(runner.main([]), 1)
        self.assertEqual(cumulative.CURRENT_HEAD, original)
