"""Adversarial semantic and persistence qualification of the opt-in boundary."""
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from alembic import command
from sqlalchemy import insert, select, text
from sqlalchemy.exc import IntegrityError

from profit_doctor.core.db import connect
from profit_doctor.persistence import DatabaseConfig, build_engine, session_factory
from profit_doctor.persistence import canonical_schema as tables
from profit_doctor.reasoning.canonical.contracts import CanonicalFact, Measurement, render_fact
from profit_doctor.reasoning.canonical.registry import REGISTRY, MAPPING_VERSIONS, Unit
from profit_doctor.reasoning.canonical.service import CanonicalService
from profit_doctor.reasoning.canonical.source import LegacySignalSource
from profit_doctor.reasoning.domain.contracts import Actor, ConfidenceProfile, MaterialityProfile, ReasoningObject
from profit_doctor.reasoning.domain.service import ScopeError
from scripts.inventory_signals_v244 import inventory
from tests.test_postgresql_live_qualification_v218 import alembic_config

T = '2026-09-28T00:00:00+00:00'


class CanonicalV244(unittest.TestCase):
    def target_url(self, directory):
        return 'sqlite+pysqlite:///' + (Path(directory) / 'canonical.db').as_posix()

    def prepare_target(self):
        command.upgrade(alembic_config(self.url), 'head')

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.legacy = connect(Path(directory.name) / 'source.db')
        self.addCleanup(self.legacy.close)
        self.url = self.target_url(directory.name)
        self.prepare_target()
        self.engine = build_engine(DatabaseConfig(self.url))
        self.addCleanup(self.engine.dispose)
        self.factory = session_factory(self.engine)
        self.session = self.factory()
        self.addCleanup(self.session.close)
        with self.engine.begin() as c:
            for client in ('c1', 'c2'):
                c.execute(text('INSERT INTO client VALUES (:c, :c, \'GBP\', NULL, :t)'), {'c': client, 't': T})
            for run, client, started in [('r1', 'c1', T), ('r2', 'c2', T), ('r3', 'c1', '2026-10-28T00:00:00+00:00')]:
                c.execute(text("INSERT INTO engine_run (run_id,client_id,run_type,started_at,status,engine_version) VALUES (:r,:c,'BASELINE',:t,'COMPLETED','2.43')"), {'r': run, 'c': client, 't': started})
        self.actor = Actor(actor_type='SYSTEM', actor_id='v244-test', source_authority='SYSTEM_DERIVED')
        self.source = LegacySignalSource(self.legacy, 'c1')
        self.service = CanonicalService(self.session, 'c1', self.actor, self.source)

    def signal(self, sid='s1', typ='CUSTOMER_PROFITABILITY', test='CUS-02', run='r1',
               observed='123.4500', comparison='500.0000', variance='24.6900', unit='GBP',
               entity='CUSTOMER', entity_id='customer-a', eligibility='FULL', period_from=None, period_to=None,
               limitation=None, lineage=True):
        self.legacy.execute('INSERT INTO test_execution VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            ('ex-'+sid, run, 'c1', test, 'FROZEN_METHOD', eligibility, 'COMPLETED', 1, limitation, T, T))
        self.legacy.execute('INSERT INTO signal VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (sid, 'ex-'+sid, run, 'c1', test, typ, entity, entity_id, period_from, period_to,
             observed, comparison, variance, unit, 'HIGH', 'ACTIVE', 'Untrusted prose must not define truth', None, T))
        if lineage:
            self.legacy.execute('INSERT INTO diagnostic_lineage VALUES (?,?,?,?,?,?)',
                ('lin-'+sid, sid, 'SOURCE_FILE', 'shared-source-file', 'DERIVED_FROM', 'captured source ancestry'))
        self.legacy.commit()
        return sid

    def revenue(self, sid='s1', **kwargs):
        return self.signal(sid, typ='COMPARABLE_REVENUE_CHANGE', test='REV-01', entity=None,
            entity_id=None, observed='120', comparison='100', variance='20', **kwargs)

    def test_mixed_gbp_percent_precision_roundtrip_and_render(self):
        fact = self.service.canonicalise(self.signal()).fact
        self.assertEqual([Unit.CURRENCY, Unit.CURRENCY, Unit.PERCENTAGE],
                         [fact.observed.unit, fact.comparison.unit, fact.derived.unit])
        self.assertEqual(Decimal('123.4500'), fact.observed.value)
        self.assertIn('123.4500 GBP CURRENCY', render_fact(fact))
        self.assertIn('24.6900 %', render_fact(fact))
        self.assertNotIn('movement', render_fact(fact))
        self.assertEqual(fact, CanonicalFact.from_json(fact.to_json()))
        self.session.commit()
        with self.factory() as session:
            self.assertEqual(fact, CanonicalService(session, 'c1', self.actor, self.source).get_fact(fact.object_id))

    def test_percent_and_percentage_points_are_distinct(self):
        sid = self.signal(typ='CONTRIBUTION_MARGIN_CHANGE', test='GM-01', unit='PERCENTAGE_POINTS',
            observed='27', comparison='31', variance='-4', entity=None, entity_id=None)
        fact = self.service.canonicalise(sid).fact
        self.assertEqual(Unit.PERCENTAGE, fact.observed.unit)
        self.assertEqual(Unit.PERCENTAGE_POINTS, fact.derived.unit)
        self.assertIn('-4 percentage points', render_fact(fact))
        self.assertNotIn('-12.9', render_fact(fact))
        below = self.signal('just-below', typ='CONTRIBUTION_MARGIN_CHANGE', test='GM-01', unit='PERCENTAGE_POINTS',
            observed='30.00000000000000000000000000001', comparison='31', variance='-0.99999999999999999999999999999', entity=None, entity_id=None)
        below_fact = self.service.canonicalise(below).fact
        self.assertEqual('NOT_SIGNIFICANT', self.service.assess(below_fact.object_id).outcome)

    def test_missing_required_comparison_is_refused_not_zero(self):
        result = self.service.canonicalise(self.signal(comparison=None))
        self.assertEqual('REFUSED', result.outcome)
        self.assertIsNone(result.fact)
        self.assertEqual([], list(self.session.scalars(select(tables.fact.c.object_id))))

    def test_optional_margin_unknown_does_not_invent_zero(self):
        fact = self.service.canonicalise(self.signal(variance=None)).fact
        self.assertIsNone(fact.derived)
        self.assertNotIn('contribution_0_margin', render_fact(fact))

    def test_days_count_and_per_fte_ratio_units(self):
        cases = [dict(typ='WC_DSO', test='WC-01', unit='DAYS', observed='42.123'),
                 dict(typ='COMMISSION_PLAN_STRUCTURE', test='PEO-01', unit='COUNT', observed='3', comparison='1000'),
                 dict(typ='REVENUE_PER_FTE', test='PEO-02', unit='GBP_PER_FTE', observed='10000.00000000000001')]
        for i, options in enumerate(cases):
            fields = dict(entity=None, entity_id=None, comparison=None, variance=None)
            fields.update(options)
            fact = self.service.canonicalise(self.signal(str(i), **fields)).fact
            self.assertEqual(Decimal(options['observed']), fact.observed.value)
            self.assertEqual(fact, CanonicalFact.from_json(fact.to_json()))

    def test_fractional_counts_float_and_nonfinite_values_rejected(self):
        for value in ('2.5', '-1', 'NaN', 'Infinity', 2.5, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Measurement(metric='count', value=value, unit='COUNT', basis='captured')

    def test_unknown_and_ambiguous_signals_explicitly_unmapped(self):
        for i, typ in enumerate(['UNKNOWN_SIGNAL', 'REALISED_PRICE_MOVEMENT', 'FORWARD_SCENARIO_RANGE']):
            result = self.service.canonicalise(self.signal(str(i), typ=typ))
            self.assertEqual('UNMAPPED', result.outcome)
            self.assertIsNone(result.fact)

    def test_wrong_producer_or_unit_cannot_use_generic_fallback(self):
        self.assertEqual('UNMAPPED', self.service.canonicalise(self.signal(test='GM-01')).outcome)
        self.assertEqual('REFUSED', self.service.canonicalise(self.signal('s2', unit='USD')).outcome)

    def test_partial_fact_and_finding_held_without_confidence_inflation(self):
        fact = self.service.canonicalise(self.revenue(eligibility='PARTIAL-A')).fact
        self.assertEqual(ConfidenceProfile(), fact.confidence)
        result = self.service.assess(fact.object_id)
        self.assertEqual('HELD_LIMITED', result.outcome)
        self.assertEqual(MaterialityProfile(), result.materiality)
        self.assertEqual(ConfidenceProfile(), result.confidence)

    def test_unavailable_and_no_lineage_are_refused(self):
        self.assertEqual('REFUSED', self.service.canonicalise(self.signal(eligibility='UNAVAILABLE')).outcome)
        self.assertEqual('REFUSED', self.service.canonicalise(self.signal('s2', lineage=False)).outcome)

    def test_replay_is_idempotent_and_does_not_duplicate_audits(self):
        sid = self.signal()
        one = self.service.canonicalise(sid)
        before = self.service.foundation.audit_events(object_id=one.fact.object_id)
        two = self.service.canonicalise(sid)
        self.assertEqual('REPLAYED', two.outcome)
        self.assertEqual(one.fact, two.fact)
        self.assertEqual(before, self.service.foundation.audit_events(object_id=one.fact.object_id))

    def test_mutated_source_cannot_overwrite_historical_fact(self):
        sid = self.signal()
        old = self.service.canonicalise(sid).fact
        self.legacy.execute('UPDATE signal SET observed_value=? WHERE signal_id=?', ('999', sid))
        self.assertEqual('REFUSED', self.service.canonicalise(sid).outcome)
        self.assertEqual(old, self.service.get_fact(old.object_id))

    def test_same_text_different_entity_and_run_do_not_collide(self):
        a = self.service.canonicalise(self.signal()).fact
        b = self.service.canonicalise(self.signal('s2', entity_id='customer-b')).fact
        c = self.service.canonicalise(self.signal('s3', run='r3')).fact
        self.assertEqual(3, len({a.object_id, b.object_id, c.object_id}))

    def test_period_entity_and_ancestry_survive_persistence(self):
        fact = self.service.canonicalise(self.signal(period_from='2026-01-01', period_to='2026-01-31')).fact
        self.session.commit()
        saved = self.service.get_fact(fact.object_id)
        self.assertEqual(fact.scope, saved.scope)
        self.assertEqual(fact.lineage, saved.lineage)
        self.assertEqual('customer-a', saved.scope.entity_id)
        department = self.service.canonicalise(self.signal('department', test='PEO-03',
            typ='DEPARTMENT_WORKFORCE_ECONOMICS', entity='DEPARTMENT', entity_id='Sales & Marketing')).fact
        self.assertEqual('Sales & Marketing', self.service.get_fact(department.object_id).scope.entity_id)

    def test_shared_ancestry_retains_existing_source_identity(self):
        a = self.service.canonicalise(self.signal()).fact
        b = self.service.canonicalise(self.signal('s2')).fact
        for fact in (a, b):
            ref = next(r for r in fact.lineage if r.kind == 'DIAGNOSTIC_LINEAGE')
            row = self.legacy.execute('SELECT source_object_type,source_object_id FROM diagnostic_lineage WHERE diagnostic_lineage_id=?', (ref.source_id,)).fetchone()
            self.assertEqual(('SOURCE_FILE', 'shared-source-file'), tuple(row))
        self.assertEqual(ConfidenceProfile(), b.confidence)

    def test_management_assertion_can_hold_but_never_become_fact(self):
        context = self.service.foundation.create_object(ReasoningObject(client_id='c1', run_id='r1',
            object_type='SIGNAL', source_authority='MANAGEMENT_ASSERTION'))
        with self.assertRaises(ScopeError):
            self.service.canonicalise(context.object_id)
        fact = self.service.canonicalise(self.revenue()).fact
        result = self.service.assess(fact.object_id, contradictory=(context.object_id,))
        self.assertEqual('HELD_LIMITED', result.outcome)
        self.assertEqual('SYSTEM_DERIVED', fact.source_authority)
        self.assertEqual('MANAGEMENT_ASSERTION', self.service.foundation.get_object(context.object_id).source_authority)

    def test_fact_creation_and_significance_are_separate(self):
        fact = self.service.canonicalise(self.revenue()).fact
        self.assertEqual([], list(self.session.scalars(select(tables.finding.c.object_id))))
        result = self.service.assess(fact.object_id)
        self.assertEqual('FINDING_CREATED', result.outcome)
        finding = self.service.get_finding(result.finding_id)
        self.assertEqual('DETECTED', finding.status)
        self.assertEqual(fact.object_id, finding.observations[0].fact_id)
        self.assertIn('no causality', result.rationale)

    def test_valid_but_not_significant_and_insufficient_are_distinct(self):
        sid = self.revenue()
        self.legacy.execute("UPDATE signal SET observed_value='101',variance_value='1' WHERE signal_id=?", (sid,))
        fact = self.service.canonicalise(sid).fact
        self.assertEqual('NOT_SIGNIFICANT', self.service.assess(fact.object_id).outcome)
        other = self.service.canonicalise(self.signal('s2')).fact
        self.assertEqual('INSUFFICIENT_EVIDENCE', self.service.assess(other.object_id).outcome)

    def test_longitudinal_identity_and_comparability(self):
        a = self.service.canonicalise(self.revenue(period_from='2026-01-01', period_to='2026-01-31')).fact
        b = self.service.canonicalise(self.revenue('s2', run='r3', period_from='2026-03-01', period_to='2026-03-31')).fact
        first = self.service.assess(a.object_id)
        second = self.service.assess(b.object_id)
        self.assertEqual(first.finding_id, second.finding_id)
        finding = self.service.get_finding(first.finding_id)
        self.assertEqual(('r1', 'r3', 2), (finding.first_seen_run, finding.latest_seen_run, finding.revision))
        self.assertEqual('PREVIOUS_COMPARABLE_PERIOD', finding.temporal_state)
        self.assertEqual(2, len(self.service.history(finding.object_id)))

    def test_missing_dates_never_establish_persistence(self):
        a = self.service.canonicalise(self.revenue()).fact
        b = self.service.canonicalise(self.revenue('s2', run='r3')).fact
        result = self.service.assess(a.object_id)
        self.service.assess(b.object_id)
        finding = self.service.get_finding(result.finding_id)
        self.assertEqual('INSUFFICIENT_TEMPORAL_EVIDENCE', finding.temporal_state)
        self.assertEqual('NOT_ASSESSED', finding.assessment.materiality.persistence)

    def test_invalidation_retains_audit_and_previous_revision(self):
        old = self.service.canonicalise(self.signal()).fact
        new = self.service.invalidate(old.object_id, 'Source challenged')
        self.assertEqual('INVALIDATED', new.state)
        self.assertEqual(old, CanonicalFact.from_json(self.service.history(old.object_id)[0]))
        self.assertEqual('INSUFFICIENT_EVIDENCE', self.service.assess(old.object_id).outcome)
        self.assertTrue(any(e.event_type == 'STATUS_CHANGED' for e in self.service.foundation.audit_events(object_id=old.object_id)))

    def test_mapping_revision_supersedes_without_rewriting_history(self):
        sid = self.signal()
        old = self.service.canonicalise(sid).fact
        key = ('CUS-02', 'CUSTOMER_PROFITABILITY')
        revised = replace(REGISTRY[key], version='SF-TEST-CORRECTED')
        with patch.dict(REGISTRY, {key: revised}), patch.dict(MAPPING_VERSIONS, {(*key, revised.version): revised}):
            new = self.service.canonicalise(sid, supersedes=old.object_id, correction_rationale='Qualified mapping correction').fact
            self.assertNotEqual(old.object_id, new.object_id)
            self.assertEqual(old.object_id, new.supersedes)
            self.assertEqual('SUPERSEDED', self.service.get_fact(old.object_id).state)
            self.assertEqual(old, CanonicalFact.from_json(self.service.history(old.object_id)[0]))

    def test_caller_rollback_removes_semantics_and_audit(self):
        fact = self.service.canonicalise(self.signal()).fact
        self.session.rollback()
        with self.assertRaises(ScopeError):
            self.service.get_fact(fact.object_id)
        self.assertEqual([], list(self.session.scalars(select(tables.history.c.revision_id))))

    def test_scope_and_database_endpoint_integrity(self):
        fact = self.service.canonicalise(self.signal()).fact
        other = CanonicalService(self.session, 'c2', self.actor, LegacySignalSource(self.legacy, 'c2'))
        with self.assertRaises(ScopeError):
            other.get_fact(fact.object_id)
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.execute(insert(tables.fact).values(object_id='missing', client_id='c1', revision=1, document='{}'))

    def test_corrupt_semantics_rejected_on_read(self):
        fact = self.service.canonicalise(self.signal()).fact
        doc = fact.model_dump(mode='json')
        doc['derived']['unit'] = 'CURRENCY'
        doc['derived']['currency'] = 'GBP'
        self.session.execute(tables.fact.update().where(tables.fact.c.object_id == fact.object_id).values(document=json.dumps(doc)))
        with self.assertRaises(ValueError):
            self.service.get_fact(fact.object_id)

    def test_inventory_covers_every_frozen_emission_site(self):
        current = inventory()
        captured = json.loads((Path(__file__).resolve().parents[1]/'qualification/signal_mapping_v244.json').read_text(encoding='utf-8'))
        self.assertEqual(captured['signals'], json.loads(json.dumps(current)))
        self.assertEqual(86, len({r['signal_type'] for r in current}))

    def test_all_registered_slot_contracts_persist_without_unit_relabelling(self):
        for i, mapping in enumerate(REGISTRY.values()):
            values = ['2' if slot and slot.unit == Unit.COUNT else '1.2500' if slot else None for slot in mapping.slots]
            sid = self.signal('mapped-'+str(i), typ=mapping.signal_type, test=mapping.diagnostic,
                observed=values[0], comparison=values[1], variance=values[2], unit=mapping.source_unit,
                entity=mapping.entity_type, entity_id='scope' if mapping.entity_type else None)
            with self.subTest(mapping=(mapping.diagnostic, mapping.signal_type)):
                result = self.service.canonicalise(sid)
                self.assertEqual('CREATED', result.outcome)
                self.assertEqual(result.fact, self.service.get_fact(result.fact.object_id))
                for spec, value in zip(mapping.slots, (result.fact.observed, result.fact.comparison, result.fact.derived)):
                    if spec:
                        self.assertEqual((spec.metric, spec.unit, spec.basis), (value.metric, value.unit, value.basis))

    def test_existing_finding_retains_contradiction_and_assessment_history(self):
        fact = self.service.canonicalise(self.revenue()).fact
        original = self.service.assess(fact.object_id)
        context = self.service.foundation.create_object(ReasoningObject(client_id='c1', run_id='r1',
            object_type='SIGNAL', source_authority='MANAGEMENT_ASSERTION'))
        held = self.service.assess(fact.object_id, contradictory=(context.object_id,))
        self.assertEqual(original.finding_id, held.finding_id)
        self.assertEqual('HELD_LIMITED', held.outcome)
        finding = self.service.get_finding(held.finding_id)
        self.assertEqual((context.object_id,), finding.contradictory_evidence)
        self.assertEqual(2, len(self.service.history(finding.object_id)))
        self.assertEqual(ConfidenceProfile(), finding.assessment.confidence)

    def test_different_finding_entity_and_type_do_not_collide(self):
        ids = []
        for i, entity in enumerate(('customer-a', 'customer-b')):
            fact = self.service.canonicalise(self.signal(str(i), test='CUS-01', typ='TOP_CUSTOMER_CONCENTRATION',
                observed='30', comparison=None, variance=None, unit='PERCENT', entity_id=entity)).fact
            ids.append(self.service.assess(fact.object_id).finding_id)
        fact = self.service.canonicalise(self.revenue('revenue')).fact
        ids.append(self.service.assess(fact.object_id).finding_id)
        self.assertEqual(3, len(set(ids)))

    def test_cross_client_source_run_and_counter_evidence_rejected(self):
        with self.assertRaises(ScopeError):
            self.service.canonicalise(self.signal(run='r2'))
        from profit_doctor.reasoning.domain.service import FoundationService
        foreign = FoundationService(self.session, 'c2', self.actor).create_object(ReasoningObject(
            client_id='c2', run_id='r2', object_type='SIGNAL', source_authority='SYSTEM_DERIVED'))
        fact = self.service.canonicalise(self.revenue('valid')).fact
        with self.assertRaises(ScopeError):
            self.service.assess(fact.object_id, contradictory=(foreign.object_id,))

    def test_repeated_same_period_never_means_persistent(self):
        ids = [self.service.canonicalise(self.revenue(sid, run=run,
            period_from='2026-01-01', period_to='2026-01-31')).fact.object_id for sid, run in [('a', 'r1'), ('b', 'r3')]]
        first = self.service.assess(ids[0])
        self.service.assess(ids[1])
        self.assertEqual('REPEATED_OBSERVATION', self.service.get_finding(first.finding_id).temporal_state)

    def test_partial_limitations_are_visible_in_rendering(self):
        fact = self.service.canonicalise(self.signal(eligibility='PARTIAL-A', limitation='Incomplete comparison coverage')).fact
        self.assertIn('PARTIAL-A', render_fact(fact))
        self.assertIn('Incomplete comparison coverage', render_fact(fact))

    def test_independent_reader_only_sees_committed_semantics(self):
        fact = self.service.canonicalise(self.signal()).fact
        with self.factory() as reader:
            service = CanonicalService(reader, 'c1', self.actor, self.source)
            with self.assertRaises(ScopeError):
                service.get_fact(fact.object_id)
        self.session.commit()
        with self.factory() as reader:
            self.assertEqual(fact, CanonicalService(reader, 'c1', self.actor, self.source).get_fact(fact.object_id))

    def test_database_composite_scope_foreign_key(self):
        fact = self.service.canonicalise(self.signal()).fact
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.execute(insert(tables.history).values(revision_id='cross-tenant', object_id=fact.object_id,
                client_id='c2', revision=99, document='{}'))

    def test_ambiguous_zero_denominator_sentinels_are_not_facts(self):
        from profit_doctor.reasoning.canonical.registry import ZERO_DENOMINATOR_GUARDS
        for i, (key, slot) in enumerate(ZERO_DENOMINATOR_GUARDS.items()):
            mapping = REGISTRY[key]
            fields = dict(observed='2', comparison='2', variance='2')
            for spec, name in zip(mapping.slots, ('observed', 'comparison', 'variance')):
                if spec is None:
                    fields[name] = None
            fields[{'observed':'observed', 'comparison':'comparison', 'derived':'variance'}[slot]] = '0'
            sid = self.signal('sentinel-'+str(i), typ=mapping.signal_type, test=mapping.diagnostic,
                entity=mapping.entity_type, entity_id='scope' if mapping.entity_type else None,
                unit=mapping.source_unit, **fields)
            with self.subTest(signal=key):
                result = self.service.canonicalise(sid)
                self.assertEqual('REFUSED', result.outcome)
                self.assertIsNone(result.fact)
                self.assertIn('denominator', result.reason)


if __name__ == '__main__':
    unittest.main()
