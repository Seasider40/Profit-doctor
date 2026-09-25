import unittest,tempfile,uuid
from pathlib import Path
from decimal import Decimal as D
from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import ingest_northstar
from profit_doctor.trust.engine import run_trust_layer
from profit_doctor.calc.primitive_engine import run_primitive_engine
from profit_doctor.diagnostic.engine import run_diagnostic_engine
from profit_doctor.reasoning.engine import run_reasoning_engine
from profit_doctor.economic.engine import run_economic_engine,qualify_opportunity_candidate,record_mechanism_evidence
from profit_doctor.management.engine import record_decision,create_action,update_action_progress,record_realised_benefit,verify_benefit,assess_retention,relate_benefits,realised_portfolio_value
ROOT=Path(__file__).resolve().parent/'fixtures'/'northstar'
def now(): return '2026-09-24T00:00:00+00:00'
def setup(d):
 con=connect(Path(d)/'x.db'); c='c_'+uuid.uuid4().hex; r='r_'+uuid.uuid4().hex
 con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Northstar','GBP','PRODUCT_DISTRIBUTION',now())); con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'BASELINE',now(),None,'RUNNING',None,r,'1.2.0')); con.commit()
 ing=ingest_northstar(con,c,r,ROOT,Path(d)/'store'); run_trust_layer(con,r,c,ing['dataset_version_id']); run_primitive_engine(con,r,c,ing['dataset_version_id']); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); run_reasoning_engine(con,r,c); run_economic_engine(con,r,c)
 f=con.execute('SELECT finding_id FROM finding WHERE client_id=? LIMIT 1',(c,)).fetchone()['finding_id']; story='story_'+uuid.uuid4().hex; t=now(); con.execute('INSERT INTO economic_story VALUES (?,?,?,?,?,?,?,?,?,?)',(story,c,'MGMT_'+uuid.uuid4().hex,'PERFORMANCE','Management test','OPEN',r,r,t,t)); cid='oc_'+uuid.uuid4().hex; con.execute('INSERT INTO opportunity_candidate VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(cid,r,c,story,f,None,'IMPROVE','B1_RECURRING_PROFIT_IMPROVEMENT',None,'10000',None,None,'GBP','IMMEDIATE','REQUIRES_ECONOMIC_RESOLUTION','test',t)); con.commit(); record_mechanism_evidence(con,cid,'M1','MANAGEMENT_VALIDATED','Validated management mechanism','Addressability validated','Recovery basis validated','HIGH'); oid=qualify_opportunity_candidate(con,cid,'M1','10000','6000','3000','6000','Validated management plan'); return con,c,r,oid
class ManagementBenefitTests(unittest.TestCase):
 def test_supported_opportunity_to_decision_and_action(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,o=setup(d); dec=record_decision(con,r,c,o,'Proceed','Management approved',owner='FD'); a=create_action(con,r,c,dec,'Implement pricing change',owner='Sales Director'); self.assertEqual(con.execute('SELECT status FROM action WHERE action_id=?',(a,)).fetchone()['status'],'OPEN')
 def test_benefit_cannot_be_claimed_before_action_completion(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,o=setup(d); dec=record_decision(con,r,c,o,'Proceed','Approved'); a=create_action(con,r,c,dec,'Implement')
   with self.assertRaises(ValueError): record_realised_benefit(con,r,c,o,a,'2500','Observed post-action economics')
 def test_realised_benefit_is_net_of_costs_and_does_not_rewrite_expected(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,o=setup(d); dec=record_decision(con,r,c,o,'Proceed','Approved'); a=create_action(con,r,c,dec,'Implement'); update_action_progress(con,a,r,'COMPLETED'); b=record_realised_benefit(con,r,c,o,a,'4000','Invoice evidence','500','100','100'); row=con.execute('SELECT * FROM benefit_leg WHERE benefit_leg_id=?',(b,)).fetchone(); self.assertEqual(D(row['net_amount']),D('3300')); self.assertEqual(D(con.execute('SELECT expected_amount FROM opportunity WHERE opportunity_id=?',(o,)).fetchone()['expected_amount']),D('3000'))
 def test_uncertain_attribution_does_not_become_verified(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,o=setup(d); dec=record_decision(con,r,c,o,'Proceed','Approved'); a=create_action(con,r,c,dec,'Implement'); update_action_progress(con,a,r,'COMPLETED'); b=record_realised_benefit(con,r,c,o,a,'2500','Observed','0','0','0','UNCERTAIN'); status=verify_benefit(con,b,r,'2400','Follow-up evidence','UNCERTAIN'); self.assertEqual(status,'REALISED')
 def test_retention_cannot_exceed_realised_net(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,o=setup(d); dec=record_decision(con,r,c,o,'Proceed','Approved'); a=create_action(con,r,c,dec,'Implement'); update_action_progress(con,a,r,'COMPLETED'); b=record_realised_benefit(con,r,c,o,a,'2500','Observed')
   with self.assertRaises(ValueError): assess_retention(con,b,r,'2501','Later period')
 def test_cash_manifestation_is_not_double_counted(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,o=setup(d); dec=record_decision(con,r,c,o,'Proceed','Approved'); a=create_action(con,r,c,dec,'Implement'); update_action_progress(con,a,r,'COMPLETED'); b1=record_realised_benefit(con,r,c,o,a,'3000','Profit evidence'); b2=record_realised_benefit(con,r,c,o,a,'3000','Cash evidence'); relate_benefits(con,r,c,b1,b2,'CASH_MANIFESTATION','Same profit later converted to cash'); p=realised_portfolio_value(con,c); self.assertEqual(p['gross_realised'],D('6000')); self.assertEqual(p['portfolio_realised'],D('3000'))
 def test_retention_records_persistence_without_inflating_value(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,o=setup(d); dec=record_decision(con,r,c,o,'Proceed','Approved'); a=create_action(con,r,c,dec,'Implement'); update_action_progress(con,a,r,'COMPLETED'); b=record_realised_benefit(con,r,c,o,a,'2500','Observed'); assess_retention(con,b,r,'2000','Three-month persistence','PARTIALLY_RETAINED'); x=con.execute('SELECT * FROM benefit_retention WHERE benefit_leg_id=?',(b,)).fetchone(); self.assertEqual(D(x['retained_amount']),D('2000'))
if __name__=='__main__': unittest.main()
