import tempfile, unittest, uuid
from pathlib import Path
from decimal import Decimal
from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import ingest_northstar
from profit_doctor.trust.engine import run_trust_layer
from profit_doctor.diagnostic.engine import run_diagnostic_engine
class MarginExpansion(unittest.TestCase):
 def setup_ns(self,d):
  root=Path(__file__).resolve().parent/'fixtures'/'northstar'; con=connect(Path(d)/'x.db'); c='c_'+uuid.uuid4().hex
  con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Margin Test','GBP','PRODUCT_DISTRIBUTION','2026-09-24T00:00:00+00:00')); r='r_'+uuid.uuid4().hex
  con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'BASELINE','2026-09-24T00:00:00+00:00',None,'RUNNING',None,r,'1.5.0')); con.commit(); ing=ingest_northstar(con,c,r,root,Path(d)/'store'); run_trust_layer(con,r,c,ing['dataset_version_id']); return con,c,r,ing
 def test_complete_margin_module(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); out=run_diagnostic_engine(con,r,c,ing['dataset_version_id']); self.assertTrue(all(x in out for x in [f'GM-0{i}' for i in range(1,8)]))
 def test_margin_variance_is_not_opportunity(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); txt=' '.join(x['evidence_summary'] for x in con.execute("SELECT * FROM signal WHERE run_id=? AND test_id IN ('GM-03','GM-04','GM-05')",(r,))); self.assertNotIn('recoverable opportunity.',txt.lower().replace('not automatically recoverable opportunity.',''))
 def test_cost_recovery_never_exceeds_pressure(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']);
   for x in con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='GM-06'",(r,)): self.assertGreaterEqual(Decimal(x['observed_value']),Decimal(x['comparison_value']))
 def test_anomaly_language_is_forensic_not_accusatory(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); run_diagnostic_engine(con,r,c,ing['dataset_version_id']);
   for x in con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='GM-07'",(r,)): self.assertIn('not automatically',x['evidence_summary'].lower())
 def test_gm03_requires_customer_mapping_and_gm04_product_mapping(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); out=run_diagnostic_engine(con,r,c,ing['dataset_version_id']); self.assertNotEqual(out['GM-03']['eligibility'],'UNAVAILABLE'); self.assertNotEqual(out['GM-04']['eligibility'],'UNAVAILABLE')
if __name__=='__main__': unittest.main()
