"""v2.49 Impact and inherited Bridge/foundation qualification on the verified dedicated disposable branch.

Requires the existing test-only URL, branch opt-in and independently verified
direct host. Never reads a production DATABASE_URL. No connection string in reports.
"""
import argparse
import gc
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
import warnings

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alembic import command
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import Pool
from profit_doctor.persistence import Base, DatabaseConfig, build_engine
from scripts.run_full_estate import EstateResult
from scripts import qualify_reasoning_postgresql_v243 as foundation_qualification
from tests.test_canonical_facts_findings_v244 import CanonicalV244
from tests.test_canonical_migrations_v244 import CanonicalMigrationsV244
from tests.test_postgresql_live_qualification_v218 import alembic_config, reset_qualification_schema

from tests.test_economic_bridge_v248b import EconomicBridgeV248B
from tests.test_economic_bridge_migrations_v248b import EconomicBridgeMigrationsV248B

from tests.test_economic_impact_v249 import EconomicImpactV249, GoldenImpactV249
from tests.test_economic_impact_migrations_v249 import EconomicImpactMigrationsV249

URL = None


class LiveCanonical(CanonicalV244):
    def target_url(self, directory):
        return URL

    def prepare_target(self):
        engine = build_engine(DatabaseConfig(URL))
        try:
            self.assertEqual('postgresql', engine.dialect.name)
            with engine.begin() as c:
                for table in reversed(Base.metadata.sorted_tables):
                    c.execute(table.delete())
        finally:
            engine.dispose()


class LiveCanonicalMigrations(CanonicalMigrationsV244):
    def setUp(self):
        self.url = URL
        self.cfg = alembic_config(URL)
        self.engine = build_engine(DatabaseConfig(URL))
        self.addCleanup(self.engine.dispose)
        self.addCleanup(lambda: self.assertEqual(0, self.engine.pool.checkedout()))
        self.assertEqual('postgresql', self.engine.dialect.name)
        # This destructive reset exists only in the opted-in qualification fixture.
        command.downgrade(self.cfg, 'base')
        with self.engine.begin() as c:
            c.execute(text('DROP TABLE IF EXISTS alembic_version'))


class LiveBridge(EconomicBridgeV248B):
    target_url = LiveCanonical.target_url
    prepare_target = LiveCanonical.prepare_target


class LiveBridgeMigrations(EconomicBridgeMigrationsV248B):
    setUp = LiveCanonicalMigrations.setUp


class LiveImpact(EconomicImpactV249):
    target_url = LiveCanonical.target_url
    prepare_target = LiveCanonical.prepare_target


class LiveGoldenImpact(GoldenImpactV249):
    target_url = LiveCanonical.target_url
    prepare_target = LiveCanonical.prepare_target


class LiveImpactMigrations(EconomicImpactMigrationsV249):
    setUp = LiveCanonicalMigrations.setUp


def main():
    global URL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disposable-branch', required=True, choices=['v2-41-qualification'])
    parser.add_argument('--expected-host', required=True)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--impact-only', action='store_true',
        help='Explicit affected-suite qualification: Impact migrations/mechanics, PostgreSQL static checks and unchanged v2.41 gate')
    args = parser.parse_args()
    URL = os.environ.get('PROFIT_DOCTOR_POSTGRES_TEST_URL', '')
    if not URL:
        parser.error('PROFIT_DOCTOR_POSTGRES_TEST_URL is required')
    parsed = make_url(URL)
    if parsed.drivername != 'postgresql+psycopg' or parsed.host != args.expected_host or '-pooler.' in parsed.host:
        parser.error('Require psycopg and the independently verified direct disposable host')
    os.chdir(ROOT)
    start = time.monotonic()
    engine = build_engine(DatabaseConfig(URL))
    try:
        with engine.connect() as c:
            version = c.scalar(text('SELECT version()'))
        reset_qualification_schema(engine, URL)
    finally:
        engine.dispose()
    opened, checked_out, unraisable = set(), set(), []
    def connected(dbapi, record): opened.add(id(dbapi))
    def closed(dbapi, record): opened.discard(id(dbapi))
    def checkout(dbapi, record, proxy): checked_out.add(id(record))
    def checkin(dbapi, record): checked_out.discard(id(record))
    listeners = [('connect', connected), ('close', closed), ('checkout', checkout), ('checkin', checkin)]
    for name, callback in listeners:
        event.listen(Pool, name, callback)
    hook = sys.unraisablehook
    sys.unraisablehook = lambda e: unraisable.append(f'{e.exc_type.__name__}: {e.exc_value}')
    foundation_qualification.URL = URL
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', DeprecationWarning)
            warnings.simplefilter('error', ResourceWarning)
            loader = unittest.defaultTestLoader
            # Finish migration tests with a complete schema before persistence.
            suite = unittest.TestSuite([
                LiveImpactMigrations('test_frozen_checkpoint_all_tables_preserved_downgrade_and_reupgrade'),
                LiveImpactMigrations('test_clean_creation_and_repeat_head'),
                loader.loadTestsFromTestCase(LiveImpact),
                loader.loadTestsFromTestCase(LiveGoldenImpact),
            ] + ([] if args.impact_only else [
                LiveBridgeMigrations('test_frozen_checkpoint_all_tables_preserved_downgrade_and_reupgrade'),
                LiveBridgeMigrations('test_clean_creation_and_repeat_head'),
                loader.loadTestsFromTestCase(LiveBridge),
                loader.loadTestsFromTestCase(foundation_qualification.LiveFoundation),
            ]) + [
                loader.loadTestsFromName('tests.test_postgresql_readiness_v217'),
                loader.loadTestsFromName('tests.test_postgresql_live_qualification_v218'),
            ])
            collected = suite.countTestCases()
            result = unittest.TextTestRunner(verbosity=2, failfast=True, resultclass=lambda *a, **kw:
                EstateResult(*a, unraisable=unraisable, **kw)).run(suite)
            gc.collect()
    finally:
        sys.unraisablehook = hook
        for name, callback in listeners:
            event.remove(Pool, name, callback)
    counts = {s: sum(x['status'] == s for x in result.outcomes.values()) for s in ('passed', 'failed', 'error', 'skipped')}
    report = dict(postgresql_version=version, branch=args.disposable_branch, collected=collected,
        scope='impact-and-v241' if args.impact_only else 'impact-bridge-foundation-and-v241',
        run=result.testsRun, **counts, seconds=round(time.monotonic()-start, 3),
        open_connections=len(opened), checked_out=len(checked_out), unraisable=unraisable, tests=result.outcomes)
    serialized = json.dumps(report, indent=2)
    for secret in (URL, parsed.password):
        if secret:
            serialized = serialized.replace(secret, '[REDACTED]')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(serialized, encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'tests'}, indent=2))
    return 0 if result.wasSuccessful() and not result.skipped and not opened and not checked_out and not unraisable else 1


if __name__ == '__main__':
    raise SystemExit(main())
