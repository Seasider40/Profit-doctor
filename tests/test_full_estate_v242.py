"""CI completeness, fixture provenance and exception-path ownership regressions."""
from contextlib import ExitStack, redirect_stderr
import hashlib
import io
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings

from profit_doctor.core import db
from profit_doctor.intake import bridge, workbook
from profit_doctor import qualification_level3, product_demo, cli
from scripts.run_full_estate import EstateResult, inventory_errors, main
from tests.resources import close_with
from tests.workbook_fixtures import SCENARIO2, SYNTHETIC, generate_scenario1


class FullEstateV242(unittest.TestCase):
    def test_every_test_module_is_classified(self):
        self.assertEqual([], inventory_errors())

    def test_live_url_is_refused_by_non_live_runner(self):
        with patch.dict('os.environ', {'PROFIT_DOCTOR_POSTGRES_TEST_URL': 'configured'}):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main([])
        self.assertEqual(2, error.exception.code)

    def test_test_resource_owner_closes_before_directory_on_exception(self):
        connection = None
        with self.assertRaisesRegex(RuntimeError, 'fixture failed'):
            with tempfile.TemporaryDirectory() as directory, ExitStack() as resources:
                connection = close_with(resources.callback, db.connect(Path(directory) / 'test.db'))
                raise RuntimeError('fixture failed')
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute('SELECT 1')

    def assert_closed_on_error(self, module, call, failure_name):
        opened = []
        original = db.connect

        def capture(path):
            connection = original(path)
            opened.append(connection)
            return connection

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(module, 'connect', side_effect=capture), patch.object(
                module, failure_name, side_effect=RuntimeError('injected failure')
            ):
                with self.assertRaisesRegex(RuntimeError, 'injected failure'):
                    call(Path(directory))
            self.assertEqual(1, len(opened))
            with self.assertRaises(sqlite3.ProgrammingError):
                opened[0].execute('SELECT 1')

    def test_intake_closes_connection_on_failed_workbook(self):
        self.assert_closed_on_error(bridge, lambda d: bridge.execute_unknown_workbook(
            d / 'missing.xlsx', d / 'test.db'), '_ma_rows')

    def test_level3_closes_connection_on_failed_setup(self):
        self.assert_closed_on_error(qualification_level3, lambda d: qualification_level3.build_level3_case(
            d / 'test.db', d / 'missing', d / 'store'), 'ingest_northstar')

    def test_report_closes_connection_on_failed_projection(self):
        with patch.object(product_demo, 'execute_unknown_workbook', return_value={'run_id': 'r'}):
            self.assert_closed_on_error(product_demo, lambda d: product_demo.run_upload_to_report(
                SCENARIO2, d), 'get_product_view_json')

    def test_cli_closes_connection_on_failed_ingestion(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sys, 'argv', ['profit-doctor', '--input', 'unused', '--db', str(Path(directory) / 'cli.db')]):
                self.assert_closed_on_error(cli, lambda d: cli.main(), 'ingest_northstar')

    def test_connection_factory_closes_on_bootstrap_failure(self):
        opened = []
        connect = sqlite3.connect

        def capture(*args, **kwargs):
            connection = connect(*args, **kwargs)
            opened.append(connection)
            return connection

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(db.sqlite3, 'connect', side_effect=capture), patch.object(
                db, '_schema_template', side_effect=RuntimeError('bootstrap failed')
            ):
                with self.assertRaisesRegex(RuntimeError, 'bootstrap failed'):
                    db.connect(Path(directory) / 'test.db')
            with self.assertRaises(sqlite3.ProgrammingError):
                opened[0].execute('SELECT 1')

    def test_workbook_stream_closes_on_parser_failure(self):
        streams = []

        def fail(stream, **options):
            streams.append(stream)
            raise ValueError('invalid workbook')

        with patch.object(workbook, 'load_workbook', side_effect=fail):
            with self.assertRaisesRegex(ValueError, 'invalid workbook'):
                with workbook.open_workbook(SCENARIO2):
                    self.fail('Parser failure must propagate')
        self.assertTrue(streams[0].closed)

    def test_workbook_evidence_is_reproducible_and_original_scenario2_unchanged(self):
        self.assertEqual('ab0d260fccec7fab83b9e9a0eafb9c40147118bb0d99e2015776c40067963a5a',
                         hashlib.sha256(SCENARIO2.read_bytes()).hexdigest())
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / 'one.xlsx', Path(directory) / 'two.xlsx'
            generate_scenario1(first)
            generate_scenario1(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(SYNTHETIC.read_bytes(), first.read_bytes())

    def test_runner_fails_unraisable_resource_warnings(self):
        class LeakedResource:
            def __del__(self):
                warnings.warn('deliberate resource probe', ResourceWarning)

        class Probe(unittest.TestCase):
            def runTest(self):
                resource = LeakedResource()
                del resource

        failures = []
        old_hook = sys.unraisablehook
        try:
            sys.unraisablehook = lambda event: failures.append(str(event.exc_value))
            with warnings.catch_warnings():
                warnings.simplefilter('error', ResourceWarning)
                result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=lambda *a, **kw:
                    EstateResult(*a, unraisable=failures, **kw)).run(Probe())
        finally:
            sys.unraisablehook = old_hook
        self.assertFalse(result.wasSuccessful())
        self.assertEqual(1, len(result.errors))
        self.assertIn('deliberate resource probe', result.errors[0][1])
