import json, tempfile, unittest
from pathlib import Path
from profit_doctor.intake.readiness import build_upload_readiness
from profit_doctor.product_demo import run_upload_to_report
SRC=Path(__file__).resolve().parents[1]/'demo/v237_scenario2/uploaded_source.xlsx'
class UploadReadinessV238(unittest.TestCase):
 def test_readiness_is_explanatory_not_score(self):
  r=build_upload_readiness(SRC)
  self.assertEqual(r['version'],'UIR-2.38'); self.assertNotIn('score',r); self.assertGreater(len(r['sheets']),0)
 def test_scenario2_failed_controls_visible(self):
  r=build_upload_readiness(SRC)
  self.assertGreaterEqual(len(r['failed_controls']),4); self.assertEqual(r['readiness_state'],'ANALYSIS_WITH_CONTROL_LIMITATIONS')
 def test_missing_advanced_data_becomes_request_not_invention(self):
  r=build_upload_readiness(SRC); codes={x['domain'] for x in r['recommended_next_data']}
  self.assertIn('D15_CRM',codes); self.assertIn('D14_PRICING',codes)
 def test_end_to_end_exports_readiness_and_coverage(self):
  with tempfile.TemporaryDirectory() as td:
   m=run_upload_to_report(SRC,td,'V238_CLIENT'); x=json.loads((Path(td)/'upload_readiness.json').read_text())
   self.assertEqual(m['demo_version'],'UDR-2.37'); self.assertEqual(m['outputs']['upload_readiness'],'upload_readiness.json')
   self.assertEqual(x['diagnostic_coverage']['total'],56); self.assertGreater(x['diagnostic_coverage']['completed'],0)
 def test_no_failed_control_is_mislabeled_as_opportunity(self):
  with tempfile.TemporaryDirectory() as td:
   run_upload_to_report(SRC,td); x=json.loads((Path(td)/'upload_readiness.json').read_text())
   self.assertTrue(all('opportunity' not in c['status'].lower() for c in x['controls']))
if __name__=='__main__': unittest.main()
