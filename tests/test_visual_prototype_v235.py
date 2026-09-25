import json,re,unittest
from pathlib import Path
class TestVisualPrototypeV235(unittest.TestCase):
 def setUp(self):
  self.html=Path('prototype/v235/index.html').read_text(); self.data=json.loads(Path('prototype/v235/scenario2_product_view.json').read_text())
 def test_required_product_surfaces_exist(self):
  for x in ('Business Health Check','Management attention','Profit & Cash Opportunity Register','Diagnostic coverage','Financial integrity & controls'): self.assertIn(x,self.html)
 def test_scenario2_owner_view_is_corrected(self):
  k={x['label']:x['value'] for x in self.data['executive_health_check']['kpis']}
  self.assertEqual(float(k['Available cash']),95000); self.assertEqual(float(k['Revenue']),15000000); self.assertEqual(len(self.data['management_attention']),5)
 def test_no_additive_profit_cash_total(self):
  self.assertIsNone(self.data['opportunity_register']['portfolio_headline']['combined_total']); self.assertIn('non-additive',self.data['opportunity_register']['portfolio_headline']['rule'])
 def test_unavailable_diagnostics_are_visible_in_payload(self):
  self.assertGreater(len(self.data['performance_diagnostics']['unavailable']),0)
if __name__=='__main__':unittest.main()
