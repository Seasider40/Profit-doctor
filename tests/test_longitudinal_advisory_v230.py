import tempfile,uuid,unittest
from pathlib import Path
from decimal import Decimal as D
from profit_doctor.core.db import connect
from profit_doctor.management.engine import record_decision,create_action,update_action_progress,record_realised_benefit,verify_benefit,assess_retention
from profit_doctor.management.longitudinal import observe_issue,track_opportunity,register_benefit_claim,longitudinal_summary

def t(): return '2026-09-25T14:00:00+00:00'
def seed(con,client,run,expected='3000'):
 con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(run,client,'ADVISORY',t(),None,'RUNNING',None,run,'2.30.0'))
 f='f_'+uuid.uuid4().hex; s='s_'+uuid.uuid4().hex; o='o_'+uuid.uuid4().hex
 con.execute('INSERT INTO finding VALUES (?,?,?,?,?,?,?,?,?)',(f,client,'OPPORTUNITY','Margin','OPEN',run,run,t(),t()))
 con.execute('INSERT INTO economic_story VALUES (?,?,?,?,?,?,?,?,?,?)',(s,client,'MARGIN_'+run,'PERFORMANCE','Margin','OPEN',run,run,t(),t()))
 con.execute('INSERT INTO economic_baseline VALUES (?,?,?,?,?,?,?,?,?,?,?)',('b_'+uuid.uuid4().hex,run,client,s,'VALIDATED',None,None,'5000','GBP','baseline',t()))
 bid=con.execute('SELECT economic_baseline_id FROM economic_baseline WHERE run_id=? ORDER BY rowid DESC LIMIT 1',(run,)).fetchone()[0]
 con.execute('INSERT INTO opportunity VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(o,run,client,s,f,'M1','IMPROVE','B1_RECURRING_PROFIT_IMPROVEMENT',bid,'10000','6000',expected,'GBP','IMMEDIATE','SUPPORTED',t())); con.commit(); return o

def setup(d):
 con=connect(Path(d)/'x.db'); c='c_'+uuid.uuid4().hex; con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Longitudinal Ltd','GBP','MANUFACTURING',t())); con.commit(); return con,c

class LongitudinalTests(unittest.TestCase):
 def test_issue_resolve_and_reopen(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl=setup(d); r1='r1';r2='r2';r3='r3'; [seed(c,cl,r) for r in (r1,r2,r3)]
   observe_issue(c,cl,r1,'AR_CONTROL','FINANCIAL_INTEGRITY','AR control','OPEN','£100k mismatch',100000)
   observe_issue(c,cl,r2,'AR_CONTROL','FINANCIAL_INTEGRITY','AR control','RESOLVED','reconciled',0)
   observe_issue(c,cl,r3,'AR_CONTROL','FINANCIAL_INTEGRITY','AR control','RECURRED','new £20k mismatch',20000)
   x=longitudinal_summary(c,cl); self.assertEqual(x['open_issues'],1); self.assertEqual(x['reopened_issues'],1)
 def test_claim_cannot_be_counted_twice_across_runs(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl=setup(d); o1=seed(c,cl,'r1','3000'); lid=track_opportunity(c,cl,'r1',o1,'MARGIN_RECOVERY','baseline')
   dec=record_decision(c,'r1',cl,o1,'Proceed','approved'); a=create_action(c,'r1',cl,dec,'price action'); update_action_progress(c,a,'r1','COMPLETED'); b=record_realised_benefit(c,'r1',cl,o1,a,'2000','invoices'); register_benefit_claim(c,cl,lid,b)
   o2=seed(c,cl,'r2','3000'); track_opportunity(c,cl,'r2',o2,'MARGIN_RECOVERY','repeat run')
   with self.assertRaisesRegex(ValueError,'already been claimed'): register_benefit_claim(c,cl,lid,b)
   x=longitudinal_summary(c,cl); self.assertEqual(x['claimed_realised'],D('2000')); self.assertEqual(x['remaining_expected'],D('1000'))
 def test_new_run_expected_is_net_of_prior_claim(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl=setup(d); o1=seed(c,cl,'r1','3000'); lid=track_opportunity(c,cl,'r1',o1,'MARGIN_RECOVERY','baseline'); dec=record_decision(c,'r1',cl,o1,'Proceed','approved'); a=create_action(c,'r1',cl,dec,'act'); update_action_progress(c,a,'r1','COMPLETED'); b=record_realised_benefit(c,'r1',cl,o1,a,'1200','evidence'); register_benefit_claim(c,cl,lid,b)
   o2=seed(c,cl,'r2','2500'); track_opportunity(c,cl,'r2',o2,'MARGIN_RECOVERY','updated economics'); row=c.execute('SELECT * FROM longitudinal_opportunity WHERE longitudinal_opportunity_id=?',(lid,)).fetchone(); self.assertEqual(D(row['remaining_expected_amount']),D('1300'))
 def test_stale_opportunity_has_zero_remaining_expected(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl=setup(d); o=seed(c,cl,'r1','3000'); lid=track_opportunity(c,cl,'r1',o,'MARGIN_RECOVERY','baseline',True,'Pricing evidence expired'); row=c.execute('SELECT * FROM longitudinal_opportunity WHERE longitudinal_opportunity_id=?',(lid,)).fetchone(); self.assertEqual(row['lifecycle_state'],'STALE'); self.assertEqual(D(row['remaining_expected_amount']),D('0'))
 def test_verified_and_retained_benefit_remains_single_claim(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl=setup(d); o=seed(c,cl,'r1','3000'); lid=track_opportunity(c,cl,'r1',o,'MARGIN_RECOVERY','baseline'); dec=record_decision(c,'r1',cl,o,'Proceed','approved'); a=create_action(c,'r1',cl,dec,'act'); update_action_progress(c,a,'r1','COMPLETED'); b=record_realised_benefit(c,'r1',cl,o,a,'2000','evidence'); verify_benefit(c,b,'r1','1900','verification'); assess_retention(c,b,'r1','1700','quarter later','PARTIALLY_RETAINED'); register_benefit_claim(c,cl,lid,b); self.assertEqual(longitudinal_summary(c,cl)['claimed_realised'],D('2000'))
 def test_cross_client_claim_is_refused(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl=setup(d); o=seed(c,cl,'r1'); lid=track_opportunity(c,cl,'r1',o,'MARGIN_RECOVERY','baseline'); dec=record_decision(c,'r1',cl,o,'Proceed','approved'); a=create_action(c,'r1',cl,dec,'act'); update_action_progress(c,a,'r1','COMPLETED'); b=record_realised_benefit(c,'r1',cl,o,a,'1000','evidence'); other='other'; c.execute('INSERT INTO client VALUES (?,?,?,?,?)',(other,'Other','GBP','SERVICES',t())); c.commit();
   with self.assertRaises(ValueError): register_benefit_claim(c,other,lid,b)
if __name__=='__main__': unittest.main()
