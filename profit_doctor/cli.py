import argparse, uuid
from datetime import datetime, timezone
from pathlib import Path
from .core.db import connect
from .ingestion.northstar import ingest_northstar
from .calc.primitives import calculate_commercial_financials

def now(): return datetime.now(timezone.utc).isoformat()
def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--db',default='profit_doctor.db'); p.add_argument('--storage',default='.profit_doctor_source_store'); a=p.parse_args()
    con=connect(a.db); client='northstar'; started=now()
    con.execute('INSERT OR IGNORE INTO client VALUES (?,?,?,?,?)',(client,'Northstar Distribution Ltd','GBP','PRODUCT_DISTRIBUTION',started))
    run='run_'+uuid.uuid4().hex
    con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(run,client,'BASELINE',started,None,'RUNNING',None,run,'0.2.0')); con.commit()
    try:
        info=ingest_northstar(con,client,run,a.input,a.storage)
        vals=calculate_commercial_financials(con,run,client,info['dataset_version_id'])
        con.execute('UPDATE engine_run SET completed_at=?, status=? WHERE run_id=?',(now(),'COMPLETED',run)); con.commit()
    except Exception:
        con.execute('UPDATE engine_run SET completed_at=?, status=? WHERE run_id=?',(now(),'FAILED',run)); con.commit(); raise
    print('Profit Doctor Engine v0.2')
    print('Run:',run); print('Transactions:',info['transactions'],'New dataset version:',info['new_version'])
    for k,v in vals.items(): print(f'{k}: {v}' if v is not None else f'{k}: NOT_MEANINGFUL')
if __name__=='__main__': main()
