import json,unittest
from pathlib import Path
class TestVisualPrototypeV236(unittest.TestCase):
 def setUp(self): self.h=Path('prototype/v236/index.html').read_text(); self.d=json.loads(Path('prototype/v236/scenario2_interactive.json').read_text())
 def test_richer_product_surfaces(self):
  for s in ('Executive view','Profit & cash','Diagnostics','Controls & evidence','Management attention','Open diagnostic'): self.assertIn(s,self.h)
 def test_five_priority_drilldowns(self): self.assertEqual(len(self.d['priority_details']),5)
 def test_drilldown_contains_lineage(self):
  p=self.d['priority_details']['FINANCIAL_INTEGRITY']; self.assertGreater(len(p['supporting_evidence']),0); self.assertGreater(len(p['diagnostic_ids']),0); self.assertGreater(len(p['recommended_actions']),0); self.assertGreater(len(p['opportunities']),0)
 def test_no_unsupported_economics(self): self.assertTrue(all(x['expected'] is None for x in self.d['view']['opportunity_register']['items']))
 def test_corrected_cash_survives(self):
  k={x['label']:x['value'] for x in self.d['view']['executive_health_check']['kpis']}; self.assertEqual(float(k['Available cash']),95000)
if __name__=='__main__': unittest.main()
