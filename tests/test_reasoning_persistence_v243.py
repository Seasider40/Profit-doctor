"""Real migrated SQLite persistence and frozen-v2.42 upgrade qualification.

PostgreSQL DDL parity is additionally exercised by the unchanged v2.41 tests.
None of these tests claims live PostgreSQL qualification.
"""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import sqlite3
import tempfile
import unittest

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import MetaData, inspect, insert, select, text, update
from sqlalchemy.exc import IntegrityError

from profit_doctor.persistence import Base, DatabaseConfig, build_engine, session_factory
from profit_doctor.persistence import reasoning_schema as tables
from profit_doctor.reasoning.domain.contracts import (
    Actor, AuditEvent, ConfidenceProfile, EconomicEffect, EffectOverlap, EffectReference,
    EvidenceLink, LineageReference, MaterialityProfile, ReasoningObject,
)
from profit_doctor.reasoning.domain.service import FoundationService, ResolvedScope, RevisionConflict, ScopeError
from profit_doctor.reasoning.domain.vocabulary import AuditEventType, SourceAuthority
from tests.test_postgresql_live_qualification_v218 import alembic_config
from tests.test_reasoning_domain_v243 import T, obj

FIXTURE = Path(__file__).parent / 'fixtures' / 'v242_schema.sql'
ACTOR = Actor(actor_type='SYSTEM', source_authority='SYSTEM_DERIVED', actor_id='test-harness')


class ReasoningPersistenceV243(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'foundation.db'
        self.url = f'sqlite+pysqlite:///{self.path}'
        self.cfg = alembic_config(self.url)
        command.upgrade(self.cfg, 'head')
        self.engine = build_engine(DatabaseConfig(self.url))
        self.addCleanup(self.engine.dispose)
        with self.engine.begin() as connection:
            for client, run in [('c1', 'r1'), ('c2', 'r2'), ('c1', 'r3')]:
                if run != 'r3':
                    connection.execute(text("INSERT INTO client VALUES (:c, 'Client', 'GBP', NULL, :t)"), {'c': client, 't': T.isoformat()})
                connection.execute(text("INSERT INTO engine_run (run_id,client_id,run_type,started_at,status,engine_version) VALUES (:r,:c,'BASELINE',:t,'COMPLETED','2.42')"), {'r': run, 'c': client, 't': T.isoformat()})
        self.factory = session_factory(self.engine)
        self.session = self.factory()
        self.addCleanup(self.session.close)
        self.service = FoundationService(self.session, 'c1', ACTOR)

    def test_create_read_persist_precision_profiles_and_creation_audit(self):
        value = obj(materiality=MaterialityProfile(currency='GBP', cash_impact='999999999999999999.000000000000000009'),
                    confidence=ConfidenceProfile(data_confidence='HIGH', quantification_confidence='LOW'))
        self.service.create_object(value)
        self.session.commit()
        with self.factory() as reader:
            service = FoundationService(reader, 'c1', ACTOR)
            self.assertEqual(value, service.get_object(value.object_id))
            audit = service.audit_events(object_id=value.object_id)
            self.assertEqual(1, len(audit))
            self.assertEqual(AuditEventType.OBJECT_CREATED, audit[0].event_type)
            self.assertEqual('999999999999999999.000000000000000009', audit[0].new['materiality']['cash_impact'])

    def test_update_and_independent_changes_are_audited(self):
        value = self.service.create_object(obj(object_type='FINDING', status='DETECTED'))
        updated = ReasoningObject.model_validate(value.model_dump() | dict(
            revision=2, updated_at=T + timedelta(seconds=1), status='VALIDATED',
            confidence=ConfidenceProfile(data_confidence='HIGH'),
            materiality=MaterialityProfile(urgency='HIGH')))
        self.service.update_object(updated)
        self.assertEqual(updated, self.service.get_object(value.object_id))
        events = self.service.audit_events(object_id=value.object_id)
        self.assertEqual({AuditEventType.OBJECT_CREATED, AuditEventType.OBJECT_UPDATED,
                          AuditEventType.STATUS_CHANGED, AuditEventType.CONFIDENCE_CHANGED,
                          AuditEventType.MATERIALITY_CHANGED}, {e.event_type for e in events})
        status = next(e for e in events if e.event_type == AuditEventType.STATUS_CHANGED)
        self.assertEqual(('DETECTED', 'VALIDATED'), (status.previous, status.new))
        self.assertEqual('test-harness', status.actor.actor_id)

    def test_stale_revision_and_identity_changes_are_rejected(self):
        value = self.service.create_object(obj())
        update = value.model_copy(update=dict(revision=2, updated_at=T + timedelta(seconds=1)))
        self.service.update_object(update)
        with self.assertRaises(RevisionConflict):
            self.service.update_object(update)
        with self.assertRaises(ValueError):
            self.service.update_object(update.model_copy(update=dict(revision=3, source_authority=SourceAuthority.MANAGEMENT_ASSERTION)))
        self.assertEqual(update, self.service.get_object(value.object_id))

    def test_caller_rollback_removes_object_and_audit(self):
        value = self.service.create_object(obj())
        self.session.rollback()
        with self.assertRaises(ScopeError):
            self.service.get_object(value.object_id)
        self.assertEqual([], list(self.session.scalars(select(tables.audit_event.c.event_id))))

    def test_invalid_client_run_and_cross_tenant_reads_are_rejected(self):
        value = self.service.create_object(obj())
        for candidate in [obj(client_id='c2'), obj(run_id='r2'), obj(run_id='missing')]:
            with self.subTest(candidate=candidate), self.assertRaises(ScopeError):
                self.service.create_object(candidate)
        other = FoundationService(self.session, 'c2', ACTOR)
        with self.assertRaises(ScopeError):
            other.get_object(value.object_id)
        with self.assertRaises(ScopeError):
            other.audit_events(object_id=value.object_id)

    def test_links_round_trip_without_causal_promotion(self):
        source = self.service.create_object(obj(source_authority='MANAGEMENT_ASSERTION'))
        target = self.service.create_object(obj(object_type='HYPOTHESIS', status='GENERATED'))
        link = EvidenceLink(client_id='c1', run_id='r1', source_id=source.object_id, target_id=target.object_id,
                            source_authority='MANAGEMENT_ASSERTION', relationship_type='POTENTIALLY_DRIVES',
                            evidence_role='DRIVER_CANDIDATE', metadata={'source_note': 'Customer may renew'})
        self.service.link_evidence(link)
        self.session.commit()
        self.assertEqual(link, self.service.get_link(link.link_id))
        self.assertEqual('GENERATED', self.service.get_object(target.object_id).status)
        self.assertEqual(ConfidenceProfile(), self.service.get_object(target.object_id).confidence)
        self.assertEqual(1, sum(e.event_type == AuditEventType.EVIDENCE_LINKED
                                for e in self.service.audit_events(object_id=target.object_id)))

    def test_links_reject_missing_cross_client_and_relabelled_authority(self):
        source = self.service.create_object(obj(source_authority='MANAGEMENT_ASSERTION'))
        other = FoundationService(self.session, 'c2', ACTOR).create_object(obj(client_id='c2', run_id='r2'))
        for target in ['missing', other.object_id]:
            with self.subTest(target=target), self.assertRaises(ScopeError):
                self.service.link_evidence(EvidenceLink(client_id='c1', source_id=source.object_id,
                    target_id=target, relationship_type='SUPPORTS', source_authority='MANAGEMENT_ASSERTION'))
        target = self.service.create_object(obj())
        with self.assertRaises(ValueError):
            self.service.link_evidence(EvidenceLink(client_id='c1', source_id=source.object_id,
                target_id=target.object_id, relationship_type='SUPPORTS', source_authority='SYSTEM_DERIVED'))

    def test_database_fk_rejects_missing_and_cross_tenant_endpoints(self):
        a = self.service.create_object(obj())
        b = FoundationService(self.session, 'c2', ACTOR).create_object(obj(client_id='c2', run_id='r2'))
        for target in ['missing', b.object_id]:
            with self.subTest(target=target), self.assertRaises(IntegrityError):
                with self.session.begin_nested():
                    self.session.execute(insert(tables.evidence_link).values(link_id='bad', client_id='c1',
                        schema_version='RDF-2.43', created_at=T.isoformat(), document='{}',
                        source_id=a.object_id, target_id=target, relationship_type='SUPPORTS'))

    def test_existing_sqlalchemy_and_prior_run_lineage(self):
        ref = LineageReference(kind='ANALYTICAL_RUN', store='SQLALCHEMY', resource='engine_run',
                               source_id='r1', client_id='c1', run_id='r1')
        a = self.service.create_object(obj(run_id='r3', lineage=(ref,)))
        b = self.service.create_object(obj(run_id='r3', lineage=(ref,)))
        self.session.commit()
        self.assertEqual((ref,), self.service.get_object(a.object_id).lineage)
        self.assertEqual(self.service.get_object(a.object_id).lineage, self.service.get_object(b.object_id).lineage)
        with self.assertRaises(ScopeError):
            self.service.create_object(obj(lineage=(ref.model_copy(update={'source_id': 'r2'}),)))

    def test_legacy_lineage_requires_verified_owning_store_resolution(self):
        ref = LineageReference(kind='SOURCE_FILE', store='LEGACY_SQLITE', resource='source_file',
                               source_id='existing-file', client_id='c1')
        with self.assertRaises(ScopeError):
            self.service.create_object(obj(lineage=(ref,)))
        service = FoundationService(self.session, 'c1', ACTOR, legacy_resolver=lambda r: ResolvedScope('c2'))
        with self.assertRaises(ScopeError):
            service.create_object(obj(lineage=(ref,)))
        # Resolver's contract is tested against an actual owning-store lookup below.
        legacy = sqlite3.connect(':memory:')
        try:
            legacy.execute('CREATE TABLE source_file (source_file_id TEXT PRIMARY KEY, client_id TEXT)')
            legacy.execute("INSERT INTO source_file VALUES ('existing-file','c1')")
            def resolve(reference):
                row = legacy.execute('SELECT client_id FROM source_file WHERE source_file_id=?', (reference.source_id,)).fetchone()
                if row is None:
                    raise ScopeError('Missing legacy source')
                return ResolvedScope(row[0])
            service = FoundationService(self.session, 'c1', ACTOR, legacy_resolver=resolve)
            a = service.create_object(obj(lineage=(ref,)))
            b = service.create_object(obj(lineage=(ref,)))
            self.assertEqual(service.get_object(a.object_id).lineage, service.get_object(b.object_id).lineage)
        finally:
            legacy.close()

    def test_canonical_ancestor_endpoint_and_scope_are_validated(self):
        parent = self.service.create_object(obj())
        ref = LineageReference(kind='DERIVED_ANCESTOR', store='CANONICAL', resource='reasoning_object_v243',
                               source_id=parent.object_id, client_id='c1', run_id='r1')
        child = self.service.create_object(obj(lineage=(ref,)))
        self.assertEqual(parent.object_id, self.service.get_object(child.object_id).lineage[0].source_id)
        with self.assertRaises(ScopeError):
            self.service.create_object(obj(lineage=(ref.model_copy(update={'source_id': 'missing'}),)))

    def test_multiple_objects_share_one_independent_effect(self):
        effect = self.service.create_effect(EconomicEffect(client_id='c1', run_id='r1'))
        story = self.service.create_object(obj(object_type='ECONOMIC_STORY'))
        impact = self.service.create_object(obj(object_type='ECONOMIC_IMPACT', impact_type='CASH_TRAPPED', impact_basis='CASH_RELEASE'))
        for value in [story, impact]:
            reference = self.service.reference_effect(EffectReference(client_id='c1', object_id=value.object_id, effect_id=effect.effect_id))
            self.assertEqual(reference, self.service.get_effect_reference(reference.reference_id))
        self.session.commit()
        ids = list(self.session.scalars(select(tables.effect_reference.c.effect_id)))
        self.assertEqual([effect.effect_id, effect.effect_id], ids)
        self.assertEqual(effect, self.service.get_effect(effect.effect_id))
        self.assertEqual(AuditEventType.OBJECT_CREATED, self.service.audit_events(effect_id=effect.effect_id)[0].event_type)

    def test_effect_relationships_reject_cross_tenant_duplicate_and_self(self):
        a, b = [self.service.create_effect(EconomicEffect(client_id='c1')) for _ in range(2)]
        overlap = EffectOverlap(client_id='c1', source_effect_id=a.effect_id, target_effect_id=b.effect_id,
                                overlap_type='PARENT_CHILD')
        self.service.relate_effects(overlap)
        self.assertEqual(overlap, self.service.get_effect_overlap(overlap.overlap_id))
        with self.assertRaises(IntegrityError):
            with self.session.begin_nested():
                self.service.relate_effects(EffectOverlap(client_id='c1', source_effect_id=b.effect_id,
                    target_effect_id=a.effect_id, overlap_type='INDEPENDENT'))
        with self.assertRaises(ScopeError):
            self.service.relate_effects(EffectOverlap(client_id='c1', source_effect_id=a.effect_id,
                target_effect_id='missing', overlap_type='UNKNOWN_OVERLAP'))

    def test_management_and_human_audit_do_not_change_canonical_state(self):
        value = self.service.create_object(obj(object_type='FINDING', status='DETECTED'))
        for event, actor in [('MANAGEMENT_ASSERTION_RECORDED', Actor(actor_type='MANAGEMENT', source_authority='MANAGEMENT_ASSERTION')),
                             ('HUMAN_OVERRIDE_RECORDED', Actor(actor_type='HUMAN', source_authority='HUMAN_FD_JUDGEMENT'))]:
            self.service.append_audit(AuditEvent(client_id='c1', object_id=value.object_id, event_type=event,
                                               actor=actor, previous={'assessment': None}, new={'context': 'renewal expected'}))
        self.assertEqual(value, self.service.get_object(value.object_id))
        self.assertEqual(3, len(self.service.audit_events(object_id=value.object_id)))

    def test_model_copy_cannot_bypass_service_validation(self):
        invalid = obj().model_copy(update={'status': 'ACCEPTED'})
        with self.assertRaises(ValueError):
            self.service.create_object(invalid)
        self.assertEqual([], list(self.session.scalars(select(tables.reasoning_object.c.object_id))))

    def test_corrupt_document_cannot_bypass_tenant_scoped_read(self):
        value = self.service.create_object(obj())
        forged = obj(object_id=value.object_id, client_id='c2', run_id='r2')
        self.session.execute(update(tables.reasoning_object).where(
            tables.reasoning_object.c.object_id == value.object_id).values(document=forged.to_json()))
        with self.assertRaises(ScopeError):
            self.service.get_object(value.object_id)

    def test_effect_references_and_audits_reject_foreign_tenant(self):
        other = FoundationService(self.session, 'c2', ACTOR)
        effect = other.create_effect(EconomicEffect(client_id='c2', run_id='r2'))
        story = self.service.create_object(obj(object_type='ECONOMIC_STORY'))
        with self.assertRaises(ScopeError):
            self.service.reference_effect(EffectReference(client_id='c1', object_id=story.object_id,
                                                          effect_id=effect.effect_id))
        with self.assertRaises(ScopeError):
            self.service.append_audit(AuditEvent(client_id='c1', effect_id=effect.effect_id,
                                                event_type='OBJECT_UPDATED', actor=ACTOR))

    def test_duplicate_object_effect_reference_is_rejected(self):
        effect = self.service.create_effect(EconomicEffect(client_id='c1'))
        story = self.service.create_object(obj(object_type='ECONOMIC_STORY'))
        self.service.reference_effect(EffectReference(client_id='c1', object_id=story.object_id,
                                                      effect_id=effect.effect_id))
        with self.assertRaises(IntegrityError):
            with self.session.begin_nested():
                self.service.reference_effect(EffectReference(client_id='c1', object_id=story.object_id,
                                                              effect_id=effect.effect_id))


class ReasoningMigrationV243(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'migration.db'
        self.cfg = alembic_config(f'sqlite+pysqlite:///{self.path}')
        self.engine = build_engine(DatabaseConfig(f'sqlite+pysqlite:///{self.path}'))
        self.addCleanup(self.engine.dispose)

    def assert_matches(self):
        with self.engine.connect() as connection:
            self.assertEqual([], compare_metadata(MigrationContext.configure(connection,
                             opts={'compare_type': True, 'compare_server_default': True}), Base.metadata))
        self.assertEqual(set(Base.metadata.tables), set(inspect(self.engine).get_table_names()) - {'alembic_version'})
        for name in Base.metadata.tables:
            self.assertEqual([], inspect(self.engine).get_check_constraints(name))

    def test_clean_creation_and_repeat_upgrade(self):
        command.upgrade(self.cfg, 'head')
        self.assert_matches()
        command.upgrade(self.cfg, 'head')
        self.assert_matches()

    def test_preserved_v242_schema_and_every_table_data_survive_upgrade_and_rollback(self):
        connection = sqlite3.connect(self.path)
        try:
            connection.executescript(FIXTURE.read_text(encoding='utf-8'))
        finally:
            connection.close()
        old = MetaData()
        old.reflect(self.engine)
        self.assertEqual(16, len(old.tables) - 1)
        self.assertFalse(any(name.endswith('_v243') for name in old.tables))
        expected = {}
        # Seed all baseline tables and every field using the preserved schema.
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
                        value = {'status': 'OPEN', 'candidate_status': 'QUALIFIED',
                                 'impact_type': 'REV', 'currency': 'GBP', 'base_currency': 'GBP',
                                 'amount': '123.4500', 'created_at': T.isoformat()}.get(col.name, 'legacy')
                    row[col.name] = value
                connection.execute(insert(table).values(**row))
                expected[table.name] = row
        command.upgrade(self.cfg, 'head')
        self.assert_matches()
        for revision in ['head', '0003_rev_gm_diagnostics']:
            if revision != 'head':
                command.downgrade(self.cfg, revision)
            with self.engine.connect() as connection:
                for name, row in expected.items():
                    with self.subTest(revision=revision, table=name):
                        self.assertEqual(row, dict(connection.execute(select(old.tables[name])).mappings().one()))
        self.assertEqual(set(old.tables), set(inspect(self.engine).get_table_names()))
        command.upgrade(self.cfg, 'head')
        self.assert_matches()

    def test_new_migration_is_independent_of_current_metadata(self):
        source = (Path(__file__).resolve().parents[1] / 'alembic/versions/0004_reasoning_foundation.py').read_text()
        self.assertNotIn('profit_doctor', source)
        self.assertNotIn('metadata', source)
        self.assertNotIn('create_all', source)
        self.assertIn("down_revision = '0003_rev_gm_diagnostics'", source)


if __name__ == '__main__':
    unittest.main()
