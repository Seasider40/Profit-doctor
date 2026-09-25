import csv, uuid
from pathlib import Path
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from .northstar import register_dataset_version, id4, now

CONTRACTS={
'D01_PNL':({'period_end','line_code','line_name','amount'},'D01','pnl'),
'D02_BALANCE_SHEET':({'period_end','line_code','line_name','amount'},'D02','balance_sheet'),
'D03_TRIAL_BALANCE':({'period_end','account_code','account_name','account_type','debit','credit'},'D03','trial_balance'),
'D04_AR':({'invoice_id','customer_id','invoice_date','due_date','original_amount','outstanding_amount'},'D04','ar'),
'D05_AP':({'invoice_id','supplier_id','invoice_date','due_date','original_amount','outstanding_amount'},'D05','ap'),
'D06_BANK':({'transaction_id','transaction_date','amount','balance'},'D06','bank'),
'D12_INVENTORY':({'snapshot_date','product_id','quantity_on_hand','inventory_value'},'D12','inventory')}

def _rows(path, required):
    with open(path,newline='',encoding='utf-8-sig') as f:
        rd=csv.DictReader(f); rows=list(rd); fields=set(rd.fieldnames or [])
    missing=required-fields
    if missing: raise ValueError('MISSING_REQUIRED_COLUMNS:'+','.join(sorted(missing)))
    return rows

def _dec(v, field):
    try: return Decimal(v)
    except (InvalidOperation,TypeError): raise ValueError(f'INVALID_DECIMAL:{field}:{v}')

def _date(v, field):
    try: return datetime.fromisoformat(v).date().isoformat()
    except Exception: raise ValueError(f'INVALID_DATE:{field}:{v}')

def ingest_accounting_file(con,client_id,run_id,path,contract_key,storage_root):
    required,domain,logical=CONTRACTS[contract_key]; path=Path(path)
    job=id4('job'); con.execute('INSERT INTO ingestion_job VALUES (?,?,?,?,?,?,?)',(job,run_id,client_id,now(),None,'RUNNING',None)); con.commit()
    try:
        rows=_rows(path,required)
        dvid,rows2,fields2,is_new=register_dataset_version(con,client_id,job,path,domain,f'accounting:{logical}',storage_root,'period_end' if contract_key in ('D01_PNL','D02_BALANCE_SHEET','D03_TRIAL_BALANCE') else ('invoice_date' if contract_key in ('D04_AR','D05_AP') else ('snapshot_date' if contract_key=='D12_INVENTORY' else 'transaction_date')))
        info={'dataset_version_id':dvid,'new_version':is_new}
        if not is_new:
            con.execute("UPDATE ingestion_job SET status='COMPLETED',completed_at=? WHERE ingestion_job_id=?",(now(),job)); con.commit(); return info
        with con:
            if contract_key in ('D01_PNL','D02_BALANCE_SHEET'):
                st='PNL' if contract_key=='D01_PNL' else 'BALANCE_SHEET'
                for i,r in enumerate(rows,2):
                    con.execute('INSERT INTO financial_statement_line VALUES (?,?,?,?,?,?,?,?,?)',(id4('fsl'),client_id,st,_date(r['period_end'],'period_end'),r['line_code'],r['line_name'],str(_dec(r['amount'],'amount')),dvid,i))
            elif contract_key=='D03_TRIAL_BALANCE':
                for i,r in enumerate(rows,2):
                    ac=con.execute('SELECT account_id FROM account WHERE client_id=? AND account_code=?',(client_id,r['account_code'])).fetchone()
                    aid=ac['account_id'] if ac else id4('acct')
                    if not ac: con.execute('INSERT INTO account VALUES (?,?,?,?,?)',(aid,client_id,r['account_code'],r['account_name'],r['account_type']))
                    con.execute('INSERT INTO trial_balance VALUES (?,?,?,?,?,?,?,?)',(id4('tb'),client_id,_date(r['period_end'],'period_end'),aid,str(_dec(r['debit'],'debit')),str(_dec(r['credit'],'credit')),dvid,i))
            elif contract_key in ('D04_AR','D05_AP'):
                table='ar_invoice' if contract_key=='D04_AR' else 'ap_invoice'; party='customer_id' if contract_key=='D04_AR' else 'supplier_id'
                ids=set()
                for i,r in enumerate(rows,2):
                    if r['invoice_id'] in ids: raise ValueError('DUPLICATE_INVOICE_ID:'+r['invoice_id'])
                    ids.add(r['invoice_id']); vals=(id4('inv'),client_id,r['invoice_id'],r[party],_date(r['invoice_date'],'invoice_date'),_date(r['due_date'],'due_date'),str(_dec(r['original_amount'],'original_amount')),str(_dec(r['outstanding_amount'],'outstanding_amount')),dvid,i)
                    con.execute(f'INSERT INTO {table} VALUES (?,?,?,?,?,?,?,?,?,?)',vals)
            elif contract_key=='D12_INVENTORY':
                seen=set()
                for i,r in enumerate(rows,2):
                    key=(r['snapshot_date'],r['product_id'])
                    if key in seen: raise ValueError('DUPLICATE_INVENTORY_SNAPSHOT:'+':'.join(key))
                    seen.add(key)
                    con.execute('INSERT INTO inventory_snapshot VALUES (?,?,?,?,?,?,?,?)',(id4('invst'),client_id,_date(r['snapshot_date'],'snapshot_date'),r['product_id'],str(_dec(r['quantity_on_hand'],'quantity_on_hand')) if r['quantity_on_hand']!='' else None,str(_dec(r['inventory_value'],'inventory_value')),dvid,i))
            elif contract_key=='D06_BANK':
                ids=set()
                for i,r in enumerate(rows,2):
                    if r['transaction_id'] in ids: raise ValueError('DUPLICATE_BANK_TRANSACTION:'+r['transaction_id'])
                    ids.add(r['transaction_id']); con.execute('INSERT INTO bank_transaction VALUES (?,?,?,?,?,?,?,?)',(id4('bank'),client_id,r['transaction_id'],_date(r['transaction_date'],'transaction_date'),str(_dec(r['amount'],'amount')),str(_dec(r['balance'],'balance')) if r['balance']!='' else None,dvid,i))
            con.execute('UPDATE dataset_version SET row_count=?,ingestion_status=? WHERE dataset_version_id=?',(len(rows),'COMPLETED',dvid))
            con.execute("UPDATE ingestion_job SET status='COMPLETED',completed_at=? WHERE ingestion_job_id=?",(now(),job))
        return info
    except Exception as e:
        con.rollback(); con.execute("UPDATE ingestion_job SET status='FAILED',completed_at=?,error_detail=? WHERE ingestion_job_id=?",(now(),str(e),job)); con.commit(); raise
