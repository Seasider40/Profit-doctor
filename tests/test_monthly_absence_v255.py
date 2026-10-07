"""Isolated issuer fixtures; never a production evidence authority connector."""
from datetime import date
from decimal import Decimal
import unittest
from pydantic import ValidationError

from tests import test_production_semantics_v255 as semantic
from profit_doctor.reasoning.production_evidence.monthly import MonthlyMeasurementService, MonthlyMeasurement
from profit_doctor.reasoning.production_evidence.absence import (ARScope, ARExport, ARManifest, ARControl, InvoiceReview, ReceivablesAbsenceService)
from profit_doctor.reasoning.receivables.contracts import Invoice, StatusEvidence
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict


class MonthlyOwnersV255(unittest.TestCase):
    def setUp(self):
        self.fx = semantic.SemanticVerificationV255('runTest')
        self.fx.setUp();self.addCleanup(self.fx.doCleanups)
        self.service = MonthlyMeasurementService(self.fx.con,'c1','r1',self.fx.authority)

    def qualify(self, *, family='REVENUE', manifest=None, mapping=None, **kw):
        return self.service.qualify(self.fx.records,self.fx.controls,
            self.fx.document(manifest or self.fx.manifest,'manifest'),
            mapping_version=self.fx.document(mapping or self.fx.mapping,'mapping','HUMAN_FD_JUDGEMENT'),
            family=family,**kw)

    def test_qualified_revenue_source_derived(self):
        value = self.qualify().value
        self.assertEqual(value.measurement.value,Decimal('100'))
        self.assertEqual(value.qualification_contract,'MONTHLY_REVENUE_1')

    def test_partial_population_refuses(self):
        self.assertEqual(self.qualify(manifest=self.fx.manifest.model_copy(update={'excluded_record_ids':('missing',)})).outcome,'REFUSED')

    def test_reconciliation_mismatch_refuses(self):
        self.fx.controls=self.fx.amounts('control1','99')
        self.assertEqual(self.qualify().outcome,'REFUSED')

    def test_unknown_definition_refuses(self):
        self.assertEqual(self.qualify(mapping=self.fx.mapping.model_copy(update={'definition':'UNKNOWN'})).outcome,'REFUSED')

    def test_declared_completeness_is_not_verified(self):
        self.fx.grants.clear()
        self.assertEqual(self.qualify().outcome,'REFUSED')

    def test_wrong_client_refuses(self):
        with self.assertRaises(ScopeError):
            MonthlyMeasurementService(self.fx.con,'c2','r1',self.fx.authority)

    def test_wrong_scope_refuses(self):
        with self.assertRaises(ScopeError):
            self.qualify(manifest=self.fx.manifest.model_copy(update={'scope':self.fx.scope.model_copy(update={'entity_id':'e2'})}))

    def test_wrong_period_refuses(self):
        self.fx.records=self.fx.amounts('s1','100',changes={'period_start':'2026-01-02'})
        with self.assertRaises(ScopeError):self.qualify()

    def test_wrong_currency_refuses(self):
        self.fx.controls=self.fx.amounts('control1','100',changes={'currency':'EUR'})
        with self.assertRaises(ScopeError):self.qualify()

    def test_missing_source_lineage_refuses(self):
        version=self.fx.records
        self.fx.con.execute('DELETE FROM dataset_version WHERE dataset_version_id=?',(version,))
        with self.assertRaises(ScopeError):self.qualify()

    def test_untrusted_source_refuses(self):
        self.service=MonthlyMeasurementService(self.fx.con,'c1','r1')
        self.assertEqual(self.qualify().outcome,'REFUSED')

    def test_rolling_rev01_cannot_qualify(self):
        self.fx.records=self.fx.amounts('s1','100',changes={'time_basis':'ROLLING'})
        with self.assertRaises(ValueError):self.qualify()

    def test_injected_amount_not_an_argument(self):
        with self.assertRaises(TypeError):self.qualify(amount='100000')

    def test_precision_beyond_ambient_decimal_context(self):
        amount='100000000000000000000000000000.00000000000000000001'
        self.fx.records=self.fx.amounts('s1',amount);self.fx.controls=self.fx.amounts('control1',amount)
        self.fx.manifest=self.fx.manifest.model_copy(update={'record_version_id':self.fx.records})
        self.assertEqual(self.qualify().value.measurement.value,Decimal(amount))

    def test_replay_idempotent(self):
        old=self.qualify().value
        self.assertEqual(self.qualify(previous=old).value,old)

    def test_restatement_same_owner_period_history(self):
        old=self.qualify().value
        self.fx.records=self.fx.amounts('s1','101');self.fx.controls=self.fx.amounts('control1','101')
        new=self.qualify(previous=old,manifest=self.fx.manifest.model_copy(update={
            'record_version_id':self.fx.records,'change_kind':'RESTATEMENT','predecessor_version_id':old.semantic.contract.source_version.source_id})).value
        self.assertEqual(new.series_id,old.series_id);self.assertEqual(new.supersedes,old.measurement_id)
        self.assertEqual(old.measurement.value,Decimal('100'));self.assertEqual(new.revision,2)

    def test_duplicate_period_refuses(self):
        self.qualify();self.fx.records=self.fx.amounts('s1','101');self.fx.controls=self.fx.amounts('control1','101')
        self.assertEqual(self.qualify(manifest=self.fx.manifest.model_copy(update={'record_version_id':self.fx.records})).outcome,'REFUSED')

    def test_monthly_context_distinct_from_rev01_fact_owner(self):
        value=self.qualify().value
        self.assertEqual(value.context.origin.resource,'canonical_monthly_measurement')
        self.assertEqual(value.context.period.basis,'MONTHLY')
        with self.assertRaises(ValueError):
            MonthlyMeasurement.model_validate({**value.model_dump(),'context':{**value.context.model_dump(),
                'origin':{'store':'CANONICAL','resource':'canonical_fact','source_id':'REV-01','slot':'observed'}}})

    def test_c0_qualified_exact_derivation(self):
        self.fx.c0();value=self.qualify(family='CONTRIBUTION_0').value
        self.assertEqual((value.revenue,value.direct_cost,value.measurement.value),(Decimal('100'),Decimal('40'),Decimal('60')))

    def test_c0_revenue_prerequisite_missing(self):
        self.fx.c0()
        self.assertEqual(self.qualify(family='CONTRIBUTION_0',mapping=self.fx.mapping.model_copy(update={'revenue_accounts':()})).outcome,'REFUSED')

    def test_c0_partial_cost_population_refuses(self):
        self.fx.c0()
        self.assertEqual(self.qualify(family='CONTRIBUTION_0',manifest=self.fx.manifest.model_copy(update={'excluded_record_ids':('cost-missing',)})).outcome,'REFUSED')

    def test_c0_unverified_mapping_refuses(self):
        self.fx.c0()
        version=self.fx.mapping.source_chart_version;profile,digest,_=self.fx.grants[version]
        self.fx.grants[version]=(profile,digest,'MANAGEMENT_ASSERTION')
        self.assertEqual(self.qualify(family='CONTRIBUTION_0').outcome,'REFUSED')

    def test_c0_conflicted_mapping_refuses(self):
        self.fx.c0()
        self.assertEqual(self.qualify(family='CONTRIBUTION_0',mapping=self.fx.mapping.model_copy(update={'source_policy_reference':'wrong'})).outcome,'REFUSED')

    def test_missing_cost_not_zero(self):
        self.fx.c0();self.fx.records=self.fx.amounts('s1','100',changes={'definition':'REVENUE_MINUS_DIRECT_COST'})
        self.fx.controls=self.fx.amounts('control1','100',changes={'definition':'REVENUE_MINUS_DIRECT_COST'})
        self.fx.manifest=self.fx.manifest.model_copy(update={'record_version_id':self.fx.records,'record_ids':('s1',),'record_count':1})
        self.assertEqual(self.qualify(family='CONTRIBUTION_0').outcome,'REFUSED')

    def test_no_account_name_mapping(self):
        self.fx.c0()
        with self.assertRaises(ValidationError):
            type(self.fx.mapping).model_validate({**self.fx.mapping.model_dump(),'account_names':['Materials']})

    def test_c0_precision(self):
        self.fx.c0();self.fx.records=self.fx.amounts('s1','100.000000000000000000000000001',changes={'definition':'REVENUE_MINUS_DIRECT_COST'},extras=({'record_id':'s2','account_code':'5000','amount':'40'},))
        self.fx.controls=self.fx.amounts('control1','100.000000000000000000000000001',changes={'definition':'REVENUE_MINUS_DIRECT_COST'},extras=({'record_id':'control2','account_code':'5000','amount':'40'},))
        self.fx.manifest=self.fx.manifest.model_copy(update={'record_version_id':self.fx.records})
        self.assertEqual(self.qualify(family='CONTRIBUTION_0').value.measurement.value,Decimal('60.000000000000000000000000001'))

    def test_c0_not_gross_profit(self):
        self.fx.c0();v=self.qualify(family='CONTRIBUTION_0').value
        self.assertEqual(v.context.economic_basis,'REVENUE_MINUS_DIRECT_COST')
        self.assertNotIn('GROSS',v.to_json())

    def test_c0_cross_scope_refuses(self):
        self.fx.c0()
        with self.assertRaises(ScopeError):self.qualify(family='CONTRIBUTION_0',mapping=self.fx.mapping.model_copy(update={'scope':self.fx.scope.model_copy(update={'ledger_id':'l2'})}))

    def test_c0_missing_control_refuses(self):
        self.fx.c0();self.fx.controls='missing'
        with self.assertRaises(ScopeError):self.qualify(family='CONTRIBUTION_0')

    def test_rolling_gm01_cannot_qualify(self):
        self.fx.c0();self.fx.records=self.fx.amounts('s1','100',changes={'definition':'REVENUE_MINUS_DIRECT_COST','time_basis':'ROLLING'})
        with self.assertRaises(ValueError):self.qualify(family='CONTRIBUTION_0')

    def test_c0_injected_value_refuses(self):
        self.fx.c0()
        with self.assertRaises(TypeError):self.qualify(family='CONTRIBUTION_0',value='100000')

    def test_c0_mapping_attribution_retained(self):
        self.fx.c0();v=self.qualify(family='CONTRIBUTION_0').value
        self.assertEqual(v.semantic.mapping.actor.actor_id,'adviser1')
        self.assertEqual(v.semantic.mapping.actor.source_authority,'HUMAN_FD_JUDGEMENT')

    def test_monthly_c0_not_gm01_owner(self):
        self.fx.c0();v=self.qualify(family='CONTRIBUTION_0').value
        self.assertEqual(v.context.origin.resource,'canonical_monthly_measurement')
        self.assertNotEqual(v.measurement_id,'GM-01')

    def test_c0_replay(self):
        self.fx.c0();old=self.qualify(family='CONTRIBUTION_0').value
        self.assertEqual(self.qualify(family='CONTRIBUTION_0',previous=old).value,old)

    def test_synthetic_origin_not_accepted(self):
        with self.assertRaises(TypeError):self.qualify(origin='SYNTHETIC')

    def test_monthly_roundtrip(self):
        value=self.qualify().value
        self.assertEqual(MonthlyMeasurement.from_json(value.to_json()),value)

    def test_revenue_rejects_cost_membership_even_if_chart_agrees(self):
        chart=self.fx.chart.model_copy(update={'direct_cost_accounts':('5000',)})
        mapping=self.fx.mapping.model_copy(update={'direct_cost_accounts':('5000',),'source_chart_version':self.fx.document(chart,'chart')})
        self.assertEqual(self.qualify(mapping=mapping).outcome,'REFUSED')

    def test_c0_mapping_revision_with_source_restatement_retains_history(self):
        self.fx.c0();old=self.qualify(family='CONTRIBUTION_0').value
        records=self.fx.records
        self.fx.records=self.fx.amounts('s3','100',changes={'definition':'REVENUE_MINUS_DIRECT_COST'},
            extras=({'record_id':'s4','account_code':'5000','amount':'40'},))
        manifest=self.fx.manifest.model_copy(update={'change_kind':'RESTATEMENT','predecessor_version_id':records,
            'record_version_id':self.fx.records,'record_ids':('s3','s4'),
            'revision_id':'source-rev2','change_reference':'qualified mapping correction'})
        mapping=self.fx.mapping.model_copy(update={'mapping_id':'mapping2','revision':2,'supersedes':'mapping1'})
        new=self.qualify(family='CONTRIBUTION_0',manifest=manifest,mapping=mapping,previous=old).value
        self.assertEqual(new.semantic.mapping.supersedes,old.semantic.mapping.mapping_id)
        self.assertEqual(new.supersedes,old.measurement_id)

    def test_source_version_cannot_restate_itself(self):
        old=self.qualify().value
        self.assertEqual(self.qualify(previous=old,manifest=self.fx.manifest.model_copy(update={
            'change_kind':'RESTATEMENT','predecessor_version_id':self.fx.records})).outcome,'REFUSED')

    def test_monthly_deserialization_rejects_unverified_dimensional_snapshot(self):
        value=self.qualify().value
        data=value.model_dump();data['semantic']['contract']['unit']={}
        with self.assertRaises(ValueError):MonthlyMeasurement.model_validate(data)


class ReceivablesAbsenceV255(unittest.TestCase):
    def setUp(self):
        self.fx=semantic.SemanticVerificationV255('runTest');self.fx.setUp();self.addCleanup(self.fx.doCleanups)
        self.service=ReceivablesAbsenceService(self.fx.con,'c1','r1',self.fx.authority)
        self.scope=ARScope(client_id='c1',entity_id='e1',ledger_id='l1',as_of='2026-01-31',population='all-open-ar')
        self.invoice=Invoice(invoice_id='inv1',customer_id='customer1',invoice_date='2026-01-01',explicit_due='2026-02-01',
            outstanding='100',as_of='2026-01-31',source_reference='invoice-ledger1',
            status=StatusEvidence(status='NONE_RECORDED',reviewed_at='2026-01-31',authority='SOURCE_RECORD',reference='status-ledger1'))
        self.review=InvoiceReview(customer_id='customer1',invoice_id='inv1',reviewed_at='2026-01-31',
            source_reference='complete-constraint-review1',dispute='NONE_RECORDED',payment_plan='NONE_RECORDED',pending_credit='NONE_RECORDED')
        self.export=ARExport(scope=self.scope,system_id='system1',report_id='open-ar',invoices=(self.invoice,),reviews=(self.review,))
        self.control=ARControl(scope=self.scope,amount='100',source_reference='ar-gl-control1',basis='AR_OPEN_ITEM_CONTROL')
        self.ev=self.fx.document(self.export,'ar-export')
        self.manifest=ARManifest(scope=self.scope,system_id='system1',report_id='open-ar',record_version_id=self.ev,
            open_items=(('customer1','inv1'),),extraction_boundary='all-open-ar',extraction_query='all open receivables, no exclusions',
            extraction_as_of='2026-01-31',change_kind='ORIGINAL',change_reference='source-report-rev1')

    def assess(self, *, export=None, manifest=None, control=None, previous=None):
        if export is not None:self.ev=self.fx.document(export,'ar-export')
        manifest=manifest or self.manifest.model_copy(update={'record_version_id':self.ev})
        return self.service.assess(self.ev,self.fx.document(manifest,'ar-manifest'),
            self.fx.document(control or self.control,'ar-control'),previous=previous)

    def test_complete_nonqualifying_population_absent(self):
        a=self.assess();self.assertEqual(a.outcome,'ABSENT_VERIFIED');self.assertEqual(a.qualifying,0)

    def test_overdue_unconstrained_prevents_absence(self):
        a=self.assess(export=self.export.model_copy(update={'invoices':(self.invoice.model_copy(update={'explicit_due':date(2026,1,30)}),)}))
        self.assertEqual(a.outcome,'QUALIFYING_BALANCE_PRESENT');self.assertEqual(a.qualifying,100)

    def test_partial_population_refuses(self):
        self.assertEqual(self.assess(manifest=self.manifest.model_copy(update={'excluded_items':(('c2','i2'),)})).outcome,'NOT_ASSESSED')

    def test_control_mismatch_refuses(self):
        self.assertEqual(self.assess(control=self.control.model_copy(update={'amount':Decimal('99')})).outcome,'NOT_ASSESSED')

    def test_untrusted_source_refuses(self):
        self.service=ReceivablesAbsenceService(self.fx.con,'c1','r1')
        self.assertEqual(self.assess().outcome,'NOT_ASSESSED')

    def test_missing_terms_due_refuses(self):
        self.assertEqual(self.assess(export=self.export.model_copy(update={'invoices':(self.invoice.model_copy(update={'explicit_due':None}),)})).outcome,'NOT_ASSESSED')

    def test_unknown_due_does_not_become_within_terms(self):
        a=self.assess(export=self.export.model_copy(update={'invoices':(self.invoice.model_copy(update={'explicit_due':None}),)}))
        self.assertIn('DUE_DATE_UNKNOWN:inv1',a.blockers)

    def unknown_status(self):
        return self.export.model_copy(update={'invoices':(self.invoice.model_copy(update={'status':self.invoice.status.model_copy(update={'status':'UNKNOWN'})}),)})

    def test_unresolved_dispute_refuses(self):
        self.assertEqual(self.assess(export=self.unknown_status()).outcome,'NOT_ASSESSED')

    def test_unresolved_payment_plan_refuses(self):
        status=self.invoice.status.model_copy(update={'authority':'UNKNOWN'})
        self.assertEqual(self.assess(export=self.export.model_copy(update={'invoices':(self.invoice.model_copy(update={'status':status}),)})).outcome,'NOT_ASSESSED')

    def test_unresolved_pending_credit_refuses(self):
        status=self.invoice.status.model_copy(update={'reference':None})
        self.assertEqual(self.assess(export=self.export.model_copy(update={'invoices':(self.invoice.model_copy(update={'status':status}),)})).outcome,'NOT_ASSESSED')

    def test_constrained_overdue_remains_reconciled(self):
        for status in ('ACTIVE_DISPUTE','AGREED_PAYMENT_PLAN','CREDIT_NOTE_PENDING'):
            with self.subTest(status=status):
                # New source fixture per subcase to avoid introducing ambiguous roots.
                self.fx.con.execute("DELETE FROM dataset_version WHERE dataset_id IN (SELECT dataset_id FROM dataset WHERE logical_dataset_key='production-evidence:ar-manifest-1')")
                invoice=self.invoice.model_copy(update={'explicit_due':date(2026,1,10),'status':self.invoice.status.model_copy(update={'status':status})})
                field={'ACTIVE_DISPUTE':'dispute','AGREED_PAYMENT_PLAN':'payment_plan','CREDIT_NOTE_PENDING':'pending_credit'}[status]
                a=self.assess(export=self.export.model_copy(update={'invoices':(invoice,),
                    'reviews':(self.review.model_copy(update={field:'PRESENT'}),)}))
                self.assertEqual((a.outcome,a.total,a.difference),('ABSENT_VERIFIED',Decimal('100'),Decimal(0)))

    def test_empty_export_refuses(self):
        a=self.assess(export=self.export.model_copy(update={'invoices':(),'reviews':()}),manifest=self.manifest.model_copy(update={'open_items':(),'record_version_id':self.fx.document(self.export.model_copy(update={'invoices':(),'reviews':()}),'ar-export')}),control=self.control.model_copy(update={'amount':Decimal(0)}))
        self.assertEqual(a.outcome,'NOT_ASSESSED')

    def test_no_impact_not_an_absence_input(self):
        with self.assertRaises(TypeError):self.service.assess(impact=None)

    def test_zero_impact_not_an_absence_input(self):
        with self.assertRaises(TypeError):self.service.assess(impact_amount=0)

    def test_management_assertion_not_source_authority(self):
        p,h,_=self.fx.grants[self.ev];self.fx.grants[self.ev]=(p,h,'MANAGEMENT_ASSERTION')
        self.assertEqual(self.assess().outcome,'NOT_ASSESSED')

    def test_wrong_client_refuses(self):
        with self.assertRaises(ScopeError):ReceivablesAbsenceService(self.fx.con,'c2','r1')

    def test_wrong_reporting_date_refuses(self):
        with self.assertRaises(ScopeError):self.assess(control=self.control.model_copy(update={'scope':self.scope.model_copy(update={'as_of':date(2026,2,1)})}))

    def test_incomplete_lineage_refuses(self):
        self.fx.con.execute('DELETE FROM dataset_version WHERE dataset_version_id=?',(self.ev,))
        with self.assertRaises(ScopeError):self.assess()

    def test_same_date_restatement_history(self):
        old=self.assess();newexport=self.export.model_copy(update={'invoices':(self.invoice.model_copy(update={'outstanding':Decimal('90')}),)})
        self.ev=self.fx.document(newexport,'ar-export')
        manifest=self.manifest.model_copy(update={'record_version_id':self.ev,'change_kind':'RESTATEMENT','predecessor_version_id':old.source_versions[0]})
        new=self.assess(manifest=manifest,control=self.control.model_copy(update={'amount':Decimal('90')}),previous=old)
        self.assertEqual((new.outcome,new.series_id,new.supersedes),('ABSENT_VERIFIED',old.series_id,old.assessment_id))
        self.assertEqual(old.total,100)

    def test_duplicate_snapshot_refuses(self):
        self.assess()
        self.assertEqual(self.assess(export=self.export.model_copy(update={'report_id':'open-ar'})).outcome,'ABSENT_VERIFIED')
        altered=self.export.model_copy(update={'invoices':(self.invoice.model_copy(update={'outstanding':Decimal('90')}),)})
        a=self.assess(export=altered,control=self.control.model_copy(update={'amount':Decimal('90')}))
        self.assertEqual(a.outcome,'NOT_ASSESSED')

    def test_replay_idempotent(self):
        old=self.assess();self.assertEqual(self.assess(previous=old),old)

    def test_synthetic_flag_not_an_argument(self):
        with self.assertRaises(TypeError):self.service.assess(self.ev,'m','c',origin='SYNTHETIC')

    def test_due_on_reporting_date_within_terms(self):
        a=self.assess(export=self.export.model_copy(update={'invoices':(self.invoice.model_copy(update={'explicit_due':self.scope.as_of}),)}))
        self.assertEqual(a.outcome,'ABSENT_VERIFIED')

    def test_stale_status_even_within_terms_refuses(self):
        status=self.invoice.status.model_copy(update={'reviewed_at':date(2026,1,30)})
        self.assertEqual(self.assess(export=self.export.model_copy(update={'invoices':(self.invoice.model_copy(update={'status':status}),)})).outcome,'NOT_ASSESSED')

    def test_zero_control_without_authority_refuses(self):
        self.service=ReceivablesAbsenceService(self.fx.con,'c1','r1')
        self.assertEqual(self.assess(control=self.control.model_copy(update={'amount':Decimal(0)})).outcome,'NOT_ASSESSED')

    def test_absence_roundtrip_preserves_source_and_decimal(self):
        a=self.assess();self.assertEqual(type(a).from_json(a.to_json()),a)

    def test_missing_separate_constraint_review_refuses(self):
        self.assertEqual(self.assess(export=self.export.model_copy(update={'reviews':()})).outcome,'NOT_ASSESSED')

    def test_known_dispute_does_not_hide_unknown_payment_plan(self):
        invoice=self.invoice.model_copy(update={'explicit_due':date(2026,1,10),
            'status':self.invoice.status.model_copy(update={'status':'ACTIVE_DISPUTE'})})
        review=self.review.model_copy(update={'dispute':'PRESENT','payment_plan':'UNKNOWN'})
        self.assertEqual(self.assess(export=self.export.model_copy(update={'invoices':(invoice,),'reviews':(review,)})).outcome,'NOT_ASSESSED')

    def test_constraint_review_contradiction_refuses(self):
        review=self.review.model_copy(update={'pending_credit':'PRESENT'})
        self.assertEqual(self.assess(export=self.export.model_copy(update={'reviews':(review,)})).outcome,'NOT_ASSESSED')

    def test_ar_source_cannot_supersede_itself(self):
        with self.assertRaises(ValueError):
            ARManifest.model_validate({**self.manifest.model_dump(),'predecessor_version_id':self.ev,'change_kind':'RESTATEMENT'})

    def test_absence_historical_document_cannot_hide_foreign_scope(self):
        value=self.assess();data=value.model_dump();data['scope']['client_id']='c2'
        with self.assertRaisesRegex(ValidationError,'Absence assessment and evidence scopes differ'):
            type(value).model_validate(data)
