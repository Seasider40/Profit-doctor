import tempfile,uuid,shutil
from pathlib import Path
from decimal import Decimal
from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import ingest_northstar
from profit_doctor.ingestion.accounting import ingest_accounting_file
from profit_doctor.trust.engine import assess_level1_accounting_trust,assess_cross_source_reconciliations,set_business_model_runtime
from profit_doctor.calc.primitive_engine import run_primitive_engine
from profit_doctor.revenue_semantics import assign_product_revenue_type,revenue_mix
from profit_doctor.economic.engine import record_mechanism_evidence,qualify_opportunity_candidate_evidenced

SRC=Path(__file__).resolve().parent/'fixtures'/'gate3_micro'
def now(): return '2026-09-24T00:00:00+00:00'
def load_all(tmp):
    con=connect(Path(tmp)/'x.db'); c='c1'; r='run_'+uuid.uuid4().hex
    con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Micro','GBP','PROFESSIONAL_SERVICES',now()))
    con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'BASELINE',now(),None,'RUNNING',None,r,'1.3')); con.commit()
    sales=ingest_northstar(con,c,r,SRC,Path(tmp)/'store')
    for f,k in [('pnl.csv','D01_PNL'),('bs.csv','D02_BALANCE_SHEET'),('tb.csv','D03_TRIAL_BALANCE'),('ar.csv','D04_AR'),('ap.csv','D05_AP'),('bank.csv','D06_BANK')]: ingest_accounting_file(con,c,r,SRC/f,k,Path(tmp)/'store')
    assess_level1_accounting_trust(con,r,c)
    return con,c,r,sales

def test_cross_source_matrix_clean_and_detects_break():
    with tempfile.TemporaryDirectory() as d:
        con,c,r,s=load_all(d); x=assess_cross_source_reconciliations(con,r,c)
        assert x['SALES_TO_PNL_REVENUE']=='RECONCILED'; assert x['AR_LEDGER_TO_BS']=='RECONCILED'; assert x['AP_LEDGER_TO_BS']=='RECONCILED'; assert x['BANK_TO_BS_CASH']=='RECONCILED'
        # Break AR subledger and prove cross-source integrity catches it.
        con.execute("UPDATE ar_invoice SET outstanding_amount=CAST(outstanding_amount AS REAL)+5000 WHERE ar_invoice_id=(SELECT ar_invoice_id FROM ar_invoice LIMIT 1)"); con.commit()
        x2=assess_cross_source_reconciliations(con,r,c); assert x2['AR_LEDGER_TO_BS']=='FAILED'; con.close()

def test_inventory_not_applicable_is_na_and_ccc_excludes_dio():
    with tempfile.TemporaryDirectory() as d:
        con,c,r,s=load_all(d); set_business_model_runtime(con,c,'PROFESSIONAL_SERVICES','NOT_APPLICABLE'); out=run_primitive_engine(con,r,c,s['dataset_version_id'])['level1']
        ex=con.execute("SELECT execution_status FROM primitive_execution WHERE run_id=? AND primitive_id='WC_DIO' ORDER BY executed_at DESC LIMIT 1",(r,)).fetchone()[0]
        assert ex=='N/A'; assert out['WC_CCC']==out['WC_DSO']-out['WC_DPO']; con.close()

def test_revenue_semantics_separates_recurring_from_project_event():
    with tempfile.TemporaryDirectory() as d:
        con,c,r,s=load_all(d)
        assign_product_revenue_type(con,c,'RETAINER','RETAINER'); assign_product_revenue_type(con,c,'PROJECT','PROJECT'); assign_product_revenue_type(con,c,'EVENT','EVENT')
        mix=revenue_mix(con,c,s['dataset_version_id']); assert mix['recurring_revenue']>0; assert mix['recurring_revenue']<mix['total_revenue']; assert mix['unmapped_revenue']==0; con.close()

def test_mechanism_evidence_required_for_evidenced_qualification():
    with tempfile.TemporaryDirectory() as d:
        con,c,r,s=load_all(d); t=now(); fid='f_'+uuid.uuid4().hex; story='story_'+uuid.uuid4().hex; cid='oc_'+uuid.uuid4().hex
        # Minimal economic objects for qualification contract.
        con.execute('INSERT INTO finding VALUES (?,?,?,?,?,?,?,?,?)',(fid,c,'OPPORTUNITY','Test finding','ACCEPTED',r,r,t,t))
        con.execute('INSERT INTO economic_story VALUES (?,?,?,?,?,?,?,?,?,?)',(story,c,'S_'+uuid.uuid4().hex,'PERFORMANCE','Test','OPEN',r,r,t,t))
        con.execute('INSERT INTO opportunity_candidate VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(cid,r,c,story,fid,None,'IMPROVE','B1_RECURRING_PROFIT_IMPROVEMENT',None,'10000',None,None,'GBP','CONDITIONAL','REQUIRES_ECONOMIC_RESOLUTION','test',t)); con.commit()
        try: qualify_opportunity_candidate_evidenced(con,cid,'M1','10000','5000','3000','5000','baseline')
        except ValueError: pass
        else: raise AssertionError('qualification should require mechanism evidence')
        record_mechanism_evidence(con,cid,'M1','MANAGEMENT_VALIDATED','Management validated price recovery route','Customer list and contract review','Supported recovery envelope')
        oid=qualify_opportunity_candidate_evidenced(con,cid,'M1','10000','5000','3000','5000','baseline'); assert oid; con.close()

# Make these historical Gate-3 function tests visible to unittest discovery as well as pytest.
def load_tests(loader, tests, pattern):
    import unittest
    suite=unittest.TestSuite()
    for fn in [test_cross_source_matrix_clean_and_detects_break,
               test_inventory_not_applicable_is_na_and_ccc_excludes_dio,
               test_revenue_semantics_separates_recurring_from_project_event,
               test_mechanism_evidence_required_for_evidenced_qualification]:
        suite.addTest(unittest.FunctionTestCase(fn))
    return suite
