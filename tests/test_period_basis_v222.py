import tempfile, unittest, csv, uuid
from pathlib import Path
from decimal import Decimal
from profit_doctor.core.db import connect
from profit_doctor.ingestion.accounting import ingest_accounting_file
from profit_doctor.calc.primitive_engine import calculate_level1_primitives

def write(p,fields,rows):
 with open(p,'w',newline='') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
class PeriodBasisV222(unittest.TestCase):
 def test_monthly_pnl_is_aggregated_before_dso_dpo(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td); con=connect(d/'x.db'); c='c_'+uuid.uuid4().hex; r='r_'+uuid.uuid4().hex; now='2026-12-31T00:00:00+00:00'
   con.execute('insert into client values (?,?,?,?,?)',(c,'x','GBP','PRODUCT_DISTRIBUTION',now)); con.execute('insert into engine_run values (?,?,?,?,?,?,?,?,?)',(r,c,'Q',now,None,'RUNNING',None,r,'2.22')); con.commit()
   pnl=[]
   for m in range(1,13):
    pe=f'2026-{m:02d}-28' if m==2 else f'2026-{m:02d}-30'
    pnl += [{'period_end':pe,'line_code':'REV','line_name':'Revenue','amount':100},{'period_end':pe,'line_code':'COGS','line_name':'Cost of Sales','amount':60}]
   bs=[{'period_end':'2026-12-30','line_code':'AR','line_name':'Trade Debtors','amount':120},{'period_end':'2026-12-30','line_code':'AP','line_name':'Trade Creditors','amount':60}]
   write(d/'pnl.csv',['period_end','line_code','line_name','amount'],pnl); write(d/'bs.csv',['period_end','line_code','line_name','amount'],bs)
   ingest_accounting_file(con,c,r,d/'pnl.csv','D01_PNL',d/'store'); ingest_accounting_file(con,c,r,d/'bs.csv','D02_BALANCE_SHEET',d/'store')
   out=calculate_level1_primitives(con,r,c)
   self.assertEqual(out['FIN_REVENUE'],Decimal('1200')); self.assertEqual(out['FIN_DIRECT_COST'],Decimal('720'))
   self.assertAlmostEqual(float(out['WC_DSO']),36.4,places=1); self.assertAlmostEqual(float(out['WC_DPO']),30.333333,places=3)
   con.close()
if __name__=='__main__': unittest.main()
