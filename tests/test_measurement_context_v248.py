"""Real owning-store accounting capture; synthetic files are labelled fixtures."""
import csv
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from sqlalchemy import insert, select, text
from sqlalchemy.exc import IntegrityError

from profit_doctor.ingestion.accounting import ingest_accounting_file
from profit_doctor.calc.primitive_engine import run_primitive_engine
from profit_doctor.diagnostic.engine import working_capital_diagnostics
from profit_doctor.persistence import measurement_schema as tables
from profit_doctor.reasoning.measurement.contracts import MeasurementContext, MeasurementSlot
from profit_doctor.reasoning.measurement.service import MeasurementContextService
from profit_doctor.reasoning.bridge.context_qualification import qualify_contexts
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from tests import test_evidence_graph_v245 as fixtures


class MeasurementContextV248(unittest.TestCase):
    target_url = fixtures.EvidenceGraphV245.target_url
    prepare_target = fixtures.EvidenceGraphV245.prepare_target
    signal = fixtures.EvidenceGraphV245.signal
    fact = fixtures.EvidenceGraphV245.fact

    def setUp(self):
        fixtures.EvidenceGraphV245.setUp(self)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.contexts = MeasurementContextService(self.session, 'c1', 'r1', self.actor, self.legacy)

    def load_rows(self, rows, contract='D01_PNL', *, capture=True, filename='source.csv'):
        path = self.directory / filename
        fields = list(dict.fromkeys(k for row in rows for k in row))
        with path.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        result = ingest_accounting_file(self.legacy, 'c1', 'r1', path, contract, self.directory/'store',
            context_sink=self.contexts.capture_dataset if capture else None)
        return [r[0] for r in self.legacy.execute('SELECT statement_line_id FROM financial_statement_line WHERE dataset_version_id=? ORDER BY source_row_reference', (result['dataset_version_id'],)).fetchall()]

    def row(self, month=1, *, stock=False, **updates):
        value = dict(period_end=f'2026-{month:02d}-'+('28' if month == 2 else '31'),
            line_code='AR' if stock else 'REVENUE', line_name='Trade Debtors' if stock else 'Revenue',
            amount='100.00000000000000000001', currency='GBP', economic_basis='Source-declared accrual reporting',
            segment_scope='Entire explicitly supplied statement scope', coverage='COMPLETE',
            coverage_basis='All rows of the declared statement scope; no claim beyond that scope',
            reporting_basis='POINT_IN_TIME' if stock else 'MONTHLY', reporting_convention='Calendar reporting',
            period_start='' if stock else f'2026-{month:02d}-01')
        value.update(updates)
        return value

    def binding(self, row_id):
        return self.contexts.lookup(MeasurementSlot(store='LEGACY_SQLITE', resource='financial_statement_line', source_id=row_id, slot='amount'))

    def test_upstream_explicit_context_preserved_without_amount_store(self):
        row_id = self.load_rows([self.row()])[0]
        ctx = self.contexts.get_context(self.binding(row_id).context_id, current=True)
        self.assertEqual('2026-01-01', ctx.period.start.isoformat())
        self.assertEqual(31, ctx.period.duration_days)
        self.assertEqual('financial_revenue', ctx.metric)
        self.assertEqual('FLOW', ctx.period.nature)
        self.assertNotIn('value', type(ctx).model_fields)
        self.assertEqual(ctx, MeasurementContext.from_json(ctx.to_json()))
        amount = self.legacy.execute('SELECT amount FROM financial_statement_line WHERE statement_line_id=?', (row_id,)).fetchone()[0]
        self.assertEqual(Decimal('100.00000000000000000001'), Decimal(amount))

    def test_level1_calendar_months_qualify_without_advanced_data(self):
        ids = self.load_rows([self.row(), self.row(2, amount='125.00')])
        result = qualify_contexts(self.contexts, 'REVENUE_BRIDGE', *(self.binding(i).binding_id for i in ids))
        self.assertEqual('QUALIFIED', result.outcome)
        self.assertEqual('SAME_IMMUTABLE_DATASET_SNAPSHOT', result.version_basis)
        self.assertEqual(0, self.legacy.execute('SELECT COUNT(*) FROM sales_transaction').fetchone()[0])
        self.assertEqual(result, qualify_contexts(self.contexts, 'REVENUE_BRIDGE', *(self.binding(i).binding_id for i in ids)))

    def test_unknown_historical_fields_not_backfilled_from_period_end(self):
        ids = self.load_rows([dict(period_end='2026-12-31', line_code='REVENUE', line_name='Revenue', amount='100')])
        ctx = self.contexts.get_context(self.binding(ids[0]).context_id)
        self.assertIsNone(ctx.period.start)
        self.assertEqual('UNKNOWN', ctx.period.basis)
        self.assertIsNone(ctx.currency)
        self.assertIsNone(ctx.economic_basis)
        self.assertEqual('UNKNOWN', ctx.coverage)
        self.assertEqual('UNKNOWN_UNBOUND', ctx.revision_state)

    def test_stock_asof_survives_primitive_signal_and_fact_binding(self):
        row_id = self.load_rows([self.row(stock=True)], 'D02_BALANCE_SHEET')[0]
        root = self.binding(row_id)
        run_primitive_engine(self.legacy, 'r1', 'c1')
        primitive_id = self.legacy.execute("SELECT primitive_result_id FROM primitive_result WHERE primitive_id='BS_ACCOUNTS_RECEIVABLE'").fetchone()[0]
        primitive = self.contexts.propagate(root.binding_id, MeasurementSlot(store='LEGACY_SQLITE', resource='primitive_result', source_id=primitive_id, slot='numeric_value'))
        working_capital_diagnostics(self.legacy, 'r1', 'c1')
        signal_id = self.legacy.execute("SELECT signal_id FROM signal WHERE signal_type='BS_ACCOUNTS_RECEIVABLE'").fetchone()[0]
        signal = self.contexts.propagate(primitive.binding_id, MeasurementSlot(store='LEGACY_SQLITE', resource='signal', source_id=signal_id, slot='observed'))
        fact = self.service.canonicalise(signal_id).fact
        bound = self.contexts.propagate(signal.binding_id, MeasurementSlot(store='CANONICAL', resource='canonical_fact', source_id=fact.object_id, slot='observed'))
        ctx = self.contexts.get_context(bound.context_id)
        self.assertEqual(root.context_id, ctx.context_id)
        self.assertEqual('STOCK', ctx.period.nature)
        self.assertEqual(ctx.period.start, ctx.period.end)
        self.assertIsNone(fact.scope.period_to)  # Frozen Fact was not rewritten.
        self.assertEqual(bound, self.contexts.resolve_binding(bound.binding_id)[0])
        self.legacy.execute('UPDATE primitive_result SET numeric_value=? WHERE primitive_result_id=?', ('999', primitive_id))
        with self.assertRaises(RevisionConflict):
            self.contexts.resolve_binding(bound.binding_id)

    def test_same_dates_different_basis_cannot_qualify(self):
        ids = self.load_rows([self.row(), self.row(2, reporting_basis='YTD', period_start='2026-01-01')])
        result = qualify_contexts(self.contexts, 'REVENUE_BRIDGE', *(self.binding(i).binding_id for i in ids))
        self.assertEqual('INCOMPARABLE', result.outcome)
        self.assertIn('REPORTING_BASIS_MISMATCH', result.gaps)

    def test_partial_coverage_remains_partial(self):
        ids = self.load_rows([self.row(), self.row(2, coverage='PARTIAL')])
        result = qualify_contexts(self.contexts, 'REVENUE_BRIDGE', *(self.binding(i).binding_id for i in ids))
        self.assertEqual('PARTIALLY_QUALIFIED', result.outcome)

    def test_different_complete_coverage_definitions_are_incomparable(self):
        ids = self.load_rows([self.row(), self.row(2, coverage_basis='Only one reporting division')])
        result = qualify_contexts(self.contexts, 'REVENUE_BRIDGE', *(self.binding(i).binding_id for i in ids))
        self.assertEqual('INCOMPARABLE', result.outcome)
        self.assertIn('COVERAGE_BASIS_MISMATCH', result.gaps)

    def test_cross_version_does_not_infer_compatibility(self):
        a = self.load_rows([self.row()])[0]
        b = self.load_rows([self.row(2)], filename='second.csv')[0]
        result = qualify_contexts(self.contexts, 'REVENUE_BRIDGE', self.binding(a).binding_id, self.binding(b).binding_id)
        self.assertEqual('INSUFFICIENT_EVIDENCE', result.outcome)
        self.assertIn('CROSS_VERSION_COMPATIBILITY_UNQUALIFIED', result.gaps)

    def test_no_context_override_in_biq(self):
        ids = self.load_rows([self.row(), self.row(2)])
        with self.assertRaises(TypeError):
            qualify_contexts(self.contexts, 'REVENUE_BRIDGE', *(self.binding(i).binding_id for i in ids), coverage='COMPLETE')

    def test_replay_no_duplicate_context_binding_audit(self):
        row_id = self.load_rows([self.row()])[0]
        first = self.contexts.capture_accounting(row_id)
        self.assertEqual(first, self.contexts.capture_accounting(row_id))
        self.assertEqual(1, self.session.scalar(select(text('count(*)')).select_from(tables.measurement_context)))
        self.assertEqual(1, self.session.scalar(select(text('count(*)')).select_from(tables.measurement_binding)))
        self.assertEqual(2, self.session.scalar(select(text('count(*)')).select_from(tables.measurement_audit)))
        self.assertEqual({'OBJECT_CREATED','EVIDENCE_LINKED'}, {e['event_type'] for e in self.contexts.audit_events(first.context_id)})

    def test_caller_rollback_removes_context_and_audits(self):
        self.session.commit()
        self.load_rows([self.row()])
        self.session.rollback()
        self.assertEqual(0, self.session.scalar(select(text('count(*)')).select_from(tables.measurement_context)))
        self.assertEqual(0, self.session.scalar(select(text('count(*)')).select_from(tables.measurement_audit)))

    def test_foreign_run_and_context_rejected(self):
        with self.assertRaises(ScopeError):
            MeasurementContextService(self.session, 'c1', 'r2', self.actor, self.legacy)
        row_id = self.load_rows([self.row()])[0]
        with self.assertRaises(ScopeError):
            MeasurementContextService(self.session, 'c2', 'r2', self.actor, self.legacy).get_context(self.binding(row_id).context_id)

    def test_database_rejects_foreign_context_binding(self):
        row_id = self.load_rows([self.row()])[0]
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.execute(insert(tables.measurement_binding).values(binding_id='bad', client_id='c2', run_id='r2',
                context_id=self.binding(row_id).context_id, owner_key='bad', owner_digest='a'*64, document='{}'))

    def test_missing_original_source_backfill_retains_unknown(self):
        row_id = self.load_rows([self.row()], capture=False)[0]
        version = self.legacy.execute('SELECT dataset_version_id FROM financial_statement_line WHERE statement_line_id=?', (row_id,)).fetchone()[0]
        self.legacy.execute("UPDATE source_file SET storage_location=? WHERE source_file_id=(SELECT source_file_id FROM dataset_version WHERE dataset_version_id=?)", (str(self.directory/'absent'), version))
        ctx = self.contexts.capture_accounting(row_id)
        self.assertEqual('RETAINED_ACCOUNTING_V1', ctx.capture_method)
        self.assertIsNone(ctx.period.start)
        self.assertEqual('UNKNOWN', ctx.coverage)

    def test_source_mutation_rejected_and_historical_context_readable(self):
        row_id = self.load_rows([self.row()])[0]
        ctx = self.contexts.get_context(self.binding(row_id).context_id)
        self.legacy.execute('UPDATE financial_statement_line SET amount=? WHERE statement_line_id=?', ('999', row_id))
        with self.assertRaises(RevisionConflict):
            self.contexts.get_context(ctx.context_id, current=True)
        self.assertEqual(ctx, self.contexts.get_context(ctx.context_id))

    def test_changed_version_preserves_context_history(self):
        a = self.load_rows([self.row()])[0]
        old = self.contexts.get_context(self.binding(a).context_id)
        b = self.load_rows([self.row(amount='101')], capture=False, filename='corrected.csv')[0]
        new = self.contexts.capture_accounting(b, supersedes=old.context_id)
        self.assertNotEqual(old.context_id, new.context_id)
        self.assertEqual(old.context_id, new.supersedes)
        self.assertEqual(old, self.contexts.get_context(old.context_id))

    def test_bad_slot_and_fake_restatement_rejected(self):
        with self.assertRaises(ValueError):
            MeasurementSlot(store='LEGACY_SQLITE', resource='financial_statement_line', source_id='x', slot='comparison')
        ids = self.load_rows([self.row(source_revision_id='missing')], capture=False)
        with self.assertRaises(ScopeError):
            self.contexts.capture_accounting(ids[0])

    def test_mixed_slots_get_separate_unknown_contexts_without_relabel(self):
        fact = self.fact('mixed')
        contexts = [self.contexts.backfill_fact_slot(fact.object_id, slot) for slot in ('observed', 'comparison', 'derived')]
        self.assertEqual(['CURRENCY','CURRENCY','PERCENTAGE'], [c.unit.value for c in contexts])
        self.assertEqual(3, len({c.context_id for c in contexts}))
        self.assertTrue(all(c.period.start is None and c.coverage == 'UNKNOWN' for c in contexts))
        self.assertEqual(fact, self.service.get_fact(fact.object_id))
        for context in contexts:
            self.assertEqual(context, self.contexts.get_context(context.context_id, current=True))

    def test_existing_revision_identity_retained_without_cross_version_promotion(self):
        from profit_doctor.management.restatement import register_revision
        first = register_revision(self.legacy, 'c1', 'r1', 'accounting:pnl', {'January':'100'}, 'initial', '2026-01')
        second = register_revision(self.legacy, 'c1', 'r1', 'accounting:pnl', {'January':'101'}, 'correction', '2026-01')
        row = self.legacy.execute('SELECT * FROM source_revision WHERE revision_id=?', (second['revision_id'],)).fetchone()
        rid = self.load_rows([self.row(source_revision_id=second['revision_id'], source_revision_content_hash=row['content_hash'])])[0]
        ctx = self.contexts.get_context(self.binding(rid).context_id)
        self.assertEqual(second['revision_id'], ctx.source_revision_id)
        self.assertEqual(first['revision_id'], ctx.prior_source_revision_id)
        self.assertEqual('RESTATEMENT', ctx.revision_state)

    def test_context_sink_failure_does_not_relabel_committed_ingestion(self):
        row_id = self.load_rows([self.row()], capture=False)[0]
        def fail(version):
            raise ValueError('Context failed')
        with self.assertRaisesRegex(ValueError, 'Context failed'):
            ingest_accounting_file(self.legacy, 'c1', 'r1', self.directory/'source.csv', 'D01_PNL', self.directory/'store', context_sink=fail)
        self.assertEqual('COMPLETED', self.legacy.execute('SELECT ingestion_status FROM dataset_version WHERE dataset_version_id=(SELECT dataset_version_id FROM financial_statement_line WHERE statement_line_id=?)', (row_id,)).fetchone()[0])

    def test_workbook_month_and_original_file_survive_without_numeric_change(self):
        from openpyxl import Workbook
        from profit_doctor.intake.measurement_context import capture_management_accounts
        from profit_doctor.intake.bridge import _ma_rows
        book = Workbook()
        book.active.title = 'Management Accounts'
        book.active.append(['Management accounts 2026'])
        book.active.append(['£000 unless stated','Jan','Feb'])
        book.active.append(['Revenue',100,120])
        path = self.directory/'accounts.xlsx'
        try:
            book.save(path)
        finally:
            book.close()
        before = _ma_rows(path)
        contexts = capture_management_accounts(path, self.directory/'store', self.contexts)
        self.assertEqual(2, len(contexts))
        self.assertEqual(['2026-01-01','2026-02-01'], [c.period.start.isoformat() for c in contexts])
        self.assertTrue(all(c.currency == 'GBP' and c.coverage == 'UNKNOWN' for c in contexts))
        self.assertTrue(all(c.source_locator.startswith('Management Accounts!R3C') for c in contexts))
        self.assertTrue(all(len([r for r in c.lineage if r.kind == 'SOURCE_FILE']) == 2 for c in contexts))
        actual = self.legacy.execute('SELECT amount FROM financial_statement_line ORDER BY source_row_reference').fetchall()
        self.assertEqual([Decimal(str(r['amount'])) for r in before], [Decimal(r[0]) for r in actual])
        for ctx in contexts:
            self.assertEqual(ctx, self.contexts.get_context(ctx.context_id, current=True))

    def test_workbook_fallback_year_and_scale_do_not_qualify_context(self):
        from openpyxl import Workbook
        from profit_doctor.intake.measurement_context import capture_management_accounts
        book = Workbook()
        book.active.title = 'Management Accounts'
        book.active.append(['Undated management accounts'])
        book.active.append(['Amount','Jan','Feb'])
        book.active.append(['Revenue',100,120])
        path = self.directory/'undated.xlsx'
        try:
            book.save(path)
        finally:
            book.close()
        contexts = capture_management_accounts(path, self.directory/'store', self.contexts)
        self.assertEqual(2, len(contexts))
        self.assertTrue(all(c.period.start is None and c.currency is None for c in contexts))
        self.assertTrue(all(c.period.basis == 'UNKNOWN' for c in contexts))
