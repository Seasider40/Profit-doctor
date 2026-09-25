import unittest,tempfile,uuid,csv
from decimal import Decimal
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import ingest_northstar
from profit_doctor.ingestion.accounting import ingest_accounting_file
from profit_doctor.trust.engine import run_trust_layer,assess_level1_accounting_trust
from profit_doctor.calc.primitive_engine import run_primitive_engine,calculate_level1_primitives
from profit_doctor.diagnostic.engine import run_diagnostic_engine,seed_registry
ROOT=Path(__file__).resolve().parent/'fixtures'/'northstar'
def now(): return '2026-09-24T00:00:00+00:00'
def client(con):
 c='c_'+uuid.uuid4().hex; con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Northstar','GBP','PRODUCT_DISTRIBUTION',now())); con.commit(); return c
def run(con,c):
 r='r_'+uuid.uuid4().hex; con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'BASELINE',now(),None,'RUNNING',None,r,'0.8.0')); con.commit(); return r
def write(p,fields,rows):
 with open(p,'w',newline='') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
class DiagnosticTests(unittest.TestCase):
 def setup_ns(self,d):
  con=connect(Path(d)/'x.db'); c=client(con); r=run(con,c); ing=ingest_northstar(con,c,r,ROOT,Path(d)/'store'); run_trust_layer(con,r,c,ing['dataset_version_id']); run_primitive_engine(con,r,c,ing['dataset_version_id']); return con,c,r,ing
 def test_registry_has_first_nine_tests_and_core_questions(self):
  with tempfile.TemporaryDirectory() as d:
   con=connect(Path(d)/'x.db'); seed_registry(con); self.assertGreaterEqual(con.execute('SELECT count(*) n FROM test_registry').fetchone()['n'],12); self.assertEqual(con.execute("SELECT core_question FROM test_registry WHERE test_id='WC-02'").fetchone()['core_question'][:5],'Which')
 def test_northstar_runs_first_seven_transaction_diagnostics(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); out=run_diagnostic_engine(con,r,c,ing['dataset_version_id']);
   for t in ['REV-01','REV-02','REV-03','GM-01','GM-02','CUS-01','CUS-04']: self.assertEqual(out[t]['status'],'COMPLETED')
   self.assertGreater(con.execute('SELECT count(*) n FROM signal WHERE run_id=?',(r,)).fetchone()['n'],0)
 def test_revenue_bridge_reconciles_exactly(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); s=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='REV-02' AND signal_type='REVENUE_BRIDGE_TOTAL'",(r,)).fetchone(); self.assertEqual(Decimal(s['observed_value'])-Decimal(s['comparison_value']),Decimal(s['variance_value']))
 def test_customer_concentration_detects_alpha_as_largest_current_customer(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); s=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='CUS-01' AND signal_type='TOP_CUSTOMER_CONCENTRATION'",(r,)).fetchone(); name=con.execute('SELECT canonical_name FROM entity WHERE entity_id=?',(s['entity_id'],)).fetchone()['canonical_name']; self.assertIn('Alpha',name)
 def test_wc_tests_do_not_fake_signals_without_primitives(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); out=run_diagnostic_engine(con,r,c,ing['dataset_version_id']); self.assertEqual(out['WC-01']['status'],'NOT_RUN'); self.assertEqual(out['WC-02']['status'],'NOT_RUN')
 def test_wc_signals_consume_primitive_results(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d); con=connect(d/'x.db'); c=client(con); r=run(con,c)
   write(d/'pnl.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'REV','line_name':'Revenue','amount':'1200'},{'period_end':'2026-12-31','line_code':'COGS','line_name':'Cost of Sales','amount':'-800'}]); write(d/'bs.csv',['period_end','line_code','line_name','amount'],[{'period_end':'2026-12-31','line_code':'AR','line_name':'Trade Receivables','amount':'100'},{'period_end':'2026-12-31','line_code':'AP','line_name':'Trade Payables','amount':'80'},{'period_end':'2026-12-31','line_code':'STOCK','line_name':'Stock','amount':'200'}]); write(d/'ar.csv',['invoice_id','customer_id','invoice_date','due_date','original_amount','outstanding_amount'],[{'invoice_id':'A1','customer_id':'C1','invoice_date':'2026-10-01','due_date':'2026-11-01','original_amount':'100','outstanding_amount':'60'}])
   for f,k in [('pnl.csv','D01_PNL'),('bs.csv','D02_BALANCE_SHEET'),('ar.csv','D04_AR')]: ingest_accounting_file(con,c,r,d/f,k,d/'store')
   assess_level1_accounting_trust(con,r,c); calculate_level1_primitives(con,r,c); out=run_diagnostic_engine(con,r,c); self.assertEqual(out['WC-01']['status'],'COMPLETED'); self.assertEqual(out['WC-02']['status'],'COMPLETED'); self.assertGreaterEqual(out['WC-01']['signal_count'],4)
 def test_signals_have_lineage(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); self.assertEqual(con.execute('SELECT count(*) n FROM signal s LEFT JOIN diagnostic_lineage l ON l.signal_id=s.signal_id WHERE s.run_id=? AND l.signal_id IS NULL',(r,)).fetchone()['n'],0)
if __name__=='__main__': unittest.main()
