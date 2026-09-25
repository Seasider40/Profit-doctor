import unittest, tempfile, uuid
from pathlib import Path
from decimal import Decimal
from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import ingest_northstar
from profit_doctor.trust.engine import run_trust_layer, assess_sales_trust, assess_test_eligibility

FIXTURE=Path(__file__).resolve().parent/'fixtures'/'northstar'
def now(): return '2026-09-24T00:00:00+00:00'
def setup_run(con, client='c1'):
    con.execute('INSERT OR IGNORE INTO client VALUES (?,?,?,?,?)',(client,client,'GBP','PRODUCT_DISTRIBUTION',now()))
    run='run_'+uuid.uuid4().hex
    con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(run,client,'BASELINE',now(),None,'RUNNING',None,run,'0.3.0')); con.commit(); return run

def load(con,d):
    run=setup_run(con); info=ingest_northstar(con,'c1',run,FIXTURE,Path(d)/'store'); return run,info

class TrustLayer(unittest.TestCase):
    def test_clean_northstar_is_reliable_and_full(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); run,info=load(con,d)
            out=run_trust_layer(con,run,'c1',info['dataset_version_id'])
            self.assertEqual(out['trust']['availability'],'AVAILABLE')
            self.assertEqual(out['trust']['history_months'],36)
            self.assertEqual(out['trust']['quality'],'RELIABLE')
            self.assertEqual(out['trust']['integrity'],'RELIABLE')
            self.assertEqual(out['trust']['reconciliation'],'RECONCILED')
            self.assertTrue(all(x['eligibility']=='FULL' for x in out['tests'].values()))
            self.assertEqual(out['domains']['D07'],'AVAILABLE')
            self.assertEqual(out['domains']['D08'],'AVAILABLE')
            self.assertEqual(out['domains']['D09'],'AVAILABLE')
            self.assertEqual(out['domains']['D10'],'AVAILABLE')
            self.assertEqual(out['domains']['D01'],'UNAVAILABLE')
            cov=con.execute("select economic_coverage_pct from mapping_coverage where run_id=? and mapping_type='CUSTOMER'",(run,)).fetchone()[0]
            self.assertEqual(Decimal(cov),Decimal('100'))

    def test_short_history_degrades_not_bluffs(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); run,info=load(con,d)
            # retain only final 12 months in the active analytical scope
            dates=[r[0] for r in con.execute('select distinct transaction_date from sales_transaction order by transaction_date')]
            cutoff=dates[-12]
            con.execute("update sales_transaction set record_status='EXCLUDED_TEST' where transaction_date < ?",(cutoff,)); con.commit()
            assess_sales_trust(con,run,'c1',info['dataset_version_id'])
            e=assess_test_eligibility(con,run,'c1','REV-01',info['dataset_version_id'],24)
            self.assertEqual(e['eligibility'],'PARTIAL-A')
            self.assertTrue(any('12 months' in x for x in e['limitations']))

    def test_missing_customer_mapping_degrades_customer_test(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); run,info=load(con,d)
            # remove mapping from economically material rows (>5% revenue)
            total=Decimal(con.execute('select sum(cast(net_revenue as real)) from sales_transaction').fetchone()[0])
            rows=con.execute('select sales_transaction_id,net_revenue from sales_transaction order by cast(net_revenue as real) desc').fetchall()
            removed=Decimal('0')
            for r in rows:
                con.execute('update sales_transaction set customer_entity_id=NULL where sales_transaction_id=?',(r['sales_transaction_id'],)); removed += Decimal(r['net_revenue'])
                if removed/total > Decimal('0.06'): break
            con.commit(); assess_sales_trust(con,run,'c1',info['dataset_version_id'])
            e=assess_test_eligibility(con,run,'c1','CUS-04',info['dataset_version_id'],24,needs_customer=True)
            self.assertEqual(e['eligibility'],'PARTIAL-B')
            self.assertLess(e['economic_coverage_pct'],Decimal('95'))

    def test_arithmetic_break_constrains_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); run,info=load(con,d)
            row=con.execute('select sales_transaction_id from sales_transaction limit 1').fetchone()
            con.execute("update sales_transaction set source_gross_profit=cast(source_gross_profit as real)+1000 where sales_transaction_id=?",(row[0],)); con.commit()
            t=assess_sales_trust(con,run,'c1',info['dataset_version_id'])
            self.assertEqual(t['reconciliation'],'FAILED')
            self.assertEqual(t['integrity'],'MATERIALLY_CONSTRAINED')
            e=assess_test_eligibility(con,run,'c1','GM-01',info['dataset_version_id'],24)
            self.assertEqual(e['eligibility'],'PARTIAL-C')

    def test_trust_records_are_persisted(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); run,info=load(con,d); run_trust_layer(con,run,'c1',info['dataset_version_id'])
            self.assertEqual(con.execute('select count(*) from data_availability where run_id=?',(run,)).fetchone()[0],18)
            self.assertGreaterEqual(con.execute('select count(*) from test_eligibility where run_id=?',(run,)).fetchone()[0],10)
            self.assertEqual(con.execute('select count(*) from reconciliation where run_id=?',(run,)).fetchone()[0],1)

if __name__=='__main__': unittest.main()
