import tempfile, unittest, uuid
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import ingest_northstar
from profit_doctor.trust.engine import run_trust_layer
from profit_doctor.diagnostic.engine import run_diagnostic_engine

class PricingExpansion(unittest.TestCase):
 def setup_ns(self,d):
  root=Path(__file__).resolve().parent/'fixtures'/'northstar'; con=connect(Path(d)/'x.db'); c='c_'+uuid.uuid4().hex
  con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Pricing Test','GBP','PRODUCT_DISTRIBUTION','2026-09-24T00:00:00+00:00')); r='r_'+uuid.uuid4().hex
  con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'BASELINE','2026-09-24T00:00:00+00:00',None,'RUNNING',None,r,'1.8.0')); con.commit(); ing=ingest_northstar(con,c,r,root,Path(d)/'store'); run_trust_layer(con,r,c,ing['dataset_version_id']); return con,c,r,ing
 def test_complete_pricing_module(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); out=run_diagnostic_engine(con,r,c,ing['dataset_version_id']); self.assertTrue(all(f'PRI-0{i}' in out for i in range(1,6)))
 def test_realised_price_movement_does_not_claim_cause(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); xs=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='PRI-01'",(r,)).fetchall();
   for x in xs: self.assertIn('not proof of list-price action',x['evidence_summary'])
 def test_dispersion_is_not_automatic_leakage(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); xs=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='PRI-02'",(r,)).fetchall(); self.assertTrue(xs)
   self.assertTrue(all('not automatically leakage' in x['evidence_summary'] for x in xs))
 def test_below_reference_price_does_not_become_recoverable_opportunity(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); out=run_diagnostic_engine(con,r,c,ing['dataset_version_id']); xs=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='PRI-03'",(r,)).fetchall();
   for x in xs:
    t=x['evidence_summary'].lower(); self.assertIn('does not establish',t); self.assertIn('recoverability',t); self.assertIn('d14',t)
   self.assertIn('D14',out['PRI-03']['limitations'])
 def test_price_increase_effectiveness_refuses_campaign_claim_without_d14(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); out=run_diagnostic_engine(con,r,c,ing['dataset_version_id']); xs=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='PRI-04'",(r,)).fetchall(); self.assertTrue(xs)
   self.assertIn('not a measure of planned price-increase effectiveness',xs[0]['evidence_summary']); self.assertIn('requires D14',out['PRI-04']['limitations'])
 def test_pricing_candidates_are_not_addressable_or_expected_value(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); xs=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='PRI-05'",(r,)).fetchall();
   for x in xs:
    t=x['evidence_summary'].lower(); self.assertIn('investigation candidates only',t); self.assertIn('addressable',t); self.assertIn('expected opportunity',t)
if __name__=='__main__': unittest.main()
