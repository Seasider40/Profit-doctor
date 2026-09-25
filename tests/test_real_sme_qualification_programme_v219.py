import unittest
from qualification.real_sme.programme import CASES,BUSINESS_MODELS,GATES,RELEASE_RULES,validate_programme
class RealSMEProgramme(unittest.TestCase):
 def test_matrix_contract(self): self.assertTrue(validate_programme())
 def test_all_business_models_covered(self): self.assertEqual(set(BUSINESS_MODELS),{c.business_model for c in CASES})
 def test_fail_closed_release_rules(self):
  for k in ('material_numeric_error','unsupported_opportunity_value','cross_client_contamination','double_counted_benefit','unsupported_causal_claim','silent_material_data_repair','missing_material_limitation'):
   self.assertEqual(RELEASE_RULES[k],'FAIL')
 def test_management_and_fd_gates_exist(self):
  self.assertIn('MANAGEMENT_USEFULNESS',GATES); self.assertIn('FD_REVIEW_AGREEMENT',GATES)
if __name__=='__main__': unittest.main()
