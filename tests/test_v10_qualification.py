import unittest,tempfile,uuid
from tests.test_management_benefit_engine import setup
from profit_doctor.management.engine import record_decision,create_action,update_action_progress,record_realised_benefit,verify_benefit,assess_retention,relate_benefits,realised_portfolio_value

class QualificationIntegrityTests(unittest.TestCase):
 def _completed(self,d):
  con,c,r,o=setup(d); dec=record_decision(con,r,c,o,'Proceed','Approved'); a=create_action(con,r,c,dec,'Implement'); update_action_progress(con,a,r,'COMPLETED'); return con,c,r,o,a
 def test_realised_benefit_rejects_cross_run_relabel(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,o,a=self._completed(d); r2='r_'+uuid.uuid4().hex
   con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r2,c,'BASELINE','2026-09-25T00:00:00+00:00',None,'RUNNING',None,r2,'1.0')); con.commit()
   with self.assertRaises(ValueError): record_realised_benefit(con,r2,c,o,a,'1000','attempted cross-run relabel')
 def test_verify_and_retention_reject_wrong_run(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,o,a=self._completed(d); b=record_realised_benefit(con,r,c,o,a,'1000','evidence'); wrong='wrong_run'
   with self.assertRaises(ValueError): verify_benefit(con,b,wrong,'900','wrong run')
   with self.assertRaises(ValueError): assess_retention(con,b,wrong,'900','wrong run')
 def test_reverse_cash_manifestation_relationship_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r,o,a=self._completed(d); b1=record_realised_benefit(con,r,c,o,a,'1000','profit'); b2=record_realised_benefit(con,r,c,o,a,'1000','cash')
   relate_benefits(con,r,c,b1,b2,'CASH_MANIFESTATION','same economics')
   with self.assertRaises(ValueError): relate_benefits(con,r,c,b2,b1,'CASH_MANIFESTATION','reverse duplicate')
   self.assertEqual(str(realised_portfolio_value(con,c)['portfolio_realised']),'1000')
if __name__=='__main__': unittest.main()
