import os, unittest
from profit_doctor.intake.workbook import profile_workbook, reconcile_workbook

class TestUnknownWorkbookIntake(unittest.TestCase):
    def setUp(self):
        self.s1=os.environ.get('PD_UWB1','/mnt/data/v223/scenario1.xlsx')
        self.s2=os.environ.get('PD_UWB2','/mnt/data/v223/scenario2.xlsx')
    def test_scenario1_classification(self):
        p=profile_workbook(self.s1); d={x['sheet']:x['domain'] for x in p['sheets']}
        self.assertEqual(d['Customers'],'D04_AR'); self.assertEqual(d['Staff Costs'],'D11_WORKFORCE'); self.assertEqual(d['Capacity'],'D16_OPERATIONS'); self.assertEqual(d['Trial Balance'],'D03_TB_GL'); self.assertEqual(d['Management Accounts'],'D01_PNL')
    def test_scenario2_classification(self):
        p=profile_workbook(self.s2); d={x['sheet']:x['domain'] for x in p['sheets']}
        self.assertEqual(d['AR Customer Ledger'],'D04_AR'); self.assertEqual(d['AP Supplier Ledger'],'D05_AP'); self.assertEqual(d['Reconciliations'],'CONTROL_EVIDENCE')
    def test_recalculate_not_trust_embedded_recon(self):
        r=reconcile_workbook(self.s2); m={x['control']:x for x in r}
        self.assertEqual(m['AR_TO_TB']['status'],'FAIL'); self.assertEqual(m['AP_TO_TB']['status'],'FAIL')
        self.assertGreater(abs(m['AR_TO_TB']['difference']),900000); self.assertGreater(abs(m['AP_TO_TB']['difference']),200000)
    def test_formula_cache_quality_signal(self):
        p=profile_workbook(self.s1)
        self.assertTrue(any(x['formula_cells']>0 for x in p['sheets']))
        self.assertTrue(all(x['formula_values_missing']>=0 for x in p['sheets']))
if __name__=='__main__': unittest.main()
