import csv,tempfile,unittest,uuid
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.ingestion.accounting import ingest_accounting_file
from profit_doctor.trust.engine import assess_level1_accounting_trust,assess_level1_eligibility,assess_cross_source_reconciliations

def now(): return '2026-09-24T22:47:00+01:00'
def write(p,fields,rows):
    with open(p,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def setup(con,c='c1'):
    r='run_'+uuid.uuid4().hex
    con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Adversarial SME','GBP','PRODUCT_DISTRIBUTION',now()))
    con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'ADVERSARIAL',now(),None,'RUNNING',None,r,'2.5')); con.commit(); return r

def base_files(d,ar=40,ap=30,cash=150,tb_credit=1000):
    d=Path(d)
    write(d/'pnl.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-08-31','line_code':'REV','line_name':'Revenue','amount':'1000'},{'period_end':'2026-08-31','line_code':'GP','line_name':'Gross Profit','amount':'350'}])
    write(d/'bs.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-08-31','line_code':'AR','line_name':'Trade Debtors','amount':str(ar)},{'period_end':'2026-08-31','line_code':'AP','line_name':'Trade Creditors','amount':str(ap)},{'period_end':'2026-08-31','line_code':'CASH','line_name':'Cash','amount':str(cash)}])
    write(d/'tb.csv',['period_end','account_code','account_name','account_type','debit','credit'],[{'period_end':'2026-08-31','account_code':'1000','account_name':'Cash','account_type':'ASSET','debit':str(tb_credit),'credit':'0'},{'period_end':'2026-08-31','account_code':'4000','account_name':'Sales','account_type':'REVENUE','debit':'0','credit':'1000'}])
    write(d/'ar.csv',['invoice_id','customer_id','invoice_date','due_date','original_amount','outstanding_amount'],[{'invoice_id':'AR1','customer_id':'C1','invoice_date':'2026-08-01','due_date':'2026-08-31','original_amount':'100','outstanding_amount':'40'}])
    write(d/'ap.csv',['invoice_id','supplier_id','invoice_date','due_date','original_amount','outstanding_amount'],[{'invoice_id':'AP1','supplier_id':'S1','invoice_date':'2026-08-01','due_date':'2026-08-31','original_amount':'80','outstanding_amount':'30'}])
    write(d/'bank.csv',['transaction_id','transaction_date','amount','balance'],[{'transaction_id':'B1','transaction_date':'2026-08-01','amount':'100','balance':'100'},{'transaction_id':'B2','transaction_date':'2026-08-02','amount':'50','balance':'150'}])

def ingest_all(con,c,r,d):
    for f,k in [('pnl.csv','D01_PNL'),('bs.csv','D02_BALANCE_SHEET'),('tb.csv','D03_TRIAL_BALANCE'),('ar.csv','D04_AR'),('ap.csv','D05_AP'),('bank.csv','D06_BANK')]: ingest_accounting_file(con,c,r,Path(d)/f,k,Path(d)/'store')

class AdversarialSMEGate(unittest.TestCase):
    def test_missing_required_column_refused(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); r=setup(con); p=Path(d)/'p.csv'; write(p,['period_end','line_code','amount'],[{'period_end':'2026-08-31','line_code':'REV','amount':'1'}])
            with self.assertRaisesRegex(ValueError,'MISSING_REQUIRED_COLUMNS:line_name'): ingest_accounting_file(con,'c1',r,p,'D01_PNL',Path(d)/'store')
            con.close()
    def test_malformed_date_refused(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); r=setup(con); p=Path(d)/'p.csv'; write(p,['period_end','line_code','line_name','amount'],[{'period_end':'31/08/26','line_code':'REV','line_name':'Revenue','amount':'1'}])
            with self.assertRaisesRegex(ValueError,'INVALID_DATE'): ingest_accounting_file(con,'c1',r,p,'D01_PNL',Path(d)/'store')
            con.close()
    def test_duplicate_ar_invoice_refused_and_rolled_back(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); r=setup(con); p=Path(d)/'ar.csv'; rows=[{'invoice_id':'X','customer_id':'C1','invoice_date':'2026-08-01','due_date':'2026-08-31','original_amount':'100','outstanding_amount':'100'}]*2; write(p,['invoice_id','customer_id','invoice_date','due_date','original_amount','outstanding_amount'],rows)
            with self.assertRaisesRegex(ValueError,'DUPLICATE_INVOICE_ID:X'): ingest_accounting_file(con,'c1',r,p,'D04_AR',Path(d)/'store')
            self.assertEqual(con.execute('select count(*) from ar_invoice').fetchone()[0],0); con.close()
    def test_duplicate_bank_transaction_refused(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); r=setup(con); p=Path(d)/'bank.csv'; rows=[{'transaction_id':'B','transaction_date':'2026-08-01','amount':'1','balance':'1'}]*2; write(p,['transaction_id','transaction_date','amount','balance'],rows)
            with self.assertRaisesRegex(ValueError,'DUPLICATE_BANK_TRANSACTION:B'): ingest_accounting_file(con,'c1',r,p,'D06_BANK',Path(d)/'store'); con.close()
    def test_abnormal_ar_outstanding_is_limitation_not_clean(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); r=setup(con); base_files(d); p=Path(d)/'ar.csv'; write(p,['invoice_id','customer_id','invoice_date','due_date','original_amount','outstanding_amount'],[{'invoice_id':'AR1','customer_id':'C1','invoice_date':'2026-08-01','due_date':'2026-08-31','original_amount':'100','outstanding_amount':'125'}]); ingest_all(con,'c1',r,d); out=assess_level1_accounting_trust(con,r,'c1'); self.assertEqual(out['D04']['integrity'],'USABLE_WITH_LIMITATION'); self.assertEqual(assess_level1_eligibility(con,r,'c1','WC-02',['D04'])['eligibility'],'PARTIAL-B'); con.close()
    def test_unbalanced_tb_materially_constrained(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); r=setup(con); base_files(d,tb_credit=999); ingest_all(con,'c1',r,d); out=assess_level1_accounting_trust(con,r,'c1'); self.assertEqual(out['D03']['integrity'],'MATERIALLY_CONSTRAINED'); con.close()
    def test_ar_cross_source_mismatch_constrains_both_domains(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); r=setup(con); base_files(d,ar=500); ingest_all(con,'c1',r,d); assess_level1_accounting_trust(con,r,'c1'); x=assess_cross_source_reconciliations(con,r,'c1'); self.assertEqual(x['AR_LEDGER_TO_BS'],'FAILED'); states={q['data_domain']:q['integrity_state'] for q in con.execute('select data_domain,integrity_state from financial_integrity where run_id=?',(r,))}; self.assertEqual(states['D02'],'MATERIALLY_CONSTRAINED'); self.assertEqual(states['D04'],'MATERIALLY_CONSTRAINED'); con.close()
    def test_bank_cross_source_mismatch_detected(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); r=setup(con); base_files(d,cash=999); ingest_all(con,'c1',r,d); assess_level1_accounting_trust(con,r,'c1'); self.assertEqual(assess_cross_source_reconciliations(con,r,'c1')['BANK_TO_BS_CASH'],'FAILED'); con.close()
    def test_missing_bank_refuses_liquidity_test(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); r=setup(con); base_files(d)
            for f,k in [('pnl.csv','D01_PNL'),('bs.csv','D02_BALANCE_SHEET'),('tb.csv','D03_TRIAL_BALANCE'),('ar.csv','D04_AR'),('ap.csv','D05_AP')]: ingest_accounting_file(con,'c1',r,Path(d)/f,k,Path(d)/'store')
            assess_level1_accounting_trust(con,r,'c1'); self.assertEqual(assess_level1_eligibility(con,r,'c1','WC-05',['D06'])['eligibility'],'UNAVAILABLE'); con.close()
    def test_client_isolation_in_accounting_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); r1=setup(con,'c1'); r2=setup(con,'c2'); d1=Path(d)/'one'; d2=Path(d)/'two'; d1.mkdir(); d2.mkdir(); base_files(d1); base_files(d2,tb_credit=900); ingest_all(con,'c1',r1,d1); ingest_all(con,'c2',r2,d2); a=assess_level1_accounting_trust(con,r1,'c1'); b=assess_level1_accounting_trust(con,r2,'c2'); self.assertEqual(a['D03']['integrity'],'RELIABLE'); self.assertEqual(b['D03']['integrity'],'MATERIALLY_CONSTRAINED'); con.close()

if __name__=='__main__': unittest.main()
