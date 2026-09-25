import json,os,sqlite3,tempfile,unittest
from pydantic import ValidationError
from profit_doctor.intake.bridge import execute_unknown_workbook
from profit_doctor.api import API_VERSION,get_product_view,get_product_view_json
from profit_doctor.api.view_models import ProductView

class TestProductViewModelV234(unittest.TestCase):
 def setUp(self):
  self.s1=os.environ.get('PD_UWB1','/mnt/data/v227/scenario1.xlsx'); self.s2=os.environ.get('PD_UWB2','/mnt/data/v227/scenario2.xlsx')
 def run_case(self,p):
  f=tempfile.NamedTemporaryFile(suffix='.db',delete=False); f.close(); r=execute_unknown_workbook(p,f.name); c=sqlite3.connect(f.name); c.row_factory=sqlite3.Row; client=c.execute('select client_id from engine_run where run_id=?',(r['run_id'],)).fetchone()['client_id']; return r,c,client
 def test_scenario2_validates_as_typed_product_view(self):
  r,c,client=self.run_case(self.s2); v=get_product_view(c,r['run_id'],client)
  self.assertEqual(v.api_version,API_VERSION); self.assertGreaterEqual(len(v.management_attention),3); self.assertLessEqual(len(v.management_attention),7); c.close()
 def test_json_payload_is_serializable_and_stable(self):
  r,c,client=self.run_case(self.s1); p=get_product_view_json(c,r['run_id'],client); json.dumps(p)
  self.assertEqual(p['api_version'],'PVM-2.34'); self.assertEqual(p['run_id'],r['run_id']); self.assertIsNone(p['opportunity_register']['portfolio_headline']['combined_total']); c.close()
 def test_ui_contract_preserves_profit_cash_non_additivity(self):
  r,c,client=self.run_case(self.s2); p=get_product_view_json(c,r['run_id'],client)
  self.assertIsNone(p['opportunity_register']['portfolio_headline']['combined_total']); self.assertIn('non-additive',p['opportunity_register']['portfolio_headline']['rule']); c.close()
 def test_wrong_client_fails_closed_at_api_boundary(self):
  r,c,client=self.run_case(self.s2)
  with self.assertRaises(ValueError): get_product_view(c,r['run_id'],'other-client')
  c.close()
 def test_schema_rejects_unknown_frontend_fields(self):
  r,c,client=self.run_case(self.s1); p=get_product_view_json(c,r['run_id'],client); p['executive_health_check']['invented_score']=92
  with self.assertRaises(ValidationError): ProductView.model_validate(p)
  c.close()
 def test_diagnostics_are_explicit_not_silently_dropped(self):
  r,c,client=self.run_case(self.s2); p=get_product_view_json(c,r['run_id'],client); d=p['performance_diagnostics']
  self.assertEqual(len(d['completed'])+len(d['unavailable']),56); self.assertTrue(len(d['unavailable'])>0); c.close()
if __name__=='__main__': unittest.main()
