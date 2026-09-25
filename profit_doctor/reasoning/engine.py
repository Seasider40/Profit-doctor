"""Sprint 5 hardening: conservative FD reasoning, clustering, contradiction handling,
longitudinal finding identity and management-attention budgeting.

No opportunity economics are created here.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone

D=lambda x: Decimal(str(x))
def id4(p): return f"{p}_{uuid.uuid4().hex}"
def now(): return datetime.now(timezone.utc).isoformat()
MATERIALITY_RANK={'INFORMATIONAL':0,'LOW':1,'MEDIUM':2,'HIGH':3}


def add_context_event(con,client,context_type,description,entity_type=None,entity_id=None,period_from=None,period_to=None,source_type='MANAGEMENT'):
    cid=id4('ctx')
    con.execute('INSERT INTO context_event VALUES (?,?,?,?,?,?,?,?,?,?,?)',(cid,client,context_type,entity_type,entity_id,period_from,period_to,description,source_type,'CURRENT',now()))
    con.commit(); return cid


def _overlaps(sig,ctx):
    if ctx['entity_id'] and ctx['entity_id'] != sig['entity_id']: return False
    sf=sig['period_from']; st=sig['period_to']; cf=ctx['period_from']; ct=ctx['period_to']
    if not sf and not st: return True
    if cf and st and cf>st: return False
    if ct and sf and ct<sf: return False
    return True


def _contexts(con,client,sig):
    rows=con.execute("SELECT * FROM context_event WHERE client_id=? AND validity_state='CURRENT'",(client,)).fetchall()
    return [r for r in rows if _overlaps(sig,r)]


def _context_effect(contexts):
    hard={'PLANNED_SHUTDOWN','KNOWN_SEASONAL_EVENT','ACCOUNTING_RESTATEMENT','KNOWN_ONE_OFF'}
    contradictory={'MANAGEMENT_DISPUTE','CONTRADICTORY_EVIDENCE','DATA_CONFLICT'}
    if any(c['context_type'] in hard for c in contexts): return 'SUPPRESS'
    if any(c['context_type'] in contradictory for c in contexts): return 'CONTRADICT'
    return 'NONE'


def _suppression(con,run,client,sig,contexts):
    if _context_effect(contexts)!='SUPPRESS': return False,None
    c=next(c for c in contexts if c['context_type'] in {'PLANNED_SHUTDOWN','KNOWN_SEASONAL_EVENT','ACCOUNTING_RESTATEMENT','KNOWN_ONE_OFF'})
    reason=f"{c['context_type']}: {c['description']}"
    con.execute('INSERT INTO suppression_result VALUES (?,?,?,?,?,?,?,?,?)',(id4('sup'),run,client,sig['signal_id'],'CONTEXTUAL','CTX-001',reason,'SUPPRESSED',now()))
    return True,reason


def _persistence(con,run,client,sig):
    prior=con.execute("""SELECT count(*) n FROM signal s JOIN engine_run er ON er.run_id=s.run_id
      WHERE s.client_id=? AND s.test_id=? AND s.signal_type=? AND COALESCE(s.entity_id,'')=COALESCE(?, '')
      AND s.run_id<>? AND s.status='ACTIVE'""",(client,sig['test_id'],sig['signal_type'],sig['entity_id'],run)).fetchone()['n']
    state='REPEATED' if prior else 'EMERGING'
    ev='Similar active signal exists in a prior engine run.' if prior else 'First evidenced occurrence in available engine-run history.'
    con.execute('INSERT INTO persistence_profile VALUES (?,?,?,?,?,?,?)',(id4('per'),run,client,sig['signal_id'],state,ev,now()))
    return state


def _confidence(eligibility,contradicted=False):
    if eligibility=='FULL': c='HIGH'
    elif eligibility and eligibility.startswith('PARTIAL'): c='MEDIUM'
    else: c='LOW'
    if contradicted: return 'MEDIUM' if c=='HIGH' else 'LOW'
    return c


def _fact_text(sig):
    typ=sig['signal_type']; obs=sig['observed_value']; comp=sig['comparison_value']; var=sig['variance_value']; unit=sig['unit'] or ''
    if comp is not None and var is not None: return f"{typ}: observed {obs} {unit} versus {comp} {unit}, a movement of {var} {unit}."
    return f"{typ}: observed {obs} {unit}."


def _interpretation(sig,contexts,contradicted=False):
    t=sig['signal_type']; v=D(sig['variance_value']) if sig['variance_value'] is not None else None
    ctx_note=(' Relevant management context exists and should be considered before causal conclusions.' if contexts else '')
    if t=='CUSTOMER_DECLINE': base='The evidence supports a material customer revenue deterioration in the comparable period.'; unc='Causality is not established by the revenue movement alone.'
    elif t=='CUSTOMER_GROWTH': base='The evidence supports a material customer revenue improvement in the comparable period.'; unc='The engine has not attributed the growth to price, volume, mix or management action.'
    elif t=='COMPARABLE_REVENUE_CHANGE':
        direction='increased' if (v or D('0'))>0 else ('decreased' if (v or D('0'))<0 else 'was unchanged'); base=f'Comparable revenue {direction}; this is an observed performance movement, not a causal explanation.'; unc='Underlying drivers require bridge and contextual evidence.'
    elif t=='CONTRIBUTION_MARGIN_CHANGE': base='Comparable contribution margin changed materially enough to warrant context review.'; unc='The movement is not automatically leakage or a recoverable opportunity.'
    elif t in ('TOP_CUSTOMER_CONCENTRATION','TOP5_CONCENTRATION'): base='Revenue is concentrated in a limited number of customer relationships.'; unc='Revenue concentration alone does not establish customer loss probability or expected loss.'
    elif t.startswith('WC_') or t.startswith('AR_') or t=='BS_ACCOUNTS_RECEIVABLE': base='The working-capital measure is evidenced and available for management review.'; unc='A benchmark, trend or causal explanation is required before concluding that cash is unnecessarily trapped.'
    else: base='The signal is evidenced and may be relevant to management.'; unc='Further context is required before a stronger conclusion.'
    if contradicted:
        return base+ctx_note+' Contradictory evidence is present, so the interpretation remains unresolved.', 'UNRESOLVED', unc+' Resolve the contradiction before escalation.'
    return base+ctx_note, ('SUPPORTED' if t!='UNKNOWN' else 'PLAUSIBLE'), unc


def _candidate_spec(sig):
    t=sig['signal_type']
    if t in ('CUSTOMER_DECLINE','CUSTOMER_BRIDGE_LEG'): return ('INSIGHT','Material customer revenue movement','Which commercial or relationship factors explain this movement?','Investigate customer/product mix, pricing, cadence and management context.')
    if t=='COMPARABLE_REVENUE_CHANGE': return ('INSIGHT','Material comparable revenue movement','What are the main evidenced drivers of the revenue movement?','Review the reconciled revenue bridge and material customer movements.')
    if t=='CONTRIBUTION_MARGIN_CHANGE': return ('INSIGHT','Contribution margin movement','What is driving the margin movement and is it temporary, structural or explained?','Review price, cost and mix evidence before attributing cause.')
    if t in ('TOP_CUSTOMER_CONCENTRATION','TOP5_CONCENTRATION'): return ('RISK','Customer concentration exposure','How economically dependent is the business on these relationships and what mitigants exist?','Assess GP/contribution exposure, contract position and relationship resilience.')
    if t=='AR_OVERDUE_OUTSTANDING': return ('RISK','Overdue receivables require review','Which balances are genuinely collectible and what is causing delay?','Review ageing, customer behaviour, disputes and collection actions.')
    return ('INSIGHT',t.replace('_',' ').title(),'What additional context would change the management conclusion?','Review supporting evidence and management context.')


def _priority(mat,conf):
    score=MATERIALITY_RANK.get(mat,0)+(2 if conf=='HIGH' else 1 if conf=='MEDIUM' else 0)
    return 'HIGH' if score>=4 else ('MEDIUM' if score>=2 else 'LOW')


def _cluster_key(sig):
    # Keep distinct economics separate while consolidating duplicate views of the same issue.
    if sig['signal_type'] in ('TOP_CUSTOMER_CONCENTRATION','TOP5_CONCENTRATION'): return 'CUSTOMER_CONCENTRATION'
    if sig['signal_type'] in ('COMPARABLE_REVENUE_CHANGE','CUSTOMER_BRIDGE_LEG','CUSTOMER_DECLINE','CUSTOMER_GROWTH'):
        return f"REVENUE_MOVEMENT:{sig['entity_id'] or 'BUSINESS'}"
    if sig['signal_type']=='CONTRIBUTION_MARGIN_CHANGE': return 'MARGIN_MOVEMENT:BUSINESS'
    if sig['signal_type'].startswith('AR_') or sig['signal_type']=='BS_ACCOUNTS_RECEIVABLE': return 'RECEIVABLES:BUSINESS'
    return f"{sig['test_id']}:{sig['signal_type']}:{sig['entity_id'] or 'BUSINESS'}"


def _finding_identity_key(sig,ftype,title):
    return f"{ftype}|{_cluster_key(sig)}|{title}".upper()


def _get_or_create_finding(con,client,run,sig,ftype,title):
    key=_finding_identity_key(sig,ftype,title); row=con.execute('SELECT * FROM finding_identity WHERE client_id=? AND identity_key=?',(client,key)).fetchone(); t=now()
    if row:
        fid=row['finding_id']; con.execute('UPDATE finding SET last_run_id=?,updated_at=?,status=? WHERE finding_id=?',(run,t,'NEW',fid)); con.execute('UPDATE finding_identity SET last_seen_at=? WHERE finding_identity_id=?',(t,row['finding_identity_id'])); return fid,False
    fid=id4('find'); con.execute('INSERT INTO finding VALUES (?,?,?,?,?,?,?,?,?)',(fid,client,ftype,title,'NEW',run,run,t,t)); con.execute('INSERT INTO finding_identity VALUES (?,?,?,?,?,?)',(id4('fi'),client,key,fid,t,t)); return fid,True


def _record_contradictions(con,run,client,bundle,contexts):
    n=0
    for c in contexts:
        if c['context_type'] in {'MANAGEMENT_DISPUTE','CONTRADICTORY_EVIDENCE','DATA_CONFLICT'}:
            con.execute('INSERT INTO contradictory_evidence VALUES (?,?,?,?,?,?,?,?,?,?)',(id4('ce'),run,client,bundle,'CONTEXT_EVENT',c['context_event_id'],c['context_type'],c['description'],'WEAKEN_AND_HOLD_FOR_REVIEW',now())); n+=1
    return n


def run_reasoning_engine(con,run,client,max_primary_items=7):
    signals=con.execute("SELECT * FROM signal WHERE run_id=? AND client_id=? AND status='ACTIVE' ORDER BY created_at",(run,client)).fetchall()
    summary={'signals_considered':len(signals),'suppressed':0,'facts':0,'interpretations':0,'candidates':0,'findings':0,'fd_queue':0,'clusters':0,'contradictions':0,'deferred':0}
    candidate_rows=[]; clusters={}
    for sig in signals:
        ex=con.execute('SELECT * FROM test_execution WHERE test_execution_id=?',(sig['test_execution_id'],)).fetchone(); contexts=_contexts(con,client,sig)
        suppressed,_=_suppression(con,run,client,sig,contexts); _persistence(con,run,client,sig)
        if suppressed: summary['suppressed']+=1; continue
        if MATERIALITY_RANK.get(sig['materiality_state'],0)==0: continue
        ck=_cluster_key(sig); clusters.setdefault(ck,[]).append(sig)
        bundle=id4('eb'); con.execute('INSERT INTO evidence_bundle VALUES (?,?,?,?,?,?)',(bundle,run,client,sig['signal_id'],'SIGNAL_CONTEXT_BUNDLE',now())); con.execute('INSERT INTO evidence_bundle_item VALUES (?,?,?,?,?,?)',(id4('ebi'),bundle,'SIGNAL',sig['signal_id'],'PRIMARY_EVIDENCE',now()))
        for c in contexts: con.execute('INSERT INTO evidence_bundle_item VALUES (?,?,?,?,?,?)',(id4('ebi'),bundle,'CONTEXT_EVENT',c['context_event_id'],'CONTEXT',now()))
        fact=id4('fact'); ftext=_fact_text(sig); con.execute('INSERT INTO fact VALUES (?,?,?,?,?,?,?,?,?)',(fact,run,client,bundle,sig['signal_type'],ftext,sig['observed_value'],sig['unit'],now())); summary['facts']+=1
        contradicted=_context_effect(contexts)=='CONTRADICT'; summary['contradictions']+=_record_contradictions(con,run,client,bundle,contexts)
        itext,istat,unc=_interpretation(sig,contexts,contradicted); conf=_confidence(ex['eligibility_state'] if ex else None,contradicted); con.execute('INSERT INTO interpretation VALUES (?,?,?,?,?,?,?,?,?)',(id4('int'),run,client,bundle,itext,istat,conf,unc,now())); summary['interpretations']+=1
        ftype,title,q,nxt=_candidate_spec(sig); cid=id4('fc'); mat=sig['materiality_state']; status='HELD_CONTRADICTORY' if contradicted else 'READY_FOR_FD_REVIEW'
        con.execute('INSERT INTO finding_candidate VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(cid,run,client,bundle,ftype,title,mat,conf,status,q,nxt,now())); summary['candidates']+=1
        if MATERIALITY_RANK.get(mat,0)>=2 and not contradicted:
            fid,is_new=_get_or_create_finding(con,client,run,sig,ftype,title); why='Material evidenced movement warrants management attention; no opportunity value or causal claim has been created.'; con.execute('INSERT INTO finding_version VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(id4('fv'),fid,run,cid,ftext,itext,why,mat,conf,q,nxt,now())); summary['findings']+=1
            candidate_rows.append((fid,_priority(mat,conf),MATERIALITY_RANK.get(mat,0),conf,sig['signal_id']))
    # Persist clusters for traceability. Clustering informs attention management; it does not erase member evidence.
    for ck,members in clusters.items():
        if len(members)>1:
            primary=sorted(members,key=lambda s:MATERIALITY_RANK.get(s['materiality_state'],0),reverse=True)[0]; fc=id4('fcl'); con.execute('INSERT INTO finding_cluster VALUES (?,?,?,?,?,?,?,?,?)',(fc,run,client,ck,'DUPLICATE_OR_RELATED_VIEW',primary['signal_id'],len(members),'Related diagnostic views are grouped for management attention without deleting underlying evidence.',now()))
            for s in members: con.execute('INSERT INTO finding_cluster_member VALUES (?,?,?,?,?)',(id4('fcm'),fc,s['signal_id'],'RELATED_VIEW',now()))
            summary['clusters']+=1
    # Attention budget: highest-priority unique findings only. Other valid findings remain stored and reviewable.
    rank={'HIGH':3,'MEDIUM':2,'LOW':1}; unique={}
    for row in candidate_rows:
        fid=row[0]
        if fid not in unique or rank[row[1]]>rank[unique[fid][1]]: unique[fid]=row
    ordered=sorted(unique.values(),key=lambda x:(rank[x[1]],x[2]),reverse=True); selected=ordered[:max_primary_items]; deferred=ordered[max_primary_items:]
    for fid,prio,_,_,_ in selected:
        con.execute('INSERT INTO fd_review_queue VALUES (?,?,?,?,?,?,?,?,?)',(id4('fdq'),run,client,'FINDING',fid,'Evidence-bound finding selected within management attention budget.',prio,'PENDING',now())); summary['fd_queue']+=1
    summary['deferred']=len(deferred)
    con.execute('INSERT INTO management_attention_budget VALUES (?,?,?,?,?,?,?,?,?)',(id4('mab'),run,client,max_primary_items,len(ordered),len(selected),len(deferred),'MAB-1.0',now()))
    con.commit(); return summary
