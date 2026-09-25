import json, tempfile, uuid, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import ingest_northstar
from profit_doctor.ingestion.accounting import ingest_accounting_file
from profit_doctor.trust.engine import run_trust_layer,assess_level1_accounting_trust,assess_cross_source_reconciliations
from profit_doctor.calc.primitive_engine import run_primitive_engine
from profit_doctor.diagnostic.engine import run_diagnostic_engine
from profit_doctor.reasoning.engine import run_reasoning_engine
from profit_doctor.economic.engine import run_economic_engine
BASE=Path('/mnt/data/e2e_assets/unzip/profit_doctor_e2e_review_v1_3')
def now(): return '2026-09-24T00:00:00+00:00'
res={}
for name,model in [('micro','PROFESSIONAL_SERVICES'),('mid','PRODUCT_DISTRIBUTION'),('large','SUBSCRIPTION')]:
  with tempfile.TemporaryDirectory() as td:
    td=Path(td); con=connect(td/'engine.db'); c='c_'+name; r='r_'+uuid.uuid4().hex
    con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,name,'GBP',model,now())); con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'BASELINE',now(),None,'RUNNING',None,r,'2.4')); con.commit()
    src=BASE/name; ing=ingest_northstar(con,c,r,src,td/'store')
    run_trust_layer(con,r,c,ing['dataset_version_id'])
    for f,k in [('pnl.csv','D01_PNL'),('bs.csv','D02_BALANCE_SHEET'),('tb.csv','D03_TRIAL_BALANCE'),('ar.csv','D04_AR'),('ap.csv','D05_AP'),('bank.csv','D06_BANK')]:
      if (src/f).exists(): ingest_accounting_file(con,c,r,src/f,k,td/'store')
    assess_level1_accounting_trust(con,r,c); rec=assess_cross_source_reconciliations(con,r,c)
    run_primitive_engine(con,r,c,ing['dataset_version_id'])
    d=run_diagnostic_engine(con,r,c,ing['dataset_version_id']); rr=run_reasoning_engine(con,r,c); ee=run_economic_engine(con,r,c)
    status={k:v['status'] for k,v in d.items()}; completed=sum(v=='COMPLETED' for v in status.values()); notrun=sum(v!='COMPLETED' for v in status.values())
    res[name]={'registered':len(status),'completed':completed,'not_completed':notrun,'signals':con.execute('select count(*) n from signal where run_id=?',(r,)).fetchone()['n'],'findings':con.execute('select count(*) n from finding where client_id=?',(c,)).fetchone()['n'],'stories':con.execute('select count(*) n from economic_story where client_id=?',(c,)).fetchone()['n'],'reconciliations':rec,'not_completed_ids':[k for k,v in status.items() if v!='COMPLETED']}
    con.close()
print(json.dumps(res,indent=2))
