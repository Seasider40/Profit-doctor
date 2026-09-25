import csv, hashlib, shutil, uuid
from pathlib import Path
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

now=lambda: datetime.now(timezone.utc).isoformat()
id4=lambda p: f"{p}_{uuid.uuid4().hex}"
REQUIRED_TX={'transaction_id','month','customer_id','customer_name','product_id','product_name','units','unit_price','unit_cost','revenue','direct_cost','gross_profit','cts','contribution'}

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def _copy_immutable(path, client_id, storage_root):
    path=Path(path); digest=sha256(path)
    dest=Path(storage_root)/client_id/digest[:2]/digest
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(path,dest)
        dest.chmod(0o444)
    if sha256(dest)!=digest: raise ValueError('IMMUTABLE_COPY_HASH_MISMATCH')
    return dest,digest

def register_file(con, client_id, path, storage_root):
    path=Path(path); stored,digest=_copy_immutable(path,client_id,storage_root)
    existing=con.execute('SELECT source_file_id,storage_location FROM source_file WHERE client_id=? AND file_hash=?',(client_id,digest)).fetchone()
    if existing: return existing['source_file_id']
    sfid=id4('src')
    con.execute('INSERT INTO source_file VALUES (?,?,?,?,?,?,?,?)',(sfid,client_id,path.name,str(stored),digest,path.stat().st_size,1,now()))
    return sfid

def _read_csv(path):
    with open(path,newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f); rows=list(reader); fields=set(reader.fieldnames or [])
    return rows,fields

def register_dataset_version(con, client_id, ingestion_job_id, path, domain, logical_key, storage_root, period_field=None):
    sfid=register_file(con,client_id,path,storage_root)
    ds=con.execute('SELECT dataset_id FROM dataset WHERE client_id=? AND logical_dataset_key=?',(client_id,logical_key)).fetchone()
    if ds: dsid=ds['dataset_id']
    else:
        dsid=id4('ds'); con.execute('INSERT INTO dataset VALUES (?,?,?,?,?,?)',(dsid,client_id,sfid,domain,logical_key,now()))
    latest=con.execute('SELECT version_number,source_file_id,dataset_version_id FROM dataset_version WHERE dataset_id=? ORDER BY version_number DESC LIMIT 1',(dsid,)).fetchone()
    rows,fields=_read_csv(path)
    if latest and latest['source_file_id']==sfid:
        return latest['dataset_version_id'],rows,fields,False
    ver=(latest['version_number']+1) if latest else 1
    vals=[r.get(period_field) for r in rows if period_field and r.get(period_field)]
    dvid=id4('dsv')
    con.execute('INSERT INTO dataset_version VALUES (?,?,?,?,?,?,?,?,?,?)',(dvid,dsid,ingestion_job_id,sfid,ver,len(rows),min(vals) if vals else None,max(vals) if vals else None,'INGESTED',now()))
    return dvid,rows,fields,True

def ensure_entity(con, client_id, etype, source_key, name, source_file_id=None):
    if not source_key: raise ValueError(f'MISSING_{etype}_KEY')
    row=con.execute('''SELECT e.entity_id FROM entity_alias a JOIN entity e ON e.entity_id=a.entity_id
                       WHERE a.client_id=? AND e.entity_type=? AND a.source_entity_key=? LIMIT 1''',(client_id,etype,source_key)).fetchone()
    if row: return row['entity_id']
    eid=id4('ent')
    con.execute('INSERT INTO entity VALUES (?,?,?,?,?)',(eid,client_id,etype,name or source_key,'ACTIVE'))
    con.execute('INSERT INTO entity_alias VALUES (?,?,?,?,?,?,?,?)',(id4('alias'),client_id,eid,source_file_id,source_key,name,'SOURCE_ID','CONFIRMED'))
    return eid

def dec(value, field):
    if value in (None,''): return None
    try: return Decimal(value)
    except InvalidOperation as e: raise ValueError(f'INVALID_DECIMAL:{field}:{value}') from e

def ingest_northstar(con, client_id, run_id, folder, storage_root):
    folder=Path(folder); job=id4('ing'); con.execute('INSERT INTO ingestion_job VALUES (?,?,?,?,?,?,?)',(job,run_id,client_id,now(),None,'RUNNING',None))
    try:
        con.execute('SAVEPOINT ingest_job')
        c_dv,customers,c_fields,_=register_dataset_version(con,client_id,job,folder/'customers.csv','D08_CUSTOMER_MASTER','northstar:customers',storage_root)
        p_dv,products,p_fields,_=register_dataset_version(con,client_id,job,folder/'products.csv','D09_PRODUCT_MASTER','northstar:products',storage_root)
        if not {'customer_id','customer_name'}.issubset(c_fields): raise ValueError('CUSTOMER_SCHEMA_INVALID')
        if not {'product_id','product_name'}.issubset(p_fields): raise ValueError('PRODUCT_SCHEMA_INVALID')
        for r in customers: ensure_entity(con,client_id,'CUSTOMER',r.get('customer_id'),r.get('customer_name'))
        for r in products: ensure_entity(con,client_id,'PRODUCT',r.get('product_id'),r.get('product_name'))
        t_dv,tx,t_fields,is_new=register_dataset_version(con,client_id,job,folder/'transactions.csv','D07_SALES_TRANSACTIONS','northstar:transactions',storage_root,'month')
        missing=REQUIRED_TX-t_fields
        if missing: raise ValueError('TRANSACTION_SCHEMA_MISSING:'+','.join(sorted(missing)))
        if is_new:
            seen=set()
            for i,r in enumerate(tx,2):
                sk=r.get('transaction_id')
                if not sk: raise ValueError(f'MISSING_TRANSACTION_ID:row={i}')
                if sk in seen: raise ValueError(f'DUPLICATE_TRANSACTION_ID:{sk}')
                seen.add(sk)
                cid=ensure_entity(con,client_id,'CUSTOMER',r.get('customer_id'),r.get('customer_name'))
                pid=ensure_entity(con,client_id,'PRODUCT',r.get('product_id'),r.get('product_name'))
                vals=(id4('txn'),client_id,sk,r['month'],cid,pid,
                      str(dec(r['units'],'units')),str(dec(r['unit_price'],'unit_price')),str(dec(r['unit_cost'],'unit_cost')),
                      str(dec(r['revenue'],'revenue')),str(dec(r['direct_cost'],'direct_cost')),str(dec(r['gross_profit'],'gross_profit')),
                      str(dec(r['cts'],'cts')),str(dec(r['contribution'],'contribution')),t_dv,i,'ACTIVE')
                con.execute('INSERT INTO sales_transaction VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',vals)
        con.execute("UPDATE dataset_version SET ingestion_status='COMPLETED' WHERE ingestion_job_id=? AND ingestion_status='INGESTED'",(job,))
        con.execute('UPDATE ingestion_job SET completed_at=?,status=? WHERE ingestion_job_id=?',(now(),'COMPLETED',job))
        con.execute('INSERT INTO audit_event VALUES (?,?,?,?,?,?,?,?)',(id4('audit'),client_id,run_id,'INGESTION','dataset_version',t_dv,f'{len(tx)} sales rows processed; new_version={is_new}',now()))
        con.execute('RELEASE SAVEPOINT ingest_job'); con.commit()
        return {'transactions':len(tx),'dataset_version_id':t_dv,'new_version':is_new,'ingestion_job_id':job}
    except Exception as e:
        con.execute('ROLLBACK TO SAVEPOINT ingest_job'); con.execute('RELEASE SAVEPOINT ingest_job')
        # job row was rolled back too; preserve failure as an audit-safe job record.
        con.execute('INSERT OR REPLACE INTO ingestion_job VALUES (?,?,?,?,?,?,?)',(job,run_id,client_id,now(),now(),'FAILED',str(e)))
        con.commit(); raise
