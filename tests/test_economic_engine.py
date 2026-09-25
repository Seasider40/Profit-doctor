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
ROOT=Path(__file__).resolve().parent/'fixtures'/'northstar'
def now(): return '2026-09-24T00:00:00+00:00'
def setup(d):
 con=connect(Path(d)/'x.db'); c='c_'+uuid.uuid4().hex; r='r_'+uuid.uuid4().hex
 con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Northstar','GBP','PRODUCT_DISTRIBUTION',now())); con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'BASELINE',now(),None,'RUNNING',None,r,'1.1.0')); con.commit()
 ing=ingest_northstar(con,c,r,ROOT,Path(d)/'store'); run_trust_layer(con,r,c,ing['dataset_version_id']); run_primitive_engine(con,r,c,ing['dataset_version_id']); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); run_reasoning_engine(con,r,c); return con,c,r
def manual_candidate(con,c,r,theoretical='10000'):
 story='story_'+uuid.uuid4().hex; finding=con.execute('SELECT finding_id FROM finding WHERE client_id=? LIMIT 1',(c,)).fetchone()['finding_id']; t=now()
 con.execute('INSERT INTO economic_story VALUES (?,?,?,?,?,?,?,?,?,?)',(story,c,'MANUAL_TEST_'+uuid.uuid4().hex,'PERFORMANCE','Test story','OPEN',r,r,t,t))
 cid='oc_'+uuid.uuid4().hex; con.execute('INSERT INTO opportunity_candidate VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(cid,r,c,story,finding,None,'RECOVER','B1_RECURRING_PROFIT_IMPROVEMENT',None,theoretical,None,None,'GBP','CONDITIONAL','REQUIRES_ECONOMIC_RESOLUTION','Test candidate',t)); con.commit(); return cid
def support(con,cid,mechanism):
 record_mechanism_evidence(con,cid,mechanism,'MANAGEMENT_VALIDATED','Supported test mechanism evidence','Addressability validated','Recovery basis validated','HIGH')
class EconomicEngineTests(unittest.TestCase):
 def test_findings_resolve_to_stories_without_auto_opportunities(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); out=run_economic_engine(con,r,c); self.assertGreater(out['stories'],0); self.assertGreater(out['candidates'],0); self.assertEqual(out['opportunities'],0); self.assertEqual(con.execute('SELECT count(*) n FROM opportunity WHERE run_id=?',(r,)).fetchone()['n'],0)
 def test_positive_revenue_movement_is_not_mislabelled_as_negative_impact(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); run_economic_engine(con,r,c); s=con.execute("SELECT variance_value FROM signal WHERE run_id=? AND signal_type='COMPARABLE_REVENUE_CHANGE' LIMIT 1",(r,)).fetchone(); self.assertGreater(D(s['variance_value']),0); self.assertEqual(con.execute("SELECT count(*) n FROM economic_impact WHERE run_id=? AND impact_type='OBSERVED_REVENUE_DETERIORATION'",(r,)).fetchone()['n'],0)
 def test_concentration_creates_exposure_without_expected_loss(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); run_economic_engine(con,r,c); x=con.execute("SELECT * FROM economic_exposure WHERE run_id=? AND exposure_type='CUSTOMER_DEPENDENCY' LIMIT 1",(r,)).fetchone(); self.assertIsNotNone(x); self.assertIsNone(x['amount']); self.assertIn('probability of loss is not inferred',x['evidence_basis'])
 def test_concentration_candidate_has_no_invented_money(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); run_economic_engine(con,r,c); x=con.execute("SELECT * FROM opportunity_candidate WHERE run_id=? AND benefit_type='B6_RISK_MITIGATION' LIMIT 1",(r,)).fetchone(); self.assertIsNotNone(x); self.assertIsNone(x['theoretical_amount']); self.assertIsNone(x['addressable_amount']); self.assertIsNone(x['expected_amount'])
 def test_direct_qualification_cannot_bypass_mechanism_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); cid=manual_candidate(con,c,r)
   with self.assertRaisesRegex(ValueError,'Supported mechanism evidence is required'):
    qualify_opportunity_candidate(con,cid,'NO-EVIDENCE','10000','6000','3000','6000','Narrative alone is insufficient')
   con.close()
 def test_qualification_requires_expected_not_above_addressable(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); cid=manual_candidate(con,c,r); support(con,cid,'MECH-1')
   with self.assertRaises(ValueError): qualify_opportunity_candidate(con,cid,'MECH-1','10000','5000','5001','6000','Management-validated recovery mechanism')
 def test_recovery_envelope_caps_opportunity(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); cid=manual_candidate(con,c,r); support(con,cid,'MECH-1')
   with self.assertRaises(ValueError): qualify_opportunity_candidate(con,cid,'MECH-1','10000','6000','4000','5000','Validated recovery envelope')
 def test_supported_qualification_creates_one_opportunity_and_preserves_funnel(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); cid=manual_candidate(con,c,r); support(con,cid,'MECH-VALIDATED'); oid=qualify_opportunity_candidate(con,cid,'MECH-VALIDATED','10000','6000','3000','6000','Validated management recovery plan and supported baseline')
   o=con.execute('SELECT * FROM opportunity WHERE opportunity_id=?',(oid,)).fetchone(); self.assertEqual(D(o['theoretical_amount']),D('10000')); self.assertEqual(D(o['addressable_amount']),D('6000')); self.assertEqual(D(o['expected_amount']),D('3000'))


class RelationshipDedupHardeningTests(unittest.TestCase):
 def test_reverse_symmetric_relationship_is_rejected(self):
  from profit_doctor.economic.engine import relate_opportunities
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d)
   run_economic_engine(con,r,c)
   c1=manual_candidate(con,c,r); support(con,c1,'M1'); o1=qualify_opportunity_candidate(con,c1,'M1','100','80','50','80','e1')
   c2=manual_candidate(con,c,r); support(con,c2,'M2'); o2=qualify_opportunity_candidate(con,c2,'M2','100','80','50','80','e2')
   relate_opportunities(con,o1,o2,'OVERLAPPING','evidence','10')
   with self.assertRaisesRegex(ValueError,'Duplicate symmetric'):
    relate_opportunities(con,o2,o1,'OVERLAPPING','same relationship reversed','10')
   con.close()

if __name__=='__main__': unittest.main()

class OpportunityRelationshipTests(unittest.TestCase):
 def test_overlapping_opportunities_are_not_fully_additive(self):
  from profit_doctor.economic.engine import relate_opportunities,portfolio_expected_value
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); c1=manual_candidate(con,c,r,'10000'); support(con,c1,'M1'); o1=qualify_opportunity_candidate(con,c1,'M1','10000','6000','3000','6000','Evidence 1'); c2=manual_candidate(con,c,r,'8000'); support(con,c2,'M2'); o2=qualify_opportunity_candidate(con,c2,'M2','8000','5000','2500','5000','Evidence 2'); relate_opportunities(con,o1,o2,'OVERLAPPING','Same underlying recovery economics','1500'); p=portfolio_expected_value(con,r,c); self.assertEqual(p['gross_expected'],D('5500')); self.assertEqual(p['portfolio_expected'],D('4000'))
 def test_mutually_exclusive_opportunities_use_only_larger_expected_value(self):
  from profit_doctor.economic.engine import relate_opportunities,portfolio_expected_value
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); c1=manual_candidate(con,c,r,'10000'); support(con,c1,'M1'); o1=qualify_opportunity_candidate(con,c1,'M1','10000','6000','3000','6000','Evidence 1'); c2=manual_candidate(con,c,r,'8000'); support(con,c2,'M2'); o2=qualify_opportunity_candidate(con,c2,'M2','8000','5000','2500','5000','Evidence 2'); relate_opportunities(con,o1,o2,'MUTUALLY_EXCLUSIVE','Choose one commercial route'); p=portfolio_expected_value(con,r,c); self.assertEqual(p['portfolio_expected'],D('3000'))
