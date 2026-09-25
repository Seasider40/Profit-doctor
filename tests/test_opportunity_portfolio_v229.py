import tempfile,uuid,unittest
from decimal import Decimal as D
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.economic.engine import record_mechanism_evidence,qualify_opportunity_candidate,relate_opportunities
from profit_doctor.economic.portfolio import portfolio_economics,create_portfolio_envelope

def now(): return '2026-09-25T12:00:00+00:00'
def setup(d):
 c=connect(Path(d)/'x.db'); client='c_'+uuid.uuid4().hex; run='r_'+uuid.uuid4().hex; t=now()
 c.execute('INSERT INTO client VALUES (?,?,?,?,?)',(client,'Opportunity Stress Ltd','GBP','MANUFACTURING',t)); c.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(run,client,'QUALIFICATION',t,None,'RUNNING',None,run,'2.29.0'))
 f='f_'+uuid.uuid4().hex; c.execute('INSERT INTO finding VALUES (?,?,?,?,?,?,?,?,?)',(f,client,'OPPORTUNITY','Stress finding','OPEN',run,run,t,t)); c.commit(); return c,client,run,f

def opp(c,client,run,f,name,btype,theoretical,addressable,expected,envelope):
 t=now(); story='s_'+uuid.uuid4().hex; c.execute('INSERT INTO economic_story VALUES (?,?,?,?,?,?,?,?,?,?)',(story,client,name,'PERFORMANCE',name,'OPEN',run,run,t,t)); cid='oc_'+uuid.uuid4().hex
 c.execute('INSERT INTO opportunity_candidate VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(cid,run,client,story,f,None,'IMPROVE',btype,None,str(theoretical),None,None,'GBP','IMMEDIATE','REQUIRES_ECONOMIC_RESOLUTION','qualification',t)); c.commit()
 mech='M_'+name; record_mechanism_evidence(c,cid,mech,'MANAGEMENT_VALIDATED',name+' mechanism','Addressability evidenced','Recovery evidenced','HIGH')
 return qualify_opportunity_candidate(c,cid,mech,theoretical,addressable,expected,envelope,name+' baseline and envelope')

class TestOpportunityPortfolioV229(unittest.TestCase):
 def test_profit_overlap_reduces_portfolio(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl,r,f=setup(d); p=opp(c,cl,r,f,'pricing','B1_RECURRING_PROFIT_IMPROVEMENT',240000,150000,95000,150000); m=opp(c,cl,r,f,'margin','B1_RECURRING_PROFIT_IMPROVEMENT',180000,120000,80000,120000); relate_opportunities(c,p,m,'OVERLAPPING','Same customer-margin economics',60000); x=portfolio_economics(c,r,cl); self.assertEqual(x['buckets']['RECURRING_PROFIT']['gross_expected'],D('175000')); self.assertEqual(x['buckets']['RECURRING_PROFIT']['portfolio_expected'],D('115000'))
 def test_envelope_caps_three_related_profit_routes(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl,r,f=setup(d); ids=[opp(c,cl,r,f,n,'B1_RECURRING_PROFIT_IMPROVEMENT',200000,120000,90000,120000) for n in ('price','mix','customer')]; create_portfolio_envelope(c,r,cl,'CUSTOMER_MARGIN_POOL','RECURRING_PROFIT',140000,'GBP','Validated common margin recovery pool',ids); x=portfolio_economics(c,r,cl); self.assertEqual(x['buckets']['RECURRING_PROFIT']['gross_expected'],D('270000')); self.assertEqual(x['buckets']['RECURRING_PROFIT']['portfolio_expected'],D('140000'))
 def test_cash_release_is_not_added_to_profit(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl,r,f=setup(d); p=opp(c,cl,r,f,'profit','B1_RECURRING_PROFIT_IMPROVEMENT',150000,100000,70000,100000); cash=opp(c,cl,r,f,'cash','B3_ONE_OFF_CASH_RELEASE',200000,140000,100000,140000); relate_opportunities(c,p,cash,'CASH_MANIFESTATION','Some profit improvement later manifests in cash'); x=portfolio_economics(c,r,cl); self.assertEqual(x['buckets']['RECURRING_PROFIT']['portfolio_expected'],D('70000')); self.assertEqual(x['buckets']['ONE_OFF_CASH']['portfolio_expected'],D('100000')); self.assertIsNone(x['headline_total']); self.assertTrue(x['notes'])
 def test_cross_bucket_overlap_is_refused(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl,r,f=setup(d); p=opp(c,cl,r,f,'profit','B1_RECURRING_PROFIT_IMPROVEMENT',100,80,50,80); cash=opp(c,cl,r,f,'cash','B3_ONE_OFF_CASH_RELEASE',100,80,50,80); relate_opportunities(c,p,cash,'OVERLAPPING','bad semantic relationship',20); 
   with self.assertRaisesRegex(ValueError,'different economic buckets'): portfolio_economics(c,r,cl)
 def test_funnel_guard_expected_cannot_exceed_addressable(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl,r,f=setup(d); t=now(); s='s_'+uuid.uuid4().hex; c.execute('INSERT INTO economic_story VALUES (?,?,?,?,?,?,?,?,?,?)',(s,cl,'guard','PERFORMANCE','guard','OPEN',r,r,t,t)); cid='oc_'+uuid.uuid4().hex; c.execute('INSERT INTO opportunity_candidate VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(cid,r,cl,s,f,None,'IMPROVE','B1_RECURRING_PROFIT_IMPROVEMENT',None,'100',None,None,'GBP','IMMEDIATE','REQUIRES_ECONOMIC_RESOLUTION','x',t)); c.commit(); record_mechanism_evidence(c,cid,'M','VALIDATED','evidence');
   with self.assertRaises(ValueError): qualify_opportunity_candidate(c,cid,'M',100,60,61,80,'evidence')
if __name__=='__main__': unittest.main()
