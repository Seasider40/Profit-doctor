from decimal import Decimal as D
from datetime import datetime, timezone
import uuid

def now(): return datetime.now(timezone.utc).isoformat()
def id4(p): return p+'_'+uuid.uuid4().hex

def record_decision(con, run_id, client_id, opportunity_id, selected_course, rationale, owner=None, issue=None, review_date=None):
    o=con.execute('SELECT * FROM opportunity WHERE opportunity_id=? AND run_id=? AND client_id=?',(opportunity_id,run_id,client_id)).fetchone()
    if not o: raise ValueError('Supported opportunity not found in client/run')
    if o['status']!='SUPPORTED': raise ValueError('Decision requires a supported opportunity')
    did=id4('decision')
    con.execute('INSERT INTO decision VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(did,run_id,client_id,o['economic_story_id'],opportunity_id,None,issue or 'Opportunity decision',selected_course,rationale,owner,'MADE',now(),review_date,now()))
    con.commit(); return did

def create_action(con, run_id, client_id, decision_id, description, owner=None, target_date=None, action_type='IMPLEMENT', expected_effect=None):
    d=con.execute('SELECT * FROM decision WHERE decision_id=? AND run_id=? AND client_id=?',(decision_id,run_id,client_id)).fetchone()
    if not d: raise ValueError('Decision not found in client/run')
    aid=id4('action'); t=now()
    con.execute('INSERT INTO action VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(aid,run_id,client_id,decision_id,d['opportunity_id'],action_type,description,owner,target_date,'OPEN',expected_effect,t,t))
    con.commit(); return aid

def update_action_progress(con, action_id, run_id, progress_state, note=None):
    allowed={'OPEN','IN_PROGRESS','BLOCKED','COMPLETED','CANCELLED'}
    if progress_state not in allowed: raise ValueError('Unsupported action progress state')
    a=con.execute('SELECT * FROM action WHERE action_id=?',(action_id,)).fetchone()
    if not a or a['run_id']!=run_id: raise ValueError('Action not found in run')
    con.execute('UPDATE action SET status=?,updated_at=? WHERE action_id=?',(progress_state,now(),action_id))
    con.execute('INSERT INTO action_progress VALUES (?,?,?,?,?,?)',(id4('ap'),action_id,run_id,progress_state,note,now()))
    con.commit()

def record_realised_benefit(con, run_id, client_id, opportunity_id, action_id, gross_amount, evidence_basis, implementation_cost='0', ongoing_cost='0', adverse_effect='0', attribution_state='DIRECTLY_ATTRIBUTABLE', period_from=None, period_to=None):
    o=con.execute('SELECT * FROM opportunity WHERE opportunity_id=? AND client_id=? AND run_id=?',(opportunity_id,client_id,run_id)).fetchone()
    a=con.execute('SELECT * FROM action WHERE action_id=? AND client_id=? AND run_id=?',(action_id,client_id,run_id)).fetchone()
    if not o or not a or a['opportunity_id']!=opportunity_id: raise ValueError('Benefit must link to the opportunity and its action in the same client/run')
    if a['status']!='COMPLETED': raise ValueError('Action completion is required before recording realised benefit')
    vals=[D(str(x)) for x in (gross_amount,implementation_cost,ongoing_cost,adverse_effect)]
    if min(vals)<0: raise ValueError('Benefit economics cannot be negative')
    gross,impl,ongoing,adverse=vals; net=gross-impl-ongoing-adverse
    if net<0: raise ValueError('Net benefit cannot be negative in a realised benefit leg; record adverse economics separately')
    # Expected is not a cap on realised benefit, but variance must remain visible; never silently rewrite expected economics.
    be=id4('be'); bl=id4('bl'); t=now()
    con.execute('INSERT INTO benefit_event VALUES (?,?,?,?,?,?,?,?,?)',(be,run_id,client_id,opportunity_id,action_id,'REALISATION',t,evidence_basis,t))
    con.execute('INSERT INTO benefit_leg VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(bl,run_id,client_id,be,opportunity_id,action_id,o['benefit_type'],period_from,period_to,str(gross),str(impl),str(ongoing),str(adverse),str(net),o['currency'],attribution_state,'REALISED',t))
    con.execute('INSERT INTO benefit_observation VALUES (?,?,?,?,?,?,?)',(id4('bo'),bl,run_id,str(net),o['currency'],evidence_basis,t))
    con.commit(); return bl

def verify_benefit(con, benefit_leg_id, run_id, observed_amount, evidence_basis, attribution_state=None):
    b=con.execute('SELECT * FROM benefit_leg WHERE benefit_leg_id=? AND run_id=?',(benefit_leg_id,run_id)).fetchone()
    if not b: raise ValueError('Benefit leg not found in run')
    observed=D(str(observed_amount))
    if observed<0: raise ValueError('Observed benefit cannot be negative')
    if attribution_state:
        allowed={'DIRECTLY_ATTRIBUTABLE','STRONGLY_SUPPORTED','PARTIALLY_ATTRIBUTABLE','UNCERTAIN','NOT_ATTRIBUTABLE'}
        if attribution_state not in allowed: raise ValueError('Unsupported attribution state')
        con.execute('UPDATE benefit_leg SET attribution_state=? WHERE benefit_leg_id=?',(attribution_state,benefit_leg_id))
    con.execute('INSERT INTO benefit_observation VALUES (?,?,?,?,?,?,?)',(id4('bo'),benefit_leg_id,run_id,str(observed),b['currency'],evidence_basis,now()))
    status='VERIFIED' if (attribution_state or b['attribution_state']) not in ('UNCERTAIN','NOT_ATTRIBUTABLE') else 'REALISED'
    con.execute('UPDATE benefit_leg SET status=? WHERE benefit_leg_id=?',(status,benefit_leg_id)); con.commit(); return status

def assess_retention(con, benefit_leg_id, run_id, retained_amount, evidence_basis, retention_state='RETAINED'):
    b=con.execute('SELECT * FROM benefit_leg WHERE benefit_leg_id=? AND run_id=?',(benefit_leg_id,run_id)).fetchone()
    if not b: raise ValueError('Benefit leg not found in run')
    retained=D(str(retained_amount)); net=D(b['net_amount'])
    if retained<0 or retained>net: raise ValueError('Retained amount must be between zero and realised net benefit')
    if retention_state not in {'RETAINED','PARTIALLY_RETAINED','NOT_RETAINED','TOO_EARLY'}: raise ValueError('Unsupported retention state')
    con.execute('INSERT INTO benefit_retention VALUES (?,?,?,?,?,?,?,?)',(id4('br'),benefit_leg_id,run_id,str(retained),b['currency'],retention_state,evidence_basis,now()))
    if retention_state in {'RETAINED','PARTIALLY_RETAINED','NOT_RETAINED'}: con.execute("UPDATE benefit_leg SET status='RETAINED' WHERE benefit_leg_id=?",(benefit_leg_id,))
    con.commit()

def relate_benefits(con, run_id, client_id, left_id, right_id, relationship_type, evidence_basis, overlap_amount=None):
    allowed={'INDEPENDENT','CASH_MANIFESTATION','OVERLAPPING','OFFSETTING','DERIVED_FROM'}
    if relationship_type not in allowed: raise ValueError('Unsupported benefit relationship')
    if left_id==right_id: raise ValueError('Benefit cannot relate to itself')
    l=con.execute('SELECT * FROM benefit_leg WHERE benefit_leg_id=? AND client_id=? AND run_id=?',(left_id,client_id,run_id)).fetchone(); r=con.execute('SELECT * FROM benefit_leg WHERE benefit_leg_id=? AND client_id=? AND run_id=?',(right_id,client_id,run_id)).fetchone()
    if not l or not r: raise ValueError('Benefits not found in the same client/run')
    ov=None if overlap_amount is None else D(str(overlap_amount))
    if relationship_type=='OVERLAPPING' and (ov is None or ov<0): raise ValueError('Overlap amount required')
    symmetric={'INDEPENDENT','CASH_MANIFESTATION','OVERLAPPING'}
    if relationship_type in symmetric:
        duplicate=con.execute('SELECT 1 FROM benefit_relationship WHERE run_id=? AND client_id=? AND relationship_type=? AND ((left_benefit_leg_id=? AND right_benefit_leg_id=?) OR (left_benefit_leg_id=? AND right_benefit_leg_id=?)) LIMIT 1',(run_id,client_id,relationship_type,left_id,right_id,right_id,left_id)).fetchone()
        if duplicate: raise ValueError('Duplicate symmetric benefit relationship')
    con.execute('INSERT INTO benefit_relationship VALUES (?,?,?,?,?,?,?,?,?)',(id4('brel'),run_id,client_id,left_id,right_id,relationship_type,None if ov is None else str(ov),evidence_basis,now())); con.commit()

def realised_portfolio_value(con, client_id):
    legs=con.execute("SELECT * FROM benefit_leg WHERE client_id=? AND status IN ('REALISED','VERIFIED','RETAINED')",(client_id,)).fetchall()
    by={x['benefit_leg_id']:x for x in legs}; gross=sum((D(x['net_amount']) for x in legs),D('0')); deduction=D('0')
    for rel in con.execute('SELECT * FROM benefit_relationship WHERE client_id=?',(client_id,)).fetchall():
        l=by.get(rel['left_benefit_leg_id']); r=by.get(rel['right_benefit_leg_id'])
        if not l or not r: continue
        lv=D(l['net_amount']); rv=D(r['net_amount'])
        if rel['relationship_type']=='CASH_MANIFESTATION': deduction+=min(lv,rv)
        elif rel['relationship_type']=='OVERLAPPING': deduction+=min(D(rel['overlap_amount'] or '0'),lv,rv)
    return {'gross_realised':gross,'non_additive_deduction':deduction,'portfolio_realised':max(D('0'),gross-deduction)}
