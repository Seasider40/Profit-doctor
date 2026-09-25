import tempfile, unittest, uuid
from decimal import Decimal
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import ingest_northstar
from profit_doctor.trust.engine import run_trust_layer
from profit_doctor.diagnostic.engine import run_diagnostic_engine
from profit_doctor.revenue_semantics import assign_product_revenue_type

class RevenueExpansion(unittest.TestCase):
 def setup_ns(self,d):
  root=Path(__file__).resolve().parent/'fixtures'/'northstar'
  con=connect(Path(d)/'x.db'); c='c_'+uuid.uuid4().hex; con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Revenue Test','GBP','PRODUCT_DISTRIBUTION','2026-09-24T00:00:00+00:00')); r='r_'+uuid.uuid4().hex; con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'BASELINE','2026-09-24T00:00:00+00:00',None,'RUNNING',None,r,'1.4.0')); con.commit(); ing=ingest_northstar(con,c,r,root,Path(d)/'store'); run_trust_layer(con,r,c,ing['dataset_version_id']); return con,c,r,ing
 def test_registry_contains_complete_revenue_module(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); out=run_diagnostic_engine(con,r,c,ing['dataset_version_id']); self.assertTrue(all(x in out for x in ['REV-01','REV-02','REV-03','REV-04','REV-05','REV-06']))
 def test_pvm_reconciles_exactly(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); out=run_diagnostic_engine(con,r,c,ing['dataset_version_id']); self.assertEqual(out['REV-04']['status'],'COMPLETED'); s=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='REV-04' AND signal_type='PVM_RECONCILIATION'",(r,)).fetchone(); self.assertEqual(Decimal(s['variance_value']),Decimal('0'))
 def test_seasonality_is_descriptive_not_causal(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); out=run_diagnostic_engine(con,r,c,ing['dataset_version_id']); self.assertEqual(out['REV-05']['status'],'COMPLETED'); txt=' '.join(x['evidence_summary'] for x in con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='REV-05'",(r,))); self.assertNotIn('caused by',txt.lower())
 def test_volatility_does_not_claim_forecast_accuracy(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); out=run_diagnostic_engine(con,r,c,ing['dataset_version_id']); self.assertEqual(out['REV-06']['status'],'COMPLETED'); s=con.execute("SELECT * FROM signal WHERE run_id=? AND test_id='REV-06' AND signal_type='MONTHLY_REVENUE_VOLATILITY'",(r,)).fetchone(); self.assertIsNotNone(s); self.assertIn('does not equal forecast error',s['evidence_summary'])
 def test_recurring_mix_withheld_when_semantics_unmapped(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,ing=self.setup_ns(d); out=run_diagnostic_engine(con,r,c,ing['dataset_version_id']); self.assertIsNone(con.execute("SELECT 1 FROM signal WHERE run_id=? AND signal_type='EVIDENCED_RECURRING_REVENUE_MIX'",(r,)).fetchone())
if __name__=='__main__': unittest.main()
