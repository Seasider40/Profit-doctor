"""v2.33 Management Output Specification.
Stable, owner-facing presentation contract. This module does not create new economic facts;
it only projects already-evidenced engine objects into a UI/report view model.
"""
from decimal import Decimal

OUTPUT_SPEC_VERSION="MOS-2.33"
SECTIONS=(
 "EXECUTIVE_HEALTH_CHECK","MANAGEMENT_ATTENTION","PROFIT_CASH_OPPORTUNITY_REGISTER",
 "PERFORMANCE_DIAGNOSTICS","RECOMMENDED_ACTIONS","DATA_MI_MATURITY","BENEFIT_PROGRESS","EVIDENCE_AND_LIMITATIONS"
)

def _num(v):
    if v is None: return None
    try: return str(Decimal(str(v)))
    except Exception: return None

def build_management_output(con,run_id,client_id):
    """Build the stable product-output contract from persisted evidence.
    No arithmetic opportunity is created here and profit/cash are never combined.
    """
    run=con.execute('SELECT * FROM engine_run WHERE run_id=? AND client_id=?',(run_id,client_id)).fetchone()
    if not run: raise ValueError('Run not found for client')
    attention=[dict(x) for x in con.execute('SELECT * FROM management_attention_item WHERE run_id=? AND client_id=? ORDER BY rank_order',(run_id,client_id)).fetchall()]
    register=[dict(x) for x in con.execute('SELECT * FROM profit_cash_opportunity_register WHERE run_id=? AND client_id=? ORDER BY rowid',(run_id,client_id)).fetchall()]
    actions=[dict(x) for x in con.execute('SELECT * FROM management_action_candidate WHERE run_id=? AND client_id=? ORDER BY rowid',(run_id,client_id)).fetchall()]
    execs=[dict(x) for x in con.execute('SELECT test_id,eligibility_state,execution_status,limitation FROM test_execution WHERE run_id=? ORDER BY test_id',(run_id,)).fetchall()]
    recs=[dict(x) for x in con.execute('SELECT reconciliation_type,status,residual,left_object,right_object,left_value,right_value,limitation FROM reconciliation WHERE run_id=?',(run_id,)).fetchall()]
    prim={x['primitive_id']:dict(x) for x in con.execute("SELECT * FROM primitive_result WHERE run_id=? AND client_id=? AND result_status='VALID'",(run_id,client_id)).fetchall()}
    def pv(*ids):
        for i in ids:
            if i in prim: return {'value':_num(prim[i]['numeric_value']),'unit':prim[i]['unit'],'primitive_id':i}
        return None
    kpis=[]
    for label,ids in [('Revenue',('FIN_REVENUE','REVENUE','TOTAL_REVENUE')),('Gross profit',('FIN_GROSS_PROFIT','GROSS_PROFIT','GP')),('EBITDA',('FIN_EBITDA','EBITDA')),('Available cash',('AVAILABLE_CASH','CASH_AVAILABLE')),('DSO',('WC_DSO','DSO')),('DIO',('WC_DIO','DIO')),('DPO',('WC_DPO','DPO')),('Cash conversion cycle',('WC_CCC','CCC'))]:
        v=pv(*ids)
        if v: kpis.append({'label':label,**v})
    completed=sum(1 for x in execs if x['execution_status']=='COMPLETED')
    constrained=sum(1 for x in execs if x['execution_status']!='COMPLETED')
    control_failures=sum(1 for x in recs if x['status']=='FAILED')
    health={'headline':'Management review generated from evidenced data','kpis':kpis,'diagnostic_coverage':{'completed':completed,'total':len(execs),'not_completed':constrained},'control_failures':control_failures,'guardrail':'Health Check is a decision summary, not a universal score or rating.'}
    priorities=[{'rank':x['rank_order'],'theme':x['theme_key'],'title':x['title'],'issue_type':x['issue_type'],'priority':x['priority_state'],'confidence':x['confidence_state'],'management_question':x['management_question'],'rationale':x['rationale'],'next_step':x['next_step'],'limitation':x['limitation']} for x in attention]
    opp=[]
    for x in register:
        opp.append({'theme':x['theme_key'],'purpose':x['purpose'],'benefit_type':x['benefit_type'],'availability':x['availability_state'],'economic_state':x['economic_state'],'currency':x['currency'],'theoretical':_num(x['theoretical_amount']),'addressable':_num(x['addressable_amount']),'expected':_num(x['expected_amount']),'recommended_action':x['recommended_action'],'evidence_required':x['evidence_required'],'limitation':x['limitation']})
    # Never publish an additive grand total across benefit types.
    quantified={'recurring_profit_expected':None,'one_off_cash_release_expected':None,'combined_total':None,'rule':'Profit and cash are non-additive; no combined headline benefit is permitted.'}
    rp=sum((Decimal(x['expected']) for x in opp if x['expected'] is not None and x['benefit_type']=='B1_RECURRING_PROFIT_IMPROVEMENT'),Decimal('0'))
    cr=sum((Decimal(x['expected']) for x in opp if x['expected'] is not None and x['benefit_type']=='B3_ONE_OFF_CASH_RELEASE'),Decimal('0'))
    if any(x['expected'] is not None and x['benefit_type']=='B1_RECURRING_PROFIT_IMPROVEMENT' for x in opp): quantified['recurring_profit_expected']=str(rp)
    if any(x['expected'] is not None and x['benefit_type']=='B3_ONE_OFF_CASH_RELEASE' for x in opp): quantified['one_off_cash_release_expected']=str(cr)
    action_view=[{'theme':x['theme_key'],'action_type':x['action_type'],'recommended_action':x['recommended_action'],'evidence_required':x['evidence_required'],'owner_role':x['owner_role'],'state':x['action_state'],'limitation':x['limitation']} for x in actions]
    diag={'completed':[x['test_id'] for x in execs if x['execution_status']=='COMPLETED'],'partial':[x['test_id'] for x in execs if str(x['eligibility_state']).startswith('PARTIAL')],'unavailable':[{'test_id':x['test_id'],'limitation':x['limitation']} for x in execs if x['execution_status']!='COMPLETED']}
    data_mi={'control_reconciliations':recs,'coverage':health['diagnostic_coverage'],'message':'Data quality, financial integrity, diagnostic coverage and analytical confidence remain distinct concepts.'}
    benefit={'status':'NO_LONGITUDINAL_BENEFIT_EVIDENCE_IN_THIS_VIEW','realised':None,'verified':None,'retained':None,'rule':'Realised, verified and retained benefits require explicit lifecycle evidence; they are not inferred from opportunity values.'}
    return {'spec_version':OUTPUT_SPEC_VERSION,'run_id':run_id,'client_id':client_id,'section_order':list(SECTIONS),'executive_health_check':health,'management_attention':priorities,'opportunity_register':{'items':opp,'portfolio_headline':quantified},'performance_diagnostics':diag,'recommended_actions':action_view,'data_mi_maturity':data_mi,'benefit_progress':benefit,'evidence_and_limitations':{'reconciliations':recs,'principles':['Observed evidence is separated from interpretation and opportunity.','Exposure is not expected loss.','Cash release is not profit.','Capacity released is not a saving without evidenced economic use.','Unavailable evidence remains unavailable rather than being invented.']}}
