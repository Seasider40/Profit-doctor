"""v2.29 Opportunity Economics & Overlap Qualification.
Portfolio economics deliberately separates profit, cash, avoided cost, risk and capability.
There is no cross-type headline £ total. Opportunity envelopes cap related economics and
relationships prevent additive presentation of overlapping/alternative routes.
"""
from decimal import Decimal as D
from datetime import datetime, timezone
import uuid

def _id(p): return p+'_'+uuid.uuid4().hex
def _now(): return datetime.now(timezone.utc).isoformat()

SCHEMA='''
CREATE TABLE IF NOT EXISTS opportunity_portfolio_envelope (
 portfolio_envelope_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 envelope_key TEXT NOT NULL, economic_bucket TEXT NOT NULL, maximum_expected_amount TEXT NOT NULL,
 currency TEXT NOT NULL, evidence_basis TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(run_id,client_id,envelope_key)
);
CREATE TABLE IF NOT EXISTS opportunity_portfolio_envelope_member (
 member_id TEXT PRIMARY KEY, portfolio_envelope_id TEXT NOT NULL, opportunity_id TEXT NOT NULL,
 created_at TEXT NOT NULL, UNIQUE(portfolio_envelope_id,opportunity_id)
);
'''

BUCKETS={
 'B1_RECURRING_PROFIT_IMPROVEMENT':'RECURRING_PROFIT',
 'B2_ONE_OFF_PROFIT_RECOVERY':'ONE_OFF_PROFIT',
 'B3_ONE_OFF_CASH_RELEASE':'ONE_OFF_CASH',
 'B4_RECURRING_WORKING_CAPITAL_EFFICIENCY':'WORKING_CAPITAL_EFFICIENCY',
 'B5_AVOIDED_FUTURE_COST':'AVOIDED_FUTURE_COST',
 'B6_RISK_MITIGATION':'RISK_MITIGATION',
 'B7_CAPABILITY_DECISION_IMPROVEMENT':'CAPABILITY_DECISION',
}

def economic_bucket(benefit_type): return BUCKETS.get(benefit_type,'OTHER')

def create_portfolio_envelope(con,run,client,envelope_key,economic_bucket_name,maximum_expected_amount,currency,evidence_basis,opportunity_ids):
    con.executescript(SCHEMA)
    cap=D(str(maximum_expected_amount))
    if cap<0: raise ValueError('Portfolio envelope cannot be negative')
    if not evidence_basis or not opportunity_ids: raise ValueError('Envelope evidence and members are required')
    rows=[]
    for oid in opportunity_ids:
        o=con.execute("SELECT * FROM opportunity WHERE opportunity_id=? AND run_id=? AND client_id=? AND status='SUPPORTED'",(oid,run,client)).fetchone()
        if not o: raise ValueError('Envelope members must be supported opportunities in the same client/run')
        if o['currency']!=currency: raise ValueError('Envelope members must use the envelope currency')
        if economic_bucket(o['benefit_type'])!=economic_bucket_name: raise ValueError('Envelope cannot combine different economic buckets')
        rows.append(o)
    eid=_id('penv')
    con.execute('INSERT INTO opportunity_portfolio_envelope VALUES (?,?,?,?,?,?,?,?,?,?)',(eid,run,client,envelope_key,economic_bucket_name,str(cap),currency,evidence_basis,'SUPPORTED',_now()))
    for o in rows: con.execute('INSERT INTO opportunity_portfolio_envelope_member VALUES (?,?,?,?)',(_id('pem'),eid,o['opportunity_id'],_now()))
    con.commit(); return eid

def portfolio_economics(con,run,client):
    con.executescript(SCHEMA)
    opps=con.execute("SELECT * FROM opportunity WHERE run_id=? AND client_id=? AND status='SUPPORTED'",(run,client)).fetchall()
    by={o['opportunity_id']:o for o in opps}
    bucket_gross={}; bucket_deduction={}; notes=[]
    for o in opps:
        b=economic_bucket(o['benefit_type']); bucket_gross[b]=bucket_gross.get(b,D('0'))+D(o['expected_amount'] or '0'); bucket_deduction.setdefault(b,D('0'))
    # Pair relationships apply only to additive economics in the same bucket. Cross-bucket cash manifestation is disclosed, not netted into a fake total.
    for rel in con.execute('SELECT * FROM opportunity_relationship WHERE run_id=? AND client_id=?',(run,client)).fetchall():
        l=by.get(rel['left_opportunity_id']); r=by.get(rel['right_opportunity_id'])
        if not l or not r: continue
        lb=economic_bucket(l['benefit_type']); rb=economic_bucket(r['benefit_type']); le=D(l['expected_amount'] or '0'); re=D(r['expected_amount'] or '0')
        if rel['relationship_type']=='CASH_MANIFESTATION':
            notes.append('Profit-to-cash manifestation is non-additive and is presented in separate economic buckets; no combined headline total is produced.')
            continue
        if lb!=rb:
            if rel['relationship_type'] in ('OVERLAPPING','ALTERNATIVE','MUTUALLY_EXCLUSIVE'):
                raise ValueError('Additive overlap/exclusivity relationships cannot span different economic buckets')
            continue
        if rel['relationship_type']=='OVERLAPPING': bucket_deduction[lb]+=min(D(rel['overlap_amount'] or '0'),le,re)
        elif rel['relationship_type'] in ('ALTERNATIVE','MUTUALLY_EXCLUSIVE'): bucket_deduction[lb]+=min(le,re)
    bucket_net={b:max(D('0'),bucket_gross[b]-bucket_deduction.get(b,D('0'))) for b in bucket_gross}
    # Evidence-backed portfolio envelopes cap the related group's contribution without double counting pairwise deductions again.
    for env in con.execute("SELECT * FROM opportunity_portfolio_envelope WHERE run_id=? AND client_id=? AND status='SUPPORTED'",(run,client)).fetchall():
        ids=[x['opportunity_id'] for x in con.execute('SELECT opportunity_id FROM opportunity_portfolio_envelope_member WHERE portfolio_envelope_id=?',(env['portfolio_envelope_id'],)).fetchall()]
        member_gross=sum((D(by[x]['expected_amount'] or '0') for x in ids if x in by),D('0'))
        cap=D(env['maximum_expected_amount']); b=env['economic_bucket']
        excess=max(D('0'),member_gross-cap)
        # envelope deduction is at least the excess, but do not stack it blindly on pairwise deductions for the same economics
        bucket_deduction[b]=max(bucket_deduction.get(b,D('0')),excess)
        bucket_net[b]=max(D('0'),bucket_gross.get(b,D('0'))-bucket_deduction[b])
    return {
      'buckets':{b:{'gross_expected':bucket_gross[b],'non_additive_deduction':bucket_deduction.get(b,D('0')),'portfolio_expected':bucket_net[b]} for b in bucket_gross},
      'headline_total':None,
      'headline_total_reason':'Profit, cash release, avoided cost, risk mitigation and capability value are not additive economic measures.',
      'notes':sorted(set(notes)),
      'supported_opportunities':len(opps)
    }
