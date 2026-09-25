import os,sqlite3,tempfile,unittest
from decimal import Decimal
from profit_doctor.intake.bridge import execute_unknown_workbook
from profit_doctor.api import get_product_view_json

class TestVisualReadinessV235(unittest.TestCase):
    def setUp(self): self.s2=os.environ.get('PD_UWB2','/mnt/data/v227/scenario2.xlsx')
    def test_scenario2_control_balances_are_not_polluted_by_broad_names(self):
        f=tempfile.NamedTemporaryFile(suffix='.db',delete=False); f.close(); r=execute_unknown_workbook(self.s2,f.name)
        c=sqlite3.connect(f.name); c.row_factory=sqlite3.Row
        vals={x['primitive_id']:Decimal(x['numeric_value']) for x in c.execute("select primitive_id,numeric_value from primitive_result where run_id=? and result_status='VALID'",(r['run_id'],))}
        self.assertEqual(vals['BS_ACCOUNTS_RECEIVABLE'],Decimal('3450000'))
        self.assertEqual(vals['BS_ACCOUNTS_PAYABLE'],Decimal('1710000'))
        self.assertEqual(vals['BS_CASH'],Decimal('95000'))
        self.assertEqual(vals['AVAILABLE_CASH'],Decimal('95000'))
        c.close()
    def test_owner_view_exposes_core_kpis(self):
        f=tempfile.NamedTemporaryFile(suffix='.db',delete=False); f.close(); r=execute_unknown_workbook(self.s2,f.name)
        c=sqlite3.connect(f.name); c.row_factory=sqlite3.Row
        client=c.execute('select client_id from engine_run where run_id=?',(r['run_id'],)).fetchone()['client_id']
        p=get_product_view_json(c,r['run_id'],client); labels={x['label'] for x in p['executive_health_check']['kpis']}
        self.assertTrue({'Revenue','Gross profit','EBITDA','Available cash','DSO','DIO','DPO','Cash conversion cycle'} <= labels)
        self.assertIsNone(p['opportunity_register']['portfolio_headline']['combined_total'])
        c.close()
if __name__=='__main__': unittest.main()
