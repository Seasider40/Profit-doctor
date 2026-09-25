from pathlib import Path
from datetime import datetime, timezone
from shutil import copytree
from decimal import Decimal
import uuid, json
from .core.db import connect
from .ingestion.northstar import ingest_northstar
from .trust.engine import run_trust_layer
from .diagnostic.engine import run_diagnostic_engine
from .calc.primitive_engine import seed_registry as seed_primitives

now=lambda: datetime.now(timezone.utc).isoformat()
id4=lambda p:f'{p}_{uuid.uuid4().hex}'

def build_level3_case(db_path, fixture_root, storage_root):
    con=connect(db_path); client='level3_manufacturing'; run='level3_run'; t=now()
    con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(client,'Apex Precision Manufacturing Ltd','GBP','MANUFACTURING',t))
    con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(run,client,'QUALIFICATION',t,None,'RUNNING',None,run,'2.39'))
    con.commit()
    ing=ingest_northstar(con,client,run,fixture_root,storage_root)
    run_trust_layer(con,run,client,ing['dataset_version_id'])
    seed_primitives(con)
    # workforce/capacity
    for i in range(25):
        dep=['Sales','Engineering','Production','Production','Operations'][i%5]; role={'Sales':'Account Manager','Engineering':'Engineer','Production':'Operator','Operations':'Planner'}[dep]
        cap=1600; used=[1250,1500,1660,1720,1450][i%5]
        con.execute('INSERT INTO workforce_snapshot VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(f'w{i}',client,'2026-09-30',f'E{i+1:03}',dep,role,'1',str(42000+i*700),'6500',str(3000 if dep=='Sales' else 0),'1500','0',str(cap),str(used),'synthetic Level-3 workforce evidence'))
    con.execute('INSERT INTO commission_plan VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',('cp1',client,'Sales Growth Plan','COMMISSION','REVENUE','0.04',None,None,'Sales','Account Manager','synthetic approved plan',1))
    # suppliers/purchases/overheads
    for s in range(1,7): con.execute('INSERT INTO supplier_master VALUES (?,?,?,?,?,?,?,?)',(f'S{s}',client,f'Supplier {s}','Materials','CRITICAL' if s==1 else 'STANDARD',45,1 if s==1 else 0,'synthetic supplier master'))
    for m in range(1,10):
        for s in range(1,7):
            amt=70000*(7-s)*(1+(0.03*m if s==1 else 0)); unit=10*(1+(0.025*m if s==1 else 0))
            con.execute('INSERT INTO purchase_transaction VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(f'p{m}_{s}',client,f'2026-{m:02}-15',f'S{s}','Materials',f'P{s}',f'Component {s}','1000',f'{amt:.2f}',f'{unit:.4f}',f'INV-{m}-{s}',None,'synthetic Level-3 purchasing'))
    con.execute('INSERT INTO purchase_transaction VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',('pdup',client,'2026-09-15','S2','Materials','P2','Component 2','1000','350000.00','10','INV-9-2',None,'synthetic duplicate-looking test case'))
    for m in range(1,10):
        con.execute('INSERT INTO overhead_transaction VALUES (?,?,?,?,?,?,?,?,?,?)',(f'o{m}',client,f'2026-{m:02}-01','S6','Software','ERP/CRM',str(12000 if m<7 else 18000),f'SW-{m}','ERP','synthetic overhead evidence'))
    # forecast / KPI
    con.execute('INSERT INTO plan_version VALUES (?,?,?,?,?,?,?,?,?)',('pv1',client,'BUDGET','FY26 Board Budget','2025-12-01','2026-01-01','2026-12-31','ACTIVE','synthetic board budget'))
    for m in range(1,10):
        per=f'2026-{m:02}'; budget=1250000; actual=budget*(0.92+0.015*m); forecast=budget*(0.96+0.008*m)
        con.execute('INSERT INTO plan_line VALUES (?,?,?,?,?,?,?,?,?,?)',(f'pl{m}','pv1',client,per,'REVENUE',None,None,f'{budget:.2f}','GBP','synthetic budget'))
        con.execute('INSERT INTO actual_metric VALUES (?,?,?,?,?,?,?)',(f'am{m}',client,per,'REVENUE',f'{actual:.2f}','GBP','synthetic actual'))
        con.execute('INSERT INTO forecast_vintage VALUES (?,?,?,?,?,?,?,?)',(f'fv{m}',client,'2025-12-15',per,'REVENUE',f'{forecast:.2f}','GBP','synthetic forecast vintage'))
        con.execute('INSERT INTO kpi_observation VALUES (?,?,?,?,?,?,?,?,?,?)',(f'k{m}',client,per,'UTIL','Plant utilisation',str(78+m),'PCT','LEADING','REVENUE','synthetic ops KPI'))
    # AR snapshot dataset for customer payment quality
    sf=id4('src'); job=id4('ing'); ds=id4('ds'); dv=id4('dsv')
    con.execute('INSERT INTO ingestion_job VALUES (?,?,?,?,?,?,?)',(job,run,client,t,t,'COMPLETED',None)); con.execute('INSERT INTO source_file VALUES (?,?,?,?,?,?,?,?)',(sf,client,'ar_aging.csv','synthetic://ar','level3-ar-hash',1,1,t)); con.execute('INSERT INTO dataset VALUES (?,?,?,?,?,?)',(ds,client,sf,'D04','level3:ar',t)); con.execute('INSERT INTO dataset_version VALUES (?,?,?,?,?,?,?,?,?,?)',(dv,ds,job,sf,1,12,'2026-09-30','2026-09-30','COMPLETED',t))
    aliases=con.execute("SELECT source_entity_key FROM entity_alias WHERE client_id=? AND source_entity_key LIKE 'C%' LIMIT 12",(client,)).fetchall()
    for i,a in enumerate(aliases):
        out=100000+i*12000; due='2026-08-15' if i<8 else '2026-10-15'
        con.execute('INSERT INTO ar_invoice VALUES (?,?,?,?,?,?,?,?,?,?)',(f'ar{i}',client,f'AR{i}',a['source_entity_key'],'2026-07-15',due,str(out),str(out),dv,i+2))
    # WC primitives
    vals=[('WC_DSO','58','DAYS'),('WC_DIO','72','DAYS'),('WC_DPO','47','DAYS'),('WC_CCC','83','DAYS'),('BS_ACCOUNTS_RECEIVABLE','2800000','GBP'),('AR_LEDGER_OUTSTANDING','2720000','GBP'),('AR_OVERDUE_OUTSTANDING','1650000','GBP'),('BS_ACCOUNTS_PAYABLE','1900000','GBP'),('AP_LEDGER_OUTSTANDING','1870000','GBP'),('AP_OVERDUE_OUTSTANDING','310000','GBP'),('BS_INVENTORY','2200000','GBP'),('INVENTORY_SNAPSHOT_VALUE','2140000','GBP'),('AVAILABLE_CASH','210000','GBP')]
    for i,(pid,val,unit) in enumerate(vals): con.execute('INSERT INTO primitive_result VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(f'l3pr{i}',run,client,pid,'L3_SYNTHETIC',None,None,None,None,val,unit,'VALID',t))
    # D15 CRM / pipeline / win-loss evidence (canonical v2.40 qualification)
    from profit_doctor.crm import ingest_crm, analyse_crm
    opps=[]
    stages=['QUALIFY','DISCOVERY','PROPOSAL','NEGOTIATION']
    for i in range(1,31):
        status='OPEN' if i<=14 else ('WON' if i<=23 else 'LOST')
        opps.append({'opportunity_id':f'crm{i}','source_opportunity_key':f'OPP-{i:03}','opportunity_name':f'Precision opportunity {i}','owner_key':f'SALES-{1+(i%4)}','created_date':f'2026-{1+(i%7):02}-05','expected_close_date':f'2026-{6+(i%6):02}-20','actual_close_date':None if status=='OPEN' else f'2026-{6+(i%3):02}-25','stage':stages[i%4] if status=='OPEN' else status,'status':status,'amount':str(45000+i*7000),'probability_pct':str([20,40,60,80][i%4]) if status=='OPEN' else ('100' if status=='WON' else '0'),'lost_reason':'PRICE' if status=='LOST' and i%2 else ('TIMING' if status=='LOST' else None),'source_system':'SYNTHETIC_CRM','evidence_note':'Level-3 synthetic CRM evidence'})
    ingest_crm(con,client,opps)
    crm_summary=analyse_crm(con,run,client)
    # risk/control evidence
    con.execute('INSERT INTO financial_integrity VALUES (?,?,?,?,?,?,?,?)',('fi1',run,client,'D03_TB_GL','MATERIALLY_CONSTRAINED','Synthetic control reconciliation requires review','Investigate reconciliation difference',t))
    con.execute('INSERT INTO control_exception VALUES (?,?,?,?,?,?,?,?,?,?)',('ce1',client,'2026-09-20','AP','DUPLICATE_LOOKING','Two invoice records share supplier/date/value/reference','350000','dup-ap','synthetic exception evidence','OPEN'))
    con.execute('INSERT INTO financial_exposure_evidence VALUES (?,?,?,?,?,?,?,?,?)',('fe1',client,'2026-09-20','SUPPLIER_DEPENDENCY','Critical component has single-source dependency','1400000','42','PARTIAL','synthetic contract/risk evidence'))
    con.commit()
    out=run_diagnostic_engine(con,run,client,ing['dataset_version_id'])
    rows=con.execute('SELECT test_id,execution_status,eligibility_state,signal_count FROM test_execution WHERE run_id=? ORDER BY test_id',(run,)).fetchall()
    summary={'crm':crm_summary,'client_id':client,'run_id':run,'diagnostics_total':len(rows),'completed':sum(r['execution_status']=='COMPLETED' for r in rows),'not_run':[r['test_id'] for r in rows if r['execution_status']!='COMPLETED'],'signals':con.execute('SELECT count(*) n FROM signal WHERE run_id=?',(run,)).fetchone()['n']}
    return con,summary
