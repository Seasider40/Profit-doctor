"""Reusable production contract, synthetic adversaries and unchanged blind evidence."""
import csv
import hashlib
from datetime import date
from decimal import Decimal
from pathlib import Path
import unittest
from sqlalchemy import select, func
from profit_doctor.persistence import receivables_schema as ar, impact_schema as impact_tables, reasoning_schema as rd
from profit_doctor.reasoning.receivables.contracts import Snapshot, Invoice, population
from profit_doctor.reasoning.receivables.service import ReceivablesService
from profit_doctor.reasoning.impact.service import ImpactService
from profit_doctor.reasoning.impact.contracts import Source
from profit_doctor.reasoning.domain.service import FoundationService, RevisionConflict, ScopeError
from profit_doctor.reasoning.measurement.contracts import MeasurementSlot
from profit_doctor.intake.receivables import ReceivablesWorkbook
from profit_doctor.intake.declared_accounting import capture_pack, inspect_pack
from profit_doctor.reasoning.bridge.service import BridgeService
from profit_doctor.reasoning.bridge.engine import pack_binding_groups
from tests import test_measurement_context_v248 as fixtures

WORKBOOK=Path(__file__).parent/'fixtures/impact_v249/Golden_Manufacturing_v2.49_Impact_Blind.xlsx'


class ReceivablesV249(unittest.TestCase):
    target_url=fixtures.MeasurementContextV248.target_url
    prepare_target=fixtures.MeasurementContextV248.prepare_target

    def setUp(self):
        fixtures.MeasurementContextV248.setUp(self)
        self.provider=ReceivablesService(self.contexts)
        self.impacts=ImpactService(self.contexts.foundation,'r1',receivables=self.provider)

    def data(self, **patch):
        invoice=dict(invoice_id='invoice-1',customer_id='customer-1',invoice_date='2026-10-01',
            explicit_due='2026-10-31',outstanding='123.00000000000000000001',as_of='2026-12-31',
            source_reference='source-row-1',status=dict(status='NONE_RECORDED',reviewed_at='2026-12-31',
                authority='SOURCE_RECORD',reference='review-1'))
        invoice.update(patch)
        return dict(client_id='c1',run_id='r1',ledger_id='ledger-1',entity='Fixture company',as_of='2026-12-31',
            scope='LEGAL_ENTITY',coverage='COMPLETE',coverage_basis='Entire controlled ledger',source_version='1',
            origin='BLIND_QUALIFICATION',invoices=[invoice],control_amount=invoice['outstanding'],
            control_reference='control-1',dataset_version_id='pending')

    def ingest(self, data=None, previous=None):
        snapshot=Snapshot.model_validate(data or self.data())
        p=self.directory/'snapshot.csv'
        with p.open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=['snapshot']);writer.writeheader();writer.writerow({'snapshot':snapshot.to_json()})
        return self.provider.ingest_csv(p,self.directory/'store',expected_previous=previous)

    def assess(self,snapshot): return self.impacts.assess(Source(kind='RECEIVABLES',source_id=snapshot.series_id),'CASH_TRAPPED')

    def test_no_original_amount_inferred(self):
        s=self.ingest();self.assertIsNone(s.invoices[0].original_amount)
        q=self.assess(s);self.assertEqual('QUALIFIED_IMPACT',q.outcome)
        self.assertEqual(s.total,q.impact.amount.value);self.assertEqual('PRODUCTION',q.domain)

    def test_explicit_due_without_invoice_date(self):
        s=self.ingest(self.data(invoice_date=None));self.assertIsNotNone(self.assess(s).impact)

    def test_terms_derived_due(self):
        data=self.data(explicit_due=None,terms=dict(reference='terms-1',days=30,effective_from='2026-01-01',effective_to='2026-12-31'))
        s=self.ingest(data);self.assertEqual(date(2026,10,31),s.invoices[0].due);self.assertIsNotNone(self.assess(s).impact)

    def test_inconsistent_due_terms_rejected(self):
        with self.assertRaises(ValueError): self.ingest(self.data(terms=dict(reference='t',days=60,effective_from='2026-01-01',effective_to='2026-12-31')))

    def test_due_on_reporting_date_within_terms(self):
        q=self.assess(self.ingest(self.data(explicit_due='2026-12-31')))
        self.assertEqual('NOT_APPLICABLE',q.outcome);self.assertIsNone(q.impact)

    def test_status_exclusions(self):
        for status in ('AGREED_PAYMENT_PLAN','ACTIVE_DISPUTE','CREDIT_NOTE_PENDING','UNKNOWN'):
            with self.subTest(status=status):
                d=self.data(status=dict(status=status,reviewed_at='2026-12-31',authority='SOURCE_RECORD',reference='review'))
                d['ledger_id']=status
                self.assertIsNone(self.assess(self.ingest(d)).impact)

    def test_unknown_free_text_status_rejected(self):
        with self.assertRaises(ValueError): self.ingest(self.data(status=dict(status='should pay soon')))

    def test_missing_due_remains_unknown(self):
        self.assertIsNone(self.assess(self.ingest(self.data(explicit_due=None))).impact)

    def test_management_status_never_verified(self):
        d=self.data(status=dict(status='NONE_RECORDED',reviewed_at='2026-12-31',authority='MANAGEMENT_ASSERTION',reference='manager'))
        self.assertIsNone(self.assess(self.ingest(d)).impact)

    def test_stale_status_excluded(self):
        d=self.data(status=dict(status='NONE_RECORDED',reviewed_at='2026-12-30',authority='SOURCE_RECORD',reference='review'))
        self.assertIsNone(self.assess(self.ingest(d)).impact)

    def test_partial_coverage_not_extrapolated(self):
        d=self.data();d.update(coverage='PARTIAL',control_amount='1000')
        s=self.ingest(d);q=self.assess(s)
        self.assertEqual('PARTIAL',q.impact.amount.coverage);self.assertEqual(s.total,q.impact.amount.value)
        self.assertNotEqual(0,s.reconciliation_difference)

    def test_complete_reconciliation_difference_held(self):
        d=self.data();d['control_amount']='1000'
        self.assertEqual('HELD',self.assess(self.ingest(d)).outcome)

    def test_complete_missing_control_held(self):
        d=self.data();d.update(control_amount=None,control_reference=None)
        self.assertEqual('HELD',self.assess(self.ingest(d)).outcome)

    def test_partial_population_exceeding_control_held(self):
        d=self.data();d.update(coverage='PARTIAL',control_amount='1')
        self.assertEqual('HELD',self.assess(self.ingest(d)).outcome)

    def test_blind_origin_cannot_enter_real_source_total(self):
        q=self.assess(self.ingest())
        result=self.impacts.aggregate([q.candidate_id],domain='PRODUCTION',dimension='CASH',category='CASH_TRAPPED')
        self.assertEqual('NOT_SAFELY_AGGREGATABLE',result.status);self.assertIsNone(result.total)

    def test_distinct_unproven_populations_cannot_sum(self):
        a=self.ingest();q=self.assess(a)
        d=self.data(invoice_id='invoice-2');d['ledger_id']='other-ledger'
        b=self.assess(self.ingest(d))
        result=self.impacts.aggregate([q.candidate_id,b.candidate_id],domain='PRODUCTION',dimension='CASH',category='CASH_TRAPPED',qualification_origin='BLIND_QUALIFICATION')
        self.assertEqual('NOT_SAFELY_AGGREGATABLE',result.status);self.assertIsNone(result.total)

    def test_scope_fk_protects_source_relationship(self):
        from sqlalchemy import update
        from sqlalchemy.exc import IntegrityError
        q=self.assess(self.ingest())
        with self.assertRaises(IntegrityError):
            with self.session.begin_nested():self.session.execute(update(ar.impact_source).values(client_id='c2'))

    def test_raw_workbook_source_is_not_synthetic_positive(self):
        from profit_doctor.reasoning.impact.contracts import Qualification
        q=self.assess(self.ingest())
        d=q.model_dump(mode='json');d['source']['kind']='SYNTHETIC'
        with self.assertRaises(ValueError):Qualification.model_validate(d)

    def test_currency_mismatch_rejected(self):
        with self.assertRaises(ValueError):self.ingest(self.data(currency='USD'))

    def test_asof_mismatch_rejected(self):
        with self.assertRaises(ValueError):self.ingest(self.data(as_of='2026-12-30'))

    def test_duplicate_invoice_rejected(self):
        d=self.data();d['invoices']*=2
        with self.assertRaises(ValueError):self.ingest(d)

    def test_snapshot_impact_replay(self):
        a=self.ingest();q=self.assess(a);b=self.ingest()
        self.assertEqual(a,b);self.assertEqual(q,self.assess(b))
        self.assertEqual(1,self.session.scalar(select(func.count()).select_from(ar.audit)))

    def test_revision_history_and_stale_assessment(self):
        a=self.ingest();q=self.assess(a)
        d=self.data(outstanding='100');d['source_version']='2'
        with self.assertRaises(RevisionConflict):self.ingest(d)
        b=self.ingest(d,a.snapshot_id)
        with self.assertRaises(RevisionConflict):self.impacts.get(q.candidate_id,current=True)
        updated=self.impacts.assess(q.source,'CASH_TRAPPED',expected_revision=1)
        self.assertEqual(2,updated.revision);self.assertEqual(q.impact.effect_id,updated.impact.effect_id)
        self.assertEqual(q,self.impacts.get(q.candidate_id,1));self.assertEqual(a,self.provider.get(a.snapshot_id))

    def test_cmc_stock_owner_and_lineage(self):
        s=self.ingest();oid=self.provider.owner_id(s,s.invoices[0])
        owner=MeasurementSlot(store='CANONICAL',resource='canonical_receivable_invoice',source_id=oid,slot='amount')
        binding,ctx=self.contexts.resolve_binding(self.contexts.lookup(owner).binding_id)
        self.assertEqual('STOCK',ctx.period.nature);self.assertEqual('invoice_outstanding_balance',ctx.metric)
        self.assertEqual(s.as_of,ctx.period.start);self.assertEqual(s.dataset_version_id,ctx.source_version.source_id)
        self.assertTrue(self.contexts.audit_events(ctx.context_id))

    def test_rollback_canonical_state(self):
        self.assess(self.ingest());self.session.rollback()
        for t in (ar.snapshot,ar.invoice,ar.audit,impact_tables.qualification,impact_tables.impact):
            self.assertEqual(0,self.session.scalar(select(func.count()).select_from(t)))

    def test_provider_required_and_foreign_scope(self):
        s=self.ingest()
        with self.assertRaises(ScopeError):ImpactService(self.contexts.foundation,'r1').assess(Source(kind='RECEIVABLES',source_id=s.series_id),'CASH_TRAPPED')
        d=self.data();d['client_id']='c2'
        with self.assertRaises(ScopeError):self.ingest(d)

    def test_effect_parent_and_no_double_count(self):
        q=self.assess(self.ingest())
        relation=self.session.execute(select(rd.effect_overlap)).mappings().one()
        self.assertEqual('PARENT_CHILD',relation['overlap_type']);self.assertEqual(q.impact.effect_id,relation['target_effect_id'])
        result=self.impacts.aggregate([q.candidate_id,q.candidate_id],domain='PRODUCTION',dimension='CASH',category='CASH_TRAPPED',qualification_origin='BLIND_QUALIFICATION')
        self.assertEqual(q.impact.amount.value,result.total)

    def test_no_other_category_or_opportunity_promotion(self):
        s=self.ingest();q=self.assess(s)
        for category in ('OBSERVED_LOSS','RUN_RATE_LEAKAGE','CAPITAL_AT_RISK','FUTURE_EXPOSURE','VALUE_CREATION_POTENTIAL','REALISED_BENEFIT','AVOIDABLE_COST'):
            self.assertIsNone(self.impacts.assess(q.source,category).impact)
        self.assertEqual('NOT_ASSESSED',q.impact.confidence.opportunity_confidence)
        self.assertEqual('NOT_ASSESSED',q.impact.materiality.controllability)

    def test_blind_pack_end_to_end_and_negative_bridges(self):
        self.assertEqual('eb3a5995a24d4fe06b6c1f27a070438c7e138b92b1da69ec62ef3cd4c0fc982b',hashlib.sha256(WORKBOOK.read_bytes()).hexdigest())
        extension=ReceivablesWorkbook()
        pack,captured=capture_pack(self.contexts,WORKBOOK,self.directory/'store',providers=(extension,))
        s=extension.capture(self.provider,pack,WORKBOOK,self.directory/'store',origin='BLIND_QUALIFICATION',ledger_id='trade-ar')
        q=self.assess(s)
        expected=sum(i.outstanding for i in s.invoices if i.due<s.as_of and i.status.status=='NONE_RECORDED')
        self.assertEqual(expected,q.impact.amount.value);self.assertEqual(s.control_amount,s.total)
        self.assertTrue(all(i.original_amount is None for i in s.invoices))
        self.assertEqual('OVERDUE_RECEIVABLES_1',q.impact.contract)
        bridges=BridgeService(self.contexts);service=ImpactService(self.contexts.foundation,'r1',bridges=bridges,receivables=self.provider)
        for family,category in (('REVENUE_BRIDGE','VALUE_CREATION_POTENTIAL'),('MARGIN_OR_PROFIT_BRIDGE','OBSERVED_LOSS'),('WORKING_CAPITAL_BRIDGE','CASH_TRAPPED')):
            a,b,d=pack_binding_groups(self.contexts,captured,family,pack['years'])
            bridge=bridges.create(family,2025,2026,a,b,d).bridge
            self.assertIsNotNone(bridge)
            self.assertIsNone(service.assess(Source(kind='BRIDGE',source_id=bridge.snapshot_id),category).impact)
        self.assertEqual(1,self.session.scalar(select(func.count()).select_from(impact_tables.impact)))
        self.assertEqual({'Inventory Detail','Customer Contracts','Payment History'},set(pack['extensions'][extension.name]['explicitly_unconsumed']))

    def test_unregistered_extended_pack_refused(self):
        with self.assertRaisesRegex(ValueError,'sheet catalogue'):inspect_pack(WORKBOOK)

    def test_conflicting_extensions_refused(self):
        with self.assertRaisesRegex(ValueError,'Conflicting'):inspect_pack(WORKBOOK,providers=(ReceivablesWorkbook(),ReceivablesWorkbook()))

    def test_negative_inventory_and_contract_evidence_not_promoted(self):
        from profit_doctor.intake.declared_accounting import read_cells, value, data_rows
        from profit_doctor.intake.receivables import HEADERS
        sheets=read_cells(WORKBOOK)
        stock=sheets['Inventory Detail'];contracts=sheets['Customer Contracts']
        for r in data_rows(stock,HEADERS['Inventory Detail']):
            self.assertTrue(all(not value(stock,col+str(r)) for col in 'QRSTU'))
        for r in data_rows(contracts,HEADERS['Customer Contracts']):
            self.assertEqual('',value(contracts,'H'+str(r)));self.assertEqual('',value(contracts,'I'+str(r)))
        for kind in ('INVENTORY','CUSTOMER_CONCENTRATION'):
            with self.assertRaises(ValueError):Source(kind=kind,source_id='unsupported')

    def test_populated_downgrade_reupgrade_preserves_legacy(self):
        from alembic import command
        from tests.test_postgresql_live_qualification_v218 import alembic_config
        from profit_doctor.persistence import Client
        from profit_doctor.persistence import measurement_schema as cmc
        q=self.assess(self.ingest());self.session.commit()
        url=('sqlite+pysqlite:///'+self.engine.url.database if self.engine.dialect.name=='sqlite'
             else self.engine.url.render_as_string(hide_password=False))
        cfg=alembic_config(url.replace('%','%%'))
        self.session.close()
        command.downgrade(cfg,'0011_economic_impact');command.upgrade(cfg,'head')
        self.assertIsNotNone(self.session.get(Client,'c1'))
        for t in (ar.snapshot,ar.invoice,ar.audit,ar.impact_source,impact_tables.qualification,impact_tables.impact,cmc.measurement_context):
            self.assertEqual(0,self.session.scalar(select(func.count()).select_from(t)))
        # Foundation history intentionally survives typed-provider downgrade.
        self.assertIsNotNone(self.contexts.foundation.get_object(q.impact.impact_id))
