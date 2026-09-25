"""v2.30 Longitudinal Advisory & Benefit Realisation Qualification.
Cross-run continuity for issues, opportunities, actions and benefits without re-claiming prior value.
"""
from decimal import Decimal as D
from datetime import datetime, timezone
import uuid

def _now(): return datetime.now(timezone.utc).isoformat()
def _id(p): return p+'_'+uuid.uuid4().hex

SCHEMA=r'''
CREATE TABLE IF NOT EXISTS advisory_issue_thread (
 issue_thread_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, theme_key TEXT NOT NULL,
 issue_key TEXT NOT NULL, title TEXT NOT NULL, lifecycle_state TEXT NOT NULL,
 first_run_id TEXT NOT NULL, latest_run_id TEXT NOT NULL, opened_at TEXT NOT NULL,
 closed_at TEXT, reopened_count INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL, UNIQUE(client_id,issue_key)
);
CREATE TABLE IF NOT EXISTS advisory_issue_observation (
 issue_observation_id TEXT PRIMARY KEY, issue_thread_id TEXT NOT NULL, run_id TEXT NOT NULL,
 observed_state TEXT NOT NULL, evidence_basis TEXT NOT NULL, materiality_amount TEXT,
 currency TEXT, observed_at TEXT NOT NULL, UNIQUE(issue_thread_id,run_id)
);
CREATE TABLE IF NOT EXISTS longitudinal_opportunity (
 longitudinal_opportunity_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, opportunity_key TEXT NOT NULL,
 benefit_type TEXT NOT NULL, purpose TEXT NOT NULL, currency TEXT NOT NULL,
 first_opportunity_id TEXT NOT NULL, latest_opportunity_id TEXT NOT NULL,
 first_run_id TEXT NOT NULL, latest_run_id TEXT NOT NULL, lifecycle_state TEXT NOT NULL,
 expected_amount TEXT, remaining_expected_amount TEXT, stale_reason TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(client_id,opportunity_key)
);
CREATE TABLE IF NOT EXISTS longitudinal_opportunity_observation (
 observation_id TEXT PRIMARY KEY, longitudinal_opportunity_id TEXT NOT NULL, run_id TEXT NOT NULL,
 opportunity_id TEXT NOT NULL, expected_amount TEXT, remaining_expected_amount TEXT NOT NULL,
 observation_state TEXT NOT NULL, evidence_basis TEXT NOT NULL, observed_at TEXT NOT NULL,
 UNIQUE(longitudinal_opportunity_id,run_id)
);
CREATE TABLE IF NOT EXISTS benefit_claim_registry (
 claim_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, longitudinal_opportunity_id TEXT NOT NULL,
 benefit_leg_id TEXT NOT NULL UNIQUE, source_run_id TEXT NOT NULL, period_from TEXT, period_to TEXT,
 net_amount TEXT NOT NULL, currency TEXT NOT NULL, claim_state TEXT NOT NULL,
 created_at TEXT NOT NULL
);
'''

def ensure_schema(con): con.executescript(SCHEMA)

def observe_issue(con,client_id,run_id,issue_key,theme_key,title,observed_state,evidence_basis,materiality_amount=None,currency='GBP'):
    ensure_schema(con)
    allowed={'OPEN','IMPROVING','RESOLVED','RECURRED','DATA_CONSTRAINED'}
    if observed_state not in allowed: raise ValueError('Unsupported longitudinal issue state')
    row=con.execute('SELECT * FROM advisory_issue_thread WHERE client_id=? AND issue_key=?',(client_id,issue_key)).fetchone(); t=_now()
    if not row:
        tid=_id('issue'); lifecycle='RESOLVED' if observed_state=='RESOLVED' else 'OPEN'
        con.execute('INSERT INTO advisory_issue_thread VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(tid,client_id,theme_key,issue_key,title,lifecycle,run_id,run_id,t,t if lifecycle=='RESOLVED' else None,0,t,t))
    else:
        tid=row['issue_thread_id']; reopened=row['reopened_count']; lifecycle=row['lifecycle_state']; closed=row['closed_at']
        if observed_state in {'OPEN','RECURRED'} and lifecycle=='RESOLVED': reopened+=1; lifecycle='OPEN'; closed=None
        elif observed_state=='RESOLVED': lifecycle='RESOLVED'; closed=t
        elif observed_state in {'OPEN','IMPROVING','DATA_CONSTRAINED'}: lifecycle='OPEN'
        con.execute('UPDATE advisory_issue_thread SET latest_run_id=?,lifecycle_state=?,closed_at=?,reopened_count=?,updated_at=? WHERE issue_thread_id=?',(run_id,lifecycle,closed,reopened,t,tid))
    con.execute('INSERT INTO advisory_issue_observation VALUES (?,?,?,?,?,?,?,?)',(_id('iobs'),tid,run_id,observed_state,evidence_basis,None if materiality_amount is None else str(D(str(materiality_amount))),currency,t)); con.commit(); return tid

def track_opportunity(con,client_id,run_id,opportunity_id,opportunity_key,evidence_basis,stale=False,stale_reason=None):
    ensure_schema(con)
    o=con.execute('SELECT * FROM opportunity WHERE opportunity_id=? AND client_id=?',(opportunity_id,client_id)).fetchone()
    if not o: raise ValueError('Opportunity not found for client')
    expected=D(o['expected_amount'] or '0'); row=con.execute('SELECT * FROM longitudinal_opportunity WHERE client_id=? AND opportunity_key=?',(client_id,opportunity_key)).fetchone(); t=_now()
    if not row:
        lid=_id('lopp'); prior=D('0')
        state='STALE' if stale else 'ACTIVE'; remaining=D('0') if stale else expected
        con.execute('INSERT INTO longitudinal_opportunity VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(lid,client_id,opportunity_key,o['benefit_type'],o['purpose'],o['currency'],opportunity_id,opportunity_id,run_id,run_id,state,str(expected),str(remaining),stale_reason,t,t))
    else:
        lid=row['longitudinal_opportunity_id']
        # Claims are cumulative across all historical runs for this economic opportunity.
        claimed=con.execute("SELECT COALESCE(SUM(CAST(net_amount AS REAL)),0) x FROM benefit_claim_registry WHERE longitudinal_opportunity_id=? AND claim_state='COUNTED'",(lid,)).fetchone()['x']; prior=D(str(claimed))
        remaining=max(D('0'),expected-prior); state='STALE' if stale else ('EXHAUSTED' if remaining==0 else 'ACTIVE')
        if stale: remaining=D('0')
        con.execute('UPDATE longitudinal_opportunity SET latest_opportunity_id=?,latest_run_id=?,lifecycle_state=?,expected_amount=?,remaining_expected_amount=?,stale_reason=?,updated_at=? WHERE longitudinal_opportunity_id=?',(opportunity_id,run_id,state,str(expected),str(remaining),stale_reason,t,lid))
    con.execute('INSERT INTO longitudinal_opportunity_observation VALUES (?,?,?,?,?,?,?,?,?)',(_id('lobs'),lid,run_id,opportunity_id,str(expected),str(remaining),state,evidence_basis,t)); con.commit(); return lid

def register_benefit_claim(con,client_id,longitudinal_opportunity_id,benefit_leg_id):
    ensure_schema(con)
    lo=con.execute('SELECT * FROM longitudinal_opportunity WHERE longitudinal_opportunity_id=? AND client_id=?',(longitudinal_opportunity_id,client_id)).fetchone()
    b=con.execute('SELECT * FROM benefit_leg WHERE benefit_leg_id=? AND client_id=?',(benefit_leg_id,client_id)).fetchone()
    if not lo or not b: raise ValueError('Longitudinal opportunity and benefit must belong to same client')
    if b['status'] not in {'REALISED','VERIFIED','RETAINED'}: raise ValueError('Only realised/verified/retained benefit can be claimed')
    existing=con.execute('SELECT * FROM benefit_claim_registry WHERE benefit_leg_id=?',(benefit_leg_id,)).fetchone()
    if existing: raise ValueError('Benefit leg has already been claimed')
    amount=D(b['net_amount']); t=_now()
    con.execute('INSERT INTO benefit_claim_registry VALUES (?,?,?,?,?,?,?,?,?,?,?)',(_id('claim'),client_id,longitudinal_opportunity_id,benefit_leg_id,b['run_id'],b['period_from'],b['period_to'],str(amount),b['currency'],'COUNTED',t))
    total=D(str(con.execute("SELECT COALESCE(SUM(CAST(net_amount AS REAL)),0) x FROM benefit_claim_registry WHERE longitudinal_opportunity_id=? AND claim_state='COUNTED'",(longitudinal_opportunity_id,)).fetchone()['x']))
    expected=D(lo['expected_amount'] or '0'); remaining=max(D('0'),expected-total)
    state='EXHAUSTED' if remaining==0 else lo['lifecycle_state']
    con.execute('UPDATE longitudinal_opportunity SET remaining_expected_amount=?,lifecycle_state=?,updated_at=? WHERE longitudinal_opportunity_id=?',(str(remaining),state,t,longitudinal_opportunity_id)); con.commit(); return amount

def longitudinal_summary(con,client_id):
    ensure_schema(con)
    issues=con.execute('SELECT * FROM advisory_issue_thread WHERE client_id=?',(client_id,)).fetchall(); opps=con.execute('SELECT * FROM longitudinal_opportunity WHERE client_id=?',(client_id,)).fetchall()
    claimed=D(str(con.execute("SELECT COALESCE(SUM(CAST(net_amount AS REAL)),0) x FROM benefit_claim_registry WHERE client_id=? AND claim_state='COUNTED'",(client_id,)).fetchone()['x']))
    remaining=sum((D(x['remaining_expected_amount'] or '0') for x in opps),D('0'))
    return {'issue_threads':len(issues),'open_issues':sum(1 for x in issues if x['lifecycle_state']=='OPEN'),'reopened_issues':sum(x['reopened_count'] for x in issues),'opportunities':len(opps),'claimed_realised':claimed,'remaining_expected':remaining,'stale_opportunities':sum(1 for x in opps if x['lifecycle_state']=='STALE')}
