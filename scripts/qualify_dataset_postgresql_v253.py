"""One fail-fast PostgreSQL qualification from the v2.43 foundation through v2.53.

This destructive runner accepts only the established disposable Neon project and
branch. It verifies that target through read-only Neon API requests before its
first PostgreSQL connection. Credentials are read from the current process only.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import gc
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import time
import unittest
import urllib.error
import urllib.request
import warnings

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import MetaData, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import Pool

from profit_doctor.persistence import Base, DatabaseConfig, build_engine
from scripts.run_full_estate import EstateResult
from scripts import qualify_reasoning_postgresql_v243 as v243
from scripts import qualify_story_postgresql_v247 as v247
from scripts import qualify_measurement_context_postgresql_v248 as v248_context
from scripts import qualify_attention_postgresql_v252 as v252
from tests.test_dataset_contract_v253 import DatasetContractV253
from tests.test_dataset_contract_service_v253 import DatasetContractServiceV253
from tests.test_dataset_migrations_v253 import DatasetContractMigrationsV253
from tests.test_postgresql_live_qualification_v218 import reset_qualification_schema
from tests.test_bridge_input_qualification_v248 import BridgeInputPolicyV248, BridgeInputSourceV248


class LiveBridgeInputSourceV248(BridgeInputSourceV248):
    """Run the frozen BIQ source assertions with canonical records in PostgreSQL."""
    target_url = v247.LiveCanonical.target_url
    prepare_target = v247.LiveCanonical.prepare_target

PROJECT_ID = 'tiny-meadow-46991842'
BRANCH_ID = 'br-royal-math-za046ex1'
BRANCH_NAME = 'v2-41-qualification'
API_BASE = 'https://console.neon.tech/api/v2'
V243_HEAD = '0004_reasoning_foundation'
CURRENT_HEAD = '0019_production_history'


_V243_BASE = None


def _frozen_v243_base():
    """Reflect the preserved v2.43 schema fixture for its historical assertions."""
    global _V243_BASE
    if _V243_BASE is None:
        engine = build_engine(DatabaseConfig('sqlite+pysqlite:///:memory:'))
        try:
            statements = '\n'.join(
                line for line in (ROOT / 'tests' / 'fixtures' / 'v243_schema.sql')
                .read_text(encoding='utf-8').splitlines()
                if not line.lstrip().startswith('--'))
            with engine.begin() as connection:
                for statement in statements.split(';'):
                    if statement.strip():
                        connection.exec_driver_sql(statement)
            metadata = MetaData()
            metadata.reflect(engine)
            metadata.remove(metadata.tables['alembic_version'])
            _V243_BASE = SimpleNamespace(metadata=metadata)
        finally:
            engine.dispose()
    return _V243_BASE


def _reset_v243_checkpoint(engine, url):
    """Reset only the disposable schema and stop its migration graph at v2.43."""
    with engine.begin() as connection:
        Base.metadata.drop_all(connection)
        connection.execute(text('DROP TABLE IF EXISTS alembic_version'))
    command = v243.command
    command.upgrade(v243.alembic_config(url), V243_HEAD)


def _restore_current_head(url):
    """Return the disposable database to the repository head after v2.43 checks."""
    engine = build_engine(DatabaseConfig(url, pool_pre_ping=True))
    try:
        reset_qualification_schema(engine, url)
    finally:
        engine.dispose()


class V243HistoricalMigrationSuite(unittest.TestSuite):
    """Run frozen v2.43 migration checks at 0004, then restore current head."""
    def __init__(self, tests, *, url, checkpoint_reset=None,
                 restore_current=None, frozen_base=None):
        super().__init__(tests)
        self.url = url
        self.checkpoint_reset = checkpoint_reset or _reset_v243_checkpoint
        self.restore_current = restore_current or _restore_current_head
        self.frozen_base = frozen_base

    def run(self, result, debug=False):
        original_base = v243.Base
        original_reset = v243.reset_qualification_schema
        original_upgrade = v243.command.upgrade
        historical_base = self.frozen_base or _frozen_v243_base()

        def upgrade_to_v243_head(config, revision, *args, **kwargs):
            if revision == 'head':
                revision = V243_HEAD
            return original_upgrade(config, revision, *args, **kwargs)

        try:
            v243.Base = historical_base
            v243.reset_qualification_schema = self.checkpoint_reset
            v243.command.upgrade = upgrade_to_v243_head
            return super().run(result, debug)
        finally:
            v243.command.upgrade = original_upgrade
            v243.reset_qualification_schema = original_reset
            v243.Base = original_base
            self.restore_current(self.url)


class UnsafeQualificationTarget(ValueError):
    """Raised when current Neon metadata does not prove the disposable target."""


def neon_api_get(path: str, token: str) -> dict:
    """Perform one read-only Neon API GET without exposing response details."""
    request = urllib.request.Request(
        API_BASE + path,
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'},
        method='GET',
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        status = getattr(exc, 'code', None)
        detail = f'HTTP {status}' if status else type(exc).__name__
        raise UnsafeQualificationTarget(f'Neon read-only verification failed ({detail})') from None
    if not isinstance(payload, dict):
        raise UnsafeQualificationTarget('Neon API returned an unexpected response shape')
    return payload


def _record(payload: dict, key: str) -> dict:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise UnsafeQualificationTarget(f'Neon API did not return the expected {key} record')
    return value


def verify_neon_target(url: str, expected_host: str, token: str, *, api_get=neon_api_get) -> dict:
    """Prove project, branch flags and one enabled direct read-write endpoint."""
    parsed = make_url(url)
    host = (parsed.host or '').lower().rstrip('.')
    expected = expected_host.lower().rstrip('.')
    if parsed.drivername not in {'postgresql', 'postgresql+psycopg'}:
        raise UnsafeQualificationTarget('The qualification URL must use PostgreSQL with psycopg')
    if not host or host != expected or '-pooler.' in host:
        raise UnsafeQualificationTarget('The URL must match the expected direct, non-pooler host')
    if not token:
        raise UnsafeQualificationTarget('NEON_API_KEY or NEON_API_TOKEN is required for independent target verification')

    project_payload = api_get(f'/projects/{PROJECT_ID}', token)
    project = _record(project_payload, 'project')
    if project.get('id') != PROJECT_ID:
        raise UnsafeQualificationTarget('Neon project identity did not match the approved disposable project')

    branch_payload = api_get(f'/projects/{PROJECT_ID}/branches/{BRANCH_ID}', token)
    branch = _record(branch_payload, 'branch')
    if (branch.get('id') != BRANCH_ID or branch.get('project_id') != PROJECT_ID
            or branch.get('name') != BRANCH_NAME):
        raise UnsafeQualificationTarget('Neon branch identity did not match the approved qualification branch')
    if branch.get('primary') is not False or branch.get('default') is not False:
        raise UnsafeQualificationTarget('Neon branch must explicitly report primary=False and default=False')
    branch_state = branch.get('current_state', branch.get('state'))
    if not isinstance(branch_state, str) or branch_state.upper() != 'READY':
        raise UnsafeQualificationTarget('Neon qualification branch must explicitly report READY state')

    endpoint_payload = api_get(f'/projects/{PROJECT_ID}/endpoints', token)
    endpoints = endpoint_payload.get('endpoints')
    if not isinstance(endpoints, list):
        raise UnsafeQualificationTarget('Neon project endpoint response did not contain an endpoint list')
    # Fail closed on any host collision; the one matching endpoint must itself
    # prove exact branch ownership and enabled read-write capability.
    host_matches = [row for row in endpoints if isinstance(row, dict)
                    and str(row.get('host', '')).lower().rstrip('.') == host]
    eligible = [row for row in host_matches
                if row.get('branch_id') == BRANCH_ID
                and row.get('type', row.get('endpoint_type')) == 'read_write'
                and row.get('disabled') is False
                and row.get('project_id', PROJECT_ID) == PROJECT_ID]
    if len(host_matches) != 1 or len(eligible) != 1:
        raise UnsafeQualificationTarget('The direct host must map uniquely to an enabled read-write endpoint on the verified branch')
    endpoint = eligible[0]
    return {
        'project_id': PROJECT_ID,
        'branch_id': BRANCH_ID,
        'branch_name': BRANCH_NAME,
        'endpoint_id': endpoint.get('id'),
        'host': host,
        'branch_state': branch_state.upper(),
    }


def build_live_suite() -> unittest.TestSuite:
    """Assemble reused release assertions once, in their qualified reset order."""
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()

    # v2.43 migration/persistence and its two additional lineage/transaction
    # assertions, which later cumulative runners did not include.
    suite.addTest(V243HistoricalMigrationSuite(
        loader.loadTestsFromTestCase(v243.LiveMigrations), url=v243.URL))
    suite.addTests(loader.loadTestsFromTestCase(v243.LiveFoundation))
    suite.addTest(v243.LiveAdditional('test_vocabulary_roundtrip'))
    suite.addTest(v243.LiveAdditional('test_caller_commit_visibility_and_rollback'))

    # Reuse the v2.47 cumulative runner's v2.44-v2.47 frozen upgrades and data
    # assertions, omitting its duplicate foundation persistence and v2.41 gate.
    suite.addTests([
        v247.LiveStoryMigrations('test_frozen_v246_all_tables_preserved_downgrade_and_reupgrade'),
        v247.LiveStoryMigrations('test_clean_creation_and_repeat_head'),
        loader.loadTestsFromTestCase(v247.LiveStory),
        v247.LiveHypothesisMigrations('test_frozen_v245_all_tables_preserved_downgrade_and_reupgrade'),
        v247.LiveHypothesisMigrations('test_clean_creation_and_repeat_head'),
        loader.loadTestsFromTestCase(v247.LiveHypothesis),
        loader.loadTestsFromName('tests.test_hypothesis_gaps_v246'),
        v247.LiveGraphMigrations('test_frozen_v244_all_tables_preserved_downgrade_and_reupgrade'),
        v247.LiveGraphMigrations('test_clean_creation_and_repeat_head'),
        loader.loadTestsFromTestCase(v247.LiveGraph),
        v247.LiveCanonicalMigrations('test_frozen_v243_all_tables_preserved_downgrade_and_reupgrade'),
        v247.LiveCanonicalMigrations('test_clean_creation_and_repeat_head'),
        loader.loadTestsFromTestCase(v247.LiveCanonical),
    ])

    # Explicit v2.48 Measurement Context checkpoint, then the v2.52 cumulative
    # runner's Bridge, Impact, receivables, Opportunity, Priority and Attention
    # suites. The context persistence assertions are covered by that runner's
    # bridge class inheritance; its migration checkpoint is distinct and kept.
    suite.addTests([
        v248_context.LiveContextMigrations('test_frozen_v247_all_tables_preserved_downgrade_and_reupgrade'),
        v248_context.LiveContextMigrations('test_clean_creation_and_repeat_head'),
        loader.loadTestsFromTestCase(v248_context.LiveContext),
        loader.loadTestsFromTestCase(BridgeInputPolicyV248),
        loader.loadTestsFromTestCase(LiveBridgeInputSourceV248),
        v252.LivePriorityMigrations('test_frozen_checkpoint_all_tables_preserved_downgrade_and_reupgrade'),
        v252.LivePriorityMigrations('test_clean_creation_and_repeat_head'),
        loader.loadTestsFromTestCase(v252.LiveAttention),
        loader.loadTestsFromTestCase(v252.LiveAttentionOpportunity),
        loader.loadTestsFromTestCase(v252.LiveGoldenAttention),
        loader.loadTestsFromTestCase(v252.LivePriorityFindings),
        loader.loadTestsFromTestCase(v252.LivePriorityOpportunity),
        loader.loadTestsFromTestCase(v252.LiveGoldenPriority),
        v252.LiveOpportunityMigrations('test_frozen_checkpoint_all_tables_preserved_downgrade_and_reupgrade'),
        v252.LiveOpportunityMigrations('test_clean_creation_and_repeat_head'),
        loader.loadTestsFromTestCase(v252.LiveOpportunity),
        v252.LiveReceivablesMigrations('test_frozen_checkpoint_all_tables_preserved_downgrade_and_reupgrade'),
        v252.LiveReceivablesMigrations('test_clean_creation_and_repeat_head'),
        loader.loadTestsFromTestCase(v252.LiveReceivables),
        v252.LiveImpactMigrations('test_frozen_checkpoint_all_tables_preserved_downgrade_and_reupgrade'),
        v252.LiveImpactMigrations('test_clean_creation_and_repeat_head'),
        loader.loadTestsFromTestCase(v252.LiveImpact),
        loader.loadTestsFromTestCase(v252.LiveGoldenImpact),
        v252.LiveBridgeMigrations('test_frozen_checkpoint_all_tables_preserved_downgrade_and_reupgrade'),
        v252.LiveBridgeMigrations('test_clean_creation_and_repeat_head'),
        loader.loadTestsFromTestCase(v252.LiveBridge),
    ])

    # v2.53 migration, domain and service checks run after inherited schema
    # gates; v2.41 resource/isolation checks are last because they reset schema.
    suite.addTests([
        # The revision-width guard is an offline migration-graph check. Keep it
        # in the local estate without adding a redundant check to the established
        # cumulative live PostgreSQL suite.
        DatasetContractMigrationsV253('test_clean_creation_and_repeat_head'),
        DatasetContractMigrationsV253(
            'test_v252_checkpoint_upgrade_preserves_legacy_rows_on_downgrade_and_reupgrade'),
        loader.loadTestsFromTestCase(DatasetContractV253),
        loader.loadTestsFromTestCase(DatasetContractServiceV253),
        loader.loadTestsFromName('tests.test_postgresql_readiness_v217'),
        loader.loadTestsFromName('tests.test_postgresql_live_qualification_v218'),
    ])
    return suite


def main(argv=None, *, api_get=None, engine_factory=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disposable-branch', required=True, choices=[BRANCH_NAME])
    parser.add_argument('--expected-host', required=True)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--list-checks', action='store_true', help='List static live suite discovery without credentials or database access')
    args = parser.parse_args(argv)

    # Suite discovery is deliberately offline and does not inspect credentials.
    if args.list_checks:
        suite = build_live_suite()
        print(json.dumps({'discovered': suite.countTestCases(), 'runner': 'v2.43-through-v2.53-plus-v2.41'}))
        return 0

    url = os.environ.get('PROFIT_DOCTOR_POSTGRES_TEST_URL', '')
    if not url:
        parser.error('PROFIT_DOCTOR_POSTGRES_TEST_URL is required')
    token = os.environ.get('NEON_API_KEY') or os.environ.get('NEON_API_TOKEN') or ''
    if not token:
        parser.error('NEON_API_KEY or NEON_API_TOKEN is required for read-only Neon target verification')
    try:
        target = verify_neon_target(url, args.expected_host, token, api_get=api_get or neon_api_get)
    except (UnsafeQualificationTarget, ValueError) as exc:
        parser.error(str(exc))

    parsed = make_url(url)
    if parsed.drivername == 'postgresql':
        parsed = parsed.set(drivername='postgresql+psycopg')
    qualified_url = parsed.render_as_string(hide_password=False)
    os.chdir(ROOT)
    started = time.monotonic()

    opened, checked_out, unraisable = set(), set(), []
    listeners = [
        ('connect', lambda dbapi, record: opened.add(id(dbapi))),
        ('close', lambda dbapi, record: opened.discard(id(dbapi))),
        ('checkout', lambda dbapi, record, proxy: checked_out.add(id(record))),
        ('checkin', lambda dbapi, record: checked_out.discard(id(record))),
    ]
    previous_hook = sys.unraisablehook
    for name, callback in listeners:
        event.listen(Pool, name, callback)
    sys.unraisablehook = lambda value: unraisable.append(f'{value.exc_type.__name__}: {value.exc_value}')
    engine = None
    try:
        # No PostgreSQL engine is created before the independent Neon API checks.
        engine = (engine_factory or build_engine)(DatabaseConfig(qualified_url, pool_pre_ping=True))
        if engine.dialect.name != 'postgresql':
            parser.error('The v2.53 live qualification requires PostgreSQL')
        with engine.connect() as connection:
            version = connection.scalar(text('SELECT version()'))
        reset_qualification_schema(engine, qualified_url)
        engine.dispose()

        v243.URL = qualified_url
        v247.URL = qualified_url
        v247.foundation_qualification.URL = qualified_url
        v248_context.URL = qualified_url
        v248_context.foundation_qualification.URL = qualified_url
        v252.URL = qualified_url
        v252.foundation_qualification.URL = qualified_url
        DatasetContractServiceV253.target_url = qualified_url
        DatasetContractMigrationsV253.target_url = qualified_url

        with warnings.catch_warnings():
            warnings.simplefilter('error', DeprecationWarning)
            warnings.simplefilter('error', ResourceWarning)
            suite = build_live_suite()
            collected = suite.countTestCases()
            result = unittest.TextTestRunner(
                verbosity=2,
                failfast=True,
                resultclass=lambda *a, **kw: EstateResult(*a, unraisable=unraisable, **kw),
            ).run(suite)
            gc.collect()
    finally:
        sys.unraisablehook = previous_hook
        for name, callback in listeners:
            event.remove(Pool, name, callback)
        if engine is not None:
            engine.dispose()

    counts = {status: sum(value['status'] == status for value in result.outcomes.values())
              for status in ('passed', 'failed', 'error', 'skipped')}
    report = dict(
        postgresql_version=version,
        project_id=target['project_id'], branch_id=target['branch_id'],
        branch=target['branch_name'], endpoint_id=target['endpoint_id'], host=target['host'],
        primary=False, default=False, collected=collected, run=result.testsRun,
        **counts, seconds=round(time.monotonic() - started, 3),
        open_connections=len(opened), checked_out=len(checked_out),
        unraisable=unraisable, tests=result.outcomes,
    )
    serialized = json.dumps(report, indent=2)
    for secret in (url, parsed.password, token):
        if secret:
            serialized = serialized.replace(secret, '[REDACTED]')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(serialized, encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'tests'}, indent=2))
    return 0 if result.wasSuccessful() and not result.skipped and not opened and not checked_out and not unraisable else 1


if __name__ == '__main__':
    awake = None
    if sys.platform == 'win32':
        import ctypes
        awake = ctypes.windll.kernel32.SetThreadExecutionState
        if not awake(0x80000001):
            raise RuntimeError('Unable to hold Windows awake for live qualification')
    try:
        raise SystemExit(main())
    finally:
        if awake is not None:
            awake(0x80000000)
