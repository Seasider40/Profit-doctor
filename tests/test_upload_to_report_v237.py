import json, os, tempfile, unittest
from pathlib import Path
from profit_doctor.product_demo import run_upload_to_report
class UploadToReportV237(unittest.TestCase):
 def setUp(self): self.src=os.environ.get('PD_UWB2','/mnt/data/v237/scenario2.xlsx')
 def test_full_upload_to_product_outputs(self):
  with tempfile.TemporaryDirectory() as td:
   m=run_upload_to_report(self.src,td,'V237_CLIENT'); r=json.loads((Path(td)/'review.json').read_text())
   self.assertEqual(m['demo_version'],'UDR-2.37'); self.assertEqual(r['client_id'],'V237_CLIENT'); self.assertTrue(m['outputs']['priority_details']); self.assertTrue(m['outputs']['diagnostic_details'])
   self.assertEqual(r['opportunity_register']['portfolio_headline']['combined_total'],None)
 def test_source_is_hashed_and_preserved(self):
  with tempfile.TemporaryDirectory() as td:
   m=run_upload_to_report(self.src,td); self.assertEqual(len(m['source']['sha256']),64); self.assertTrue((Path(td)/'uploaded_source.xlsx').exists())
 def test_scenario2_control_failures_survive_to_review(self):
  with tempfile.TemporaryDirectory() as td:
   run_upload_to_report(self.src,td); r=json.loads((Path(td)/'review.json').read_text()); self.assertGreaterEqual(r['executive_health_check']['control_failures'],4)
 def test_no_unsupported_expected_opportunity_is_created(self):
  with tempfile.TemporaryDirectory() as td:
   run_upload_to_report(self.src,td); r=json.loads((Path(td)/'review.json').read_text()); self.assertTrue(all(x['expected'] is None for x in r['opportunity_register']['items']))
 def test_priority_drilldown_files_are_scoped(self):
  with tempfile.TemporaryDirectory() as td:
   m=run_upload_to_report(self.src,td,'ONLY_ME')
   for fn in m['outputs']['priority_details']:
    x=json.loads((Path(td)/fn).read_text()); self.assertEqual(x['client_id'],'ONLY_ME'); self.assertEqual(x['run_id'],m['run_id'])
if __name__=='__main__': unittest.main()
