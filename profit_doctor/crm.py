"""v2.40 D15 CRM/pipeline/win-loss canonicalisation and deterministic intelligence.
Pipeline is commercial evidence, not recognised revenue, forecast or probability of outcome.
"""
from decimal import Decimal
from datetime import datetime, timezone
import uuid
D=lambda x: Decimal(str(x))
def _id(p): return f'{p}_{uuid.uuid4().hex}'
def _now(): return datetime.now(timezone.utc).isoformat()
VALID_STATUS={'OPEN','WON','LOST'}

def ingest_crm(con, client_id, opportunities, stage_history=None, activities=None):
    """Validate and persist canonical CRM records. Fails closed on invalid status/probability/amount."""
    n=0
    for o in opportunities:
        status=str(o['status']).upper()
        if status not in VALID_STATUS: raise ValueError(f'Invalid CRM status: {status}')
        amount=D(o.get('amount') or 0)
        if amount < 0: raise ValueError('CRM amount cannot be negative')
        prob=o.get('probability_pct')
        if prob not in (None,'') and not (D('0') <= D(prob) <= D('100')): raise ValueError('CRM probability_pct must be 0..100')
        if status in {'WON','LOST'} and not o.get('actual_close_date'): raise ValueError('Closed CRM opportunity requires actual_close_date')
        con.execute('''INSERT INTO crm_opportunity(opportunity_id,client_id,source_opportunity_key,opportunity_name,customer_entity_id,owner_key,created_date,expected_close_date,actual_close_date,stage,status,amount,currency,probability_pct,lost_reason,source_system,evidence_note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (o.get('opportunity_id') or _id('crmopp'),client_id,o['source_opportunity_key'],o['opportunity_name'],o.get('customer_entity_id'),o.get('owner_key'),o['created_date'],o.get('expected_close_date'),o.get('actual_close_date'),o['stage'],status,str(amount),o.get('currency','GBP'),None if prob in (None,'') else str(D(prob)),o.get('lost_reason'),o.get('source_system'),o.get('evidence_note'))); n+=1
    for h in stage_history or []:
        con.execute('INSERT INTO crm_stage_history VALUES (?,?,?,?,?,?,?)',(h.get('stage_history_id') or _id('crmstage'),client_id,h['opportunity_id'],h['changed_at'],h.get('from_stage'),h['to_stage'],h.get('evidence_note')))
    for a in activities or []:
        con.execute('INSERT INTO crm_activity VALUES (?,?,?,?,?,?,?)',(a.get('activity_id') or _id('crmact'),client_id,a['opportunity_id'],a['activity_date'],a['activity_type'],a.get('outcome'),a.get('evidence_note')))
    con.commit(); return {'opportunities':n,'stage_history':len(stage_history or []),'activities':len(activities or [])}

def analyse_crm(con, run_id, client_id, as_of='2026-09-30'):
    rows=con.execute('SELECT * FROM crm_opportunity WHERE client_id=?',(client_id,)).fetchall()
    con.execute('DELETE FROM crm_analysis_result WHERE run_id=? AND client_id=?',(run_id,client_id))
    if not rows: return {'available':False,'metrics':[],'limitations':['D15 CRM unavailable']}
    openr=[r for r in rows if r['status']=='OPEN']; won=[r for r in rows if r['status']=='WON']; lost=[r for r in rows if r['status']=='LOST']; closed=won+lost
    metrics=[]
    def add(code,val,unit,evidence,lim=None,dim=None,key=None):
        con.execute('INSERT INTO crm_analysis_result VALUES (?,?,?,?,?,?,?,?,?,?,?)',(_id('crma'),run_id,client_id,code,dim,key,str(val),unit,evidence,lim,_now()))
        metrics.append({'metric_code':code,'observed_value':str(val),'unit':unit,'evidence_summary':evidence,'limitation':lim})
    open_amt=sum((D(r['amount'] or 0) for r in openr),D('0'))
    add('OPEN_PIPELINE_VALUE',open_amt,'GBP',f'{len(openr)} open CRM opportunities total {open_amt}. Pipeline is not recognised revenue or a forecast.','No conversion assumption applied.')
    if closed:
        wr=D(len(won))/D(len(closed))*100
        add('OBSERVED_CLOSED_WIN_RATE',wr,'PERCENT',f'{len(won)} won of {len(closed)} closed opportunities in supplied CRM evidence.','Historical observed rate; not a probability or prediction for open opportunities.')
    # Weighted pipeline is exposed only as CRM-entered weighting, never forecast.
    weighted=sum((D(r['amount'] or 0)*D(r['probability_pct'])/100 for r in openr if r['probability_pct'] not in (None,'')),D('0'))
    weighted_n=sum(1 for r in openr if r['probability_pct'] not in (None,''))
    if weighted_n:
        add('CRM_WEIGHTED_PIPELINE',weighted,'GBP',f'CRM-entered probability weighting is available for {weighted_n}/{len(openr)} open opportunities; weighted value {weighted}.','CRM weighting is not Profit Doctor forecast probability and must not be presented as forecast revenue.')
    overdue=[r for r in openr if r['expected_close_date'] and r['expected_close_date'] < as_of]
    if overdue:
        val=sum((D(r['amount'] or 0) for r in overdue),D('0'))
        add('PAST_EXPECTED_CLOSE_OPEN_PIPELINE',val,'GBP',f'{len(overdue)} open opportunities totalling {val} are past their CRM expected close date as at {as_of}.','Timing exception only; does not establish loss or forecast slippage cause.')
    # Owner concentration is descriptive.
    owners={}
    for r in openr: owners[r['owner_key'] or 'UNASSIGNED']=owners.get(r['owner_key'] or 'UNASSIGNED',D('0'))+D(r['amount'] or 0)
    if open_amt and owners:
        top=max(owners,key=owners.get); pct=owners[top]/open_amt*100
        add('TOP_OWNER_OPEN_PIPELINE_SHARE',pct,'PERCENT',f'{top} holds {pct}% of open pipeline value.','Concentration is not performance quality or outcome probability.','OWNER',top)
    con.commit()
    return {'available':True,'opportunities':len(rows),'open':len(openr),'won':len(won),'lost':len(lost),'metrics':metrics,
            'guardrails':['Pipeline is not recognised revenue.','CRM probability is not Profit Doctor probability.','Weighted pipeline is not a forecast.','Win/loss association does not establish causality.']}
