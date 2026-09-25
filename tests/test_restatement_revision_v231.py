import tempfile,unittest,uuid
from pathlib import Path
from decimal import Decimal as D
from profit_doctor.core.db import connect
from profit_doctor.management.restatement import *
from profit_doctor.management.longitudinal import track_opportunity,register_benefit_claim,longitudinal_summary
from profit_doctor.management.engine import record_decision,create_action,update_action_progress,record_realised_benefit

def t(): return '2026-09-25T14:00:00+00:00'
def setup(d):
 c=connect(Path(d)/'x.db'); cl='c_'+uuid.uuid4().hex; c.execute('INSERT INTO client VALUES (?,?,?,?,?)',(cl,'Revision Ltd','GBP','MANUFACTURING',t())); c.commit(); return c,cl
def seed(con,cl,run,expected='3000'):
 con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(run,cl,'ADVISORY',t(),None,'RUNNING',None,run,'2.31.0'))
 f='f_'+uuid.uuid4().hex;s='s_'+uuid.uuid4().hex;o='o_'+uuid.uuid4().hex;b='b_'+uuid.uuid4().hex
 con.execute('INSERT INTO finding VALUES (?,?,?,?,?,?,?,?,?)',(f,cl,'OPPORTUNITY','Margin','OPEN',run,run,t(),t()))
 con.execute('INSERT INTO economic_story VALUES (?,?,?,?,?,?,?,?,?,?)',(s,cl,'MARGIN_'+run,'PERFORMANCE','Margin','OPEN',run,run,t(),t()))
 con.execute('INSERT INTO economic_baseline VALUES (?,?,?,?,?,?,?,?,?,?,?)',(b,run,cl,s,'VALIDATED',None,None,'5000','GBP','baseline',t()))
 con.execute('INSERT INTO opportunity VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(o,run,cl,s,f,'M1','IMPROVE','B1_RECURRING_PROFIT_IMPROVEMENT',b,'10000','6000',expected,'GBP','IMMEDIATE','SUPPORTED',t()));con.commit();return o

class RevisionTests(unittest.TestCase):
 def test_source_revision_is_immutable_and_versioned(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl=setup(d); seed(c,cl,'r1'); a=register_revision(c,cl,'r1','pnl',{'Jan':100},'initial','2026-01'); b=register_revision(c,cl,'r1','pnl',{'Jan':100},'same','2026-01'); self.assertFalse(b['is_new']); seed(c,cl,'r2'); z=register_revision(c,cl,'r2','pnl',{'Jan':110},'late journal','2026-01'); self.assertEqual(z['revision_number'],2); self.assertEqual(z['revision_type'],'RESTATEMENT')
 def test_duplicate_rows_exact_removed_conflict_refused(self):
  rows=[{'id':'1','v':10},{'id':'1','v':10},{'id':'2','v':20}]; clean,dups=deduplicate_rows(rows,['id']); self.assertEqual(len(clean),2); self.assertEqual(len(dups),1)
  with self.assertRaisesRegex(ValueError,'CONFLICTING_DUPLICATE'): deduplicate_rows([{'id':'1','v':10},{'id':'1','v':11}],['id'])
 def test_missing_periods_detected_not_interpolated(self):
  self.assertEqual(detect_missing_periods(['2026-01','2026-03'],['2026-01','2026-02','2026-03']),['2026-02'])
 def test_mapping_change_and_late_journal_are_audited(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl=setup(d); seed(c,cl,'r1'); record_dirty_exception(c,cl,'r1','customer_master','MAPPING_CHANGE','ACME moved from C01 to C99','ACME','REVIEW_REQUIRED'); record_dirty_exception(c,cl,'r1','tb','LATE_JOURNAL','£25k journal posted to prior month','J123','RESTATEMENT_REQUIRED'); self.assertEqual(restatement_summary(c,cl)['dirty_exceptions'],2)
 def test_restatement_does_not_rewrite_original_baseline_or_prior_claim(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl=setup(d); o=seed(c,cl,'r1','3000'); lid=track_opportunity(c,cl,'r1',o,'MARGIN','baseline'); lock_baseline(c,cl,lid,'margin_base','5000')
   dec=record_decision(c,'r1',cl,o,'Proceed','approved'); a=create_action(c,'r1',cl,dec,'act'); update_action_progress(c,a,'r1','COMPLETED'); leg=record_realised_benefit(c,'r1',cl,o,a,'1200','evidence'); register_benefit_claim(c,cl,lid,leg)
   seed(c,cl,'r2','2500'); rev=register_revision(c,cl,'r2','pnl',{'base':4700},'late journal','2026-01'); x=restate_baseline(c,cl,'r2',lid,'margin_base','4700','late journal',rev['revision_id']); self.assertEqual(x['original_amount'],D('5000')); self.assertEqual(x['current_restated_amount'],D('4700')); self.assertEqual(longitudinal_summary(c,cl)['claimed_realised'],D('1200'))
 def test_revised_expected_nets_prior_claim_after_baseline_restatement(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl=setup(d); o=seed(c,cl,'r1','3000'); lid=track_opportunity(c,cl,'r1',o,'MARGIN','baseline'); lock_baseline(c,cl,lid,'base','5000'); dec=record_decision(c,'r1',cl,o,'Proceed','ok');a=create_action(c,'r1',cl,dec,'act');update_action_progress(c,a,'r1','COMPLETED');leg=record_realised_benefit(c,'r1',cl,o,a,'1200','proof');register_benefit_claim(c,cl,lid,leg)
   o2=seed(c,cl,'r2','2200'); restate_baseline(c,cl,'r2',lid,'base','4800','correction'); track_opportunity(c,cl,'r2',o2,'MARGIN','restated economics'); self.assertEqual(longitudinal_summary(c,cl)['remaining_expected'],D('1000'))
 def test_cross_client_baseline_isolation(self):
  with tempfile.TemporaryDirectory() as d:
   c,cl=setup(d); o=seed(c,cl,'r1'); lid=track_opportunity(c,cl,'r1',o,'MARGIN','base'); lock_baseline(c,cl,lid,'base','5000'); other='other';c.execute('INSERT INTO client VALUES (?,?,?,?,?)',(other,'Other','GBP','SERVICES',t()));c.commit()
   with self.assertRaisesRegex(ValueError,'Baseline must be locked'): restate_baseline(c,other,'rX',lid,'base','1','bad')
if __name__=='__main__':unittest.main()
