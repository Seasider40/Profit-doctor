import uuid
from decimal import Decimal
from datetime import datetime, timezone
id4=lambda p:f"{p}_{uuid.uuid4().hex}"
now=lambda:datetime.now(timezone.utc).isoformat()
PRIMITIVES=[
('COMMERCIAL_NET_REVENUE','Commercial Net Revenue','Transaction-derived net sales revenue for selected scope','REV','FLOW','GBP','ADDITIVE','1.0'),
('COMMERCIAL_DIRECT_COST','Commercial Direct Cost','Transaction-derived direct cost for selected scope','REV','FLOW','GBP','ADDITIVE','1.0'),
('ECON_CONTRIBUTION_0','Contribution 0','Commercial net revenue less direct product/service cost','ECON','FLOW','GBP','ADDITIVE','1.0'),
('ECON_CONTRIBUTION_0_MARGIN','Contribution 0 Margin %','Contribution 0 divided by commercial net revenue','ECON','RATE','PERCENT','NON_ADDITIVE','1.0')]

def seed(con):
    con.executemany('INSERT OR IGNORE INTO primitive_registry VALUES (?,?,?,?,?,?,?,?)',PRIMITIVES); con.commit()

def _sum_decimal(rows,key):
    total=Decimal('0')
    for r in rows:
        if r[key] is not None: total += Decimal(r[key])
    return total

def calculate_commercial_financials(con,run_id,client_id,dataset_version_id=None):
    seed(con)
    if dataset_version_id is None:
        row=con.execute('''SELECT dv.dataset_version_id FROM dataset_version dv JOIN dataset d ON d.dataset_id=dv.dataset_id
                           WHERE d.client_id=? AND d.data_domain='D07_SALES_TRANSACTIONS'
                           ORDER BY dv.version_number DESC LIMIT 1''',(client_id,)).fetchone()
        if not row: raise ValueError('NO_SALES_DATASET')
        dataset_version_id=row['dataset_version_id']
    rows=con.execute('''SELECT transaction_date,net_revenue,direct_cost FROM sales_transaction
                        WHERE client_id=? AND dataset_version_id=? AND record_status='ACTIVE' ''',(client_id,dataset_version_id)).fetchall()
    if not rows: raise ValueError('NO_SALES_TRANSACTIONS_FOR_DATASET')
    rev=_sum_decimal(rows,'net_revenue'); dc=_sum_decimal(rows,'direct_cost'); c0=rev-dc
    margin=(c0/rev*Decimal('100')) if rev != 0 else None
    mn=min(r['transaction_date'] for r in rows); mx=max(r['transaction_date'] for r in rows)
    specs=[('COMMERCIAL_NET_REVENUE',rev,'GBP','SUM_CANONICAL_SALES'),('COMMERCIAL_DIRECT_COST',dc,'GBP','SUM_CANONICAL_SALES'),
           ('ECON_CONTRIBUTION_0',c0,'GBP','COMMERCIAL_REVENUE_MINUS_DIRECT_COST'),('ECON_CONTRIBUTION_0_MARGIN',margin,'PERCENT','C0_DIV_COMMERCIAL_REVENUE')]
    out={}
    for prim,val,unit,method in specs:
        rid=id4('pr'); status='VALID' if val is not None else 'NOT_MEANINGFUL'
        con.execute('INSERT INTO primitive_result VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(rid,run_id,client_id,prim,method,mn,mx,None,None,str(val) if val is not None else None,unit,status,now()))
        con.execute('INSERT INTO calculation_lineage VALUES (?,?,?,?,?,?)',(id4('lin'),rid,'DATASET_VERSION',dataset_version_id,'DERIVED_FROM','all ACTIVE canonical sales_transaction rows for client+dataset_version'))
        out[prim]=val
    con.commit(); return out
