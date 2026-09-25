import tempfile, unittest
from datetime import datetime, timezone
from profit_doctor.core.db import connect
from profit_doctor.diagnostic.engine import seed_registry, risk_control_diagnostics

def now(): return datetime.now(timezone.utc).isoformat()
class RiskControlTests(unittest.TestCase):
 def setUp(self):
  self.f=tempfile.NamedTemporaryFile(suffix='.db',delete=False); self.f.close(); self.c=connect(self.f.name); self.client='c'; self.run='r'
  self.c.execute('INSERT INTO client VALUES (?,?,?,?,?)',(self.client,'RiskCo','GBP','DISTRIBUTION',now())); self.c.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(self.run,self.client,'TEST',now(),None,'RUNNING',None,None,'2.3')); seed_registry(self.c)
 def tearDown(self): self.c.close()
 def test_registry_reaches_56(self):
  ids={r['test_id'] for r in self.c.execute('SELECT test_id FROM test_registry')}; self.assertEqual(len(ids),56); self.assertTrue({f'RISK-0{i}' for i in range(1,5)}.issubset(ids))
 def test_integrity_exception_not_audit_opinion(self):
  self.c.execute('INSERT INTO financial_integrity VALUES (?,?,?,?,?,?,?,?)',('i1',self.run,self.client,'D03_TB_GL','MATERIALLY_CONSTRAINED','TB does not balance','Investigate',now())); self.c.commit(); risk_control_diagnostics(self.c,self.run,self.client)
  s=self.c.execute("SELECT * FROM signal WHERE test_id='RISK-01'").fetchone(); self.assertIn('not an audit opinion',s['evidence_summary']); self.assertIn('not',s['evidence_summary'])
 def test_exception_does_not_imply_fraud_or_loss(self):
  self.c.execute('INSERT INTO control_exception VALUES (?,?,?,?,?,?,?,?,?,?)',('x1',self.client,'2026-09-01','AP','DUPLICATE_LOOKING','Two invoices share amount/reference','25000','dup1','AP review','OPEN')); self.c.commit(); risk_control_diagnostics(self.c,self.run,self.client)
  s=self.c.execute("SELECT * FROM signal WHERE test_id='RISK-02' AND signal_type='CONTROL_PROCESS_EXCEPTION'").fetchone(); self.assertIn('does not establish error, misconduct, fraud or financial loss',s['evidence_summary'])
 def test_exposure_not_expected_loss(self):
  self.c.execute('INSERT INTO financial_exposure_evidence VALUES (?,?,?,?,?,?,?,?,?)',('e1',self.client,'2026-09-01','CUSTOMER_DEPENDENCY','Largest customer dependency','500000','18','MONITOR','contract/customer evidence')); self.c.commit(); risk_control_diagnostics(self.c,self.run,self.client)
  s=self.c.execute("SELECT * FROM signal WHERE test_id='RISK-03'").fetchone(); self.assertIn('Exposure is not expected loss',s['evidence_summary']); self.assertIn('no probability',s['evidence_summary'])
 def test_governance_is_proportionate_and_no_expected_loss(self):
  self.c.execute('INSERT INTO financial_exposure_evidence VALUES (?,?,?,?,?,?,?,?,?)',('e1',self.client,'2026-09-01','SUPPLIER_DEPENDENCY','Single source component','900000','35','NONE','supplier contract')); self.c.commit(); risk_control_diagnostics(self.c,self.run,self.client)
  g=self.c.execute('SELECT * FROM governance_action_candidate').fetchone(); self.assertIsNotNone(g); self.assertIsNone(g['expected_loss']); self.assertIn('minimum effective governance',g['proportionality_basis'])
 def test_no_evidence_refuses_risk03_but_risk02_can_report_no_exception(self):
  o=risk_control_diagnostics(self.c,self.run,self.client); x=self.c.execute("SELECT * FROM test_execution WHERE test_id='RISK-03' ORDER BY started_at DESC LIMIT 1").fetchone(); self.assertEqual(x['execution_status'],'NOT_RUN')
 def test_client_isolation(self):
  self.c.execute('INSERT INTO client VALUES (?,?,?,?,?)',('other','Other','GBP','SERVICES',now())); self.c.execute('INSERT INTO financial_exposure_evidence VALUES (?,?,?,?,?,?,?,?,?)',('e2','other','2026-09-01','LIQUIDITY','Other client exposure','999999','90','NONE','other')); self.c.commit(); risk_control_diagnostics(self.c,self.run,self.client); self.assertEqual(self.c.execute("SELECT COUNT(*) n FROM signal WHERE run_id=? AND test_id='RISK-03'",(self.run,)).fetchone()['n'],0)
if __name__=='__main__': unittest.main()
