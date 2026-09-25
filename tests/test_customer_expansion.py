import tempfile, unittest, uuid
from pathlib import Path
from decimal import Decimal
from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import ingest_northstar
from profit_doctor.trust.engine import run_trust_layer
from profit_doctor.diagnostic.engine import run_diagnostic_engine
from profit_doctor.ingestion.accounting import ingest_accounting_file

class CustomerExpansion(unittest.TestCase):
 def setup_ns(self,d):
  root=Path(__file__).resolve().parent/'fixtures'/'northstar'; con=connect(Path(d)/'x.db'); c='c_'+uuid.uuid4().hex
  con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Customer Test','GBP','PRODUCT_DISTRIBUTION','2026-09-24T00:00:00+00:00')); r='r_'+uuid.uuid4().hex
  con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'BASELINE','2026-09-24T00:00:00+00:00',None,'RUNNING',None,r,'1.6.0')); con.commit(); ing=ingest_northstar(con,c,r,root,Path(d)/'store'); run_trust_layer(con,r,c,ing['dataset_version_id']); return con,c,r,ing
 def test_complete_customer_module(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); out=run_diagnostic_engine(con,r,c,ing['dataset_version_id']); self.assertTrue(all(f'CUS-0{i}' in out for i in range(1,8)))
 def test_customer_profitability_separates_revenue_and_contribution(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); xs=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='CUS-02'",(r,)).fetchall(); self.assertTrue(xs); self.assertTrue(all('Revenue scale and economic contribution are retained separately' in x['evidence_summary'] for x in xs))
 def test_cts_is_not_invented_when_missing(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); out=run_diagnostic_engine(con,r,c,ing['dataset_version_id']); xs=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='CUS-03'",(r,)).fetchall()
   if not xs: self.assertIn('does not proxy CTS with invented allocations',out['CUS-03']['limitations'])
 def test_retention_language_does_not_overclaim_contractual_grr(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); x=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='CUS-05' AND signal_type='CUSTOMER_RETENTION_SUMMARY'",(r,)).fetchone(); self.assertIsNotNone(x); self.assertIn('not contractual GRR',x['evidence_summary'])
 def test_concentration_is_not_loss_probability(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); x=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='CUS-01' AND signal_type='TOP_CUSTOMER_CONCENTRATION'",(r,)).fetchone(); self.assertIn('not loss probability',x['evidence_summary'])
 def test_pareto_is_descriptive_not_customer_exit_instruction(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); x=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='CUS-07'",(r,)).fetchone(); self.assertIsNotNone(x); self.assertIn('not an instruction to exit',x['evidence_summary'])
 def test_customer_ar_snapshot_does_not_invent_payment_speed(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); ar=Path(d)/'ar.csv'; ar.write_text('invoice_id,customer_id,invoice_date,due_date,original_amount,outstanding_amount\nI1,C001,2026-08-01,2026-08-31,10000,8000\nI2,C002,2026-08-15,2026-09-14,5000,5000\n')
   ingest_accounting_file(con,c,r,ar,'D04_AR',Path(d)/'store'); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); xs=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='CUS-06'",(r,)).fetchall(); self.assertTrue(xs); self.assertTrue(all('does not establish historical payment speed' in x['evidence_summary'] for x in xs))
if __name__=='__main__': unittest.main()
