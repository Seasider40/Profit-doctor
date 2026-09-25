import tempfile,unittest,uuid
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.management.governance import *

def t(): return '2026-09-25T15:00:00+00:00'
def setup(d):
 c=connect(Path(d)/'x.db');
 for cl in ('A','B'): c.execute('INSERT INTO client VALUES (?,?,?,?,?)',(cl,'Same Name Ltd','GBP','MANUFACTURING',t()))
 for cl in ('A','B'): c.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',('run_'+cl,cl,'ADVISORY',t(),None,'RUNNING',None,None,'2.32'))
 c.commit(); return c
class T(unittest.TestCase):
 def test_run_collision_isolation(self):
  with tempfile.TemporaryDirectory() as d:
   c=setup(d); self.assertTrue(assert_run_owned(c,'A','run_A'))
   with self.assertRaises(PermissionError): assert_run_owned(c,'A','run_B')
 def test_identical_account_codes_do_not_cross(self):
  with tempfile.TemporaryDirectory() as d:
   c=setup(d)
   for cl in ('A','B'): c.execute('INSERT INTO account VALUES (?,?,?,?,?)',(cl+'1',cl,'1100','Trade Receivables','ASSET'))
   c.commit(); self.assertEqual(len(scoped_rows(c,'A','account','account_code=?',('1100',))),1)
 def test_same_story_key_allowed_across_clients(self):
  with tempfile.TemporaryDirectory() as d:
   c=setup(d)
   for cl in ('A','B'): c.execute('INSERT INTO economic_story VALUES (?,?,?,?,?,?,?,?,?,?)',(cl+'s',cl,'MARGIN','PERFORMANCE','Margin','OPEN','run_'+cl,'run_'+cl,t(),t()))
   c.commit(); self.assertEqual(scoped_rows(c,'A','economic_story','story_key=?',('MARGIN',))[0]['economic_story_id'],'As')
 def test_cross_client_opportunity_relationship_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   c=setup(d)
   for cl in ('A','B'):
    c.execute('INSERT INTO finding VALUES (?,?,?,?,?,?,?,?,?)',(cl+'f',cl,'OPPORTUNITY','x','OPEN','run_'+cl,'run_'+cl,t(),t()))
   c.commit()
   with self.assertRaises(PermissionError): assert_same_client_relationship(c,'A','finding','finding_id','Af','finding','finding_id','Bf')
 def test_revision_history_tenant_scoped(self):
  with tempfile.TemporaryDirectory() as d:
   c=setup(d); from profit_doctor.management.restatement import register_revision
   register_revision(c,'A','run_A','pnl',{'x':1},'x');register_revision(c,'B','run_B','pnl',{'x':2},'x'); self.assertEqual(len(scoped_rows(c,'A','source_revision')),1)
 def test_archive_only_affects_target_client(self):
  with tempfile.TemporaryDirectory() as d:
   c=setup(d);set_archive_state(c,'A','ARCHIVED')
   with self.assertRaises(PermissionError): assert_client_active(c,'A')
   self.assertTrue(assert_client_active(c,'B'))
 def test_block_is_audited(self):
  with tempfile.TemporaryDirectory() as d:
   c=setup(d)
   with self.assertRaises(PermissionError): assert_run_owned(c,'A','run_B')
   self.assertEqual(governance_summary(c,'A')['blocked_events'],1)
 def test_unscoped_table_refused(self):
  with tempfile.TemporaryDirectory() as d:
   c=setup(d)
   with self.assertRaisesRegex(ValueError,'NOT_TENANT_SCOPED'): scoped_rows(c,'A','diagnostic_test')
if __name__=='__main__': unittest.main()
