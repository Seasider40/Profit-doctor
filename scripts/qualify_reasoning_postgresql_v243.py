"""Explicit destructive v2.43 qualification on a verified disposable PostgreSQL host.

Not part of non-live discovery. Requires the existing qualification URL plus an
operator-supplied expected direct host and the repository's disposable branch name.
Never infers a target from a production database setting. No URL goes in reports.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
from pathlib import Path
import sys
import time
import unittest
import warnings

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import MetaData, event, inspect, insert, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import Pool

from profit_doctor.persistence import Base, DatabaseConfig, build_engine, session_factory
from profit_doctor.persistence import reasoning_schema as tables
from profit_doctor.reasoning.domain.contracts import (
    ConfidenceProfile, EconomicEffect, EffectOverlap, EffectReference, EvidenceLink,
    MaterialityProfile,
)
from profit_doctor.reasoning.domain import vocabulary as vocab
from profit_doctor.reasoning.domain.service import FoundationService
from tests.test_postgresql_live_qualification_v218 import alembic_config, reset_qualification_schema
from tests.test_reasoning_domain_v243 import T, obj
from tests.test_reasoning_persistence_v243 import ACTOR, FIXTURE, ReasoningPersistenceV243
from scripts.run_full_estate import EstateResult

URL = None
NEW_TABLES = {name for name in Base.metadata.tables if name.endswith('_v243')}


def seed(connection):
    for client, run in [('c1', 'r1'), ('c2', 'r2'), ('c1', 'r3')]:
        if run != 'r3':
            connection.execute(text("INSERT INTO client VALUES (:c, 'Qualification', 'GBP', NULL, :t)"),
                               {'c': client, 't': T.isoformat()})
        connection.execute(text("INSERT INTO engine_run (run_id,client_id,run_type,started_at,status,engine_version) "
                                "VALUES (:r,:c,'BASELINE',:t,'COMPLETED','2.43')"),
                           {'r': run, 'c': client, 't': T.isoformat()})


def clear_rows(engine):
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
        seed(connection)


class LiveFoundation(ReasoningPersistenceV243):
    """Run all approved persistence assertions unchanged; replace only the fixture."""
    def setUp(self):
        self.url = URL
        self.engine = build_engine(DatabaseConfig(URL))
        self.addCleanup(self.engine.dispose)
        self.addCleanup(lambda: self.assertEqual(0, self.engine.pool.checkedout()))
        self.assertEqual('postgresql', self.engine.dialect.name)
        clear_rows(self.engine)
        self.factory = session_factory(self.engine)
        self.session = self.factory()
        self.addCleanup(self.session.close)
        self.service = FoundationService(self.session, 'c1', ACTOR)


class LiveMigrations(unittest.TestCase):
    def setUp(self):
        self.engine = build_engine(DatabaseConfig(URL))
        self.addCleanup(self.engine.dispose)
        self.addCleanup(lambda: self.assertEqual(0, self.engine.pool.checkedout()))
        self.cfg = alembic_config(URL)

    def assert_head(self):
        inspector = inspect(self.engine)
        self.assertEqual(set(Base.metadata.tables), set(inspector.get_table_names()) - {'alembic_version'})
        self.assertEqual(6, len(NEW_TABLES))
        with self.engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={'compare_type': True, 'compare_server_default': True})
            self.assertEqual(('0004_reasoning_foundation',), context.get_current_heads())
            self.assertEqual([], compare_metadata(context, Base.metadata))
        for name in NEW_TABLES:
            table = Base.metadata.tables[name]
            with self.subTest(table=name):
                self.assertEqual([c.name for c in table.primary_key], inspector.get_pk_constraint(name)['constrained_columns'])
                actual = {(tuple(f['constrained_columns']), f['referred_table'], tuple(f['referred_columns']),
                           f['options'].get('ondelete')) for f in inspector.get_foreign_keys(name)}
                expected = {(tuple(f.column_keys), f.elements[0].column.table.name,
                             tuple(e.column.name for e in f.elements), f.ondelete)
                            for f in table.foreign_key_constraints}
                self.assertEqual(expected, actual)
                self.assertEqual([], inspector.get_check_constraints(name))

    def test_01_clean_creation_upgrade_and_repeat_head(self):
        reset_qualification_schema(self.engine, URL)
        self.assert_head()
        command.upgrade(self.cfg, 'head')
        self.assert_head()

    def test_02_frozen_v242_upgrade_and_populated_downgrade(self):
        # The independent frozen fixture contains portable VARCHAR/INTEGER/Text
        # DDL. Execute its actual statements, not today's metadata or create_all.
        with self.engine.begin() as connection:
            Base.metadata.drop_all(connection)
            connection.execute(text('DROP TABLE IF EXISTS alembic_version'))
            sql = '\n'.join(line for line in FIXTURE.read_text(encoding='utf-8').splitlines()
                            if not line.lstrip().startswith('--'))
            for statement in sql.split(';'):
                if statement.strip():
                    connection.exec_driver_sql(statement)
        old = MetaData()
        old.reflect(self.engine)
        self.assertEqual(16, len(old.tables) - 1)
        self.assertFalse(NEW_TABLES.intersection(old.tables))
        expected = {}
        with self.engine.begin() as connection:
            ids = {table.name: 'old-' + table.name for table in old.sorted_tables}
            for table in old.sorted_tables:
                if table.name == 'alembic_version':
                    continue
                row = {}
                for col in table.columns:
                    if col.primary_key:
                        value = ids[table.name]
                    elif col.foreign_keys:
                        value = ids[next(iter(col.foreign_keys)).column.table.name]
                    elif str(col.type) == 'INTEGER':
                        value = 1
                    else:
                        value = {'status': 'OPEN', 'candidate_status': 'QUALIFIED', 'impact_type': 'REV',
                                 'currency': 'GBP', 'base_currency': 'GBP', 'amount': '123.4500',
                                 'created_at': T.isoformat()}.get(col.name, 'legacy')
                    row[col.name] = value
                connection.execute(insert(table).values(**row))
                expected[table.name] = row
        command.upgrade(self.cfg, 'head')
        self.assert_head()
        factory = session_factory(self.engine)
        with factory.begin() as session:
            service = FoundationService(session, 'old-client', ACTOR)
            story = service.create_object(obj(client_id='old-client', run_id='old-engine_run', object_type='ECONOMIC_STORY'))
            impact = service.create_object(obj(client_id='old-client', run_id='old-engine_run', object_type='ECONOMIC_IMPACT'))
            effects = [service.create_effect(EconomicEffect(client_id='old-client')) for _ in range(2)]
            service.link_evidence(EvidenceLink(client_id='old-client', source_id=story.object_id,
                target_id=impact.object_id, relationship_type='CONTEXTUALISES', source_authority='SYSTEM_DERIVED'))
            service.reference_effect(EffectReference(client_id='old-client', object_id=story.object_id, effect_id=effects[0].effect_id))
            service.relate_effects(EffectOverlap(client_id='old-client', source_effect_id=effects[0].effect_id,
                target_effect_id=effects[1].effect_id, overlap_type='UNKNOWN_OVERLAP'))
        with self.engine.connect() as connection:
            for name in NEW_TABLES:
                self.assertGreater(connection.scalar(text(f'SELECT count(*) FROM {name}')), 0)
            for name, row in expected.items():
                self.assertEqual(row, dict(connection.execute(select(old.tables[name])).mappings().one()))
        command.downgrade(self.cfg, '0003_rev_gm_diagnostics')
        self.assertEqual(set(old.tables), set(inspect(self.engine).get_table_names()))
        self.assertFalse(NEW_TABLES.intersection(inspect(self.engine).get_table_names()))
        with self.engine.connect() as connection:
            self.assertEqual(('0003_rev_gm_diagnostics',), MigrationContext.configure(connection).get_current_heads())
            for name, row in expected.items():
                self.assertEqual(row, dict(connection.execute(select(old.tables[name])).mappings().one()))
        command.upgrade(self.cfg, 'head')
        self.assert_head()
        with self.engine.connect() as connection:
            for name in NEW_TABLES:
                self.assertEqual(0, connection.scalar(text(f'SELECT count(*) FROM {name}')))


class LiveAdditional(LiveFoundation):
    # Build this class's suite explicitly below: inherited assertions run only once.
    def test_vocabulary_roundtrip(self):
        for kind in vocab.ObjectType:
            value = self.service.create_object(obj(object_type=kind))
            self.assertEqual(value, self.service.get_object(value.object_id))
        for authority in vocab.SourceAuthority:
            value = self.service.create_object(obj(source_authority=authority))
            self.assertEqual(authority, self.service.get_object(value.object_id).source_authority)
        for level in vocab.ConfidenceLevel:
            value = self.service.create_object(obj(confidence=ConfidenceProfile(data_confidence=level)))
            self.assertEqual(level, self.service.get_object(value.object_id).confidence.data_confidence)
        source, target = self.service.create_object(obj()), self.service.create_object(obj())
        roles = list(vocab.EvidenceRole)
        for index, relationship in enumerate(vocab.RelationshipType):
            link = self.service.link_evidence(EvidenceLink(client_id='c1', source_id=source.object_id,
                target_id=target.object_id, relationship_type=relationship, evidence_role=roles[index % len(roles)],
                source_authority='SYSTEM_DERIVED'))
            self.assertEqual(link, self.service.get_link(link.link_id))
        for overlap_type in vocab.OverlapType:
            a, b = [self.service.create_effect(EconomicEffect(client_id='c1')) for _ in range(2)]
            relation = self.service.relate_effects(EffectOverlap(client_id='c1', source_effect_id=a.effect_id,
                target_effect_id=b.effect_id, overlap_type=overlap_type))
            self.assertEqual(relation, self.service.get_effect_overlap(relation.overlap_id))
        for impact_type in vocab.ImpactType:
            value = self.service.create_object(obj(object_type='ECONOMIC_IMPACT', impact_type=impact_type))
            self.assertEqual(impact_type, self.service.get_object(value.object_id).impact_type)
        self.session.commit()

    def test_caller_commit_visibility_and_rollback(self):
        value = self.service.create_object(obj(materiality=MaterialityProfile(currency='GBP', cash_impact='1.230000000000000009')))
        with self.factory() as reader:
            query = select(tables.reasoning_object.c.document).where(tables.reasoning_object.c.object_id == value.object_id)
            self.assertIsNone(reader.scalar(query))
            self.session.commit()
            recovered = FoundationService(reader, 'c1', ACTOR).get_object(value.object_id)
            self.assertEqual(value, recovered)
        rolled_back = self.service.create_object(obj())
        self.session.rollback()
        with self.factory() as reader:
            self.assertIsNone(reader.scalar(select(tables.reasoning_object.c.object_id).where(
                tables.reasoning_object.c.object_id == rolled_back.object_id)))
            self.assertIsNone(reader.scalar(select(tables.audit_event.c.event_id).where(
                tables.audit_event.c.object_id == rolled_back.object_id)))


def main():
    global URL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disposable-branch', required=True, choices=['v2-41-qualification'])
    parser.add_argument('--expected-host', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    URL = os.environ.get('PROFIT_DOCTOR_POSTGRES_TEST_URL', '')
    if not URL:
        parser.error('PROFIT_DOCTOR_POSTGRES_TEST_URL is required')
    parsed = make_url(URL)
    if parsed.drivername != 'postgresql+psycopg' or parsed.host != args.expected_host or '-pooler.' in parsed.host:
        parser.error('Require psycopg and the verified direct disposable host')
    os.chdir(ROOT)
    started = time.monotonic()
    engine = build_engine(DatabaseConfig(URL))
    try:
        with engine.connect() as connection:
            version = connection.scalar(text('SELECT version()'))
            isolation = connection.scalar(text('SHOW transaction_isolation'))
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
    old_hook = sys.unraisablehook
    sys.unraisablehook = lambda e: unraisable.append(f'{e.exc_type.__name__}: {e.exc_value}')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', DeprecationWarning)
            warnings.simplefilter('error', ResourceWarning)
            loader = unittest.defaultTestLoader
            suite = unittest.TestSuite([
                loader.loadTestsFromTestCase(LiveMigrations),
                loader.loadTestsFromTestCase(LiveFoundation),
                LiveAdditional('test_vocabulary_roundtrip'),
                LiveAdditional('test_caller_commit_visibility_and_rollback'),
                loader.loadTestsFromName('tests.test_postgresql_readiness_v217'),
                loader.loadTestsFromName('tests.test_postgresql_live_qualification_v218'),
            ])
            collected = suite.countTestCases()
            result = unittest.TextTestRunner(verbosity=2, resultclass=lambda *a, **kw:
                EstateResult(*a, unraisable=unraisable, **kw)).run(suite)
            gc.collect()
    finally:
        sys.unraisablehook = old_hook
        for name, callback in listeners:
            event.remove(Pool, name, callback)
    counts = {status: sum(o['status'] == status for o in result.outcomes.values())
              for status in ('passed', 'failed', 'error', 'skipped')}
    report = dict(branch=args.disposable_branch, postgresql_version=version, isolation=isolation,
                  collected=collected, run=result.testsRun, **counts, seconds=round(time.monotonic()-started,3),
                  open_connections=len(opened), checked_out=len(checked_out), unraisable=unraisable,
                  tests=result.outcomes)
    # Redact credentials even if a driver's exception unexpectedly includes a URL.
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
