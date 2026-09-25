from decimal import Decimal
from datetime import datetime, timezone
import uuid

now=lambda: datetime.now(timezone.utc).isoformat()
id4=lambda p: f"{p}_{uuid.uuid4().hex}"
D=lambda x: Decimal(str(x))

SALES_DOMAIN='D07_SALES_TRANSACTIONS'

# First Trust-layer contract. This deliberately assesses what is evidenced rather
# than pretending unavailable accounting/AR/AP domains exist in Northstar.
def assess_sales_trust(con, run_id, client_id, dataset_version_id):
    rows=con.execute('''SELECT * FROM sales_transaction WHERE client_id=? AND dataset_version_id=? AND record_status='ACTIVE' ''',(client_id,dataset_version_id)).fetchall()
    n=len(rows)
    months=sorted({r['transaction_date'][:7] for r in rows if r['transaction_date']})
    pfrom=min((r['transaction_date'] for r in rows),default=None); pto=max((r['transaction_date'] for r in rows),default=None)
    history=len(months)
    state='AVAILABLE' if n else 'UNAVAILABLE'
    con.execute('INSERT INTO data_availability VALUES (?,?,?,?,?,?,?,?,?,?,?)',(id4('avail'),run_id,client_id,SALES_DOMAIN,state,history,n,pfrom,pto,dataset_version_id,now()))

    required=['source_transaction_key','transaction_date','customer_entity_id','product_entity_id','net_revenue','direct_cost']
    cells=n*len(required)
    present=sum(1 for r in rows for f in required if r[f] not in (None,''))
    completeness=(D(present)*100/D(cells)) if cells else None
    keys=[r['source_transaction_key'] for r in rows]
    uniqueness=(D(len(set(keys)))*100/D(len(keys))) if keys else None
    valid=0
    for r in rows:
        try:
            Decimal(r['net_revenue']); Decimal(r['direct_cost']); valid+=1
        except Exception: pass
    validity=(D(valid)*100/D(n)) if n else None
    qstate='UNUSABLE' if not n else ('RELIABLE' if completeness==100 and uniqueness==100 and validity==100 else ('USABLE_WITH_LIMITATION' if (completeness or 0)>=95 and (validity or 0)>=95 else 'MATERIALLY_CONSTRAINED'))
    limits=[]
    if completeness is not None and completeness<100: limits.append(f'Completeness {completeness:.2f}%')
    if uniqueness is not None and uniqueness<100: limits.append(f'Uniqueness {uniqueness:.2f}%')
    if validity is not None and validity<100: limits.append(f'Validity {validity:.2f}%')
    con.execute('INSERT INTO data_quality_assessment VALUES (?,?,?,?,?,?,?,?,?,?,?)',(id4('qual'),run_id,client_id,SALES_DOMAIN,qstate,str(completeness) if completeness is not None else None,str(validity) if validity is not None else None,str(uniqueness) if uniqueness is not None else None,'CURRENT', '; '.join(limits) or None,now()))

    revenue=sum((Decimal(r['net_revenue']) for r in rows if r['net_revenue'] not in (None,'')),Decimal('0'))
    for typ,field in [('CUSTOMER','customer_entity_id'),('PRODUCT','product_entity_id')]:
        mapped=[r for r in rows if r[field]]
        mapped_rev=sum((Decimal(r['net_revenue']) for r in mapped if r['net_revenue'] not in (None,'')),Decimal('0'))
        cp=(D(len(mapped))*100/D(n)) if n else None; ep=(mapped_rev*100/revenue) if revenue else None
        con.execute('INSERT INTO mapping_coverage VALUES (?,?,?,?,?,?,?,?,?,?)',(id4('map'),run_id,client_id,SALES_DOMAIN,typ,len(mapped),n,str(cp) if cp is not None else None,str(ep) if ep is not None else None,now()))

    # Internal arithmetic reconciliation only: transaction revenue - direct cost = calculated contribution 0.
    calc_gp=sum((Decimal(r['net_revenue'])-Decimal(r['direct_cost']) for r in rows),Decimal('0')) if n else Decimal('0')
    source_gp=sum((Decimal(r['source_gross_profit']) for r in rows if r['source_gross_profit'] not in (None,'')),Decimal('0'))
    residual=source_gp-calc_gp
    tolerance=max(Decimal('10.00'), abs(calc_gp)*Decimal('0.00001'))
    rec_status='RECONCILED' if abs(residual)<=tolerance else 'FAILED'
    con.execute('INSERT INTO reconciliation VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(id4('rec'),run_id,client_id,'SALES_GP_ARITHMETIC','SOURCE_GROSS_PROFIT','REVENUE_MINUS_DIRECT_COST',str(source_gp),str(calc_gp),str(residual),rec_status,(f'Immaterial rounding residual {residual} within tolerance {tolerance}' if residual!=0 and rec_status=='RECONCILED' else (None if residual==0 else 'Source gross profit does not reconcile to revenue less direct cost')),now()))
    integrity='RELIABLE' if rec_status=='RECONCILED' and qstate=='RELIABLE' else ('USABLE_WITH_LIMITATION' if rec_status=='RECONCILED' and qstate!='UNUSABLE' else 'MATERIALLY_CONSTRAINED')
    con.execute('INSERT INTO financial_integrity VALUES (?,?,?,?,?,?,?,?)',(id4('int'),run_id,client_id,SALES_DOMAIN,integrity,'Internal transaction arithmetic reconciliation',None if integrity=='RELIABLE' else '; '.join(limits) or 'Reconciliation failure',now()))
    con.commit()
    return {'availability':state,'history_months':history,'row_count':n,'quality':qstate,'integrity':integrity,'reconciliation':rec_status}

def assess_test_eligibility(con, run_id, client_id, test_id, dataset_version_id, min_history_months=24, needs_customer=False, needs_product=False):
    # Reuse persisted trust assessments; this is deterministic and test-specific.
    a=con.execute('SELECT * FROM data_availability WHERE run_id=? AND client_id=? AND data_domain=? ORDER BY assessed_at DESC LIMIT 1',(run_id,client_id,SALES_DOMAIN)).fetchone()
    q=con.execute('SELECT * FROM data_quality_assessment WHERE run_id=? AND client_id=? AND data_domain=? ORDER BY assessed_at DESC LIMIT 1',(run_id,client_id,SALES_DOMAIN)).fetchone()
    integ=con.execute('SELECT * FROM financial_integrity WHERE run_id=? AND client_id=? AND data_domain=? ORDER BY assessed_at DESC LIMIT 1',(run_id,client_id,SALES_DOMAIN)).fetchone()
    limitations=[]; eligibility='FULL'; method='L2_TRANSACTION'
    if not a or a['availability_state']!='AVAILABLE': eligibility='UNAVAILABLE'; method=None; limitations.append('Sales transactions unavailable')
    elif (a['history_months'] or 0)<min_history_months: eligibility='PARTIAL-A'; limitations.append(f"Only {a['history_months']} months history; {min_history_months} required for full method")
    if q and q['quality_state']=='MATERIALLY_CONSTRAINED' and eligibility!='UNAVAILABLE': eligibility='PARTIAL-B'; limitations.append('Sales data quality materially constrained')
    if q and q['quality_state']=='UNUSABLE': eligibility='UNAVAILABLE'; method=None; limitations.append('Sales data unusable')
    if integ and integ['integrity_state']=='MATERIALLY_CONSTRAINED' and eligibility!='UNAVAILABLE': eligibility='PARTIAL-C'; limitations.append('Financial integrity materially constrained')
    covs=[]
    for need,typ in [(needs_customer,'CUSTOMER'),(needs_product,'PRODUCT')]:
        if need:
            m=con.execute('SELECT * FROM mapping_coverage WHERE run_id=? AND client_id=? AND mapping_type=? ORDER BY assessed_at DESC LIMIT 1',(run_id,client_id,typ)).fetchone()
            cov=Decimal(m['economic_coverage_pct']) if m and m['economic_coverage_pct'] else Decimal('0'); covs.append(cov)
            if cov<Decimal('95') and eligibility!='UNAVAILABLE': eligibility='PARTIAL-B'; limitations.append(f'{typ.title()} economic mapping coverage {cov:.2f}%')
    ec=min(covs) if covs else Decimal('100')
    con.execute('INSERT INTO economic_coverage VALUES (?,?,?,?,?,?,?,?,?,?)',(id4('ecov'),run_id,client_id,test_id,'REVENUE',None,None,str(ec),'; '.join(limitations) or None,now()))
    con.execute('INSERT OR REPLACE INTO test_eligibility VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(id4('elig'),run_id,client_id,test_id,'APPLICABLE',eligibility,method,q['quality_state'] if q else None,integ['integrity_state'] if integ else None,str(ec),'; '.join(limitations) or None,now()))
    con.commit()
    return {'test_id':test_id,'eligibility':eligibility,'method':method,'economic_coverage_pct':ec,'limitations':limitations}

def run_trust_layer(con, run_id, client_id, dataset_version_id):
    base=assess_sales_trust(con,run_id,client_id,dataset_version_id)
    domains=assess_domain_inventory(con,run_id,client_id)
    tests={}
    specs=[('REV-01',24,False,False),('REV-02',24,False,False),('REV-03',24,True,False),('REV-04',24,False,True),('REV-05',24,False,False),('REV-06',24,False,False),('GM-01',24,False,False),('GM-02',24,False,False),('GM-03',24,True,False),('GM-04',24,False,True),('GM-05',24,False,True),('GM-06',24,False,True),('GM-07',12,False,False),('CUS-01',12,True,False),('CUS-02',12,True,False),('CUS-03',12,True,False),('CUS-04',24,True,False),('CUS-05',24,True,False),('CUS-06',12,True,False),('CUS-07',12,True,False),('PROD-01',12,False,True),('PROD-02',24,False,True),('PROD-03',24,False,True),('PROD-04',12,False,True),('PROD-05',12,True,True),('PRI-01',24,True,True),('PRI-02',12,True,True),('PRI-03',12,False,True),('PRI-04',24,False,True),('PRI-05',12,True,True)]
    for tid,h,c,p in specs: tests[tid]=assess_test_eligibility(con,run_id,client_id,tid,dataset_version_id,h,c,p)
    return {'trust':base,'domains':domains,'tests':tests}

DATA_DOMAINS = {
'D01':'P&L / Management Accounts','D02':'Balance Sheet','D03':'TB / GL','D04':'Sales Ledger / AR / Invoices',
'D05':'Purchase Ledger / AP / Invoices','D06':'Cash / Bank','D07':'Sales Transactions','D08':'Customer Master / Hierarchy',
'D09':'Product / Service Master','D10':'Direct Cost / Transaction Margin','D11':'Payroll / Workforce / Departments',
'D12':'Inventory','D13':'Budget / Forecast','D14':'Detailed Pricing / Discounts / Rebates','D15':'CRM / Pipeline / Win-Loss',
'D16':'Operational / Capacity KPIs','D17':'Contracts / Commercial Terms','D18':'Users / Approvals / Master-Data / Control Evidence'}

def assess_domain_inventory(con, run_id, client_id):
    """Persist an explicit availability record for every canonical data domain.
    Missing evidence is UNAVAILABLE, never silently assumed."""
    present={r['data_domain']:r for r in con.execute('''SELECT d.data_domain,dv.dataset_version_id,dv.row_count,dv.period_from,dv.period_to
        FROM dataset d JOIN dataset_version dv ON dv.dataset_id=d.dataset_id
        WHERE d.client_id=? AND dv.version_number=(SELECT max(x.version_number) FROM dataset_version x WHERE x.dataset_id=d.dataset_id)''',(client_id,))}
    # D10 is evidenced within D07 in Northstar because direct cost is populated transaction-by-transaction.
    if 'D07_SALES_TRANSACTIONS' in present:
        present['D10_DIRECT_COST_TRANSACTION_MARGIN']=present['D07_SALES_TRANSACTIONS']
    aliases={'D07':'D07_SALES_TRANSACTIONS','D08':'D08_CUSTOMER_MASTER','D09':'D09_PRODUCT_MASTER','D10':'D10_DIRECT_COST_TRANSACTION_MARGIN'}
    out={}
    for code,name in DATA_DOMAINS.items():
        key=aliases.get(code,code); r=present.get(key); state='AVAILABLE' if r else 'UNAVAILABLE'
        out[code]=state
        # D07 already has detailed availability from assess_sales_trust; avoid duplicate record.
        if code=='D07': continue
        con.execute('INSERT INTO data_availability VALUES (?,?,?,?,?,?,?,?,?,?,?)',(id4('avail'),run_id,client_id,code,state,None,r['row_count'] if r else 0,r['period_from'] if r else None,r['period_to'] if r else None,r['dataset_version_id'] if r else None,now()))
    con.commit(); return out

ACCOUNTING_DOMAIN_TABLES={
'D01':('financial_statement_line',"statement_type='PNL'",'dataset_version_id'),
'D02':('financial_statement_line',"statement_type='BALANCE_SHEET'",'dataset_version_id'),
'D03':('trial_balance','1=1','dataset_version_id'),
'D04':('ar_invoice','1=1','dataset_version_id'),
'D05':('ap_invoice','1=1','dataset_version_id'),
'D06':('bank_transaction','1=1','dataset_version_id')}

def assess_level1_accounting_trust(con,run_id,client_id):
    """Assess D01-D06 with domain-specific integrity rules. Missing domains remain explicit UNAVAILABLE."""
    out={}
    for code,(table,where,dvcol) in ACCOUNTING_DOMAIN_TABLES.items():
        ds=con.execute('SELECT d.dataset_id,dv.dataset_version_id,dv.row_count,dv.period_from,dv.period_to FROM dataset d JOIN dataset_version dv ON dv.dataset_id=d.dataset_id WHERE d.client_id=? AND d.data_domain=? ORDER BY dv.version_number DESC LIMIT 1',(client_id,code)).fetchone()
        if not ds:
            out[code]={'availability':'UNAVAILABLE','quality':'UNAVAILABLE','integrity':'UNAVAILABLE'}; continue
        rows=con.execute(f'SELECT * FROM {table} WHERE client_id=? AND {where} AND {dvcol}=?',(client_id,ds['dataset_version_id'])).fetchall()
        n=len(rows); q='RELIABLE' if n else 'UNUSABLE'; integ='RELIABLE'; limitation=None
        if code=='D03' and n:
            deb=sum((Decimal(r['debit']) for r in rows),Decimal('0')); cred=sum((Decimal(r['credit']) for r in rows),Decimal('0')); residual=deb-cred
            status='RECONCILED' if abs(residual)<=Decimal('0.01') else 'FAILED'
            con.execute('INSERT INTO reconciliation VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(id4('rec'),run_id,client_id,'TRIAL_BALANCE_DEBITS_CREDITS','TOTAL_DEBITS','TOTAL_CREDITS',str(deb),str(cred),str(residual),status,None if status=='RECONCILED' else 'Trial balance does not balance',now()))
            if status=='FAILED': integ='MATERIALLY_CONSTRAINED'; limitation='Trial balance does not balance'
        elif code in ('D04','D05') and n:
            bad=sum(1 for r in rows if Decimal(r['outstanding_amount'])<0 or Decimal(r['outstanding_amount'])>Decimal(r['original_amount']))
            if bad: integ='USABLE_WITH_LIMITATION'; limitation=f'{bad} invoice(s) have abnormal outstanding balances'
        elif code=='D06' and n:
            ordered=sorted(rows,key=lambda r:(r['transaction_date'],r['source_row_reference']))
            withbal=[r for r in ordered if r['balance'] not in (None,'')]
            if len(withbal)>=2:
                # Balance movement should equal transaction amount for all rows after first when every row has balance.
                bad=0
                for prev,cur in zip(withbal,withbal[1:]):
                    if abs((Decimal(cur['balance'])-Decimal(prev['balance']))-Decimal(cur['amount']))>Decimal('0.01'): bad+=1
                if bad: integ='USABLE_WITH_LIMITATION'; limitation=f'{bad} bank balance movement(s) do not reconcile to transaction amount'
        con.execute('INSERT INTO data_quality_assessment VALUES (?,?,?,?,?,?,?,?,?,?,?)',(id4('qual'),run_id,client_id,code,q,'100','100','100','CURRENT',None,now()))
        con.execute('INSERT INTO financial_integrity VALUES (?,?,?,?,?,?,?,?)',(id4('int'),run_id,client_id,code,integ,'Domain-specific Level 1 integrity contract',limitation,now()))
        out[code]={'availability':'AVAILABLE','quality':q,'integrity':integ,'row_count':n,'limitation':limitation}
    con.commit(); return out

def assess_level1_eligibility(con,run_id,client_id,test_id,required_domains,partial_domains=()):
    states={}
    for d in required_domains:
        r=con.execute('SELECT integrity_state FROM financial_integrity WHERE run_id=? AND client_id=? AND data_domain=? ORDER BY assessed_at DESC LIMIT 1',(run_id,client_id,d)).fetchone()
        states[d]=r['integrity_state'] if r else 'UNAVAILABLE'
    missing=[d for d,v in states.items() if v=='UNAVAILABLE']
    constrained=[d for d,v in states.items() if v=='MATERIALLY_CONSTRAINED']
    limited=[d for d,v in states.items() if v=='USABLE_WITH_LIMITATION']
    if missing:
        eligibility='PARTIAL-A' if any(d in partial_domains for d in missing) else 'UNAVAILABLE'
    elif constrained: eligibility='PARTIAL-C'
    elif limited: eligibility='PARTIAL-B'
    else: eligibility='FULL'
    lim=[]
    if missing: lim.append('Unavailable: '+','.join(missing))
    if constrained: lim.append('Materially constrained: '+','.join(constrained))
    if limited: lim.append('Limited integrity: '+','.join(limited))
    con.execute('INSERT OR REPLACE INTO test_eligibility VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(id4('elig'),run_id,client_id,test_id,'APPLICABLE',eligibility,'L1_ACCOUNTING' if eligibility!='UNAVAILABLE' else None,None,';'.join(states.values()),None,'; '.join(lim) or None,now()))
    con.commit(); return {'test_id':test_id,'eligibility':eligibility,'domains':states,'limitations':lim}

def _latest_dataset(con,client,domain):
    return con.execute('''SELECT d.dataset_id,dv.* FROM dataset d JOIN dataset_version dv ON dv.dataset_id=d.dataset_id
      WHERE d.client_id=? AND d.data_domain=? AND dv.ingestion_status IN ('COMPLETED','CANONICALIZED','INGESTED') ORDER BY dv.version_number DESC LIMIT 1''',(client,domain)).fetchone()

def _fs_amount(con,client,domain,statement_type,aliases):
    ds=_latest_dataset(con,client,domain)
    if not ds: return None,None
    rows=con.execute('SELECT * FROM financial_statement_line WHERE client_id=? AND dataset_version_id=? AND statement_type=?',(client,ds['dataset_version_id'],statement_type)).fetchall()
    if not rows: return None,None
    period=max(r['period_end'] for r in rows); names={x.upper() for x in aliases}
    vals=[Decimal(r['amount']) for r in rows if r['period_end']==period and ((r['line_code'] or '').upper() in names or (r['line_name'] or '').upper() in names)]
    return (sum(vals,Decimal('0')) if vals else None),period

def _record_cross(con,run,client,typ,period,left_name,right_name,left,right,tolerance,status,effect,lim=None):
    con.execute('INSERT INTO cross_source_reconciliation VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(
      id4('xrec'),run,client,typ,period,left_name,right_name,None if left is None else str(left),None if right is None else str(right),
      None if left is None or right is None else str(left-right),str(tolerance),status,effect,lim,now()))

def assess_cross_source_reconciliations(con,run_id,client_id):
    """Cross-source integrity matrix. A source can be internally clean yet disagree with another source."""
    out={}
    pnl_rev,pnl_period=_fs_amount(con,client_id,'D01','PNL',{'REV','REVENUE','SALES','TURNOVER','NET_REVENUE'})
    sales=_latest_dataset(con,client_id,'D07_SALES_TRANSACTIONS')
    if pnl_rev is not None and sales:
        rows=con.execute("SELECT transaction_date,net_revenue FROM sales_transaction WHERE client_id=? AND dataset_version_id=? AND record_status='ACTIVE'",(client_id,sales['dataset_version_id'])).fetchall()
        # Compare only the P&L calendar year/period end scope, never all transaction history.
        yr=pnl_period[:4]; tx=sum((Decimal(r['net_revenue']) for r in rows if r['transaction_date'][:4]==yr and r['transaction_date']<=pnl_period),Decimal('0'))
        tol=max(Decimal('10'),abs(pnl_rev)*Decimal('0.001')); status='RECONCILED' if abs(pnl_rev-tx)<=tol else 'FAILED'
        _record_cross(con,run_id,client_id,'SALES_TO_PNL_REVENUE',pnl_period,'PNL_REVENUE','SALES_TRANSACTIONS',pnl_rev,tx,tol,status,'MATERIAL' if status=='FAILED' else 'NONE',None if status=='RECONCILED' else 'Commercial sales do not reconcile to recognised P&L revenue for the comparable period.')
        out['SALES_TO_PNL_REVENUE']=status
    bs_ar,bs_period=_fs_amount(con,client_id,'D02','BALANCE_SHEET',{'AR','ACCOUNTS_RECEIVABLE','TRADE_RECEIVABLES','TRADE DEBTORS','DEBTORS'})
    ar=_latest_dataset(con,client_id,'D04')
    if bs_ar is not None and ar:
        led=sum((Decimal(r['outstanding_amount']) for r in con.execute('SELECT outstanding_amount FROM ar_invoice WHERE client_id=? AND dataset_version_id=?',(client_id,ar['dataset_version_id']))),Decimal('0'))
        tol=max(Decimal('10'),abs(bs_ar)*Decimal('0.002')); status='RECONCILED' if abs(bs_ar-led)<=tol else 'FAILED'
        _record_cross(con,run_id,client_id,'AR_LEDGER_TO_BS',bs_period,'BS_AR','AR_LEDGER',bs_ar,led,tol,status,'MATERIAL' if status=='FAILED' else 'NONE',None if status=='RECONCILED' else 'AR subledger does not reconcile to the balance-sheet receivables control balance.')
        out['AR_LEDGER_TO_BS']=status
    bs_ap,_=_fs_amount(con,client_id,'D02','BALANCE_SHEET',{'AP','ACCOUNTS_PAYABLE','TRADE_PAYABLES','TRADE CREDITORS','CREDITORS'})
    ap=_latest_dataset(con,client_id,'D05')
    if bs_ap is not None and ap:
        led=sum((Decimal(r['outstanding_amount']) for r in con.execute('SELECT outstanding_amount FROM ap_invoice WHERE client_id=? AND dataset_version_id=?',(client_id,ap['dataset_version_id']))),Decimal('0'))
        tol=max(Decimal('10'),abs(bs_ap)*Decimal('0.002')); status='RECONCILED' if abs(bs_ap-led)<=tol else 'FAILED'
        _record_cross(con,run_id,client_id,'AP_LEDGER_TO_BS',bs_period,'BS_AP','AP_LEDGER',bs_ap,led,tol,status,'MATERIAL' if status=='FAILED' else 'NONE',None if status=='RECONCILED' else 'AP subledger does not reconcile to the balance-sheet payables control balance.')
        out['AP_LEDGER_TO_BS']=status
    bs_cash,_=_fs_amount(con,client_id,'D02','BALANCE_SHEET',{'CASH','CASH_AT_BANK','BANK','CASH AND CASH EQUIVALENTS'})
    bank=_latest_dataset(con,client_id,'D06')
    if bs_cash is not None and bank:
        br=con.execute("SELECT balance FROM bank_transaction WHERE client_id=? AND dataset_version_id=? AND balance IS NOT NULL ORDER BY transaction_date DESC,source_row_reference DESC LIMIT 1",(client_id,bank['dataset_version_id'])).fetchone(); bank_cash=Decimal(br['balance']) if br else None
        if bank_cash is not None:
            tol=max(Decimal('10'),abs(bs_cash)*Decimal('0.001')); status='RECONCILED' if abs(bs_cash-bank_cash)<=tol else 'FAILED'
            _record_cross(con,run_id,client_id,'BANK_TO_BS_CASH',bs_period,'BS_CASH','BANK_CLOSING_CASH',bs_cash,bank_cash,tol,status,'MATERIAL' if status=='FAILED' else 'NONE',None if status=='RECONCILED' else 'Bank closing balance does not reconcile to balance-sheet cash.')
            out['BANK_TO_BS_CASH']=status
    # Failed cross-source reconciliations constrain the affected domain without rewriting source evidence.
    effects={'SALES_TO_PNL_REVENUE':['D01','D07_SALES_TRANSACTIONS'],'AR_LEDGER_TO_BS':['D02','D04'],'AP_LEDGER_TO_BS':['D02','D05'],'BANK_TO_BS_CASH':['D02','D06']}
    for typ,status in out.items():
        if status=='FAILED':
            for d in effects[typ]:
                con.execute("UPDATE financial_integrity SET integrity_state='MATERIALLY_CONSTRAINED', limitation=COALESCE(limitation||'; ','')||? WHERE run_id=? AND client_id=? AND data_domain=?",(f'Cross-source reconciliation failed: {typ}',run_id,client_id,d))
    con.commit(); return out

def set_business_model_runtime(con,client_id,business_model_type,inventory_applicability='AUTO'):
    if inventory_applicability not in ('AUTO','APPLICABLE','NOT_APPLICABLE'): raise ValueError('Invalid inventory applicability')
    con.execute('INSERT OR REPLACE INTO business_model_config_runtime VALUES (?,?,?,?,?)',(client_id,business_model_type,inventory_applicability,1,now())); con.commit()
