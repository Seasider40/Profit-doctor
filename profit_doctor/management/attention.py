"""v2.27 Management Attention / FD Output qualification.

Compresses evidenced findings, control failures and material data constraints into a
small management agenda. It is deliberately non-economic: no opportunity value is
created here and absolute £ magnitude is not used as the sole priority rule.
"""
from datetime import datetime, timezone
import uuid

RANK={'CRITICAL':4,'HIGH':3,'MEDIUM':2,'LOW':1}
def _id(p): return f"{p}_{uuid.uuid4().hex}"
def _now(): return datetime.now(timezone.utc).isoformat()

SCHEMA='''
CREATE TABLE IF NOT EXISTS management_attention_item (
 attention_item_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 theme_key TEXT NOT NULL, title TEXT NOT NULL, issue_type TEXT NOT NULL,
 priority_state TEXT NOT NULL, confidence_state TEXT NOT NULL,
 evidence_count INTEGER NOT NULL, rationale TEXT NOT NULL, management_question TEXT NOT NULL,
 next_step TEXT NOT NULL, limitation TEXT, rank_order INTEGER NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(run_id, theme_key)
);
CREATE TABLE IF NOT EXISTS management_attention_evidence (
 attention_evidence_id TEXT PRIMARY KEY, attention_item_id TEXT NOT NULL,
 object_type TEXT NOT NULL, object_id TEXT NOT NULL, relationship_type TEXT NOT NULL,
 created_at TEXT NOT NULL, UNIQUE(attention_item_id, object_type, object_id)
);
'''

def _theme(sig):
    t=sig['signal_type']; test=sig['test_id']
    if t in {'RECONCILIATION_EXCEPTION','GOVERNANCE_ACTION_CANDIDATE'} or test.startswith('RISK-'): return 'FINANCIAL_INTEGRITY'
    if test.startswith('CUS-'): return 'CUSTOMER_ECONOMICS'
    if test.startswith('SUP-'): return 'SUPPLIER_DEPENDENCY'
    if test=='PEO-04' or t=='WORK_CENTRE_UTILISATION': return 'CAPACITY_CONSTRAINT'
    if test.startswith('WC-') or t.startswith(('WC_','AR_','CASH_','WORKING_CAPITAL')): return 'WORKING_CAPITAL'
    if test.startswith(('GM-','PRI-')): return 'MARGIN_PRICING'
    if test.startswith('REV-'): return 'REVENUE_PERFORMANCE'
    if test.startswith('FCST-'): return 'FORECAST_CONTROL'
    if test.startswith('PEO-'): return 'PEOPLE_PRODUCTIVITY'
    return 'OTHER'

META={
'FINANCIAL_INTEGRITY':('Resolve financial control-account discrepancies','RISK','Which balances are reliable enough to manage the business from?','Reconcile each failed control to source records, identify timing/classification differences and document resolution.'),
'CUSTOMER_ECONOMICS':('Customer economics and concentration deserve review','INSIGHT','Which customer relationships create value and where is dependency material?','Review contribution, concentration and commercial context for the customers driving the evidence.'),
'SUPPLIER_DEPENDENCY':('Supplier spend concentration requires commercial review','RISK','Where does supplier concentration create dependency or negotiating exposure?','Review critical suppliers, alternatives, contract terms and operational substitutability before assigning risk value.'),
'CAPACITY_CONSTRAINT':('Operational capacity appears constrained','INSIGHT','Which work centres are genuinely capacity constrained and what is driving the load?','Validate hours and constraints, then test overtime, bottlenecks, scheduling, mix and investment options before monetising.'),
'WORKING_CAPITAL':('Working capital requires focused investigation','INSIGHT','What portion of working capital is genuinely addressable without harming operations?','Investigate the underlying balances, causes, timing and operational guardrails before estimating cash release.'),
'MARGIN_PRICING':('Margin and pricing performance requires review','INSIGHT','What is driving the evidenced margin movement?','Separate price, volume, mix and cost effects before defining an intervention.'),
'REVENUE_PERFORMANCE':('Revenue performance requires review','INSIGHT','What are the evidenced drivers of the revenue movement?','Review customer, product, price, volume and timing evidence before attributing cause.'),
'FORECAST_CONTROL':('Forecasting and performance management require attention','CAPABILITY','Which forecast assumptions or KPI gaps are reducing decision quality?','Reconcile forecast drivers to actual outcomes and improve the smallest set of decision-useful KPIs.'),
'PEOPLE_PRODUCTIVITY':('People and productivity require review','INSIGHT','Where is workforce capacity economically constrained or underused?','Validate role, FTE, output and capacity evidence before changing cost or headcount.'),
'DATA_CAPACITY':('Capacity data is not decision-reliable','DATA_ISSUE','What units or formulas are causing the capacity schedule to produce implausible utilisation?','Confirm source units and formulas, correct the schedule at source and rerun capacity diagnostics.'),
}

def build_management_attention(con,run,client,min_items=3,max_items=7):
    con.executescript(SCHEMA)
    con.execute('DELETE FROM management_attention_evidence WHERE attention_item_id IN (SELECT attention_item_id FROM management_attention_item WHERE run_id=?)',(run,))
    con.execute('DELETE FROM management_attention_item WHERE run_id=?',(run,))
    signals=con.execute("SELECT * FROM signal WHERE run_id=? AND client_id=? AND status='ACTIVE' AND materiality_state IN ('MEDIUM','HIGH')",(run,client)).fetchall()
    groups={}
    for s in signals: groups.setdefault(_theme(s),[]).append(s)
    # A refused material capacity diagnostic is itself a management-relevant data issue, not an operational conclusion.
    cap=con.execute("SELECT * FROM test_execution WHERE run_id=? AND test_id='PEO-04' AND execution_status!='COMPLETED'",(run,)).fetchone()
    if cap and cap['limitation'] and ('implausible' in cap['limitation'].lower() or 'inconsistent' in cap['limitation'].lower()): groups['DATA_CAPACITY']=[]
    candidates=[]
    for theme,rows in groups.items():
        if theme=='OTHER': continue
        title,itype,q,nxt=META[theme]
        mats=[RANK.get(r['materiality_state'],1) for r in rows]
        high=sum(1 for r in rows if r['materiality_state']=='HIGH')
        # Priority combines severity, corroboration and decision blockage; never raw £ magnitude alone.
        score=(max(mats) if mats else 2) + (1 if len(rows)>=2 else 0) + (1 if theme=='FINANCIAL_INTEGRITY' and len(rows)>=2 else 0)
        priority='HIGH' if score>=4 else 'MEDIUM'
        exstates=[]
        for r in rows:
            ex=con.execute('SELECT eligibility_state FROM test_execution WHERE test_execution_id=?',(r['test_execution_id'],)).fetchone()
            if ex: exstates.append(ex['eligibility_state'])
        confidence='HIGH' if exstates and all(x=='FULL' for x in exstates) else ('MEDIUM' if rows else 'LOW')
        if theme=='FINANCIAL_INTEGRITY':
            recs=con.execute("SELECT * FROM reconciliation WHERE run_id=? AND status='FAILED'",(run,)).fetchall()
            residuals=', '.join(f"{r['reconciliation_type']}: {r['residual']}" for r in recs)
            rationale=f"{len(recs)} independently assessed reconciliation control(s) failed. Residuals are control exceptions, not assumed losses: {residuals}."
        elif theme=='DATA_CAPACITY':
            rationale='Capacity evidence was refused because source units/formulas produced internally inconsistent or implausible utilisation. No repaired utilisation or saving has been invented.'
        else:
            tests=sorted(set(r['test_id'] for r in rows)); rationale=f"{len(rows)} material signal(s) across {', '.join(tests)} support one management theme. Related signals are compressed without deleting their underlying evidence."
        # Tie-break by decision blockage and corroboration, not largest monetary observation.
        tie={'FINANCIAL_INTEGRITY':5,'CAPACITY_CONSTRAINT':4,'MARGIN_PRICING':4,'WORKING_CAPITAL':3,'CUSTOMER_ECONOMICS':3,'SUPPLIER_DEPENDENCY':2,'REVENUE_PERFORMANCE':2,'FORECAST_CONTROL':2,'PEOPLE_PRODUCTIVITY':2,'DATA_CAPACITY':3}.get(theme,1)
        candidates.append((score,tie,len(rows),theme,title,itype,priority,confidence,rationale,q,nxt,rows))
    candidates.sort(key=lambda x:(x[0],x[1],x[2]),reverse=True)
    # Preserve a compact 3-7 agenda where at least three genuine themes exist; never pad with invented issues.
    selected=candidates[:max_items]
    if len(selected)<min_items: selected=candidates
    out=[]
    for idx,c in enumerate(selected,1):
        _,_,_,theme,title,itype,prio,conf,rat,q,nxt,rows=c; aid=_id('mai')
        limitation='No causal or monetised opportunity conclusion is created by management-attention selection.'
        con.execute('INSERT INTO management_attention_item VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(aid,run,client,theme,title,itype,prio,conf,len(rows),rat,q,nxt,limitation,idx,_now()))
        for r in rows: con.execute('INSERT OR IGNORE INTO management_attention_evidence VALUES (?,?,?,?,?,?)',(_id('mae'),aid,'SIGNAL',r['signal_id'],'SUPPORTING_EVIDENCE',_now()))
        out.append({'rank':idx,'theme':theme,'title':title,'issue_type':itype,'priority':prio,'confidence':conf,'evidence_count':len(rows),'rationale':rat,'management_question':q,'next_step':nxt,'limitation':limitation})
    # Replace old queue with theme-level agenda so duplicate findings cannot consume the attention budget.
    con.execute('DELETE FROM fd_review_queue WHERE run_id=?',(run,))
    for x in out:
        aid=con.execute('SELECT attention_item_id FROM management_attention_item WHERE run_id=? AND theme_key=?',(run,x['theme'])).fetchone()['attention_item_id']
        con.execute('INSERT INTO fd_review_queue VALUES (?,?,?,?,?,?,?,?,?)',(_id('fdq'),run,client,'MANAGEMENT_ATTENTION',aid,'Theme-level FD agenda selected after evidence clustering.',x['priority'],'PENDING',_now()))
    con.execute('DELETE FROM management_attention_budget WHERE run_id=?',(run,))
    con.execute('INSERT INTO management_attention_budget VALUES (?,?,?,?,?,?,?,?,?)',(_id('mab'),run,client,max_items,len(candidates),len(out),max(0,len(candidates)-len(out)),'MAB-2.0',_now()))
    con.commit(); return {'eligible_themes':len(candidates),'selected':len(out),'deferred':max(0,len(candidates)-len(out)),'items':out}
