"""Arithmetic/transport foundation only; never synthetic positive production claims."""
import csv
from decimal import Decimal
from pathlib import Path
import shutil
import unittest

from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import register_dataset_version
from profit_doctor.reasoning.bridge.qualification import Period
from profit_doctor.reasoning.domain.contracts import Actor, LineageReference
from profit_doctor.reasoning.domain.service import RevisionConflict, ScopeError
from profit_doctor.reasoning.production_evidence.contracts import (
    EvidenceDeclaration, EvidenceScope, SourceAmount,
)
from profit_doctor.reasoning.production_evidence.reconciliation import exact_sum, reconcile
from profit_doctor.reasoning.production_evidence.source import (
    DOMAIN, FIELDS, PROVIDER, RegisteredAccountingSource,
)


def scope(**changes):
    return EvidenceScope(client_id='c1', entity_id='e1', ledger_id='l1', population='all-net-sales',
        period=Period(start='2026-01-01', end='2026-01-31', basis='MONTHLY', nature='FLOW'),
        currency='GBP', definition='net-sales-accrual-1').model_copy(update=changes)


def record(name='r1', amount='100', **changes):
    return SourceAmount(record_id=name, account_code='4000', kind='SALES', amount=amount,
        scope=scope(**changes), lineage=(LineageReference(kind='SOURCE_FILE', store='LEGACY_SQLITE',
            resource='source_file', source_id='f1', client_id=changes.get('client_id', 'c1')),))


class ReconciliationFoundationV255(unittest.TestCase):
    def test_exact_match_is_arithmetic_not_completeness(self):
        result = reconcile(scope(), (record(),), (record('control'),))
        self.assertEqual(result.state, 'MATCH')
        self.assertEqual(result.difference, Decimal(0))
        self.assertIn('completeness', result.limitations[0])
        self.assertFalse(hasattr(result, 'population_verified'))

    def test_mismatch_preserves_exact_difference(self):
        result = reconcile(scope(), (record(amount='100.01'),), (record('control'),))
        self.assertEqual((result.state, result.difference), ('MISMATCH', Decimal('.01')))

    def test_missing_source_is_not_zero_or_match(self):
        result = reconcile(scope(), (), (record(amount='0'),))
        self.assertEqual(result.state, 'INSUFFICIENT_EVIDENCE')
        self.assertIsNone(result.amount_a)
        self.assertIsNone(result.difference)

    def test_same_amount_different_population_is_conflicted(self):
        self.assertEqual(reconcile(scope(), (record(population='selected-sales'),), (record(),)).state, 'CONFLICTED')

    def test_same_amount_different_entity_is_conflicted(self):
        self.assertEqual(reconcile(scope(), (record(entity_id='e2'),), (record(),)).state, 'CONFLICTED')

    def test_same_amount_different_currency_is_conflicted(self):
        self.assertEqual(reconcile(scope(), (record(currency='EUR'),), (record(),)).state, 'CONFLICTED')

    def test_different_period_is_conflicted(self):
        period = Period(start='2026-02-01', end='2026-02-28', basis='MONTHLY', nature='FLOW')
        self.assertEqual(reconcile(scope(), (record(period=period),), (record(),)).state, 'CONFLICTED')

    def test_different_definition_is_conflicted(self):
        self.assertEqual(reconcile(scope(), (record(definition='cash-sales'),), (record(),)).state, 'CONFLICTED')

    def test_cross_client_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'cross-client'):
            reconcile(scope(), (record(client_id='c2'),), (record(),))

    def test_duplicate_record_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            reconcile(scope(), (record(), record()), (record(),))

    def test_order_independent_identity_and_decimal_serialization(self):
        a = reconcile(scope(), (record('a', '.01'), record('b', '99.99')), (record(),))
        b = reconcile(scope(), (record('b', '99.99'), record('a', '.01')), (record(),))
        self.assertEqual(a.reconciliation_id, b.reconciliation_id)
        self.assertEqual(type(a).from_json(a.to_json()), a)

    def test_disparate_exponents_and_cancellation_are_exact(self):
        self.assertEqual(exact_sum((Decimal('1E80'), Decimal('.000001'), Decimal('-1E80'))), Decimal('.000001'))

    def test_control_subtraction_does_not_round_large_decimal(self):
        large = '1234567890123456789012345678901234567890.000001'
        result = reconcile(scope(), (record(amount=large),), (record('control', large),))
        self.assertEqual((result.state, result.difference), ('MATCH', Decimal(0)))

    def test_float_and_invalid_kind_are_rejected(self):
        for change in ({'amount': 0.1}, {'kind': 'GUESSED_DIRECT_COST'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                SourceAmount.model_validate({**record().model_dump(), **change})

    def test_identified_human_declaration_is_not_verification(self):
        actor = Actor(actor_type='HUMAN', actor_id='adviser1', source_authority='HUMAN_FD_JUDGEMENT')
        d = EvidenceDeclaration(declaration_id='d1', client_id='c1', actor=actor,
            effective_on='2026-01-31', dimension='coverage', claim='Extract is complete',
            lineage=record().lineage, revision=1)
        self.assertEqual(type(d).from_json(d.to_json()), d)
        self.assertFalse(hasattr(d, 'verified_value'))

    def test_machine_cannot_make_adviser_declaration(self):
        actor = Actor(actor_type='SYSTEM', actor_id='system1', source_authority='SYSTEM_DERIVED')
        with self.assertRaises(ValueError):
            EvidenceDeclaration(declaration_id='d1', client_id='c1', actor=actor,
                effective_on='2026-01-31', dimension='coverage', claim='Complete',
                lineage=record().lineage, revision=1)

    def test_declaration_revision_requires_predecessor(self):
        actor = Actor(actor_type='MANAGEMENT', actor_id='manager1', source_authority='MANAGEMENT_ASSERTION')
        with self.assertRaises(ValueError):
            EvidenceDeclaration(declaration_id='d1', client_id='c1', actor=actor,
                effective_on='2026-01-31', dimension='coverage', claim='Complete',
                lineage=record().lineage, revision=2)


class RegisteredSourceFoundationV255(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent / '.v255_source_tmp'
        if self.root.exists():
            self.remove_root()
        self.root.mkdir()
        self.addCleanup(self.remove_root)
        self.connection = connect(self.root/'legacy.db')
        self.addCleanup(self.connection.close)
        t = '2026-10-01T00:00:00+00:00'
        self.connection.execute('INSERT INTO client VALUES (?,?,?,?,?)', ('c1', 'Client', 'GBP', 'SME', t))
        self.connection.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',
            ('r1', 'c1', 'ADVISORY', t, None, 'RUNNING', None, None, '2.55'))
        self.connection.execute('INSERT INTO ingestion_job VALUES (?,?,?,?,?,?,?)',
            ('j1', 'r1', 'c1', t, t, 'COMPLETED', None))
        self.connection.commit()

    def remove_root(self):
        if self.root.exists():
            for path in self.root.rglob('*'):
                if path.is_file():
                    path.chmod(0o666)
            shutil.rmtree(self.root)

    def register(self, *, profile=PROVIDER, fields=FIELDS, rows=None):
        values = dict(zip(FIELDS, ('s1', '4000', 'SALES', '100.01', 'e1', 'l1',
            'all-net-sales', '2026-01-01', '2026-01-31', 'MONTHLY', 'GBP', 'net-sales-accrual-1')))
        file = self.root/'unimportant-name.csv'
        with file.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows if rows is not None else [{k: values[k] for k in fields}])
        version, _, _, _ = register_dataset_version(self.connection, 'c1', 'j1', file,
            DOMAIN, profile, self.root/'store', 'period_end')
        self.connection.execute("UPDATE dataset_version SET ingestion_status='COMPLETED' WHERE dataset_version_id=?", (version,))
        self.connection.commit()
        return version

    def test_registered_transport_preserves_decimal_and_lineage_not_verification(self):
        rows = RegisteredAccountingSource(self.connection, 'c1').read(self.register())
        self.assertEqual(rows[0].amount, Decimal('100.01'))
        self.assertEqual({r.kind.value for r in rows[0].lineage}, {'DATASET_VERSION', 'SOURCE_FILE'})
        self.assertFalse(hasattr(rows[0], 'verified'))

    def test_foreign_source_refused(self):
        version = self.register()
        with self.assertRaises(ScopeError):
            RegisteredAccountingSource(self.connection, 'c2').read(version)

    def test_unknown_profile_refused(self):
        with self.assertRaises(ScopeError):
            RegisteredAccountingSource(self.connection, 'c1').read(self.register(profile='unknown'))

    def test_incomplete_registration_refused(self):
        version = self.register()
        self.connection.execute("UPDATE dataset_version SET ingestion_status='RUNNING' WHERE dataset_version_id=?", (version,))
        with self.assertRaises(ScopeError):
            RegisteredAccountingSource(self.connection, 'c1').read(version)

    def test_changed_retained_file_refused(self):
        version = self.register()
        row = self.connection.execute('SELECT f.storage_location FROM dataset_version v JOIN source_file f ON f.source_file_id=v.source_file_id WHERE v.dataset_version_id=?', (version,)).fetchone()
        path = Path(row[0]); path.chmod(0o666)
        path.write_text('changed', encoding='utf-8')
        with self.assertRaises(RevisionConflict):
            RegisteredAccountingSource(self.connection, 'c1').read(version)

    def test_missing_column_refused(self):
        with self.assertRaises(ValueError):
            RegisteredAccountingSource(self.connection, 'c1').read(self.register(fields=FIELDS[:-1]))

    def test_empty_registered_transport_is_not_absence(self):
        rows = RegisteredAccountingSource(self.connection, 'c1').read(self.register(rows=[]))
        self.assertEqual(rows, ())
        self.assertEqual(reconcile(scope(), rows, rows).state, 'INSUFFICIENT_EVIDENCE')
