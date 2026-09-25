"""Profit Doctor v2.18 live PostgreSQL qualification gate.

These tests are intentionally opt-in. They MUST run against a disposable PostgreSQL
qualification database via PROFIT_DOCTOR_POSTGRES_TEST_URL. SQLite is explicitly
rejected: passing this file on SQLite is not PostgreSQL qualification evidence.
"""
import os
import threading
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from profit_doctor.persistence import (
    Base, Client, EngineRun, OpportunityRelationship, DatabaseConfig,
    build_engine, session_factory, session_scope, ping,
)

URL = os.getenv("PROFIT_DOCTOR_POSTGRES_TEST_URL")
LIVE = bool(URL and URL.startswith("postgresql"))
T = "2026-09-25T00:00:00Z"


def alembic_config(url):
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@unittest.skipUnless(LIVE, "disposable live PostgreSQL URL not supplied")
class PostgreSQLLiveQualificationV218(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = URL
        cls.engine = build_engine(DatabaseConfig(cls.url, pool_pre_ping=True))
        cls.F = session_factory(cls.engine)
        if cls.engine.dialect.name != "postgresql":
            raise unittest.SkipTest("qualification database is not PostgreSQL")
        with cls.engine.begin() as c:
            Base.metadata.drop_all(c)
        command.upgrade(alembic_config(cls.url), "head")

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        # Keep the migrated schema, but isolate each test's rows.
        with self.engine.begin() as c:
            for table in reversed(Base.metadata.sorted_tables):
                c.execute(table.delete())
        with session_scope(self.F) as s:
            s.add(Client(client_id="c1", client_name="Client 1", base_currency="GBP", created_at=T))
            s.add(Client(client_id="c2", client_name="Client 2", base_currency="GBP", created_at=T))
            s.add(EngineRun(run_id="r1", client_id="c1", run_type="BASELINE", started_at=T, status="RUNNING", engine_version="2.18"))
            s.add(EngineRun(run_id="r2", client_id="c2", run_type="BASELINE", started_at=T, status="RUNNING", engine_version="2.18"))

    def test_01_alembic_head_matches_current_metadata_tables(self):
        self.assertTrue(ping(self.engine))
        names = set(inspect(self.engine).get_table_names())
        self.assertEqual(set(Base.metadata.tables), names)

    def test_02_commit_and_rollback_are_atomic(self):
        with session_scope(self.F) as s:
            s.add(Client(client_id="committed", client_name="Committed", base_currency="GBP", created_at=T))
        try:
            with session_scope(self.F) as s:
                s.add(Client(client_id="rolledback", client_name="Rollback", base_currency="GBP", created_at=T))
                raise RuntimeError("force rollback")
        except RuntimeError:
            pass
        with self.F() as s:
            self.assertIsNotNone(s.get(Client, "committed"))
            self.assertIsNone(s.get(Client, "rolledback"))

    def test_03_database_foreign_key_rejects_missing_tenant(self):
        with self.assertRaises(IntegrityError):
            with session_scope(self.F) as s:
                s.add(EngineRun(run_id="bad", client_id="missing", run_type="BASELINE", started_at=T, status="RUNNING", engine_version="2.18"))

    def test_04_concurrent_symmetric_uniqueness_race_has_one_winner(self):
        barrier = threading.Barrier(2)
        outcomes = []
        lock = threading.Lock()
        def worker(rel_id, left, right):
            try:
                with session_scope(self.F) as s:
                    s.add(OpportunityRelationship(
                        relationship_id=rel_id, client_id="c1", run_id="r1",
                        from_opportunity_id=left, to_opportunity_id=right,
                        pair_key="oppA|oppB", relationship_type="OVERLAPPING",
                        overlap_amount="20", evidence_basis="race",
                    ))
                    barrier.wait(timeout=10)
                result = "COMMIT"
            except IntegrityError:
                result = "INTEGRITY_ERROR"
            except Exception as exc:
                result = type(exc).__name__
            with lock:
                outcomes.append(result)
        a = threading.Thread(target=worker, args=("rel-a", "oppA", "oppB"))
        b = threading.Thread(target=worker, args=("rel-b", "oppB", "oppA"))
        a.start(); b.start(); a.join(20); b.join(20)
        self.assertFalse(a.is_alive() or b.is_alive(), "concurrent uniqueness test deadlocked")
        self.assertEqual(sorted(outcomes), ["COMMIT", "INTEGRITY_ERROR"])
        with self.F() as s:
            rows = s.scalars(select(OpportunityRelationship).where(OpportunityRelationship.pair_key == "oppA|oppB")).all()
            self.assertEqual(1, len(rows))

    def test_05_read_committed_does_not_expose_uncommitted_rows(self):
        writer = self.F(); reader = self.F()
        try:
            writer.begin()
            writer.add(Client(client_id="uncommitted", client_name="Hidden", base_currency="GBP", created_at=T))
            writer.flush()
            self.assertIsNone(reader.get(Client, "uncommitted"))
            writer.commit()
            reader.expire_all()
            self.assertIsNotNone(reader.get(Client, "uncommitted"))
        finally:
            writer.close(); reader.close()

    def test_06_pool_checkout_recovery_and_reuse(self):
        for _ in range(25):
            self.assertTrue(ping(self.engine))
        self.engine.dispose()
        # Engine remains reusable after its pool is disposed/recreated.
        self.assertTrue(ping(self.engine))

    def test_07_alembic_downgrade_base_and_upgrade_head(self):
        command.downgrade(alembic_config(self.url), "base")
        self.assertEqual([], inspect(self.engine).get_table_names())
        command.upgrade(alembic_config(self.url), "head")
        self.assertEqual(set(Base.metadata.tables), set(inspect(self.engine).get_table_names()))


class PostgreSQLQualificationContractV218(unittest.TestCase):
    def test_live_gate_cannot_be_accidentally_claimed_on_sqlite(self):
        if URL:
            self.assertTrue(URL.startswith("postgresql"), "PROFIT_DOCTOR_POSTGRES_TEST_URL must be PostgreSQL")
        else:
            self.assertFalse(LIVE)

    def test_required_live_attacks_are_present(self):
        names = {n for n in dir(PostgreSQLLiveQualificationV218) if n.startswith("test_")}
        required = {
            "test_01_alembic_head_matches_current_metadata_tables",
            "test_02_commit_and_rollback_are_atomic",
            "test_03_database_foreign_key_rejects_missing_tenant",
            "test_04_concurrent_symmetric_uniqueness_race_has_one_winner",
            "test_05_read_committed_does_not_expose_uncommitted_rows",
            "test_06_pool_checkout_recovery_and_reuse",
            "test_07_alembic_downgrade_base_and_upgrade_head",
        }
        self.assertTrue(required.issubset(names))


if __name__ == "__main__":
    unittest.main()
