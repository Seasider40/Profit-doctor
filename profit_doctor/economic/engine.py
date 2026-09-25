from decimal import Decimal as D
from datetime import datetime, timezone
import uuid

def now(): return datetime.now(timezone.utc).isoformat()
def id4(p): return p+'_'+uuid.uuid4().hex

def _signal_for_finding(con, finding_id, run_id):
    return con.execute('''SELECT s.*, fv.finding_version_id, f.finding_type, f.title
      FROM finding f JOIN finding_version fv ON fv.finding_id=f.finding_id
      JOIN finding_candidate fc ON fc.finding_candidate_id=fv.finding_candidate_id
      JOIN evidence_bundle eb ON eb.evidence_bundle_id=fc.evidence_bundle_id
      JOIN signal s ON s.signal_id=eb.primary_signal_id
      WHERE f.finding_id=? AND fv.run_id=? ORDER BY fv.created_at DESC LIMIT 1''',(finding_id,run_id)).fetchone()

def _story_key(sig):
    if sig['signal_type'] in ('TOP_CUSTOMER_CONCENTRATION','TOP5_CONCENTRATION'): return 'CUSTOMER_CONCENTRATION'
    if sig['signal_type'] in ('CUSTOMER_DECLINE','CUSTOMER_GROWTH','CUSTOMER_BRIDGE_LEG'): return f"CUSTOMER_REVENUE:{sig['entity_id'] or 'UNKNOWN'}"
    if sig['signal_type']=='COMPARABLE_REVENUE_CHANGE': return 'BUSINESS_REVENUE_MOVEMENT'
    if sig['signal_type']=='CONTRIBUTION_MARGIN_CHANGE': return 'BUSINESS_MARGIN_MOVEMENT'
    if sig['signal_type'].startswith('AR_') or sig['signal_type']=='BS_ACCOUNTS_RECEIVABLE': return 'RECEIVABLES'
    return f"{sig['test_id']}:{sig['signal_type']}:{sig['entity_id'] or 'BUSINESS'}"

def _get_story(con,run,client,sig):
    key=_story_key(sig); row=con.execute('SELECT * FROM economic_story WHERE client_id=? AND story_key=?',(client,key)).fetchone(); t=now()
    if row:
        con.execute('UPDATE economic_story SET last_run_id=?,updated_at=? WHERE economic_story_id=?',(run,t,row['economic_story_id'])); return row['economic_story_id']
    sid=id4('story'); stype='RISK' if sig['signal_type'] in ('TOP_CUSTOMER_CONCENTRATION','TOP5_CONCENTRATION') else 'PERFORMANCE'
    con.execute('INSERT INTO economic_story VALUES (?,?,?,?,?,?,?,?,?,?)',(sid,client,key,stype,sig['signal_type'].replace('_',' ').title(),'OPEN',run,run,t,t)); return sid

def _link(con,story,obj_type,obj_id,rel):
    con.execute('INSERT OR IGNORE INTO economic_story_object VALUES (?,?,?,?,?,?)',(id4('eso'),story,obj_type,obj_id,rel,now()))

def _amount(v):
    return None if v is None else D(str(v))

def _record_impact(con,run,client,story,sig):
    # Only already-observed negative economic movements become monetary impacts here.
    v=_amount(sig['variance_value'] if sig['variance_value'] is not None else sig['observed_value'])
    if v is None or v>=0: return 0
    if sig['signal_type'] not in ('CUSTOMER_DECLINE','CUSTOMER_BRIDGE_LEG','COMPARABLE_REVENUE_CHANGE'): return 0
    con.execute('INSERT INTO economic_impact VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(
      id4('impact'),run,client,story,'OBSERVED_REVENUE_DETERIORATION','REVENUE',sig['entity_type'],sig['entity_id'],sig['period_from'],sig['period_to'],str(abs(v)),'GBP','OBSERVED_ASSOCIATION','Signal variance; no causal or recoverability claim.','OPEN',now()))
    return 1

def _record_exposure(con,run,client,story,sig):
    if sig['signal_type'] not in ('TOP_CUSTOMER_CONCENTRATION','TOP5_CONCENTRATION'): return 0
    # Concentration % is exposure evidence, not expected loss. Monetary exposure is deliberately left unquantified here.
    con.execute('INSERT INTO economic_exposure VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(
      id4('exposure'),run,client,story,'CUSTOMER_DEPENDENCY',sig['entity_type'],sig['entity_id'],None,'GBP',
      'Revenue dependency on concentrated customer relationships.',f"Observed concentration {sig['observed_value']} {sig['unit']}; probability of loss is not inferred.",'OPEN',now()))
    return 1

def _candidate(con,run,client,story,finding,sig):
    # A problem is not an opportunity. Create a candidate with unquantified addressable/expected economics until mechanism evidence exists.
    if sig['signal_type'] in ('CUSTOMER_DECLINE','CUSTOMER_BRIDGE_LEG','COMPARABLE_REVENUE_CHANGE'):
        v=_amount(sig['variance_value'] if sig['variance_value'] is not None else sig['observed_value'])
        if v is None or v>=0: return 0
        theoretical=abs(v); purpose='RECOVER'; btype='B1_RECURRING_PROFIT_IMPROVEMENT'
        limitation='Observed deterioration defines only a theoretical ceiling. Addressability, mechanism, margin conversion and expected recovery are not yet evidenced.'
    elif sig['signal_type']=='CONTRIBUTION_MARGIN_CHANGE':
        purpose='IMPROVE'; btype='B1_RECURRING_PROFIT_IMPROVEMENT'; theoretical=None
        limitation='Margin movement requires price/cost/mix decomposition before any supported opportunity value can be created.'
    elif sig['signal_type']=='AR_OVERDUE_OUTSTANDING':
        purpose='RELEASE'; btype='B3_ONE_OFF_CASH_RELEASE'; theoretical=_amount(sig['observed_value'])
        limitation='Overdue AR is not automatically collectible cash release; disputes, credit notes, bad debt and normal collection timing must be resolved.'
    elif sig['signal_type'] in ('TOP_CUSTOMER_CONCENTRATION','TOP5_CONCENTRATION'):
        purpose='PROTECT'; btype='B6_RISK_MITIGATION'; theoretical=None
        limitation='Concentration exposure supports risk review, but no expected loss or monetary mitigation benefit is inferred without a defensible pathway and probability model.'
    else: return 0
    con.execute('INSERT INTO opportunity_candidate VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(
      id4('oc'),run,client,story,finding,None,purpose,btype,None,None if theoretical is None else str(theoretical),None,None,'GBP','CONDITIONAL','REQUIRES_ECONOMIC_RESOLUTION',limitation,now()))
    return 1

def run_economic_engine(con,run,client):
    findings=con.execute('SELECT DISTINCT f.* FROM finding f JOIN finding_version fv ON fv.finding_id=f.finding_id WHERE fv.run_id=? AND f.client_id=?',(run,client)).fetchall()
    out={'findings_resolved':0,'stories':0,'impacts':0,'exposures':0,'candidates':0,'opportunities':0}
    seen=set()
    for f in findings:
        sig=_signal_for_finding(con,f['finding_id'],run)
        if not sig: continue
        story=_get_story(con,run,client,sig); seen.add(story); _link(con,story,'FINDING',f['finding_id'],'SUPPORTED_BY'); _link(con,story,'SIGNAL',sig['signal_id'],'EVIDENCED_BY')
        ic=_record_impact(con,run,client,story,sig); ec=_record_exposure(con,run,client,story,sig); cc=_candidate(con,run,client,story,f['finding_id'],sig)
        limitation='Economic resolution is conservative: findings do not become opportunities without mechanism, baseline, addressability and envelope evidence.'
        con.execute('INSERT OR REPLACE INTO economic_resolution VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(id4('er'),run,client,f['finding_id'],story,'RESOLVED_TO_ECONOMIC_OBJECTS',ic,ec,cc,0,limitation,now()))
        out['findings_resolved']+=1; out['impacts']+=ic; out['exposures']+=ec; out['candidates']+=cc
    out['stories']=len(seen); con.commit(); return out

def qualify_opportunity_candidate(con, candidate_id, mechanism_id, baseline_amount, addressable_amount, expected_amount, envelope_amount, evidence_basis, availability_state='IMMEDIATE'):
    c=con.execute('SELECT * FROM opportunity_candidate WHERE opportunity_candidate_id=?',(candidate_id,)).fetchone()
    if not c: raise ValueError('Unknown opportunity candidate')
    if not mechanism_id or not evidence_basis: raise ValueError('Mechanism and evidence are required')
    ev=con.execute("SELECT * FROM opportunity_mechanism_evidence WHERE opportunity_candidate_id=? AND mechanism_id=? AND status='SUPPORTED' ORDER BY created_at DESC LIMIT 1",(candidate_id,mechanism_id)).fetchone()
    if not ev: raise ValueError('Supported mechanism evidence is required before opportunity qualification')
    vals=[D(str(x)) for x in (baseline_amount,addressable_amount,expected_amount,envelope_amount)]
    baseline,addressable,expected,envelope=vals
    if min(vals)<0: raise ValueError('Opportunity economics cannot be negative')
    theoretical=D(c['theoretical_amount']) if c['theoretical_amount'] is not None else None
    if theoretical is not None and addressable>theoretical: raise ValueError('Addressable opportunity exceeds theoretical ceiling')
    if expected>addressable: raise ValueError('Expected opportunity exceeds addressable opportunity')
    if expected>envelope or addressable>envelope: raise ValueError('Opportunity exceeds supported recovery envelope')
    b=id4('base'); con.execute('INSERT INTO economic_baseline VALUES (?,?,?,?,?,?,?,?,?,?,?)',(b,c['run_id'],c['client_id'],c['economic_story_id'],'ECONOMIC_BASELINE',None,None,str(baseline),c['currency'],evidence_basis,now()))
    env=id4('env'); con.execute('INSERT INTO recovery_envelope VALUES (?,?,?,?,?,?,?,?,?,?,?)',(env,c['run_id'],c['client_id'],c['economic_story_id'],c['benefit_type'],'CURRENT_PERIOD',str(envelope),c['currency'],evidence_basis,'SUPPORTED',now()))
    oid=id4('opp'); con.execute('INSERT INTO opportunity VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(oid,c['run_id'],c['client_id'],c['economic_story_id'],c['finding_id'],mechanism_id,c['purpose'],c['benefit_type'],b,c['theoretical_amount'],str(addressable),str(expected),c['currency'],availability_state,'SUPPORTED',now()))
    con.execute("UPDATE opportunity_candidate SET mechanism_id=?,economic_baseline_id=?,addressable_amount=?,expected_amount=?,availability_state=?,candidate_status='QUALIFIED',limitation=NULL WHERE opportunity_candidate_id=?",(mechanism_id,b,str(addressable),str(expected),availability_state,candidate_id))
    con.execute("UPDATE economic_resolution SET opportunity_count=opportunity_count+1 WHERE run_id=? AND finding_id=?",(c['run_id'],c['finding_id']))
    con.commit(); return oid

def relate_opportunities(con,left_id,right_id,relationship_type,evidence_basis,overlap_amount=None):
    allowed={'INDEPENDENT','OVERLAPPING','ALTERNATIVE','DEPENDENT','SEQUENTIAL','SYNERGISTIC','MUTUALLY_EXCLUSIVE','CASH_MANIFESTATION'}
    if relationship_type not in allowed: raise ValueError('Unsupported opportunity relationship')
    if left_id==right_id: raise ValueError('Opportunity cannot relate to itself')
    l=con.execute('SELECT * FROM opportunity WHERE opportunity_id=?',(left_id,)).fetchone(); r=con.execute('SELECT * FROM opportunity WHERE opportunity_id=?',(right_id,)).fetchone()
    if not l or not r or l['client_id']!=r['client_id'] or l['run_id']!=r['run_id']: raise ValueError('Opportunities must exist in the same client/run')
    ov=None if overlap_amount is None else D(str(overlap_amount))
    if relationship_type=='OVERLAPPING' and (ov is None or ov<0): raise ValueError('Overlapping opportunities require a non-negative overlap amount')
    symmetric={'INDEPENDENT','OVERLAPPING','ALTERNATIVE','SYNERGISTIC','MUTUALLY_EXCLUSIVE','CASH_MANIFESTATION'}
    if relationship_type in symmetric:
        duplicate=con.execute(
            'SELECT 1 FROM opportunity_relationship WHERE run_id=? AND client_id=? AND relationship_type=? AND ((left_opportunity_id=? AND right_opportunity_id=?) OR (left_opportunity_id=? AND right_opportunity_id=?)) LIMIT 1',
            (l['run_id'],l['client_id'],relationship_type,left_id,right_id,right_id,left_id)
        ).fetchone()
        if duplicate: raise ValueError('Duplicate symmetric opportunity relationship')
    con.execute('INSERT INTO opportunity_relationship VALUES (?,?,?,?,?,?,?,?,?)',(id4('or'),l['run_id'],l['client_id'],left_id,right_id,relationship_type,None if ov is None else str(ov),evidence_basis,now())); con.commit()

def portfolio_expected_value(con,run,client):
    opps=con.execute("SELECT * FROM opportunity WHERE run_id=? AND client_id=? AND status='SUPPORTED'",(run,client)).fetchall()
    gross=sum((D(o['expected_amount']) for o in opps if o['expected_amount'] is not None),D('0'))
    deduction=D('0')
    for rel in con.execute('SELECT * FROM opportunity_relationship WHERE run_id=? AND client_id=?',(run,client)).fetchall():
        l=next((o for o in opps if o['opportunity_id']==rel['left_opportunity_id']),None); r=next((o for o in opps if o['opportunity_id']==rel['right_opportunity_id']),None)
        if not l or not r: continue
        le=D(l['expected_amount'] or '0'); re=D(r['expected_amount'] or '0')
        if rel['relationship_type']=='OVERLAPPING': deduction+=min(D(rel['overlap_amount'] or '0'),le,re)
        elif rel['relationship_type'] in ('ALTERNATIVE','MUTUALLY_EXCLUSIVE'): deduction+=min(le,re)
    net=max(D('0'),gross-deduction)
    return {'gross_expected':gross,'overlap_or_exclusivity_deduction':deduction,'portfolio_expected':net}

def record_mechanism_evidence(con,candidate_id,mechanism_id,evidence_type,evidence_basis,addressability_basis=None,recovery_basis=None,confidence_state='MEDIUM'):
    c=con.execute('SELECT * FROM opportunity_candidate WHERE opportunity_candidate_id=?',(candidate_id,)).fetchone()
    if not c: raise ValueError('Unknown opportunity candidate')
    if not mechanism_id or not evidence_basis: raise ValueError('Mechanism and evidence basis are required')
    eid=id4('mech'); con.execute('INSERT INTO opportunity_mechanism_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(eid,c['run_id'],c['client_id'],candidate_id,mechanism_id,evidence_type,evidence_basis,addressability_basis,recovery_basis,confidence_state,'SUPPORTED',now())); con.commit(); return eid

def qualify_opportunity_candidate_evidenced(con, candidate_id, mechanism_id, baseline_amount, addressable_amount, expected_amount, envelope_amount, evidence_basis, availability_state='IMMEDIATE'):
    ev=con.execute("SELECT * FROM opportunity_mechanism_evidence WHERE opportunity_candidate_id=? AND mechanism_id=? AND status='SUPPORTED' ORDER BY created_at DESC LIMIT 1",(candidate_id,mechanism_id)).fetchone()
    if not ev: raise ValueError('Supported mechanism evidence is required before opportunity qualification')
    combined=f"{evidence_basis}; mechanism evidence: {ev['evidence_basis']}"
    return qualify_opportunity_candidate(con,candidate_id,mechanism_id,baseline_amount,addressable_amount,expected_amount,envelope_amount,combined,availability_state)
