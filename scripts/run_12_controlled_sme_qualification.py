import csv,json,tempfile,uuid,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from profit_doctor.core.db import connect
from profit_doctor.ingestion.accounting import ingest_accounting_file
from profit_doctor.ingestion.northstar import ingest_northstar
from profit_doctor.trust.engine import run_trust_layer,assess_level1_accounting_trust,assess_cross_source_reconciliations
from profit_doctor.calc.primitive_engine import run_primitive_engine
from profit_doctor.diagnostic.engine import run_diagnostic_engine
from profit_doctor.reasoning.engine import run_reasoning_engine
from profit_doctor.economic.engine import run_economic_engine
from qualification.real_sme.programme import CASES
NOW='2026-09-25T11:30:00+01:00'
ROOT=Path(__file__).resolve().parents[1]
NS=ROOT/'tests'/'fixtures'/'northstar'

def write(p,fields,rows):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def accounting_files(d,case):
 # 12 monthly periods, coherent by default. Deliberately irregular for project/services.
 revs=[]
 base={'PRODUCT_DISTRIBUTION':300000,'PROFESSIONAL_SERVICES':220000,'SUBSCRIPTION':260000,'PROJECT_CONTRACT':280000,'HOSPITALITY_TRANSACTIONAL':180000,'HYBRID':320000}[case.business_model]
 for m in range(1,13):
  factor=1+(m-1)*0.012
  if case.business_model=='PROJECT_CONTRACT': factor=[.55,1.4,.7,1.65,.5,1.2,.8,1.55,.65,1.3,.75,1.6][m-1]
  if case.business_model=='PROFESSIONAL_SERVICES': factor*= [0.75,1.1,1.0,1.2,.85,1.15,.9,1.25,.8,1.1,.95,1.2][m-1]
  rev=round(base*factor,2); cost=round(rev*(.62 if case.business_model in ('PRODUCT_DISTRIBUTION','HOSPITALITY_TRANSACTIONAL','HYBRID') else .42),2); gp=rev-cost; ebitda=round(gp-rev*.22,2)
  pe=f'2026-{m:02d}-28' if m==2 else f'2026-{m:02d}-30'
  revs.append((pe,rev,cost,gp,ebitda))
 pnl=[]
 for pe,rev,cost,gp,eb in revs:
  pnl += [{'period_end':pe,'line_code':'REV','line_name':'Revenue','amount':rev},{'period_end':pe,'line_code':'COGS','line_name':'Cost of Sales','amount':cost},{'period_end':pe,'line_code':'GP','line_name':'Gross Profit','amount':gp},{'period_end':pe,'line_code':'EBITDA','line_name':'EBITDA','amount':eb}]
 # Enhanced cases reconcile the annual accounting control total to 2025 commercial transactions.
 if case.data_state in ('L2_ENHANCED','L3_ADVANCED'):
  import csv as _csv
  from decimal import Decimal as _D
  tx=list(_csv.DictReader(open(NS/'transactions.csv',encoding='utf-8')))
  annual=float(sum((_D(x['revenue']) for x in tx if x['month'].startswith('2025')), _D('0')))
  direct=float(sum((_D(x['direct_cost']) for x in tx if x['month'].startswith('2025')), _D('0')))
  gp=annual-direct; eb=gp-annual*.22
  pnl=[{'period_end':'2025-12-31','line_code':'REV','line_name':'Revenue','amount':annual},{'period_end':'2025-12-31','line_code':'COGS','line_name':'Cost of Sales','amount':direct},{'period_end':'2025-12-31','line_code':'GP','line_name':'Gross Profit','amount':gp},{'period_end':'2025-12-31','line_code':'EBITDA','line_name':'EBITDA','amount':eb}]
 write(d/'pnl.csv',['period_end','line_code','line_name','amount'],pnl)
 annual=sum(x[1] for x in revs) if case.data_state in ('L1_CORE','L1_MESSY') else annual; ar=round(annual/365*(62 if case.case_id in ('SME-002','SME-011') else 42),2); ap=round((sum(x[2] for x in revs) if case.data_state in ('L1_CORE','L1_MESSY') else direct)/365*38,2); cash=round(annual*.055,2)
 inv=0 if case.business_model in ('PROFESSIONAL_SERVICES','SUBSCRIPTION','PROJECT_CONTRACT') else round(sum(x[2] for x in revs)/365*58,2)
 bs_ar=ar*1.35 if case.case_id=='SME-011' else ar
 bs_cash=cash*1.7 if case.case_id=='SME-012' else cash
 bs=[{'period_end':'2026-12-30','line_code':'AR','line_name':'Trade Debtors','amount':bs_ar},{'period_end':'2026-12-30','line_code':'AP','line_name':'Trade Creditors','amount':ap},{'period_end':'2026-12-30','line_code':'CASH','line_name':'Cash','amount':bs_cash}]
 if inv: bs.append({'period_end':'2026-12-30','line_code':'INVENTORY','line_name':'Inventory','amount':inv})
 write(d/'bs.csv',['period_end','line_code','line_name','amount'],bs)
 # Balanced TB simple
 write(d/'tb.csv',['period_end','account_code','account_name','account_type','debit','credit'],[{'period_end':'2026-12-30','account_code':'1000','account_name':'Cash','account_type':'ASSET','debit':1000,'credit':0},{'period_end':'2026-12-30','account_code':'4000','account_name':'Sales','account_type':'REVENUE','debit':0,'credit':1000}])
 write(d/'ar.csv',['invoice_id','customer_id','invoice_date','due_date','original_amount','outstanding_amount'],[{'invoice_id':'AR1','customer_id':'C1','invoice_date':'2026-11-01','due_date':'2026-11-30','original_amount':ar*.55,'outstanding_amount':ar*.55},{'invoice_id':'AR2','customer_id':'C2','invoice_date':'2026-12-01','due_date':'2026-12-31','original_amount':ar*.45,'outstanding_amount':ar*.45}])
 write(d/'ap.csv',['invoice_id','supplier_id','invoice_date','due_date','original_amount','outstanding_amount'],[{'invoice_id':'AP1','supplier_id':'S1','invoice_date':'2026-11-01','due_date':'2026-11-30','original_amount':ap,'outstanding_amount':ap}])
 if case.case_id!='SME-011':
  bankbal=cash if case.case_id!='SME-012' else cash
  write(d/'bank.csv',['transaction_id','transaction_date','amount','balance'],[{'transaction_id':'B1','transaction_date':'2026-12-29','amount':100,'balance':bankbal-100},{'transaction_id':'B2','transaction_date':'2026-12-30','amount':100,'balance':bankbal}])

def run_case(case,outdir):
 d=outdir/case.case_id; d.mkdir(parents=True,exist_ok=True); accounting_files(d,case)
 con=connect(d/'engine.db'); c='client_'+case.case_id; r='run_'+uuid.uuid4().hex
 con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,case.case_id,'GBP',case.business_model,NOW));con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'QUALIFICATION',NOW,None,'RUNNING',None,r,'2.20'));con.commit()
 ds=None; errors=[]
 # Enhanced/advanced receive transaction evidence. L1 intentionally does not.
 if case.data_state in ('L2_ENHANCED','L3_ADVANCED'):
  ing=ingest_northstar(con,c,r,NS,d/'store'); ds=ing['dataset_version_id']; run_trust_layer(con,r,c,ds)
 for f,k in [('pnl.csv','D01_PNL'),('bs.csv','D02_BALANCE_SHEET'),('tb.csv','D03_TRIAL_BALANCE'),('ar.csv','D04_AR'),('ap.csv','D05_AP'),('bank.csv','D06_BANK')]:
  if (d/f).exists(): ingest_accounting_file(con,c,r,d/f,k,d/'store')
 trust=assess_level1_accounting_trust(con,r,c); rec=assess_cross_source_reconciliations(con,r,c)
 run_primitive_engine(con,r,c,ds); diag=run_diagnostic_engine(con,r,c,ds); reason=run_reasoning_engine(con,r,c); econ=run_economic_engine(con,r,c)
 statuses={k:v['status'] for k,v in diag.items()}; completed=[k for k,v in statuses.items() if v=='COMPLETED']; refused=[k for k,v in statuses.items() if v!='COMPLETED']
 signals=[dict(x) for x in con.execute('select test_id,signal_type,observed_value,unit,evidence_summary from signal where run_id=? order by test_id,signal_type',(r,))]
 findings=[dict(x) for x in con.execute('''select f.finding_id,f.finding_type,f.title,f.status,v.fact_summary as fact_text,v.interpretation_summary as interpretation_text,v.why_it_matters,v.materiality_state as materiality_band from finding f join finding_version v on v.finding_id=f.finding_id and v.run_id=? where f.client_id=? order by f.created_at''',(r,c))]
 # sense checks
 checks={}
 checks['registered_56']=len(statuses)==56
 checks['no_inventory_false_cash']= not(case.business_model in ('PROFESSIONAL_SERVICES','SUBSCRIPTION','PROJECT_CONTRACT')) or not any(s['test_id']=='WC-04' and s['observed_value'] not in (None,'0','0.0') for s in signals)
 checks['l1_degrades']= case.data_state not in ('L1_CORE','L1_MESSY') or len(refused)>0
 checks['no_causal_overclaim']=not any('caused by' in ((s['evidence_summary'] or '').lower()) for s in signals)
 checks['no_fraud_overclaim']=not any('fraud' in ((f.get('interpretation_text') or '').lower()) and 'not' not in ((f.get('interpretation_text') or '').lower()) for f in findings)
 checks['project_irregularity_caution']= case.business_model!='PROJECT_CONTRACT' or not any('underlying growth' in ((s['evidence_summary'] or '').lower()) and 'not' not in ((s['evidence_summary'] or '').lower()) for s in signals)
 checks['capacity_not_money']=case.case_id!='SME-004' or not any(s['test_id'].startswith('PEO') and s['unit']=='GBP' and s['observed_value'] not in (None,'0','0.0') for s in signals if 'CAPACITY' in s['signal_type'])
 checks['mismatch_detected']=case.case_id not in ('SME-011','SME-012') or any(v=='FAILED' for v in rec.values())
 checks['missing_bank_visible']=case.case_id!='SME-011' or trust.get('D06',{}).get('availability') in ('MISSING','UNAVAILABLE') or rec.get('BANK_TO_BS_CASH') in ('UNAVAILABLE','NOT_TESTED')
 checks['repeatable_inputs_preserved']=all((d/f).exists() for f in ['pnl.csv','bs.csv','tb.csv','ar.csv','ap.csv'])
 verdict='PASS' if all(checks.values()) else 'FAIL'
 result={'case_id':case.case_id,'model':case.business_model,'data_state':case.data_state,'challenge':case.challenge,'expected':case.expected_behaviour,'diagnostics_registered':len(statuses),'completed':len(completed),'refused_or_na':len(refused),'completed_ids':completed,'refused_ids':refused,'signals':len(signals),'findings':len(findings),'stories':con.execute('select count(*) from economic_story where client_id=?',(c,)).fetchone()[0],'reconciliations':rec,'trust':trust,'sense_checks':checks,'verdict':verdict,'top_findings':findings[:7],'sample_signals':signals[:12]}
 con.close(); return result

def main():
 out=ROOT/'qualification'/'controlled_12_execution'; shutil.rmtree(out,ignore_errors=True);out.mkdir(parents=True)
 results=[]
 for case in CASES:
  try: results.append(run_case(case,out))
  except Exception as e: results.append({'case_id':case.case_id,'model':case.business_model,'data_state':case.data_state,'verdict':'FAIL','fatal_error':repr(e)})
 summary={'cases':len(results),'pass':sum(x.get('verdict')=='PASS' for x in results),'fail':sum(x.get('verdict')=='FAIL' for x in results),'results':results}
 (out/'results.json').write_text(json.dumps(summary,indent=2,default=str),encoding='utf-8')
 print(json.dumps({'cases':summary['cases'],'pass':summary['pass'],'fail':summary['fail'],'case_results':[{'id':x['case_id'],'verdict':x['verdict'],'completed':x.get('completed'),'refused':x.get('refused_or_na'),'signals':x.get('signals'),'findings':x.get('findings'),'fatal':x.get('fatal_error')} for x in results]},indent=2))
if __name__=='__main__': main()
