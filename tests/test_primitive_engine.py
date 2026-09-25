import unittest,tempfile,csv,uuid
from decimal import Decimal
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import ingest_northstar
from profit_doctor.ingestion.accounting import ingest_accounting_file
from profit_doctor.calc.primitive_engine import run_primitive_engine,calculate_level1_primitives,seed_registry

ROOT=Path(__file__).resolve().parent/'fixtures'/'northstar'
def now(): return '2026-09-24T00:00:00+00:00'
def create_client(con,name):
 c='c_'+uuid.uuid4().hex; con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,name,'GBP','PRODUCT_DISTRIBUTION',now())); con.commit(); return c
def create_run(con,c):
 r='run_'+uuid.uuid4().hex; con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'BASELINE',now(),None,'RUNNING',None,r,'0.5.0')); con.commit(); return r
def write(p,fields,rows):
 with open(p,'w',newline='') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

class PrimitiveEngineTests(unittest.TestCase):
 def test_northstar_known_answers_and_customer_rollup(self):
  with tempfile.TemporaryDirectory() as d:
   con=connect(Path(d)/'x.db'); c=create_client(con,'Northstar'); r=create_run(con,c); ing=ingest_northstar(con,c,r,ROOT,Path(d)/'store')
   out=run_primitive_engine(con,r,c,ing['dataset_version_id'])['transaction']
   self.assertEqual(out['COMMERCIAL_NET_REVENUE'],Decimal('14047932.56')); self.assertEqual(out['COMMERCIAL_DIRECT_COST'],Decimal('9110927.70')); self.assertEqual(out['ECON_CONTRIBUTION_0'],Decimal('4937004.86')); self.assertEqual(out['customer_count'],75)
   cust=con.execute("SELECT numeric_value FROM primitive_result WHERE run_id=? AND primitive_id='CUSTOMER_REVENUE'",(r,)).fetchall(); self.assertEqual(sum((Decimal(x['numeric_value']) for x in cust),Decimal('0')),Decimal('14047932.56'))
 def test_dependency_registry_seeded(self):
  with tempfile.TemporaryDirectory() as d:
   con=connect(Path(d)/'x.db'); seed_registry(con); self.assertGreaterEqual(con.execute('SELECT count(*) n FROM primitive_method').fetchone()['n'],16); self.assertGreaterEqual(con.execute('SELECT count(*) n FROM primitive_dependency').fetchone()['n'],8)
 def test_level1_accounting_primitives_and_dso(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d); con=connect(d/'x.db'); c=create_client(con,'A'); r=create_run(con,c)
   write(d/'pnl.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'REV','line_name':'Revenue','amount':'1200.00'},{'period_end':'2026-12-31','line_code':'GP','line_name':'Gross Profit','amount':'420.00'},{'period_end':'2026-12-31','line_code':'EBITDA','line_name':'EBITDA','amount':'180.00'}])
   write(d/'bs.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'AR','line_name':'Trade Receivables','amount':'100.00'},{'period_end':'2026-12-31','line_code':'AP','line_name':'Trade Payables','amount':'80.00'},{'period_end':'2026-12-31','line_code':'CASH','line_name':'Cash','amount':'50.00'}])
   write(d/'bank.csv',['transaction_id','transaction_date','amount','balance'],[{'transaction_id':'B1','transaction_date':'2026-12-31','amount':'50','balance':'50'}])
   for f,k in [('pnl.csv','D01_PNL'),('bs.csv','D02_BALANCE_SHEET'),('bank.csv','D06_BANK')]: ingest_accounting_file(con,c,r,d/f,k,d/'store')
   out=calculate_level1_primitives(con,r,c); self.assertEqual(out['FIN_REVENUE'],Decimal('1200.00')); self.assertEqual(out['FIN_GROSS_PROFIT'],Decimal('420.00')); self.assertEqual(out['FIN_EBITDA'],Decimal('180.00')); self.assertEqual(out['WC_DSO'],Decimal('100')/Decimal('1200')*Decimal('365'))
 def test_missing_pnl_does_not_become_zero(self):
  with tempfile.TemporaryDirectory() as d:
   con=connect(Path(d)/'x.db'); c=create_client(con,'A'); r=create_run(con,c); calculate_level1_primitives(con,r,c)
   self.assertEqual(con.execute("SELECT execution_status FROM primitive_execution WHERE run_id=? AND primitive_id='FIN_REVENUE'",(r,)).fetchone()['execution_status'],'UNAVAILABLE')
   self.assertEqual(con.execute("SELECT count(*) n FROM primitive_result WHERE run_id=? AND primitive_id='FIN_REVENUE'",(r,)).fetchone()['n'],0)
 def test_dpo_refuses_revenue_proxy(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d); con=connect(d/'x.db'); c=create_client(con,'A'); r=create_run(con,c)
   write(d/'pnl.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'REV','line_name':'Revenue','amount':'1200'}]); write(d/'bs.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'AP','line_name':'Trade Payables','amount':'80'}])
   for f,k in [('pnl.csv','D01_PNL'),('bs.csv','D02_BALANCE_SHEET')]: ingest_accounting_file(con,c,r,d/f,k,d/'store')
   calculate_level1_primitives(con,r,c); x=con.execute("SELECT execution_status,limitation FROM primitive_execution WHERE run_id=? AND primitive_id='WC_DPO'",(r,)).fetchone(); self.assertEqual(x['execution_status'],'UNAVAILABLE'); self.assertIn('proxy',x['limitation'])
 def test_zero_revenue_dso_not_meaningful(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d); con=connect(d/'x.db'); c=create_client(con,'A'); r=create_run(con,c)
   write(d/'pnl.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'REV','line_name':'Revenue','amount':'0'}]); write(d/'bs.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'AR','line_name':'Trade Receivables','amount':'100'}])
   for f,k in [('pnl.csv','D01_PNL'),('bs.csv','D02_BALANCE_SHEET')]: ingest_accounting_file(con,c,r,d/f,k,d/'store')
   calculate_level1_primitives(con,r,c); x=con.execute("SELECT result_status,numeric_value FROM primitive_result WHERE run_id=? AND primitive_id='WC_DSO'",(r,)).fetchone(); self.assertEqual(x['result_status'],'NOT_MEANINGFUL'); self.assertIsNone(x['numeric_value'])
 def test_lineage_exists_for_financial_result(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d); con=connect(d/'x.db'); c=create_client(con,'A'); r=create_run(con,c); write(d/'pnl.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'REV','line_name':'Revenue','amount':'10'}]); ingest_accounting_file(con,c,r,d/'pnl.csv','D01_PNL',d/'store'); calculate_level1_primitives(con,r,c)
   x=con.execute("SELECT pr.primitive_result_id FROM primitive_result pr WHERE run_id=? AND primitive_id='FIN_REVENUE'",(r,)).fetchone(); self.assertGreater(con.execute('SELECT count(*) n FROM calculation_lineage WHERE primitive_result_id=?',(x['primitive_result_id'],)).fetchone()['n'],0)
if __name__=='__main__': unittest.main()

class PrimitiveEngineExpandedTests(unittest.TestCase):
 def test_direct_cost_unlocks_dpo_without_revenue_proxy(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d); con=connect(d/'x.db'); c=create_client(con,'A'); r=create_run(con,c)
   write(d/'pnl.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'REV','line_name':'Revenue','amount':'1200'},{'period_end':'2026-12-31','line_code':'COGS','line_name':'Cost of Sales','amount':'-800'}])
   write(d/'bs.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'AP','line_name':'Trade Payables','amount':'80'}])
   for f,k in [('pnl.csv','D01_PNL'),('bs.csv','D02_BALANCE_SHEET')]: ingest_accounting_file(con,c,r,d/f,k,d/'store')
   out=calculate_level1_primitives(con,r,c); self.assertEqual(out['FIN_DIRECT_COST'],Decimal('-800')); self.assertEqual(out['WC_DPO'],Decimal('80')/Decimal('800')*Decimal('365'))
 def test_ar_ap_ledger_and_overdue_are_separate_primitives(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d); con=connect(d/'x.db'); c=create_client(con,'A'); r=create_run(con,c)
   write(d/'pnl.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'REV','line_name':'Revenue','amount':'1000'}])
   write(d/'ar.csv',['invoice_id','customer_id','invoice_date','due_date','original_amount','outstanding_amount'],[{'invoice_id':'A1','customer_id':'C1','invoice_date':'2026-10-01','due_date':'2026-11-01','original_amount':'100','outstanding_amount':'60'},{'invoice_id':'A2','customer_id':'C2','invoice_date':'2026-12-20','due_date':'2027-01-20','original_amount':'50','outstanding_amount':'50'}])
   write(d/'ap.csv',['invoice_id','supplier_id','invoice_date','due_date','original_amount','outstanding_amount'],[{'invoice_id':'P1','supplier_id':'S1','invoice_date':'2026-09-01','due_date':'2026-10-01','original_amount':'70','outstanding_amount':'20'}])
   for f,k in [('pnl.csv','D01_PNL'),('ar.csv','D04_AR'),('ap.csv','D05_AP')]: ingest_accounting_file(con,c,r,d/f,k,d/'store')
   out=calculate_level1_primitives(con,r,c); self.assertEqual(out['AR_LEDGER_OUTSTANDING'],Decimal('110')); self.assertEqual(out['AR_OVERDUE_OUTSTANDING'],Decimal('60')); self.assertEqual(out['AP_LEDGER_OUTSTANDING'],Decimal('20')); self.assertEqual(out['AP_OVERDUE_OUTSTANDING'],Decimal('20'))
 def test_available_cash_prefers_bank_and_does_not_claim_liquidity(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d); con=connect(d/'x.db'); c=create_client(con,'A'); r=create_run(con,c)
   write(d/'bs.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'CASH','line_name':'Cash','amount':'50'}]); write(d/'bank.csv',['transaction_id','transaction_date','amount','balance'],[{'transaction_id':'B1','transaction_date':'2026-12-31','amount':'45','balance':'45'}])
   for f,k in [('bs.csv','D02_BALANCE_SHEET'),('bank.csv','D06_BANK')]: ingest_accounting_file(con,c,r,d/f,k,d/'store')
   out=calculate_level1_primitives(con,r,c); self.assertEqual(out['AVAILABLE_CASH'],Decimal('45')); self.assertEqual(con.execute("SELECT count(*) n FROM primitive_registry WHERE primitive_id='AVAILABLE_LIQUIDITY'").fetchone()['n'],0)
 def test_ccc_refuses_without_inventory_dio(self):
  with tempfile.TemporaryDirectory() as d:
   con=connect(Path(d)/'x.db'); c=create_client(con,'A'); r=create_run(con,c); calculate_level1_primitives(con,r,c)
   x=con.execute("SELECT execution_status,limitation FROM primitive_execution WHERE run_id=? AND primitive_id='WC_CCC'",(r,)).fetchone(); self.assertEqual(x['execution_status'],'UNAVAILABLE'); self.assertIn('DIO',x['limitation'])

class PrimitiveInventoryTests(unittest.TestCase):
 def test_inventory_unlocks_dio_and_ccc(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d); con=connect(d/'x.db'); c=create_client(con,'A'); r=create_run(con,c)
   write(d/'pnl.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'REV','line_name':'Revenue','amount':'1200'},{'period_end':'2026-12-31','line_code':'COGS','line_name':'Cost of Sales','amount':'-800'}])
   write(d/'bs.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'AR','line_name':'Trade Receivables','amount':'100'},{'period_end':'2026-12-31','line_code':'AP','line_name':'Trade Payables','amount':'80'},{'period_end':'2026-12-31','line_code':'STOCK','line_name':'Stock','amount':'200'}])
   for f,k in [('pnl.csv','D01_PNL'),('bs.csv','D02_BALANCE_SHEET')]: ingest_accounting_file(con,c,r,d/f,k,d/'store')
   out=calculate_level1_primitives(con,r,c)
   self.assertEqual(out['WC_DIO'],Decimal('200')/Decimal('800')*Decimal('365'))
   self.assertEqual(out['WC_CCC'],out['WC_DSO']+out['WC_DIO']-out['WC_DPO'])
 def test_d12_inventory_snapshot_is_preserved_as_separate_primitive(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d); con=connect(d/'x.db'); c=create_client(con,'A'); r=create_run(con,c)
   write(d/'inv.csv',['snapshot_date','product_id','quantity_on_hand','inventory_value'],[{'snapshot_date':'2026-12-31','product_id':'P1','quantity_on_hand':'10','inventory_value':'125.50'},{'snapshot_date':'2026-12-31','product_id':'P2','quantity_on_hand':'5','inventory_value':'74.50'}])
   ingest_accounting_file(con,c,r,d/'inv.csv','D12_INVENTORY',d/'store')
   out=calculate_level1_primitives(con,r,c); self.assertEqual(out['INVENTORY_SNAPSHOT_VALUE'],Decimal('200.00'))
   self.assertNotIn('WC_DIO',out)
 def test_d12_snapshot_not_used_for_dio_when_period_is_incompatible(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d); con=connect(d/'x.db'); c=create_client(con,'A'); r=create_run(con,c)
   write(d/'pnl.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'COGS','line_name':'Cost of Sales','amount':'-800'}])
   write(d/'inv.csv',['snapshot_date','product_id','quantity_on_hand','inventory_value'],[{'snapshot_date':'2026-11-30','product_id':'P1','quantity_on_hand':'10','inventory_value':'200'}])
   ingest_accounting_file(con,c,r,d/'pnl.csv','D01_PNL',d/'store'); ingest_accounting_file(con,c,r,d/'inv.csv','D12_INVENTORY',d/'store')
   out=calculate_level1_primitives(con,r,c); self.assertNotIn('WC_DIO',out)
   x=con.execute("SELECT execution_status FROM primitive_execution WHERE run_id=? AND primitive_id='WC_DIO'",(r,)).fetchone(); self.assertEqual(x['execution_status'],'UNAVAILABLE')
 def test_inventory_duplicate_snapshot_rolls_back(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d); con=connect(d/'x.db'); c=create_client(con,'A'); r=create_run(con,c)
   write(d/'inv.csv',['snapshot_date','product_id','quantity_on_hand','inventory_value'],[{'snapshot_date':'2026-12-31','product_id':'P1','quantity_on_hand':'10','inventory_value':'100'},{'snapshot_date':'2026-12-31','product_id':'P1','quantity_on_hand':'11','inventory_value':'110'}])
   with self.assertRaises(ValueError): ingest_accounting_file(con,c,r,d/'inv.csv','D12_INVENTORY',d/'store')
   self.assertEqual(con.execute('SELECT count(*) n FROM inventory_snapshot').fetchone()['n'],0)

class PrimitivePeriodCompatibilityTests(unittest.TestCase):
 def test_dso_dpo_refuse_mismatched_pnl_and_bs_periods(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d); con=connect(d/'x.db'); c=create_client(con,'A'); r=create_run(con,c)
   write(d/'pnl.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'REV','line_name':'Revenue','amount':'1200'},{'period_end':'2026-12-31','line_code':'COGS','line_name':'Cost of Sales','amount':'-800'}])
   write(d/'bs.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-11-30','line_code':'AR','line_name':'Trade Receivables','amount':'100'},{'period_end':'2026-11-30','line_code':'AP','line_name':'Trade Payables','amount':'80'}])
   ingest_accounting_file(con,c,r,d/'pnl.csv','D01_PNL',d/'store'); ingest_accounting_file(con,c,r,d/'bs.csv','D02_BALANCE_SHEET',d/'store')
   out=calculate_level1_primitives(con,r,c); self.assertNotIn('WC_DSO',out); self.assertNotIn('WC_DPO',out)
