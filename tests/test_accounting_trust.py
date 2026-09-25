import unittest,tempfile,csv,uuid
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.ingestion.accounting import ingest_accounting_file
from profit_doctor.trust.engine import assess_level1_accounting_trust,assess_level1_eligibility

def now(): return '2026-09-24T00:00:00+00:00'
def setup(con):
 con.execute('INSERT INTO client VALUES (?,?,?,?,?)',('c1','Test','GBP','PRODUCT_DISTRIBUTION',now())); run='run_'+uuid.uuid4().hex; con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(run,'c1','BASELINE',now(),None,'RUNNING',None,run,'0.4.0')); con.commit(); return run

def write(p,fields,rows):
 with open(p,'w',newline='') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def fixture(d,break_tb=False,break_bank=False):
 d=Path(d)
 write(d/'pnl.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-08-31','line_code':'REV','line_name':'Revenue','amount':'1000.00'},{'period_end':'2026-08-31','line_code':'GP','line_name':'Gross Profit','amount':'350.00'}])
 write(d/'bs.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-08-31','line_code':'CASH','line_name':'Cash','amount':'500.00'}])
 write(d/'tb.csv',['period_end','account_code','account_name','account_type','debit','credit'],[{'period_end':'2026-08-31','account_code':'1000','account_name':'Cash','account_type':'ASSET','debit':'1000.00','credit':'0.00'},{'period_end':'2026-08-31','account_code':'4000','account_name':'Sales','account_type':'REVENUE','debit':'0.00','credit':'999.00' if break_tb else '1000.00'}])
 write(d/'ar.csv',['invoice_id','customer_id','invoice_date','due_date','original_amount','outstanding_amount'],[{'invoice_id':'AR1','customer_id':'C1','invoice_date':'2026-08-01','due_date':'2026-08-31','original_amount':'100.00','outstanding_amount':'40.00'}])
 write(d/'ap.csv',['invoice_id','supplier_id','invoice_date','due_date','original_amount','outstanding_amount'],[{'invoice_id':'AP1','supplier_id':'S1','invoice_date':'2026-08-01','due_date':'2026-08-31','original_amount':'80.00','outstanding_amount':'30.00'}])
 write(d/'bank.csv',['transaction_id','transaction_date','amount','balance'],[{'transaction_id':'B1','transaction_date':'2026-08-01','amount':'100.00','balance':'100.00'},{'transaction_id':'B2','transaction_date':'2026-08-02','amount':'50.00','balance':'999.00' if break_bank else '150.00'}])
 return [('pnl.csv','D01_PNL'),('bs.csv','D02_BALANCE_SHEET'),('tb.csv','D03_TRIAL_BALANCE'),('ar.csv','D04_AR'),('ap.csv','D05_AP'),('bank.csv','D06_BANK')]

class AccountingTrust(unittest.TestCase):
 def test_clean_level1_domains_reliable(self):
  with tempfile.TemporaryDirectory() as d:
   con=connect(Path(d)/'x.db'); run=setup(con)
   for f,k in fixture(d): ingest_accounting_file(con,'c1',run,Path(d)/f,k,Path(d)/'store')
   out=assess_level1_accounting_trust(con,run,'c1')
   self.assertTrue(all(out[x]['availability']=='AVAILABLE' for x in ('D01','D02','D03','D04','D05','D06')))
   self.assertTrue(all(out[x]['integrity']=='RELIABLE' for x in ('D01','D02','D03','D04','D05','D06')))
   self.assertEqual(assess_level1_eligibility(con,run,'c1','WC-01',['D01','D02','D03'])['eligibility'],'FULL')
 def test_unbalanced_tb_constrains_dependent_test(self):
  with tempfile.TemporaryDirectory() as d:
   con=connect(Path(d)/'x.db'); run=setup(con)
   for f,k in fixture(d,break_tb=True): ingest_accounting_file(con,'c1',run,Path(d)/f,k,Path(d)/'store')
   out=assess_level1_accounting_trust(con,run,'c1'); self.assertEqual(out['D03']['integrity'],'MATERIALLY_CONSTRAINED')
   self.assertEqual(assess_level1_eligibility(con,run,'c1','RISK-01',['D03'])['eligibility'],'PARTIAL-C')
 def test_bank_movement_anomaly_is_limitation_not_false_failure(self):
  with tempfile.TemporaryDirectory() as d:
   con=connect(Path(d)/'x.db'); run=setup(con)
   for f,k in fixture(d,break_bank=True): ingest_accounting_file(con,'c1',run,Path(d)/f,k,Path(d)/'store')
   out=assess_level1_accounting_trust(con,run,'c1'); self.assertEqual(out['D06']['integrity'],'USABLE_WITH_LIMITATION')
   self.assertEqual(assess_level1_eligibility(con,run,'c1','WC-05',['D06'])['eligibility'],'PARTIAL-B')
 def test_missing_bank_refuses_cash_test_but_not_tb_test(self):
  with tempfile.TemporaryDirectory() as d:
   con=connect(Path(d)/'x.db'); run=setup(con)
   for f,k in fixture(d):
    if k!='D06_BANK': ingest_accounting_file(con,'c1',run,Path(d)/f,k,Path(d)/'store')
   assess_level1_accounting_trust(con,run,'c1')
   self.assertEqual(assess_level1_eligibility(con,run,'c1','WC-05',['D06'])['eligibility'],'UNAVAILABLE')
   self.assertEqual(assess_level1_eligibility(con,run,'c1','RISK-01',['D03'])['eligibility'],'FULL')
 def test_bad_accounting_decimal_rolls_back(self):
  with tempfile.TemporaryDirectory() as d:
   con=connect(Path(d)/'x.db'); run=setup(con); fixture(d)
   p=Path(d)/'pnl.csv'; write(p,['period_end','line_code','line_name','amount'],[{'period_end':'2026-08-31','line_code':'REV','line_name':'Revenue','amount':'not-money'}])
   with self.assertRaisesRegex(ValueError,'INVALID_DECIMAL'): ingest_accounting_file(con,'c1',run,p,'D01_PNL',Path(d)/'store')
   self.assertEqual(con.execute('select count(*) from financial_statement_line').fetchone()[0],0)

if __name__=='__main__': unittest.main()
