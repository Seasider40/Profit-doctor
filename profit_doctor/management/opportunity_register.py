"""v2.28 Management Action & Opportunity Qualification.
Turns the FD attention agenda into action-ready records without converting exposures,
control residuals or capacity observations into unsupported savings.
"""
from datetime import datetime, timezone
import uuid

def _id(p): return f"{p}_{uuid.uuid4().hex}"
def _now(): return datetime.now(timezone.utc).isoformat()
SCHEMA='''
CREATE TABLE IF NOT EXISTS management_action_candidate (
 action_candidate_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 attention_item_id TEXT NOT NULL, theme_key TEXT NOT NULL, action_type TEXT NOT NULL,
 recommended_action TEXT NOT NULL, evidence_required TEXT NOT NULL, owner_role TEXT,
 action_state TEXT NOT NULL, limitation TEXT, created_at TEXT NOT NULL,
 UNIQUE(run_id,attention_item_id,action_type)
);
CREATE TABLE IF NOT EXISTS profit_cash_opportunity_register (
 register_item_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 attention_item_id TEXT NOT NULL, theme_key TEXT NOT NULL, register_type TEXT NOT NULL,
 purpose TEXT NOT NULL, benefit_type TEXT, opportunity_candidate_id TEXT,
 theoretical_amount TEXT, addressable_amount TEXT, expected_amount TEXT, currency TEXT,
 availability_state TEXT NOT NULL, economic_state TEXT NOT NULL,
 evidence_required TEXT NOT NULL, recommended_action TEXT NOT NULL,
 limitation TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(run_id,attention_item_id)
);
'''
META={
'FINANCIAL_INTEGRITY':('CONTROL_REMEDIATION','Reconcile failed control balances to source records and resolve timing, classification and posting differences.','Underlying ledger detail, control-account roll-forward and documented reconciling items.','PROTECT','B6_RISK_MITIGATION'),
'CUSTOMER_ECONOMICS':('COMMERCIAL_REVIEW','Review concentrated and low-contribution customer relationships; identify price, mix, service or retention interventions only where mechanism evidence exists.','Customer/product mix, price history, direct cost and where available cost-to-serve evidence.','IMPROVE','B1_RECURRING_PROFIT_IMPROVEMENT'),
'SUPPLIER_DEPENDENCY':('SUPPLIER_REVIEW','Review concentrated suppliers for criticality, alternatives, terms and negotiation opportunities.','Contracts, item-level purchases/prices, alternative-source evidence and operational criticality.','PROTECT','B6_RISK_MITIGATION'),
'CAPACITY_CONSTRAINT':('CAPACITY_REVIEW','Validate bottleneck load and test scheduling, overtime, mix, process and investment alternatives before monetising.','Validated practical capacity, productive hours, overtime, throughput, scrap/downtime and contribution at constraint.','IMPROVE','B4_RECURRING_WORKING_CAPITAL_EFFICIENCY'),
'DATA_CAPACITY':('DATA_REMEDIATION','Correct capacity units/formulas at source and rerun the capacity diagnostic.','Confirmed units, formulas and source-system extraction logic.','TRANSFORM','B7_CAPABILITY_DECISION_IMPROVEMENT'),
'WORKING_CAPITAL':('WORKING_CAPITAL_REVIEW','Identify genuinely addressable receivables, payables and inventory actions subject to operational guardrails.','Invoice/aging detail, disputes/credits, supplier terms, stock aging/service-level evidence and cash timing.','RELEASE','B3_ONE_OFF_CASH_RELEASE'),
'MARGIN_PRICING':('MARGIN_REVIEW','Decompose price, volume, mix and cost effects and identify evidenced interventions.','Transaction pricing, volume/mix, purchase/direct-cost history and commercial terms.','IMPROVE','B1_RECURRING_PROFIT_IMPROVEMENT'),
'REVENUE_PERFORMANCE':('REVENUE_REVIEW','Identify evidenced customer/product/price/volume drivers before selecting growth or recovery actions.','Customer/product time series, pipeline/churn and price-volume-mix evidence.','RECOVER','B1_RECURRING_PROFIT_IMPROVEMENT'),
'FORECAST_CONTROL':('FORECAST_REMEDIATION','Reconcile forecast drivers to actual outcomes and improve decision-useful KPIs.','Forecast versions, assumptions, actuals and KPI definitions.','TRANSFORM','B7_CAPABILITY_DECISION_IMPROVEMENT'),
'PEOPLE_PRODUCTIVITY':('PRODUCTIVITY_REVIEW','Validate role, FTE, output and capacity evidence before workforce action.','Role/FTE cost, output, utilisation and workflow evidence.','IMPROVE','B5_AVOIDED_FUTURE_COST'),
}

def build_action_opportunity_register(con,run,client):
    con.executescript(SCHEMA)
    con.execute('DELETE FROM management_action_candidate WHERE run_id=?',(run,)); con.execute('DELETE FROM profit_cash_opportunity_register WHERE run_id=?',(run,))
    items=con.execute('SELECT * FROM management_attention_item WHERE run_id=? AND client_id=? ORDER BY rank_order',(run,client)).fetchall()
    out=[]
    for a in items:
        typ,act,req,purpose,btype=META.get(a['theme_key'],('INVESTIGATE',a['next_step'],'Additional causal and economic evidence.','TRANSFORM','B7_CAPABILITY_DECISION_IMPROVEMENT'))
        acid=_id('mac'); lim='Recommended action is an investigation/intervention path, not proof of causality or benefit.'
        con.execute('INSERT INTO management_action_candidate VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(acid,run,client,a['attention_item_id'],a['theme_key'],typ,act,req,'FD/Management','PROPOSED',lim,_now()))
        # Reuse only a pre-existing economic candidate related to evidence in this attention theme; never manufacture £ economics from the agenda.
        sigids=[r['object_id'] for r in con.execute("SELECT object_id FROM management_attention_evidence WHERE attention_item_id=? AND object_type='SIGNAL'",(a['attention_item_id'],)).fetchall()]
        oc=None
        if sigids:
            q=','.join('?'*len(sigids))
            oc=con.execute(f'''SELECT oc.* FROM opportunity_candidate oc JOIN finding f ON f.finding_id=oc.finding_id JOIN finding_version fv ON fv.finding_id=f.finding_id JOIN finding_candidate fc ON fc.finding_candidate_id=fv.finding_candidate_id JOIN evidence_bundle eb ON eb.evidence_bundle_id=fc.evidence_bundle_id WHERE oc.run_id=? AND eb.primary_signal_id IN ({q}) ORDER BY oc.created_at LIMIT 1''',(run,*sigids)).fetchone()
        theoretical=oc['theoretical_amount'] if oc else None; addressable=oc['addressable_amount'] if oc else None; expected=oc['expected_amount'] if oc else None
        estate='QUALIFIED' if oc and oc['candidate_status']=='QUALIFIED' else ('CANDIDATE_UNQUANTIFIED' if oc else 'EVIDENCE_REQUIRED')
        limitation='No monetary opportunity is supported from this management priority without mechanism, addressability and recovery-envelope evidence.'
        if a['theme_key']=='FINANCIAL_INTEGRITY': limitation='Reconciliation residuals are control exceptions, not losses, savings or cash opportunities.'; theoretical=addressable=expected=None
        if a['theme_key'] in ('CAPACITY_CONSTRAINT','DATA_CAPACITY'): limitation='Capacity released or data corrected is not a saving unless an evidenced economic use or avoided cost is demonstrated.'; theoretical=addressable=expected=None
        rid=_id('pcor')
        con.execute('INSERT INTO profit_cash_opportunity_register VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(rid,run,client,a['attention_item_id'],a['theme_key'],'MANAGEMENT_PRIORITY',purpose,btype,oc['opportunity_candidate_id'] if oc else None,theoretical,addressable,expected,oc['currency'] if oc else 'GBP',oc['availability_state'] if oc else 'CONDITIONAL',estate,req,act,limitation,_now()))
        out.append({'rank':a['rank_order'],'theme':a['theme_key'],'recommended_action':act,'evidence_required':req,'economic_state':estate,'theoretical_amount':theoretical,'addressable_amount':addressable,'expected_amount':expected,'limitation':limitation})
    con.commit()
    return {'items':out,'count':len(out),'quantified_supported':sum(1 for x in out if x['addressable_amount'] is not None and x['expected_amount'] is not None)}
