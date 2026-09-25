"""Sprint 3 deterministic Primitive Engine.

Financial facts are calculated once under explicit definitions and methods. Missing evidence
never becomes zero. Results preserve method, status, scope and lineage.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone, date

D=lambda x: Decimal(str(x))
def id4(p): return f"{p}_{uuid.uuid4().hex}"
def now(): return datetime.now(timezone.utc).isoformat()

REGISTRY=[
('COMMERCIAL_NET_REVENUE','Commercial Net Revenue','Transaction-derived net sales revenue for selected scope','REVENUE','FLOW','GBP','ADDITIVE','1.1'),
('COMMERCIAL_DIRECT_COST','Commercial Direct Cost','Transaction-derived direct product/service cost for selected scope','MARGIN','FLOW','GBP','ADDITIVE','1.1'),
('ECON_CONTRIBUTION_0','Contribution 0','Commercial net revenue less direct product/service cost','MARGIN','FLOW','GBP','ADDITIVE','1.1'),
('ECON_CONTRIBUTION_0_MARGIN','Contribution 0 Margin %','Contribution 0 divided by commercial net revenue','MARGIN','RATE','PERCENT','NON_ADDITIVE','1.1'),
('FIN_REVENUE','Financial Revenue','Recognised accounting revenue from the P&L mapping','FINANCIAL','FLOW','GBP','ADDITIVE','1.0'),
('FIN_DIRECT_COST','Financial Direct Cost','Recognised accounting direct cost / cost of sales from the P&L mapping','FINANCIAL','FLOW','GBP','ADDITIVE','1.0'),
('FIN_GROSS_PROFIT','Financial Gross Profit','Recognised accounting gross profit from the P&L mapping','FINANCIAL','FLOW','GBP','ADDITIVE','1.0'),
('FIN_EBITDA','EBITDA','Recognised accounting EBITDA from the P&L mapping','FINANCIAL','FLOW','GBP','ADDITIVE','1.0'),
('BS_ACCOUNTS_RECEIVABLE','Accounts Receivable','Closing trade receivables / debtor balance','WORKING_CAPITAL','STOCK','GBP','NON_ADDITIVE','1.0'),
('BS_ACCOUNTS_PAYABLE','Accounts Payable','Closing trade payables / creditor balance','WORKING_CAPITAL','STOCK','GBP','NON_ADDITIVE','1.0'),
('AR_LEDGER_OUTSTANDING','AR Ledger Outstanding','Sum of open receivables ledger balances','WORKING_CAPITAL','STOCK','GBP','NON_ADDITIVE','1.0'),
('AR_OVERDUE_OUTSTANDING','AR Overdue Outstanding','Open receivables past contractual due date','WORKING_CAPITAL','STOCK','GBP','NON_ADDITIVE','1.0'),
('AP_LEDGER_OUTSTANDING','AP Ledger Outstanding','Sum of open payables ledger balances','WORKING_CAPITAL','STOCK','GBP','NON_ADDITIVE','1.0'),
('AP_OVERDUE_OUTSTANDING','AP Overdue Outstanding','Open payables past contractual due date','WORKING_CAPITAL','STOCK','GBP','NON_ADDITIVE','1.0'),
('BS_CASH','Balance Sheet Cash','Closing cash balance from the balance sheet','CASH','STOCK','GBP','NON_ADDITIVE','1.0'),
('BANK_CLOSING_CASH','Bank Closing Cash','Latest available bank running balance','CASH','STOCK','GBP','NON_ADDITIVE','1.0'),
('WC_DSO','Days Sales Outstanding','Closing accounts receivable divided by period revenue times days in period','WORKING_CAPITAL','RATE','DAYS','NON_ADDITIVE','1.0'),
('BS_INVENTORY','Balance Sheet Inventory','Closing inventory balance from the balance sheet','WORKING_CAPITAL','STOCK','GBP','NON_ADDITIVE','1.0'),
('INVENTORY_SNAPSHOT_VALUE','Inventory Snapshot Value','Latest evidenced inventory snapshot value','WORKING_CAPITAL','STOCK','GBP','NON_ADDITIVE','1.0'),
('WC_DIO','Days Inventory Outstanding','Closing inventory divided by period direct cost times days in period','WORKING_CAPITAL','RATE','DAYS','NON_ADDITIVE','1.0'),
('WC_DPO','Days Payables Outstanding','Closing accounts payable divided by period direct cost times days in period','WORKING_CAPITAL','RATE','DAYS','NON_ADDITIVE','1.0'),
('WC_CCC','Cash Conversion Cycle','DSO plus DIO less DPO; unavailable until inventory days is evidenced','WORKING_CAPITAL','RATE','DAYS','NON_ADDITIVE','1.0'),
('AVAILABLE_CASH','Available Cash','Best evidenced unrestricted cash balance; excludes undocumented facility headroom','CASH','STOCK','GBP','NON_ADDITIVE','1.0'),
('CUSTOMER_REVENUE','Customer Revenue','Commercial net revenue by customer','CUSTOMER','FLOW','GBP','ADDITIVE','1.0'),
('CUSTOMER_CONTRIBUTION_0','Customer Contribution 0','Commercial net revenue less direct cost by customer','CUSTOMER','FLOW','GBP','ADDITIVE','1.0'),
('CUSTOMER_REVENUE_GROWTH','Customer Revenue Growth %','Current comparable-period customer revenue versus preceding comparable period','CUSTOMER','RATE','PERCENT','NON_ADDITIVE','1.0'),
]
METHODS=[
('M_TXN_SUM_REVENUE','COMMERCIAL_NET_REVENUE','Sum canonical sales transactions','L2','D07','1.0'),
('M_TXN_SUM_DIRECT_COST','COMMERCIAL_DIRECT_COST','Sum canonical transaction direct cost','L2','D07,D10','1.0'),
('M_C0','ECON_CONTRIBUTION_0','Commercial revenue minus direct cost','L2','D07,D10','1.0'),
('M_C0_MARGIN','ECON_CONTRIBUTION_0_MARGIN','Contribution 0 divided by commercial revenue','L2','D07,D10','1.0'),
('M_PNL_REVENUE','FIN_REVENUE','Mapped P&L revenue line','L1','D01','1.0'),
('M_PNL_DIRECT_COST','FIN_DIRECT_COST','Mapped P&L direct cost / cost of sales line','L1','D01','1.0'),
('M_PNL_GP','FIN_GROSS_PROFIT','Mapped P&L gross profit line','L1','D01','1.0'),
('M_PNL_EBITDA','FIN_EBITDA','Mapped P&L EBITDA line','L1','D01','1.0'),
('M_BS_AR','BS_ACCOUNTS_RECEIVABLE','Mapped balance-sheet accounts receivable line','L1','D02','1.0'),
('M_BS_AP','BS_ACCOUNTS_PAYABLE','Mapped balance-sheet accounts payable line','L1','D02','1.0'),
('M_AR_LEDGER','AR_LEDGER_OUTSTANDING','Sum open AR invoice balances','L1','D04','1.0'),
('M_AR_OVERDUE','AR_OVERDUE_OUTSTANDING','Sum open AR balances past due date','L1','D04','1.0'),
('M_AP_LEDGER','AP_LEDGER_OUTSTANDING','Sum open AP invoice balances','L1','D05','1.0'),
('M_AP_OVERDUE','AP_OVERDUE_OUTSTANDING','Sum open AP balances past due date','L1','D05','1.0'),
('M_BS_CASH','BS_CASH','Mapped balance-sheet cash line','L1','D02','1.0'),
('M_BANK_CLOSE','BANK_CLOSING_CASH','Latest bank running balance','L1','D06','1.0'),
('M_DSO_CLOSE','WC_DSO','Closing AR / period revenue x period days','L1','D01,D02','1.0'),
('M_BS_INVENTORY','BS_INVENTORY','Mapped balance-sheet inventory line','L1','D02','1.0'),
('M_INVENTORY_SNAPSHOT','INVENTORY_SNAPSHOT_VALUE','Latest inventory snapshot total value','L2','D12','1.0'),
('M_DIO_CLOSE','WC_DIO','Closing inventory / period direct cost x period days','L1','D01,D02','1.0'),
('M_DPO_CLOSE','WC_DPO','Closing AP / period direct cost x period days','L1','D01,D02','1.0'),
('M_CCC','WC_CCC','DSO plus DIO less DPO','L1','D01,D02,D05,D12','1.0'),
('M_AVAILABLE_CASH','AVAILABLE_CASH','Prefer latest bank balance, otherwise mapped balance-sheet cash','L1','D06,D02','1.0'),
('M_CUST_REVENUE','CUSTOMER_REVENUE','Transaction revenue grouped by customer','L2','D07,D08','1.0'),
('M_CUST_C0','CUSTOMER_CONTRIBUTION_0','Transaction contribution grouped by customer','L2','D07,D08,D10','1.0'),
('M_CUST_GROWTH','CUSTOMER_REVENUE_GROWTH','Latest 12 months vs preceding 12 months by customer','L2','D07,D08','1.0'),
]
DEPS=[
('ECON_CONTRIBUTION_0','COMMERCIAL_NET_REVENUE'),('ECON_CONTRIBUTION_0','COMMERCIAL_DIRECT_COST'),
('ECON_CONTRIBUTION_0_MARGIN','ECON_CONTRIBUTION_0'),('ECON_CONTRIBUTION_0_MARGIN','COMMERCIAL_NET_REVENUE'),
('WC_DSO','FIN_REVENUE'),('WC_DSO','BS_ACCOUNTS_RECEIVABLE'),('WC_DIO','FIN_DIRECT_COST'),('WC_DIO','BS_INVENTORY'),('WC_DPO','BS_ACCOUNTS_PAYABLE'),('WC_DPO','FIN_DIRECT_COST'),('WC_CCC','WC_DSO'),('WC_CCC','WC_DIO'),('WC_CCC','WC_DPO'),
('AVAILABLE_CASH','BANK_CLOSING_CASH'),
('CUSTOMER_REVENUE_GROWTH','CUSTOMER_REVENUE')]

ALIASES={
 'REVENUE':{'REV','REVENUE','SALES','TURNOVER','NET_REVENUE'},
 'GROSS_PROFIT':{'GP','GROSS_PROFIT','GROSS PROFIT'},
 'EBITDA':{'EBITDA'},
 'DIRECT_COST':{'COGS','COST_OF_SALES','COST OF SALES','DIRECT_COST','DIRECT COST'},
 'AR':{'AR','ACCOUNTS_RECEIVABLE','TRADE_RECEIVABLES','TRADE DEBTORS','DEBTORS'},
 'AP':{'AP','ACCOUNTS_PAYABLE','TRADE_PAYABLES','TRADE CREDITORS','CREDITORS'},
 'CASH':{'CASH','CASH_AT_BANK','BANK','CASH AND CASH EQUIVALENTS'},
 'INVENTORY':{'INVENTORY','STOCK','INVENTORIES'},
}

def seed_registry(con):
    for r in REGISTRY: con.execute('INSERT OR IGNORE INTO primitive_registry VALUES (?,?,?,?,?,?,?,?)',r)
    for m in METHODS: con.execute('INSERT OR IGNORE INTO primitive_method VALUES (?,?,?,?,?,?,1)',m)
    for d in DEPS: con.execute('INSERT OR IGNORE INTO primitive_dependency VALUES (?,?,?)',(d[0],d[1],'REQUIRES'))
    con.commit()

def _record_execution(con,run,client,primitive,method,status,lim=None):
    con.execute('INSERT INTO primitive_execution VALUES (?,?,?,?,?,?,?,?)',(id4('pex'),run,client,primitive,method,status,lim,now()))

def _result(con,run,client,primitive,method,value,unit,status='VALID',period_from=None,period_to=None,dim_type=None,dim_id=None,lineage=()):
    rid=id4('pr')
    con.execute('INSERT INTO primitive_result VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(rid,run,client,primitive,method,period_from,period_to,dim_type,dim_id,None if value is None else str(value),unit,status,now()))
    for obj_type,obj_id,scope in lineage:
        con.execute('INSERT INTO calculation_lineage VALUES (?,?,?,?,?,?)',(id4('lin'),rid,obj_type,obj_id,'DERIVED_FROM',scope))
    _record_execution(con,run,client,primitive,method,status,None if status=='VALID' else status)
    return rid

def _latest_dv(con,client,domain):
    return con.execute('''SELECT dv.* FROM dataset d JOIN dataset_version dv ON dv.dataset_id=d.dataset_id
      WHERE d.client_id=? AND d.data_domain=? AND dv.ingestion_status='COMPLETED' ORDER BY dv.version_number DESC LIMIT 1''',(client,domain)).fetchone()

def _line(rows, names, period=None):
    names={x.upper() for x in names}; candidates=[]
    for r in rows:
        if period and r['period_end']!=period: continue
        if (r['line_code'] or '').strip().upper() in names or (r['line_name'] or '').strip().upper() in names: candidates.append(r)
    return candidates

def _sum_lines(rows,names,period):
    xs=_line(rows,names,period)
    if not xs: return None,[]
    return sum((D(x['amount']) for x in xs),D('0')),xs

def _period_days(period_end):
    end=date.fromisoformat(period_end); start=date(end.year,1,1)
    return (end-start).days+1

def calculate_transaction_primitives(con,run,client,dataset_version_id=None):
    seed_registry(con); dv=con.execute('SELECT * FROM dataset_version WHERE dataset_version_id=?',(dataset_version_id,)).fetchone() if dataset_version_id else _latest_dv(con,client,'D07_SALES_TRANSACTIONS')
    if not dv: return {'status':'UNAVAILABLE','reason':'D07 unavailable'}
    rows=con.execute("SELECT * FROM sales_transaction WHERE client_id=? AND dataset_version_id=? AND record_status='ACTIVE'",(client,dv['dataset_version_id'])).fetchall()
    if not rows: return {'status':'UNAVAILABLE','reason':'No active sales rows'}
    rev=sum((D(r['net_revenue']) for r in rows if r['net_revenue'] is not None),D('0')); cost=sum((D(r['direct_cost']) for r in rows if r['direct_cost'] is not None),D('0')); c0=rev-cost
    mn=min(r['transaction_date'] for r in rows); mx=max(r['transaction_date'] for r in rows); lin=[('DATASET_VERSION',dv['dataset_version_id'],'all ACTIVE canonical sales_transaction rows')]
    _result(con,run,client,'COMMERCIAL_NET_REVENUE','M_TXN_SUM_REVENUE',rev,'GBP',period_from=mn,period_to=mx,lineage=lin)
    _result(con,run,client,'COMMERCIAL_DIRECT_COST','M_TXN_SUM_DIRECT_COST',cost,'GBP',period_from=mn,period_to=mx,lineage=lin)
    _result(con,run,client,'ECON_CONTRIBUTION_0','M_C0',c0,'GBP',period_from=mn,period_to=mx,lineage=lin)
    _result(con,run,client,'ECON_CONTRIBUTION_0_MARGIN','M_C0_MARGIN',None if rev==0 else c0/rev*D('100'),'PERCENT','NOT_MEANINGFUL' if rev==0 else 'VALID',mn,mx,lineage=lin)
    # customer primitives
    groups={}
    for r in rows:
        cid=r['customer_entity_id']; g=groups.setdefault(cid,{'rev':D('0'),'cost':D('0'),'rows':[]}); g['rev']+=D(r['net_revenue']); g['cost']+=D(r['direct_cost']); g['rows'].append(r)
    for cid,g in groups.items():
        _result(con,run,client,'CUSTOMER_REVENUE','M_CUST_REVENUE',g['rev'],'GBP',period_from=mn,period_to=mx,dim_type='CUSTOMER',dim_id=cid,lineage=lin)
        _result(con,run,client,'CUSTOMER_CONTRIBUTION_0','M_CUST_C0',g['rev']-g['cost'],'GBP',period_from=mn,period_to=mx,dim_type='CUSTOMER',dim_id=cid,lineage=lin)
    # latest 12m vs prior 12m; do not fabricate growth where prior revenue is zero.
    maxd=max(date.fromisoformat(r['transaction_date']) for r in rows); cur_start=date(maxd.year-1,maxd.month,maxd.day) if not (maxd.month==2 and maxd.day==29) else date(maxd.year-1,2,28)
    prev_end=cur_start; prev_start=date(cur_start.year-1,cur_start.month,cur_start.day)
    for cid in groups:
        cur=sum((D(r['net_revenue']) for r in rows if r['customer_entity_id']==cid and date.fromisoformat(r['transaction_date'])>cur_start),D('0'))
        prev=sum((D(r['net_revenue']) for r in rows if r['customer_entity_id']==cid and prev_start < date.fromisoformat(r['transaction_date']) <= prev_end),D('0'))
        status='VALID' if prev!=0 else 'NOT_MEANINGFUL'; val=(cur-prev)/prev*D('100') if prev!=0 else None
        _result(con,run,client,'CUSTOMER_REVENUE_GROWTH','M_CUST_GROWTH',val,'PERCENT',status,prev_start.isoformat(),maxd.isoformat(),dim_type='CUSTOMER',dim_id=cid,lineage=lin)
    con.commit(); return {'COMMERCIAL_NET_REVENUE':rev,'COMMERCIAL_DIRECT_COST':cost,'ECON_CONTRIBUTION_0':c0,'ECON_CONTRIBUTION_0_MARGIN':None if rev==0 else c0/rev*D('100'),'customer_count':len(groups)}

def calculate_level1_primitives(con,run,client):
    seed_registry(con); out={}
    pnl=_latest_dv(con,client,'D01'); bs=_latest_dv(con,client,'D02'); bank=_latest_dv(con,client,'D06')
    latest_period=None
    if pnl:
        rows=con.execute("SELECT * FROM financial_statement_line WHERE client_id=? AND dataset_version_id=? AND statement_type='PNL'",(client,pnl['dataset_version_id'])).fetchall()
        if rows:
            latest_period=max(r['period_end'] for r in rows)
            # P&L flows must share the same period basis as the day-count used by working-capital ratios.
            # Accounting exports commonly contain monthly rows.  Using only the latest month while
            # multiplying by year-to-date days materially overstates DSO/DPO/DIO.  Aggregate all
            # mapped periods in the latest financial year up to the closing period; a single annual
            # row naturally remains unchanged.
            latest_year=date.fromisoformat(latest_period).year
            ytd_periods=sorted({r['period_end'] for r in rows if date.fromisoformat(r['period_end']).year==latest_year and r['period_end']<=latest_period})
            period_from=ytd_periods[0] if ytd_periods else latest_period
            for prim,method,names in [('FIN_REVENUE','M_PNL_REVENUE',ALIASES['REVENUE']),('FIN_DIRECT_COST','M_PNL_DIRECT_COST',ALIASES['DIRECT_COST']),('FIN_GROSS_PROFIT','M_PNL_GP',ALIASES['GROSS_PROFIT']),('FIN_EBITDA','M_PNL_EBITDA',ALIASES['EBITDA'])]:
                xs=[]
                for pe in ytd_periods:
                    xs.extend(_line(rows,names,pe))
                val=sum((D(x['amount']) for x in xs),D('0')) if xs else None
                status='VALID' if val is not None else 'UNAVAILABLE'; _result(con,run,client,prim,method,val,'GBP',status,period_from=period_from,period_to=latest_period,lineage=[('DATASET_VERSION',pnl['dataset_version_id'],f'mapped P&L line(s), YTD basis={period_from}..{latest_period}')])
                out[prim]=val
    else:
        for prim,method in [('FIN_REVENUE','M_PNL_REVENUE'),('FIN_DIRECT_COST','M_PNL_DIRECT_COST'),('FIN_GROSS_PROFIT','M_PNL_GP'),('FIN_EBITDA','M_PNL_EBITDA')]: _record_execution(con,run,client,prim,method,'UNAVAILABLE','D01 unavailable')
    bsvals={}; bs_period=None
    if bs:
        rows=con.execute("SELECT * FROM financial_statement_line WHERE client_id=? AND dataset_version_id=? AND statement_type='BALANCE_SHEET'",(client,bs['dataset_version_id'])).fetchall()
        if rows:
            bp=max(r['period_end'] for r in rows); bs_period=bp; latest_period=latest_period or bp
            for prim,method,key in [('BS_ACCOUNTS_RECEIVABLE','M_BS_AR','AR'),('BS_ACCOUNTS_PAYABLE','M_BS_AP','AP'),('BS_CASH','M_BS_CASH','CASH'),('BS_INVENTORY','M_BS_INVENTORY','INVENTORY')]:
                val,xs=_sum_lines(rows,ALIASES[key],bp); status='VALID' if val is not None else 'UNAVAILABLE'; _result(con,run,client,prim,method,val,'GBP',status,period_to=bp,lineage=[('DATASET_VERSION',bs['dataset_version_id'],f'mapped balance-sheet line(s), period={bp}')]); out[prim]=val; bsvals[prim]=val
    else:
        for prim,method in [('BS_ACCOUNTS_RECEIVABLE','M_BS_AR'),('BS_ACCOUNTS_PAYABLE','M_BS_AP'),('BS_CASH','M_BS_CASH'),('BS_INVENTORY','M_BS_INVENTORY')]: _record_execution(con,run,client,prim,method,'UNAVAILABLE','D02 unavailable')
    if bank:
        rows=con.execute('SELECT * FROM bank_transaction WHERE client_id=? AND dataset_version_id=? AND balance IS NOT NULL ORDER BY transaction_date,source_row_reference',(client,bank['dataset_version_id'])).fetchall()
        val=D(rows[-1]['balance']) if rows else None; status='VALID' if val is not None else 'UNAVAILABLE'; _result(con,run,client,'BANK_CLOSING_CASH','M_BANK_CLOSE',val,'GBP',status,period_to=rows[-1]['transaction_date'] if rows else None,lineage=[('DATASET_VERSION',bank['dataset_version_id'],'latest bank running balance')]); out['BANK_CLOSING_CASH']=val
    else: _record_execution(con,run,client,'BANK_CLOSING_CASH','M_BANK_CLOSE','UNAVAILABLE','D06 unavailable')
    # DSO only when compatible period revenue and AR exist.
    rev=out.get('FIN_REVENUE'); ar=out.get('BS_ACCOUNTS_RECEIVABLE'); ap=out.get('BS_ACCOUNTS_PAYABLE')
    if rev is not None and ar is not None and latest_period and bs_period==latest_period:
        days=D(_period_days(latest_period)); status='VALID' if rev!=0 else 'NOT_MEANINGFUL'; val=ar/rev*days if rev!=0 else None; _result(con,run,client,'WC_DSO','M_DSO_CLOSE',val,'DAYS',status,period_to=latest_period,lineage=[('PRIMITIVE','FIN_REVENUE','dependent primitive'),('PRIMITIVE','BS_ACCOUNTS_RECEIVABLE','dependent primitive')]); out['WC_DSO']=val
    else: _record_execution(con,run,client,'WC_DSO','M_DSO_CLOSE','UNAVAILABLE','Requires FIN_REVENUE and BS_ACCOUNTS_RECEIVABLE on a compatible period basis')
    # Ledger primitives preserve ledger economics separately from balance-sheet control balances.
    for domain,table,prefix in [('D04','ar_invoice','AR'),('D05','ap_invoice','AP')]:
        dv=_latest_dv(con,client,domain)
        prim_total=f'{prefix}_LEDGER_OUTSTANDING'; prim_over=f'{prefix}_OVERDUE_OUTSTANDING'
        meth_total=f'M_{prefix}_LEDGER'; meth_over=f'M_{prefix}_OVERDUE'
        if dv:
            inv=con.execute(f'SELECT * FROM {table} WHERE client_id=? AND dataset_version_id=?',(client,dv['dataset_version_id'])).fetchall()
            total=sum((D(x['outstanding_amount']) for x in inv),D('0'))
            asof=max((x['invoice_date'] for x in inv),default=None)
            # Use latest known financial period as the assessment date where available; never use wall-clock time.
            assessment=latest_period or asof
            overdue=sum((D(x['outstanding_amount']) for x in inv if assessment and x['due_date'] < assessment and D(x['outstanding_amount'])!=0),D('0'))
            lin=[('DATASET_VERSION',dv['dataset_version_id'],f'all {prefix} ledger invoices')]
            _result(con,run,client,prim_total,meth_total,total,'GBP',period_to=assessment,lineage=lin); out[prim_total]=total
            _result(con,run,client,prim_over,meth_over,overdue,'GBP',period_to=assessment,lineage=lin); out[prim_over]=overdue
        else:
            _record_execution(con,run,client,prim_total,meth_total,'UNAVAILABLE',f'{domain} unavailable'); _record_execution(con,run,client,prim_over,meth_over,'UNAVAILABLE',f'{domain} unavailable')
    # DPO is now permitted only with actual accounting direct cost; revenue remains forbidden as a proxy.
    direct=out.get('FIN_DIRECT_COST')
    if direct is not None and ap is not None and latest_period and bs_period==latest_period:
        days=D(_period_days(latest_period)); denom=abs(direct); status='VALID' if denom!=0 else 'NOT_MEANINGFUL'; val=ap/denom*days if denom!=0 else None
        _result(con,run,client,'WC_DPO','M_DPO_CLOSE',val,'DAYS',status,period_to=latest_period,lineage=[('PRIMITIVE','FIN_DIRECT_COST','dependent primitive'),('PRIMITIVE','BS_ACCOUNTS_PAYABLE','dependent primitive')]); out['WC_DPO']=val
    else:
        _record_execution(con,run,client,'WC_DPO','M_DPO_CLOSE','UNAVAILABLE','Requires FIN_DIRECT_COST and BS_ACCOUNTS_PAYABLE on a compatible period basis; revenue is not an allowed proxy')
    # Available cash: prefer bank evidence; fall back to balance-sheet cash. This is not Available Liquidity.
    cash=out.get('BANK_CLOSING_CASH') if out.get('BANK_CLOSING_CASH') is not None else out.get('BS_CASH')
    if cash is not None:
        src='BANK_CLOSING_CASH' if out.get('BANK_CLOSING_CASH') is not None else 'BS_CASH'
        _result(con,run,client,'AVAILABLE_CASH','M_AVAILABLE_CASH',cash,'GBP',period_to=latest_period,lineage=[('PRIMITIVE',src,'best evidenced cash source')]); out['AVAILABLE_CASH']=cash
    else: _record_execution(con,run,client,'AVAILABLE_CASH','M_AVAILABLE_CASH','UNAVAILABLE','Requires bank or balance-sheet cash evidence')
    # Inventory: prefer a same-period balance-sheet inventory balance; D12 can evidence a latest operational snapshot.
    inv=out.get('BS_INVENTORY')
    cfg=con.execute('SELECT inventory_applicability FROM business_model_config_runtime WHERE client_id=?',(client,)).fetchone()
    inventory_not_applicable = bool(cfg and cfg['inventory_applicability']=='NOT_APPLICABLE')
    invdv=_latest_dv(con,client,'D12')
    if invdv:
        snaps=con.execute('SELECT * FROM inventory_snapshot WHERE client_id=? AND dataset_version_id=? ORDER BY snapshot_date,source_row_reference',(client,invdv['dataset_version_id'])).fetchall()
        if snaps:
            snap_date=max(x['snapshot_date'] for x in snaps); snap_value=sum((D(x['inventory_value']) for x in snaps if x['snapshot_date']==snap_date),D('0'))
            _result(con,run,client,'INVENTORY_SNAPSHOT_VALUE','M_INVENTORY_SNAPSHOT',snap_value,'GBP',period_to=snap_date,lineage=[('DATASET_VERSION',invdv['dataset_version_id'],f'inventory snapshot date={snap_date}')]); out['INVENTORY_SNAPSHOT_VALUE']=snap_value
            if inv is None and latest_period==snap_date: inv=snap_value
    else: _record_execution(con,run,client,'INVENTORY_SNAPSHOT_VALUE','M_INVENTORY_SNAPSHOT','UNAVAILABLE','D12 unavailable')
    inv_period = bs_period if out.get('BS_INVENTORY') is not None else (snap_date if invdv and 'snap_date' in locals() else None)
    if inventory_not_applicable:
        _record_execution(con,run,client,'WC_DIO','M_DIO_CLOSE','N/A','Inventory is structurally not applicable to this business model')
    elif direct is not None and inv is not None and latest_period and inv_period==latest_period:
        days=D(_period_days(latest_period)); denom=abs(direct); status='VALID' if denom!=0 else 'NOT_MEANINGFUL'; dio=inv/denom*days if denom!=0 else None
        _result(con,run,client,'WC_DIO','M_DIO_CLOSE',dio,'DAYS',status,period_to=latest_period,lineage=[('PRIMITIVE','FIN_DIRECT_COST','dependent primitive'),('PRIMITIVE','BS_INVENTORY' if out.get('BS_INVENTORY') is not None else 'INVENTORY_SNAPSHOT_VALUE','dependent primitive')]); out['WC_DIO']=dio
    else: _record_execution(con,run,client,'WC_DIO','M_DIO_CLOSE','UNAVAILABLE','Requires period-compatible inventory and FIN_DIRECT_COST')
    if inventory_not_applicable and all(out.get(x) is not None for x in ('WC_DSO','WC_DPO')):
        ccc=out['WC_DSO']-out['WC_DPO']; _result(con,run,client,'WC_CCC','M_CCC',ccc,'DAYS',period_to=latest_period,lineage=[('PRIMITIVE','WC_DSO','dependent primitive'),('PRIMITIVE','WC_DPO','dependent primitive')]); out['WC_CCC']=ccc
    elif all(out.get(x) is not None for x in ('WC_DSO','WC_DIO','WC_DPO')):
        ccc=out['WC_DSO']+out['WC_DIO']-out['WC_DPO']; _result(con,run,client,'WC_CCC','M_CCC',ccc,'DAYS',period_to=latest_period,lineage=[('PRIMITIVE','WC_DSO','dependent primitive'),('PRIMITIVE','WC_DIO','dependent primitive'),('PRIMITIVE','WC_DPO','dependent primitive')]); out['WC_CCC']=ccc
    else: _record_execution(con,run,client,'WC_CCC','M_CCC','UNAVAILABLE','Requires DSO/DPO and DIO when inventory is applicable')
    con.commit(); return out

def run_primitive_engine(con,run,client,sales_dataset_version_id=None):
    seed_registry(con)
    tx=calculate_transaction_primitives(con,run,client,sales_dataset_version_id)
    l1=calculate_level1_primitives(con,run,client)
    return {'transaction':tx,'level1':l1}
