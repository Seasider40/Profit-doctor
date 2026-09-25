import unittest, tempfile, os, csv, uuid
from pathlib import Path
from decimal import Decimal
from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import sha256, ingest_northstar, ensure_entity
from profit_doctor.calc.primitives import calculate_commercial_financials

FIXTURE=Path(__file__).resolve().parent/'fixtures'/'northstar'

def now(): return '2026-09-24T00:00:00+00:00'
def setup_run(con, client='c1'):
    con.execute('INSERT OR IGNORE INTO client VALUES (?,?,?,?,?)',(client,client,'GBP','PRODUCT_DISTRIBUTION',now()))
    run='run_'+uuid.uuid4().hex
    con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(run,client,'BASELINE',now(),None,'RUNNING',None,run,'0.2.0')); con.commit(); return run

def copy_fixture(dst):
    import shutil
    for name in ('customers.csv','products.csv','transactions.csv'): shutil.copy2(FIXTURE/name,Path(dst)/name)

class Foundation(unittest.TestCase):
    def test_schema(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db')
            tables={r[0] for r in con.execute("select name from sqlite_master where type='table'")}
            need={'client','engine_run','ingestion_job','source_file','dataset','dataset_version','entity','sales_transaction','primitive_result','calculation_lineage'}
            self.assertTrue(need.issubset(tables))

    def test_hash_stable(self):
        with tempfile.NamedTemporaryFile(delete=False) as f: f.write(b'abc'); p=f.name
        try: self.assertEqual(sha256(p),sha256(p))
        finally: os.unlink(p)

    def test_client_entity_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); setup_run(con,'a'); setup_run(con,'b')
            a=ensure_entity(con,'a','CUSTOMER','C001','Same'); b=ensure_entity(con,'b','CUSTOMER','C001','Same')
            self.assertNotEqual(a,b)

    def test_northstar_known_answers_decimal_and_lineage(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); run=setup_run(con)
            info=ingest_northstar(con,'c1',run,FIXTURE,Path(d)/'store')
            vals=calculate_commercial_financials(con,run,'c1',info['dataset_version_id'])
            self.assertEqual(vals['COMMERCIAL_NET_REVENUE'],Decimal('14047932.56'))
            self.assertEqual(vals['COMMERCIAL_DIRECT_COST'],Decimal('9110927.70'))
            self.assertEqual(vals['ECON_CONTRIBUTION_0'],Decimal('4937004.86'))
            self.assertEqual(vals['ECON_CONTRIBUTION_0_MARGIN'].quantize(Decimal('0.000001')),Decimal('35.143996'))
            self.assertEqual(con.execute('select count(*) from sales_transaction').fetchone()[0],15087)
            self.assertEqual(con.execute('select count(*) from calculation_lineage').fetchone()[0],4)
            self.assertTrue(all(r[0]==info['dataset_version_id'] for r in con.execute('select source_object_id from calculation_lineage')))

    def test_idempotent_reprocess_same_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            con=connect(Path(d)/'x.db'); run1=setup_run(con); store=Path(d)/'store'
            a=ingest_northstar(con,'c1',run1,FIXTURE,store)
            run2=setup_run(con); b=ingest_northstar(con,'c1',run2,FIXTURE,store)
            self.assertTrue(a['new_version']); self.assertFalse(b['new_version'])
            self.assertEqual(a['dataset_version_id'],b['dataset_version_id'])
            self.assertEqual(con.execute('select count(*) from sales_transaction').fetchone()[0],15087)

    def test_immutable_copy_survives_external_change(self):
        with tempfile.TemporaryDirectory() as d:
            fixture=Path(d)/'fixture'; fixture.mkdir(); copy_fixture(fixture)
            con=connect(Path(d)/'x.db'); run=setup_run(con); store=Path(d)/'store'
            ingest_northstar(con,'c1',run,fixture,store)
            row=con.execute("select storage_location,file_hash from source_file where original_filename='transactions.csv'").fetchone()
            stored=Path(row['storage_location']); before=sha256(stored)
            with open(fixture/'transactions.csv','a') as f: f.write('\n')
            self.assertEqual(sha256(stored),before); self.assertEqual(before,row['file_hash'])

    def test_duplicate_transaction_causes_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            fixture=Path(d)/'fixture'; fixture.mkdir(); copy_fixture(fixture)
            p=fixture/'transactions.csv'
            with open(p,newline='') as rf: rows=list(csv.reader(rf))
            rows.append(rows[1])
            with open(p,'w',newline='') as f: csv.writer(f).writerows(rows)
            con=connect(Path(d)/'x.db'); run=setup_run(con)
            with self.assertRaisesRegex(ValueError,'DUPLICATE_TRANSACTION_ID'):
                ingest_northstar(con,'c1',run,fixture,Path(d)/'store')
            self.assertEqual(con.execute('select count(*) from sales_transaction').fetchone()[0],0)
            self.assertEqual(con.execute("select count(*) from ingestion_job where status='FAILED'").fetchone()[0],1)

    def test_zero_revenue_margin_not_meaningful(self):
        with tempfile.TemporaryDirectory() as d:
            fixture=Path(d)/'fixture'; fixture.mkdir(); copy_fixture(fixture)
            p=fixture/'transactions.csv'
            with open(p,newline='') as rf: rows=list(csv.DictReader(rf))
            fields=rows[0].keys()
            for r in rows: r['revenue']='0'; r['direct_cost']='0'; r['gross_profit']='0'; r['contribution']='0'
            with open(p,'w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
            con=connect(Path(d)/'x.db'); run=setup_run(con); info=ingest_northstar(con,'c1',run,fixture,Path(d)/'store')
            vals=calculate_commercial_financials(con,run,'c1',info['dataset_version_id'])
            self.assertIsNone(vals['ECON_CONTRIBUTION_0_MARGIN'])
            status=con.execute("select result_status from primitive_result where primitive_id='ECON_CONTRIBUTION_0_MARGIN'").fetchone()[0]
            self.assertEqual(status,'NOT_MEANINGFUL')

    def test_restatement_creates_new_version_preserves_old(self):
        with tempfile.TemporaryDirectory() as d:
            fixture=Path(d)/'fixture'; fixture.mkdir(); copy_fixture(fixture); store=Path(d)/'store'
            con=connect(Path(d)/'x.db'); r1=setup_run(con); a=ingest_northstar(con,'c1',r1,fixture,store)
            p=fixture/'transactions.csv'
            with open(p,newline='') as rf: rows=list(csv.DictReader(rf))
            fields=rows[0].keys(); rows[0]['revenue']='961.00'
            with open(p,'w',newline='') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
            r2=setup_run(con); b=ingest_northstar(con,'c1',r2,fixture,store)
            self.assertTrue(b['new_version']); self.assertNotEqual(a['dataset_version_id'],b['dataset_version_id'])
            self.assertEqual(con.execute('select count(*) from dataset_version where dataset_id=(select dataset_id from dataset where logical_dataset_key=?)',('northstar:transactions',)).fetchone()[0],2)
            self.assertEqual(con.execute('select count(*) from sales_transaction').fetchone()[0],30174)

if __name__=='__main__': unittest.main()
