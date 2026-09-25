import tempfile, unittest, uuid
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import ingest_northstar
from profit_doctor.trust.engine import run_trust_layer
from profit_doctor.diagnostic.engine import run_diagnostic_engine

class ProductExpansion(unittest.TestCase):
 def setup_ns(self,d):
  root=Path(__file__).resolve().parent/'fixtures'/'northstar'; con=connect(Path(d)/'x.db'); c='c_'+uuid.uuid4().hex
  con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Product Test','GBP','PRODUCT_DISTRIBUTION','2026-09-24T00:00:00+00:00')); r='r_'+uuid.uuid4().hex
  con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'BASELINE','2026-09-24T00:00:00+00:00',None,'RUNNING',None,r,'1.7.0')); con.commit(); ing=ingest_northstar(con,c,r,root,Path(d)/'store'); run_trust_layer(con,r,c,ing['dataset_version_id']); return con,c,r,ing
 def test_complete_product_module(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); out=run_diagnostic_engine(con,r,c,ing['dataset_version_id']); self.assertTrue(all(f'PROD-0{i}' in out for i in range(1,6)))
 def test_profitability_separates_scale_from_economics(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); xs=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='PROD-01'",(r,)).fetchall(); self.assertTrue(xs); self.assertTrue(all('Revenue scale and economic contribution are retained separately' in x['evidence_summary'] for x in xs))
 def test_mix_does_not_claim_cause_or_desirability(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); xs=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='PROD-02'",(r,)).fetchall(); self.assertTrue(all('not evidence of why' in x['evidence_summary'] for x in xs))
 def test_growth_does_not_become_opportunity(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); xs=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='PROD-03'",(r,)).fetchall(); self.assertTrue(xs); self.assertTrue(all('does not establish cause' in x['evidence_summary'] and 'recoverable opportunity' in x['evidence_summary'] for x in xs))
 def test_long_tail_is_not_exit_instruction(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); x=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='PROD-04'",(r,)).fetchone(); self.assertIsNotNone(x); self.assertIn('not evidence that an item should be removed',x['evidence_summary'])
 def test_whitespace_is_not_monetised_as_forecast_or_opportunity(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); xs=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='PROD-05'",(r,)).fetchall();
   for x in xs:
    t=x['evidence_summary'].lower(); self.assertIn('theoretical whitespace only',t); self.assertIn('no addressability',t); self.assertIn('opportunity value',t)
if __name__=='__main__': unittest.main()
