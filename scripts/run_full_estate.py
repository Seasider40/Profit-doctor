"""Authoritative non-live discovery gate; live PostgreSQL has its own workflow."""
from __future__ import annotations

import argparse
from collections import Counter
import gc
import json
import os
from pathlib import Path
import platform
import sys
import time
import unittest
import warnings

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LIVE_PREFIXES = (
    'tests.test_postgresql_readiness_v217.PostgreSQLLiveQualificationV217.',
    'tests.test_postgresql_live_qualification_v218.PostgreSQLLiveQualificationV218.',
)


def inventory_errors(root=ROOT):
    inventory = json.loads((root / 'qualification/test_estate_v242.json').read_text(encoding='utf-8'))
    found = {p.stem for p in (root / 'tests').glob('test*.py')}
    listed = set(inventory)
    return [f'Unclassified modules: {sorted(found - listed)}'] if found - listed else (
        [f'Inventory references missing modules: {sorted(listed - found)}'] if listed - found else []
    )


def collection_counts(suite):
    counts = Counter()
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            counts.update(collection_counts(test))
        else:
            module = (test._testFunc.__module__ if isinstance(test, unittest.FunctionTestCase)
                      else type(test).__module__)
            counts[module.rsplit('.', 1)[-1]] += 1
    return counts


class EstateResult(unittest.TextTestResult):
    """Fail destructor warnings too: warning filters alone cannot do that."""
    def __init__(self, *args, unraisable, **kwargs):
        super().__init__(*args, **kwargs)
        self.unraisable = unraisable
        self.outcomes = {}

    def addSuccess(self, test):
        self.outcomes[test.id()] = {'status': 'passed'}
        super().addSuccess(test)

    def addError(self, test, err):
        self.outcomes[test.id()] = {'status': 'error', 'detail': self._exc_info_to_string(err, test)}
        super().addError(test, err)

    def addFailure(self, test, err):
        self.outcomes[test.id()] = {'status': 'failed', 'detail': self._exc_info_to_string(err, test)}
        super().addFailure(test, err)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.outcomes[test.id()] = {
                'status': 'failed' if issubclass(err[0], test.failureException) else 'error',
                'detail': self._exc_info_to_string(err, test),
            }
        super().addSubTest(test, subtest, err)

    def addSkip(self, test, reason):
        self.outcomes[test.id()] = {'status': 'skipped', 'reason': reason}
        super().addSkip(test, reason)

    def addExpectedFailure(self, test, err):
        self.outcomes[test.id()] = {'status': 'expected_failure'}
        super().addExpectedFailure(test, err)

    def addUnexpectedSuccess(self, test):
        self.outcomes[test.id()] = {'status': 'unexpected_success'}
        super().addUnexpectedSuccess(test)

    def stopTest(self, test):
        # Force observation of delayed destructor failures, not resource cleanup.
        # Connections, engines and files must already have explicit owners.
        gc.collect()
        if self.unraisable:
            error = RuntimeError('Unraisable resource error: ' + '; '.join(self.unraisable))
            self.unraisable.clear()
            self.addError(test, (RuntimeError, error, None))
        super().stopTest(test)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT / 'qualification_outputs/v242/full-estate.json')
    args = parser.parse_args(argv)
    if os.getenv('PROFIT_DOCTOR_POSTGRES_TEST_URL'):
        parser.error('Clear PROFIT_DOCTOR_POSTGRES_TEST_URL; run the separate v2.41 gate for live PostgreSQL.')
    os.chdir(ROOT)
    problems = inventory_errors()
    if problems:
        parser.error('; '.join(problems))
    unraisable = []
    previous_hook = sys.unraisablehook
    started = time.monotonic()
    try:
        sys.unraisablehook = lambda event: unraisable.append(f'{event.exc_type.__name__}: {event.exc_value}')
        with warnings.catch_warnings():
            warnings.simplefilter('error', DeprecationWarning)
            warnings.simplefilter('error', ResourceWarning)
            suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), top_level_dir=str(ROOT))
            collected = suite.countTestCases()
            modules = collection_counts(suite)
            inventory = json.loads((ROOT / 'qualification/test_estate_v242.json').read_text(encoding='utf-8'))
            expected = {name: entry['expected_tests'] for name, entry in inventory.items()}
            if modules != expected:
                problems.append(f'Collected module counts do not match inventory: expected {expected}, got {dict(modules)}')
            runner = unittest.TextTestRunner(
                verbosity=2,
                resultclass=lambda *a, **kw: EstateResult(*a, unraisable=unraisable, **kw),
            )
            result = runner.run(suite)
            gc.collect()
    finally:
        sys.unraisablehook = previous_hook
    counts = {s: sum(o['status'] == s for o in result.outcomes.values()) for s in
              ('passed', 'failed', 'error', 'skipped', 'expected_failure', 'unexpected_success')}
    unexpected_skips = [test.id() for test, _ in result.skipped if not test.id().startswith(LIVE_PREFIXES)]
    policy_errors = problems
    if unexpected_skips:
        policy_errors.append(f'Unexpected skipped tests: {unexpected_skips}')
    if len(result.skipped) != 9:
        policy_errors.append(f'Expected exactly 9 explicitly live PostgreSQL skips; got {len(result.skipped)}')
    if result.expectedFailures:
        policy_errors.append('Expected failures are not allowed in the full-estate gate')
    if unraisable:
        policy_errors.extend(unraisable)
    if collected != result.testsRun or len(result.outcomes) != result.testsRun:
        policy_errors.append('Discovery/run/outcome counts disagree (missing or duplicate test IDs)')
    report = {
        'platform': platform.platform(), 'python': platform.python_version(),
        'collected': collected, 'run': result.testsRun, **counts,
        'modules': dict(modules),
        'seconds': round(time.monotonic() - started, 3),
        'policy_errors': policy_errors, 'tests': result.outcomes,
        'live_postgresql': 'NOT RUN - separate v2.41 workflow required',
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'tests'}, indent=2))
    return 0 if result.wasSuccessful() and not policy_errors else 1


if __name__ == '__main__':
    raise SystemExit(main())
