"""Sprint 4 deterministic Diagnostic Engine.

Diagnostics consume trusted canonical evidence / primitives and emit Signals, not Findings.
No AI interpretation or opportunity value is created here.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone, date
from collections import defaultdict

D=lambda x: Decimal(str(x))
def id4(p): return f"{p}_{uuid.uuid4().hex}"
def now(): return datetime.now(timezone.utc).isoformat()

TESTS=[
('REV-01','Revenue Trend','How is revenue genuinely changing over time, and is the direction improving, weakening or simply reflecting normal timing?','Measure comparable revenue trend and material movement.','1.0'),
('REV-02','Revenue Bridge','What explains the movement in revenue between comparable periods?','Reconcile prior to current revenue through customer movements.','1.0'),
('REV-03','New vs Existing Customer Growth','Is growth coming from existing customers, new customers, reactivated customers or being offset by lost customers?','Decompose revenue movement by customer state.','1.0'),
('REV-04','Price Volume Mix','Is revenue changing because of price, volume or mix — and how much does each factor explain?','Decompose comparable revenue movement into evidenced price, volume and portfolio/mix effects.','1.0'),
('REV-05','Seasonality & Normalisation','What is normal seasonality for this business, and which movements are genuinely unusual rather than timing effects?','Measure month-of-year seasonality and distinguish normal timing patterns from unusual movement.','1.0'),
('REV-06','Revenue Volatility & Predictability','How predictable is revenue, which revenue streams are stable or volatile, and how much visibility does management really have?','Measure monthly revenue volatility and evidenced recurring-revenue mix without inventing forecast certainty.','1.0'),
('GM-01','Gross Margin Trend','Is commercial margin improving or deteriorating, and is the movement persistent or temporary?','Measure transaction contribution margin trend.','1.0'),
('GM-02','Gross Margin Variance Bridge','How much economic impact has the change in commercial margin created between comparable periods?','Quantify contribution change and margin-rate effect without calling it recoverable opportunity.','1.0'),
('GM-03','Customer Margin Variance','Which customers are driving margin improvement or deterioration, and where is the movement economically material?','Measure comparable customer contribution-margin variance without assuming causality or recoverability.','1.0'),
('GM-04','Product / Service Margin Variance','Which products or services are driving margin improvement or deterioration, and where is the movement economically material?','Measure comparable product/service contribution-margin variance.','1.0'),
('GM-05','Margin Leakage','Where is realised margin below an evidenced comparable baseline, and how much historical impact does that represent?','Identify evidenced margin leakage signals while separating impact from opportunity.','1.0'),
('GM-06','Purchase-Cost Inflation Recovery','Where have comparable unit costs increased, how much economic pressure has that created, and how much has selling price subsequently recovered?','Measure comparable unit-cost inflation and evidenced selling-price recovery without inventing recoverability.','1.0'),
('GM-07','Negative & Abnormal Transaction Margins','Which transactions have negative or abnormal margins, how material are they, and do they indicate errors, exceptions or commercial issues requiring investigation?','Detect negative and abnormal transaction margins as forensic signals, not automatic errors or opportunities.','1.0'),
('CUS-01','Customer Concentration & Dependency','How dependent is the business on individual customers, and how much revenue is concentrated in its largest relationships?','Measure customer concentration and dependency signals.','1.0'),
('CUS-02','Customer Profitability','Which customers genuinely create the most and least gross profit or contribution, and where is customer economics materially different?','Measure customer revenue, Contribution 0 and margin economics without confusing revenue scale with profitability.','1.0'),
('CUS-03','Customer Contribution after Cost-to-Serve','Which customers remain economically attractive after the direct and evidenced costs of serving them are considered?','Measure customer contribution after evidenced cost-to-serve, degrading explicitly when CTS data is unavailable.','1.0'),
('CUS-04','Customer Growth & Decline','Which customers are genuinely growing or declining, by how much, and where is the movement material?','Identify material comparable-period customer movement.','1.0'),
('CUS-05','Customer Retention, Churn & Reactivation','Which customers are being retained, lost or reactivated, and what do those movements mean for the revenue base?','Classify comparable customer states and quantify retained, lost and reactivated revenue without inventing causality.','1.0'),
('CUS-06','Customer Payment Behaviour & Cash Quality','Which customers are creating collection pressure, how concentrated is overdue cash, and where does payment behaviour weaken revenue quality?','Connect customer economics to evidenced receivables and overdue balances while refusing unsupported payment-timing conclusions.','1.0'),
('CUS-07','Customer Pareto & Economic Distribution','How concentrated is economic value across the customer base, and which relationships sit in the economically important head and long tail?','Measure customer revenue and contribution Pareto distribution without turning distribution bands into automatic actions.','1.0'),
('PROD-01','Product / Service Profitability','Which products or services genuinely create the most and least economic contribution, and where are margins materially different?','Measure product/service revenue, Contribution 0 and margin economics without confusing revenue scale with profitability.','1.0'),
('PROD-02','Product / Service Mix','How is the sales and contribution mix changing, and which products or services are driving that shift?','Measure product/service revenue and contribution mix movement while separating mix observation from causal explanation.','1.0'),
('PROD-03','Product / Service Growth & Decline','Which products or services are genuinely growing or declining, by how much, and where is the movement economically material?','Identify material comparable-period product/service revenue and contribution movement.','1.0'),
('PROD-04','Long-Tail & Complexity Economics','How much of the portfolio creates meaningful economic value, where does complexity sit, and which long-tail items warrant investigation?','Measure portfolio concentration and low-scale complexity signals without automatically recommending product removal.','1.0'),
('PROD-05','Cross-Sell & Penetration','Which existing customer relationships contain evidenced product or service whitespace, and how large is the theoretical commercial space before addressability is assessed?','Identify customer-product whitespace and penetration signals without converting theoretical whitespace into forecast revenue or opportunity.','1.0'),
('PRI-01','Price Realisation & Movement','What prices are customers actually paying, how are realised prices moving, and where are those movements economically material?','Measure realised unit-price movement on comparable customer-product and product relationships.','1.0'),
('PRI-02','Price Dispersion & Comparability','Where are comparable customers paying materially different prices for comparable products or services, and which differences warrant investigation?','Measure evidenced realised-price dispersion while refusing to label price differences as errors without commercial context.','1.0'),
('PRI-03','Discount, Rebate & Commercial Leakage','Where is realised price below an evidenced commercial reference, and how much historical value sits in those differences before cause and entitlement are established?','Detect transaction price leakage signals; explicit discount/rebate analysis requires D14 commercial data.','1.0'),
('PRI-04','Price Increase Effectiveness','Where have prices increased, how broadly have increases been realised, and where has intended recovery apparently not flowed through?','Measure comparable realised-price movement and coverage; campaign effectiveness requires explicit pricing-history or campaign evidence.','1.0'),
('PRI-05','Pricing Opportunity & Optimisation','Where does pricing evidence suggest potential improvement, what is theoretical versus addressable, and what must be proven before a pricing opportunity is quantified?','Synthesize pricing candidates without converting dispersion or leakage signals into unsupported opportunity value.','1.0'),
('PEO-01','People Cost & Workforce Economics','What does the workforce genuinely cost, how is that cost structured, and how is it changing?','Measure evidenced FTE and fully loaded people cost, including separately visible variable pay.','1.0'),
('PEO-02','Revenue / GP / Contribution per FTE','How much revenue and economic contribution is the workforce supporting per FTE?','Measure current revenue and Contribution 0 per evidenced FTE without treating ratios as causal productivity proof.','1.0'),
('PEO-03','Department & Role Productivity','Where do workforce cost, FTE and evidenced operating measures differ across departments and roles?','Measure department/role workforce economics while refusing unsupported cross-role productivity rankings.','1.0'),
('PEO-04','Capacity, Utilisation & Workforce Efficiency','Where is practical workforce capacity constrained or underused, and how much capacity is genuinely evidenced?','Measure practical capacity and utilisation without converting unused hours into financial savings.','1.0'),
('PEO-05','People Opportunity & Workforce Optimisation','Where could workforce economics improve, and what must happen before released capacity becomes a financial benefit?','Identify workforce optimisation candidates while keeping capacity, avoided future cost and realised savings economically distinct.','1.0'),
('SUP-01','Supplier Spend & Cost Base Intelligence','Where is money being spent, which suppliers and categories matter most, and how is the cost base changing?','Measure supplier/category spend and concentration without equating high spend with overspend.','1.0'),
('SUP-02','Supplier Cost Inflation & Purchase Price Variance','What has genuinely happened to the prices the business pays for comparable goods and services, what caused those movements, how much economic impact have they created, and how much has subsequently been recovered through customer pricing or other action?','Measure like-for-like purchase-cost movement and PPV without assuming supplier causality or recoverability.','1.0'),
('SUP-03','Supplier Concentration, Dependency & Commercial Risk','Which suppliers does your business genuinely depend on, what profit or revenue is exposed if something changes, and where should you reduce risk or strengthen your commercial position?','Measure spend concentration and evidenced dependency while refusing to invent disruption probability or expected loss.','1.0'),
('SUP-04','Overhead Efficiency & Cost Drift','Which business costs are creeping up, growing faster than the business, or no longer delivering enough value — and where is there a realistic opportunity to improve profitability without damaging the operation?','Measure overhead/category drift without equating cost growth with waste.','1.0'),
('SUP-05','Duplicate, Recurring & Unusual Spend','Where could money be leaking out of the business through duplicate payments, forgotten subscriptions, billing errors, unusual transactions or weak purchasing controls — and which items are genuinely worth recovering or stopping?','Detect duplicate-looking, recurring and unusual spend as forensic cases, never automatic errors or savings.','1.0'),
('SUP-06','Supplier & Overhead Opportunity Optimisation','Where can your business realistically reduce costs, recover lost money or improve supplier terms — how much is each opportunity genuinely worth, how difficult is it to achieve, and what should you tackle first?','Create supplier/overhead opportunity candidates while requiring mechanism evidence before financial qualification.','1.0'),
('WC-01','Cash Conversion & Working Capital Intelligence','Your business is making profit — so where is the cash going, what is tying it up, and is your working capital getting better or worse?','Surface evidenced DSO/DIO/DPO/CCC facts.','1.0'),
('WC-02','Receivables & Collection Performance','Which customers are tying up your cash, why are they paying late, how much cash is genuinely collectible, and what needs to change to get you paid faster?','Surface evidenced receivables and overdue balance signals.','1.0'),
('WC-03','Payables & Supplier Payment Performance','Are you paying suppliers at the right time — or is cash leaving too early, discounts being missed, terms being underused, or suppliers being stretched in ways that could put the business at risk?','Measure evidenced payables and payment pressure without treating supplier stretch as free financing.','1.0'),
('WC-04','Inventory & Stock Economics','How much cash is tied up in stock, which inventory is genuinely needed, which is moving too slowly or becoming obsolete, and how much cash could realistically be released without putting sales or customer service at risk?','Measure evidenced inventory and DIO without equating inventory balance with releasable cash.','1.0'),
('WC-05','Cash Flow, Liquidity & Cash Pressure','How much cash does the business really have available, what is going to happen to it next, and how early can we identify potential cash pressure before it becomes a problem?','Measure evidenced available cash and liquidity boundaries without inventing facility headroom or forecasts.','1.0'),
('WC-06','Working Capital Leakage & Cash Release','Where is cash unnecessarily trapped in the business, why is it trapped, and how much could realistically be released without damaging customers, suppliers, operations or growth?','Identify working-capital release candidates while keeping balances, exposure and addressable cash release distinct.','1.0'),
('WC-07','Working Capital & Cash Opportunity Optimisation','What should you actually do to improve cash, how much will each action realistically release, when will the cash arrive, what could it put at risk, and what is the best combined plan for the business?','Synthesize cash optimisation candidates without treating collection, inventory reduction or payment delay as profit.','1.0'),
('FCST-01','Budget & Forecast Performance Intelligence','You had a plan — so what actually happened, where did performance differ, why did it differ, and what does that tell you about the business going forward?','Compare preserved plan versions with actual outcomes while keeping variance distinct from explanation.','1.0'),
('FCST-02','Forecast Accuracy, Bias & Predictability','How reliable are your forecasts, what do you consistently get wrong, how early could those misses have been detected, and which parts of the business can you genuinely predict with confidence?','Measure forecast-vintage error and directional bias without converting historical accuracy into certainty.','1.0'),
('FCST-03','KPI, Driver & Performance Management Intelligence','Are you measuring the things that actually drive profit and cash — and which numbers should management be watching now to understand what is likely to happen next?','Surface evidenced KPI and driver observations while distinguishing association from causality.','1.0'),
('FCST-04','Forward Outlook, Scenario & Performance Optimisation','Based on what we know today, where is the business heading, what could change that outcome, and which actions would make the biggest difference to future profit and cash?','Create transparent forward-looking scenario signals from explicit assumptions; scenarios are decision tools, not predictions.','1.0'),
('RISK-01','Financial Integrity, Reconciliation & Accounting Control','Can you trust the numbers you are using to run the business — and where could errors, unreconciled balances or weak financial controls be distorting the picture?','Synthesize financial-integrity and reconciliation evidence without representing Profit Doctor as an audit opinion.','1.0'),
('RISK-02','Transaction, Process & Control Exception Intelligence','Where are unusual transactions, repeated exceptions or weaknesses in financial processes creating unnecessary risk — and which items genuinely need management attention or investigation?','Surface evidenced control/process exceptions while keeping anomaly, error, misconduct and loss distinct.','1.0'),
('RISK-03','Financial Exposure, Resilience & Risk Intelligence','What could materially hurt the business financially, how much is genuinely exposed, how resilient are you if conditions change, and which risks actually deserve management attention?','Measure evidenced financial exposure and concentration without inventing probability or expected loss.','1.0'),
('RISK-04','Financial Risk, Control & Governance Optimisation','What should management actually fix, strengthen, monitor or consciously accept to protect the business — without creating unnecessary bureaucracy or getting in the way of profitable growth?','Create proportionate governance/action candidates from evidenced weaknesses and exposures; management judgement remains explicit.','1.0')]

def seed_registry(con):
    con.executemany('INSERT OR IGNORE INTO test_registry VALUES (?,?,?,?,?,?)',[(a,b,c,d,e,'ACTIVE') for a,b,c,d,e in TESTS]); con.commit()

def _latest_sales_dv(con,client):
    return con.execute("""SELECT dv.* FROM dataset d JOIN dataset_version dv ON dv.dataset_id=d.dataset_id
      WHERE d.client_id=? AND d.data_domain='D07_SALES_TRANSACTIONS' AND dv.ingestion_status='COMPLETED'
      ORDER BY dv.version_number DESC LIMIT 1""",(client,)).fetchone()

def _eligibility(con,run,test):
    r=con.execute('SELECT * FROM test_eligibility WHERE run_id=? AND test_id=? ORDER BY assessed_at DESC LIMIT 1',(run,test)).fetchone()
    return (r['eligibility_state'],r['selected_method'],r['limitation']) if r else ('UNAVAILABLE',None,'Eligibility not assessed')

def _execute(con,run,client,test,method,elig,status,signals,lim=None):
    x=id4('tex'); t=now(); con.execute('INSERT INTO test_execution VALUES (?,?,?,?,?,?,?,?,?,?,?)',(x,run,client,test,method,elig,status,len(signals),lim,t,t))
    for s in signals:
        sid=id4('sig'); con.execute('INSERT INTO signal VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(sid,x,run,client,test,s['type'],s.get('entity_type'),s.get('entity_id'),s.get('period_from'),s.get('period_to'),_sv(s.get('observed')),_sv(s.get('comparison')),_sv(s.get('variance')),s.get('unit'),s.get('materiality','INFORMATIONAL'),s.get('status','ACTIVE'),s['evidence'],s.get('primitive'),now()))
        for typ,obj,scope in s.get('lineage',[]): con.execute('INSERT INTO diagnostic_lineage VALUES (?,?,?,?,?,?)',(id4('dlin'),sid,typ,obj,'DERIVED_FROM',scope))
    con.commit(); return {'test_id':test,'status':status,'eligibility':elig,'signal_count':len(signals),'limitations':lim}
def _sv(v): return None if v is None else str(v)

def _windows(rows):
    mx=max(date.fromisoformat(r['transaction_date']) for r in rows)
    cur_start=date(mx.year-1,mx.month,mx.day) if not(mx.month==2 and mx.day==29) else date(mx.year-1,2,28)
    prev_end=cur_start; prev_start=date(cur_start.year-1,cur_start.month,cur_start.day)
    prev=[r for r in rows if prev_start < date.fromisoformat(r['transaction_date']) <= prev_end]
    cur=[r for r in rows if cur_start < date.fromisoformat(r['transaction_date']) <= mx]
    return prev,cur,prev_start,prev_end,cur_start,mx

def _sum(rows,key): return sum((D(r[key]) for r in rows if r[key] is not None),D('0'))
def _cust(rows):
    o=defaultdict(lambda:D('0'))
    for r in rows: o[r['customer_entity_id']] += D(r['net_revenue'])
    return o

def _materiality(amount,base):
    if base==0: return 'INFORMATIONAL'
    pct=abs(amount)/abs(base)*D('100')
    return 'HIGH' if pct>=D('10') else ('MEDIUM' if pct>=D('5') else ('LOW' if pct>=D('2') else 'INFORMATIONAL'))

def _sales_context(con,client,dv):
    rows=con.execute("SELECT * FROM sales_transaction WHERE client_id=? AND dataset_version_id=? AND record_status='ACTIVE'",(client,dv['dataset_version_id'])).fetchall()
    return rows,_windows(rows)

def revenue_diagnostics(con,run,client,dv):
    rows,(prev,cur,ps,pe,cs,mx)=_sales_context(con,client,dv); lin=[('DATASET_VERSION',dv['dataset_version_id'],'comparable 12-month canonical sales windows')]
    p=_sum(prev,'net_revenue'); c=_sum(cur,'net_revenue'); delta=c-p; growth=(delta/p*D('100')) if p else None
    out={}
    e,m,l=_eligibility(con,run,'REV-01'); sig=[]
    if e!='UNAVAILABLE': sig=[{'type':'COMPARABLE_REVENUE_CHANGE','period_from':ps.isoformat(),'period_to':mx.isoformat(),'observed':c,'comparison':p,'variance':delta,'unit':'GBP','materiality':_materiality(delta,p),'evidence':f'Current comparable revenue {c}; prior {p}; growth {growth if growth is not None else "not meaningful"}%.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin}]
    out['REV-01']=_execute(con,run,client,'REV-01',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)
    pc=_cust(prev); cc=_cust(cur); ids=set(pc)|set(cc); bridge=[]
    for cid in ids:
        d=cc[cid]-pc[cid]
        if d: bridge.append((cid,pc[cid],cc[cid],d))
    e,m,l=_eligibility(con,run,'REV-02'); sig=[]
    if e!='UNAVAILABLE':
        # only material bridge legs; execution retains reconciled total in summary signal
        sig=[{'type':'REVENUE_BRIDGE_TOTAL','observed':c,'comparison':p,'variance':delta,'unit':'GBP','materiality':_materiality(delta,p),'evidence':f'Customer bridge reconciles exactly to total revenue movement {delta}.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin}]
        for cid,a,b,d in sorted(bridge,key=lambda x:abs(x[3]),reverse=True)[:10]: sig.append({'type':'CUSTOMER_BRIDGE_LEG','entity_type':'CUSTOMER','entity_id':cid,'observed':b,'comparison':a,'variance':d,'unit':'GBP','materiality':_materiality(d,p),'evidence':f'Customer revenue moved from {a} to {b}, contribution to bridge {d}.','primitive':'CUSTOMER_REVENUE','lineage':lin})
    out['REV-02']=_execute(con,run,client,'REV-02',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)
    e,m,l=_eligibility(con,run,'REV-03'); sig=[]
    if e!='UNAVAILABLE':
        new=sum((cc[i] for i in ids if pc[i]==0 and cc[i]>0),D('0')); lost=sum((pc[i] for i in ids if pc[i]>0 and cc[i]==0),D('0')); existing=sum((cc[i]-pc[i] for i in ids if pc[i]>0 and cc[i]>0),D('0'))
        sig=[{'type':'NEW_CUSTOMER_REVENUE','observed':new,'unit':'GBP','materiality':_materiality(new,p),'evidence':f'Revenue from customers absent in prior comparable window: {new}.','primitive':'CUSTOMER_REVENUE','lineage':lin},{'type':'LOST_CUSTOMER_REVENUE','observed':lost,'unit':'GBP','materiality':_materiality(lost,p),'evidence':f'Prior revenue from customers absent in current comparable window: {lost}.','primitive':'CUSTOMER_REVENUE','lineage':lin},{'type':'EXISTING_CUSTOMER_NET_CHANGE','observed':existing,'unit':'GBP','materiality':_materiality(existing,p),'evidence':f'Net movement among customers active in both comparable windows: {existing}.','primitive':'CUSTOMER_REVENUE','lineage':lin}]
    out['REV-03']=_execute(con,run,client,'REV-03',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)
    return out

def _prod(rows):
    o=defaultdict(lambda:{'revenue':D('0'),'units':D('0')})
    for r in rows:
        pid=r['product_entity_id']
        if not pid: continue
        o[pid]['revenue'] += D(r['net_revenue'])
        if r['units'] not in (None,''): o[pid]['units'] += D(r['units'])
    return o

def extended_revenue_diagnostics(con,run,client,dv):
    rows,(prev,cur,ps,pe,cs,mx)=_sales_context(con,client,dv)
    lin=[('DATASET_VERSION',dv['dataset_version_id'],'comparable canonical sales evidence')]
    out={}
    e,m,l=_eligibility(con,run,'REV-04'); sig=[]
    if e!='UNAVAILABLE':
        pa,ca=_prod(prev),_prod(cur); ptotal=_sum(prev,'net_revenue'); ctotal=_sum(cur,'net_revenue'); total_delta=ctotal-ptotal
        price=volume=D('0'); comparable_products=0
        for pid in set(pa)&set(ca):
            q0,q1=pa[pid]['units'],ca[pid]['units']
            if q0<=0 or q1<=0: continue
            r0,r1=pa[pid]['revenue'],ca[pid]['revenue']; p0=r0/q0; p1=r1/q1
            volume += (q1-q0)*p0; price += (p1-p0)*q1; comparable_products += 1
        residual=total_delta-price-volume
        if comparable_products:
            for typ,val,desc in [('PRICE_EFFECT',price,'price'),('VOLUME_EFFECT',volume,'volume'),('MIX_PORTFOLIO_RESIDUAL',residual,'mix, new/lost products and non-comparable portfolio effects')]:
                sig.append({'type':typ,'observed':val,'unit':'GBP','materiality':_materiality(val,ptotal),'evidence':f'Comparable PVM bridge {desc} effect {val}. Residual is explicit, not silently attributed.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin})
            sig.append({'type':'PVM_RECONCILIATION','observed':price+volume+residual,'comparison':total_delta,'variance':(price+volume+residual)-total_delta,'unit':'GBP','materiality':'INFORMATIONAL','evidence':f'Price + volume + explicit residual equals total comparable revenue movement {total_delta}. Comparable products with usable units: {comparable_products}.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin})
        else: l=((l+'; ') if l else '')+'No common products with positive units in both comparable windows; PVM refused'
    out['REV-04']=_execute(con,run,client,'REV-04',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)

    e,m,l=_eligibility(con,run,'REV-05'); sig=[]
    if e!='UNAVAILABLE':
        monthly=defaultdict(lambda:D('0'))
        for r in rows: monthly[r['transaction_date'][:7]] += D(r['net_revenue'])
        if len(monthly)>=12:
            overall=sum(monthly.values(),D('0'))/D(len(monthly)); by_moy=defaultdict(list)
            for ym,v in monthly.items(): by_moy[int(ym[5:7])].append(v)
            indices={mo:(sum(vs,D('0'))/D(len(vs))/overall*D('100') if overall else None) for mo,vs in by_moy.items()}
            valid={k:v for k,v in indices.items() if v is not None}
            if valid:
                peak=max(valid,key=valid.get); trough=min(valid,key=valid.get); spread=valid[peak]-valid[trough]
                sig=[{'type':'SEASONAL_PEAK_MONTH','observed':valid[peak],'comparison':D('100'),'variance':valid[peak]-D('100'),'unit':'INDEX','materiality':'MEDIUM' if spread>=D('30') else 'LOW','evidence':f'Month {peak:02d} has highest observed month-of-year revenue index {valid[peak]} (100 = average month). Descriptive seasonality, not causal explanation.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin},
                     {'type':'SEASONAL_TROUGH_MONTH','observed':valid[trough],'comparison':D('100'),'variance':valid[trough]-D('100'),'unit':'INDEX','materiality':'MEDIUM' if spread>=D('30') else 'LOW','evidence':f'Month {trough:02d} has lowest observed month-of-year revenue index {valid[trough]}.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin},
                     {'type':'SEASONAL_INDEX_SPREAD','observed':spread,'unit':'INDEX_POINTS','materiality':'HIGH' if spread>=D('75') else ('MEDIUM' if spread>=D('30') else 'LOW'),'evidence':f'Observed peak-to-trough month-of-year index spread is {spread}; timing strength only.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin}]
        else: l=((l+'; ') if l else '')+f'Only {len(monthly)} monthly observations; seasonality requires at least 12'
    out['REV-05']=_execute(con,run,client,'REV-05',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)

    e,m,l=_eligibility(con,run,'REV-06'); sig=[]
    if e!='UNAVAILABLE':
        monthly=defaultdict(lambda:D('0'))
        for r in rows: monthly[r['transaction_date'][:7]] += D(r['net_revenue'])
        vals=list(monthly.values())
        if len(vals)>=12:
            mean=sum(vals,D('0'))/D(len(vals)); var=sum(((x-mean)*(x-mean) for x in vals),D('0'))/D(len(vals)); sd=var.sqrt() if var>=0 else D('0'); cv=(sd/mean*D('100')) if mean else None
            if cv is not None: sig.append({'type':'MONTHLY_REVENUE_VOLATILITY','observed':cv,'unit':'PERCENT_CV','materiality':'HIGH' if cv>=D('40') else ('MEDIUM' if cv>=D('20') else 'LOW'),'evidence':f'Monthly revenue coefficient of variation is {cv}% across {len(vals)} observed months. Volatility does not equal forecast error.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin})
        try:
            from profit_doctor.revenue_semantics import revenue_mix
            mix=revenue_mix(con,client,dv['dataset_version_id'])
            if mix['unmapped_pct'] is not None and mix['unmapped_pct']<=D('5') and mix['recurring_pct'] is not None:
                sig.append({'type':'EVIDENCED_RECURRING_REVENUE_MIX','observed':mix['recurring_pct'],'unit':'PERCENT','materiality':'INFORMATIONAL','evidence':f'Evidenced recurring revenue is {mix["recurring_pct"]}% of mapped transaction revenue; unmapped revenue {mix["unmapped_pct"]}%. Recurring mix supports visibility analysis but is not a forecast guarantee.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin})
            elif mix['unmapped_pct'] is not None: l=((l+'; ') if l else '')+f'Revenue semantics incomplete ({mix["unmapped_pct"]}% unmapped); recurring-mix withheld'
        except Exception: l=((l+'; ') if l else '')+'Revenue semantics unavailable for recurring-mix enrichment'
    out['REV-06']=_execute(con,run,client,'REV-06',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)
    return out

def _margin_by(rows, key):
    o=defaultdict(lambda:{'revenue':D('0'),'cost':D('0'),'gp':D('0'),'count':0})
    for r in rows:
        eid=r[key]
        if not eid: continue
        rev=D(r['net_revenue']); cost=D(r['direct_cost'])
        o[eid]['revenue'] += rev; o[eid]['cost'] += cost; o[eid]['gp'] += rev-cost; o[eid]['count'] += 1
    return o

def _gm(x): return x['gp']/x['revenue']*D('100') if x['revenue'] else None

def margin_diagnostics(con,run,client,dv):
    rows,(prev,cur,ps,pe,cs,mx)=_sales_context(con,client,dv); lin=[('DATASET_VERSION',dv['dataset_version_id'],'comparable 12-month canonical sales and direct-cost windows')]
    pr=_sum(prev,'net_revenue'); cr=_sum(cur,'net_revenue'); pgp=pr-_sum(prev,'direct_cost'); cgp=cr-_sum(cur,'direct_cost'); pm=pgp/pr*D('100') if pr else None; cm=cgp/cr*D('100') if cr else None; md=(cm-pm) if cm is not None and pm is not None else None
    out={}; e,m,l=_eligibility(con,run,'GM-01'); sig=[]
    if e!='UNAVAILABLE' and md is not None: sig=[{'type':'CONTRIBUTION_MARGIN_CHANGE','observed':cm,'comparison':pm,'variance':md,'unit':'PERCENTAGE_POINTS','materiality':'HIGH' if abs(md)>=D('3') else ('MEDIUM' if abs(md)>=D('1') else 'LOW'),'evidence':f'Comparable Contribution 0 margin moved from {pm}% to {cm}%.','primitive':'ECON_CONTRIBUTION_0_MARGIN','lineage':lin}]
    out['GM-01']=_execute(con,run,client,'GM-01',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)
    e,m,l=_eligibility(con,run,'GM-02'); sig=[]
    if e!='UNAVAILABLE' and pm is not None:
        gpdelta=cgp-pgp; rate_effect=cr*(cm-pm)/D('100') if cm is not None else None
        sig=[{'type':'CONTRIBUTION_CHANGE','observed':cgp,'comparison':pgp,'variance':gpdelta,'unit':'GBP','materiality':_materiality(gpdelta,pgp),'evidence':f'Contribution 0 moved from {pgp} to {cgp}; this is impact, not automatically recoverable opportunity.','primitive':'ECON_CONTRIBUTION_0','lineage':lin},{'type':'MARGIN_RATE_EFFECT','observed':rate_effect,'unit':'GBP','materiality':_materiality(rate_effect or 0,pgp),'evidence':f'Current-period revenue valued at comparable margin-rate change gives {rate_effect}; descriptive impact only.','primitive':'ECON_CONTRIBUTION_0_MARGIN','lineage':lin}]
    out['GM-02']=_execute(con,run,client,'GM-02',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)

    for tid,key,etype in [('GM-03','customer_entity_id','CUSTOMER'),('GM-04','product_entity_id','PRODUCT')]:
        e,m,l=_eligibility(con,run,tid); sig=[]; pa=_margin_by(prev,key); ca=_margin_by(cur,key)
        if e!='UNAVAILABLE':
            for eid in set(pa)&set(ca):
                a,b=pa[eid],ca[eid]; am,bm=_gm(a),_gm(b)
                if am is None or bm is None: continue
                pp=bm-am; impact=b['revenue']*pp/D('100')
                if abs(pp)>=D('1') and abs(impact)>=max(D('100'),abs(cgp)*D('0.002')):
                    sig.append({'type':f'{etype}_MARGIN_VARIANCE','entity_type':etype,'entity_id':eid,'observed':bm,'comparison':am,'variance':pp,'unit':'PERCENTAGE_POINTS','materiality':_materiality(impact,cgp),'evidence':f'{etype.title()} comparable contribution margin moved from {am}% to {bm}%; current-revenue margin-rate impact {impact}. This is observed impact, not automatically recoverable opportunity.','primitive':'ECON_CONTRIBUTION_0_MARGIN','lineage':lin})
        out[tid]=_execute(con,run,client,tid,m,e,'COMPLETED' if e!='UNAVAILABLE' else 'NOT_RUN',sorted(sig,key=lambda x:abs(D(x['variance'])),reverse=True)[:20],l)

    e,m,l=_eligibility(con,run,'GM-05'); sig=[]
    if e!='UNAVAILABLE':
        pa=_margin_by(prev,'product_entity_id')
        for r in cur:
            pid=r['product_entity_id']; rev=D(r['net_revenue']); cost=D(r['direct_cost']); gp=rev-cost
            if not pid or pid not in pa or rev<=0: continue
            base=_gm(pa[pid]); actual=gp/rev*D('100')
            if base is not None and actual < base-D('5'):
                impact=rev*(actual-base)/D('100')
                sig.append({'type':'MARGIN_LEAKAGE_SIGNAL','entity_type':'PRODUCT','entity_id':pid,'observed':actual,'comparison':base,'variance':impact,'unit':'GBP','materiality':_materiality(impact,cgp),'evidence':f'Transaction margin {actual}% is below the prior comparable product baseline {base}%; historical margin-rate impact {impact}. Baseline difference alone does not establish error, cause, addressability or opportunity.','primitive':'ECON_CONTRIBUTION_0_MARGIN','lineage':lin})
    out['GM-05']=_execute(con,run,client,'GM-05',m,e,'COMPLETED' if e!='UNAVAILABLE' else 'NOT_RUN',sorted(sig,key=lambda x:abs(D(x['variance'])),reverse=True)[:25],l)

    e,m,l=_eligibility(con,run,'GM-06'); sig=[]
    if e!='UNAVAILABLE':
        pa=_prod(prev); ca=_prod(cur)
        # aggregate unit economics directly so cost inflation and price recovery remain comparable
        def ue(rs):
            z=defaultdict(lambda:{'u':D('0'),'r':D('0'),'c':D('0')})
            for r in rs:
                if r['product_entity_id'] and r['units'] not in (None,'') and D(r['units'])>0:
                    q=z[r['product_entity_id']]; q['u']+=D(r['units']); q['r']+=D(r['net_revenue']); q['c']+=D(r['direct_cost'])
            return z
        pu,cu=ue(prev),ue(cur)
        for pid in set(pu)&set(cu):
            a,b=pu[pid],cu[pid]
            if not a['u'] or not b['u']: continue
            oldc,newc=a['c']/a['u'],b['c']/b['u']; oldp,newp=a['r']/a['u'],b['r']/b['u']; dc=newc-oldc; dp=newp-oldp
            if dc>D('0'):
                pressure=dc*b['u']; recovered=min(max(dp,D('0')),dc)*b['u']; unrecovered=max(pressure-recovered,D('0'))
                sig.append({'type':'PURCHASE_COST_INFLATION_RECOVERY','entity_type':'PRODUCT','entity_id':pid,'observed':pressure,'comparison':recovered,'variance':unrecovered,'unit':'GBP','materiality':_materiality(pressure,cgp),'evidence':f'Comparable unit cost rose {dc}; current-volume cost pressure {pressure}. Selling price movement {dp} supports evidenced same-unit recovery of {recovered}, leaving {unrecovered} unrecovered on this mechanical comparison. This does not prove supplier cause or a recoverable opportunity.','primitive':'ECON_CONTRIBUTION_0','lineage':lin})
    out['GM-06']=_execute(con,run,client,'GM-06',m,e,'COMPLETED' if e!='UNAVAILABLE' else 'NOT_RUN',sorted(sig,key=lambda x:D(x['observed']),reverse=True)[:20],l)

    e,m,l=_eligibility(con,run,'GM-07'); sig=[]
    if e!='UNAVAILABLE':
        prod=_margin_by(cur,'product_entity_id'); bases={k:_gm(v) for k,v in prod.items()}
        for r in cur:
            rev=D(r['net_revenue']); gp=rev-D(r['direct_cost']); margin=gp/rev*D('100') if rev else None; pid=r['product_entity_id']; base=bases.get(pid)
            abnormal=margin is not None and base is not None and margin < base-D('15')
            if gp<0 or abnormal:
                sig.append({'type':'NEGATIVE_TRANSACTION_MARGIN' if gp<0 else 'ABNORMAL_TRANSACTION_MARGIN','entity_type':'PRODUCT' if pid else None,'entity_id':pid,'observed':gp,'comparison':base,'variance':margin,'unit':'GBP','materiality':_materiality(gp,cgp),'evidence':f'Transaction contribution is {gp} at margin {margin}%; current product reference margin {base}%. This is an anomaly requiring context; it is not automatically an error, misconduct, leakage or recoverable saving.','primitive':'ECON_CONTRIBUTION_0','lineage':lin})
    out['GM-07']=_execute(con,run,client,'GM-07',m,e,'COMPLETED' if e!='UNAVAILABLE' else 'NOT_RUN',sorted(sig,key=lambda x:abs(D(x['observed'])),reverse=True)[:25],l)
    return out

def customer_diagnostics(con,run,client,dv):
    rows,(prev,cur,ps,pe,cs,mx)=_sales_context(con,client,dv)
    lin=[('DATASET_VERSION',dv['dataset_version_id'],'current/prior comparable customer economics')]
    pc=_cust(prev); cc=_cust(cur); total=sum(cc.values(),D('0')); out={}
    pm=_margin_by(prev,'customer_entity_id'); cm=_margin_by(cur,'customer_entity_id')

    e,m,l=_eligibility(con,run,'CUS-01'); sig=[]
    if e!='UNAVAILABLE' and total:
        shares=sorted(((cid,v,v/total*D('100')) for cid,v in cc.items()),key=lambda x:x[1],reverse=True); top1=shares[0]; top5=sum((x[1] for x in shares[:5]),D('0')); hhi=sum(((x[2]/D('100'))**2 for x in shares),D('0'))*D('10000')
        sig=[{'type':'TOP_CUSTOMER_CONCENTRATION','entity_type':'CUSTOMER','entity_id':top1[0],'observed':top1[2],'unit':'PERCENT','materiality':'HIGH' if top1[2]>=D('25') else ('MEDIUM' if top1[2]>=D('15') else 'LOW'),'evidence':f'Largest customer contributes {top1[1]} revenue, {top1[2]}% of current comparable revenue. This is dependency exposure, not loss probability.','primitive':'CUSTOMER_REVENUE','lineage':lin},{'type':'TOP5_CONCENTRATION','observed':top5/total*D('100'),'unit':'PERCENT','materiality':'MEDIUM','evidence':f'Top five customers contribute {top5/total*D("100")}% of current comparable revenue.','primitive':'CUSTOMER_REVENUE','lineage':lin},{'type':'CUSTOMER_HHI','observed':hhi,'unit':'INDEX','materiality':'INFORMATIONAL','evidence':f'Customer revenue HHI is {hhi}; retained as concentration evidence, not a client-facing verdict.','primitive':'CUSTOMER_REVENUE','lineage':lin}]
    out['CUS-01']=_execute(con,run,client,'CUS-01',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)

    e,m,l=_eligibility(con,run,'CUS-02'); sig=[]
    if e!='UNAVAILABLE':
        for cid,x in cm.items():
            margin=_gm(x)
            sig.append({'type':'CUSTOMER_PROFITABILITY','entity_type':'CUSTOMER','entity_id':cid,'observed':x['gp'],'comparison':x['revenue'],'variance':margin,'unit':'GBP','materiality':_materiality(x['gp'],sum((v['gp'] for v in cm.values()),D('0'))),'evidence':f'Customer revenue {x["revenue"]}; Contribution 0 {x["gp"]}; Contribution 0 margin {margin}%. Revenue scale and economic contribution are retained separately.','primitive':'ECON_CONTRIBUTION_0','lineage':lin})
    out['CUS-02']=_execute(con,run,client,'CUS-02',m,e,'COMPLETED' if e!='UNAVAILABLE' else 'NOT_RUN',sorted(sig,key=lambda x:abs(D(x['observed'])),reverse=True)[:30],l)

    e,m,l=_eligibility(con,run,'CUS-03'); sig=[]
    if e!='UNAVAILABLE':
        cts_available=any(r['cts'] not in (None,'') for r in cur)
        if cts_available:
            agg=defaultdict(lambda:{'c0':D('0'),'cts':D('0'),'rev':D('0')})
            for r in cur:
                cid=r['customer_entity_id']
                if not cid: continue
                a=agg[cid]; a['rev']+=D(r['net_revenue']); a['c0']+=D(r['net_revenue'])-D(r['direct_cost']); a['cts']+=D(r['cts'] or 0)
            for cid,a in agg.items():
                c1=a['c0']-a['cts']; pct=c1/a['rev']*D('100') if a['rev'] else None
                sig.append({'type':'CUSTOMER_CONTRIBUTION_AFTER_CTS','entity_type':'CUSTOMER','entity_id':cid,'observed':c1,'comparison':a['c0'],'variance':a['cts'],'unit':'GBP','materiality':_materiality(c1,sum((z['c0'] for z in agg.values()),D('0'))),'evidence':f'Customer Contribution 0 {a["c0"]}; evidenced direct cost-to-serve {a["cts"]}; Contribution 1 {c1} ({pct}% of revenue).','primitive':'CUSTOMER_CONTRIBUTION_AFTER_CTS','lineage':lin})
        else:
            l=((l+'; ') if l else '')+'Direct customer cost-to-serve unavailable; CUS-02 Contribution 0 remains available but CUS-03 does not proxy CTS with invented allocations'
    out['CUS-03']=_execute(con,run,client,'CUS-03',m,e,'COMPLETED' if sig else 'NOT_RUN',sorted(sig,key=lambda x:abs(D(x['observed'])),reverse=True)[:30],l)

    e,m,l=_eligibility(con,run,'CUS-04'); sig=[]
    if e!='UNAVAILABLE':
        moves=[]
        for cid in set(pc)|set(cc):
            a,b=pc[cid],cc[cid]; d=b-a
            if a and abs(d)/a>=D('0.10') and abs(d)>=total*D('0.005'): moves.append((cid,a,b,d,d/a*D('100')))
        for cid,a,b,d,g in sorted(moves,key=lambda x:abs(x[3]),reverse=True)[:20]: sig.append({'type':'CUSTOMER_GROWTH' if d>0 else 'CUSTOMER_DECLINE','entity_type':'CUSTOMER','entity_id':cid,'observed':b,'comparison':a,'variance':d,'unit':'GBP','materiality':_materiality(d,total),'evidence':f'Customer comparable revenue moved {g}% from {a} to {b}; movement alone does not establish cause.','primitive':'CUSTOMER_REVENUE_GROWTH','lineage':lin})
    out['CUS-04']=_execute(con,run,client,'CUS-04',m,e,'COMPLETED' if e!='UNAVAILABLE' else 'NOT_RUN',sig,l)

    e,m,l=_eligibility(con,run,'CUS-05'); sig=[]
    if e!='UNAVAILABLE' and total:
        retained=sum((cc[cid] for cid in cc if pc[cid]>0),D('0')); new=sum((cc[cid] for cid in cc if pc[cid]==0),D('0')); lost=sum((pc[cid] for cid in pc if cc[cid]==0),D('0'))
        # Reactivation requires an evidenced earlier history before the prior comparison window.
        earlier=defaultdict(lambda:D('0'))
        for r in rows:
            dt=date.fromisoformat(r['transaction_date'])
            if dt<=ps: earlier[r['customer_entity_id']]+=D(r['net_revenue'])
        reactivated=sum((cc[cid] for cid in cc if pc[cid]==0 and earlier[cid]>0),D('0')); genuinely_new=max(new-reactivated,D('0'))
        prior_total=sum(pc.values(),D('0')); grr=(retained/prior_total*D('100')) if prior_total else None
        sig=[{'type':'CUSTOMER_RETENTION_SUMMARY','observed':retained,'comparison':prior_total,'variance':grr,'unit':'GBP','materiality':'MEDIUM','evidence':f'Retained current revenue from prior-period customers {retained}; prior-period revenue {prior_total}; revenue retention ratio {grr}%. This is revenue retention, not contractual GRR unless contract evidence exists.','primitive':'CUSTOMER_REVENUE','lineage':lin},{'type':'LOST_CUSTOMER_REVENUE','observed':lost,'unit':'GBP','materiality':_materiality(lost,prior_total),'evidence':f'Prior-period revenue from customers with no current-period revenue is {lost}. Absence in the comparison window is a churn/lapse signal; cadence or contract context may change interpretation.','primitive':'CUSTOMER_REVENUE','lineage':lin},{'type':'REACTIVATED_CUSTOMER_REVENUE','observed':reactivated,'unit':'GBP','materiality':_materiality(reactivated,total),'evidence':f'Current revenue from customers absent in the prior window but evidenced before it is {reactivated}. Reactivation requires evidenced history before the prior comparison window.','primitive':'CUSTOMER_REVENUE','lineage':lin},{'type':'NEW_CUSTOMER_REVENUE','observed':genuinely_new,'unit':'GBP','materiality':_materiality(genuinely_new,total),'evidence':f'Current revenue from customers with no observed revenue in the prior comparison window or earlier available history is {genuinely_new}. This is an evidence-window classification, not proof the legal/customer relationship itself began in this period.','primitive':'CUSTOMER_REVENUE','lineage':lin}]
    out['CUS-05']=_execute(con,run,client,'CUS-05',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)

    e,m,l=_eligibility(con,run,'CUS-06'); sig=[]
    # AR is a snapshot: use overdue/outstanding quality, never infer historical payment days from it.
    ar=con.execute("SELECT d.dataset_id,dv.dataset_version_id,dv.period_to FROM dataset d JOIN dataset_version dv ON dv.dataset_id=d.dataset_id WHERE d.client_id=? AND d.data_domain='D04' AND dv.ingestion_status='COMPLETED' ORDER BY dv.version_number DESC LIMIT 1",(client,)).fetchone()
    if e!='UNAVAILABLE' and ar:
        amap={r['source_entity_key']:r['entity_id'] for r in con.execute("SELECT source_entity_key,entity_id FROM entity_alias WHERE client_id=?",(client,))}
        a=defaultdict(lambda:{'out':D('0'),'over':D('0')}); asof=date.fromisoformat(ar['period_to']) if ar['period_to'] else mx
        for r in con.execute('SELECT * FROM ar_invoice WHERE client_id=? AND dataset_version_id=?',(client,ar['dataset_version_id'])):
            cid=amap.get(r['customer_key'],r['customer_key']); outv=D(r['outstanding_amount']); a[cid]['out']+=outv
            if date.fromisoformat(r['due_date'])<asof: a[cid]['over']+=outv
        total_ar=sum((x['out'] for x in a.values()),D('0'))
        for cid,x in a.items():
            if x['out']<=0: continue
            pct=x['over']/x['out']*D('100'); sig.append({'type':'CUSTOMER_OVERDUE_AR','entity_type':'CUSTOMER','entity_id':cid,'observed':x['over'],'comparison':x['out'],'variance':pct,'unit':'GBP','materiality':_materiality(x['over'],total_ar),'evidence':f'Customer outstanding receivables {x["out"]}; overdue at snapshot date {x["over"]} ({pct}%). Snapshot ageing does not establish historical payment speed, collectability or customer cause.','primitive':'AR_OVERDUE_OUTSTANDING','lineage':[('DATASET_VERSION',ar['dataset_version_id'],'latest AR ageing snapshot')]})
    else:
        l=((l+'; ') if l else '')+'AR ageing unavailable; customer payment-behaviour analysis limited to sales economics'
    out['CUS-06']=_execute(con,run,client,'CUS-06',m,e,'COMPLETED' if sig else 'NOT_RUN',sorted(sig,key=lambda x:D(x['observed']),reverse=True)[:30],l)

    e,m,l=_eligibility(con,run,'CUS-07'); sig=[]
    if e!='UNAVAILABLE' and total:
        vals=[]
        for cid,x in cm.items(): vals.append((cid,x['revenue'],x['gp']))
        vals.sort(key=lambda x:x[2],reverse=True); total_gp=sum((x[2] for x in vals),D('0'))
        cum=D('0'); n80=0
        if total_gp>0:
            for _,_,gp in vals:
                cum+=gp; n80+=1
                if cum>=total_gp*D('0.8'): break
        top20n=max(1,(len(vals)+4)//5); top20gp=sum((x[2] for x in vals[:top20n]),D('0')); top20rev=sum((x[1] for x in vals[:top20n]),D('0'))
        sig=[{'type':'CUSTOMER_CONTRIBUTION_PARETO','observed':(top20gp/total_gp*D('100')) if total_gp else None,'comparison':D(top20n),'variance':(D(n80)/D(len(vals))*D('100')) if vals else None,'unit':'PERCENT','materiality':'INFORMATIONAL','evidence':f'Top {top20n} of {len(vals)} customers by Contribution 0 generate {top20gp} contribution and {top20rev} revenue. {n80} customers are required to reach 80% of positive aggregate Contribution 0. Distribution is descriptive, not an instruction to exit the long tail.','primitive':'ECON_CONTRIBUTION_0','lineage':lin}]
    out['CUS-07']=_execute(con,run,client,'CUS-07',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)
    return out


def product_diagnostics(con,run,client,dv):
    rows,(prev,cur,ps,pe,cs,mx)=_sales_context(con,client,dv)
    lin=[('DATASET_VERSION',dv['dataset_version_id'],'current/prior comparable product economics')]
    pm=_margin_by(prev,'product_entity_id'); cm=_margin_by(cur,'product_entity_id')
    total_rev=sum((x['revenue'] for x in cm.values()),D('0')); total_gp=sum((x['gp'] for x in cm.values()),D('0'))
    out={}

    e,m,l=_eligibility(con,run,'PROD-01'); sig=[]
    if e!='UNAVAILABLE':
        for pid,x in cm.items():
            margin=_gm(x)
            sig.append({'type':'PRODUCT_ECONOMICS','entity_type':'PRODUCT','entity_id':pid,'observed':x['gp'],'comparison':x['revenue'],'variance':margin,'unit':'GBP','materiality':_materiality(x['gp'],total_gp),'evidence':f'Product/service revenue {x["revenue"]}; Contribution 0 {x["gp"]}; contribution margin {margin}%. Revenue scale and economic contribution are retained separately; low margin alone is not an exit instruction.','primitive':'ECON_CONTRIBUTION_0','lineage':lin})
    out['PROD-01']=_execute(con,run,client,'PROD-01',m,e,'COMPLETED' if e!='UNAVAILABLE' else 'NOT_RUN',sorted(sig,key=lambda x:abs(D(x['observed'])),reverse=True)[:30],l)

    e,m,l=_eligibility(con,run,'PROD-02'); sig=[]
    if e!='UNAVAILABLE' and total_rev:
        prior_rev=sum((x['revenue'] for x in pm.values()),D('0'))
        for pid in set(pm)|set(cm):
            a=pm.get(pid,{'revenue':D('0'),'gp':D('0')}); b=cm.get(pid,{'revenue':D('0'),'gp':D('0')})
            oldshare=(a['revenue']/prior_rev*D('100')) if prior_rev else D('0'); newshare=b['revenue']/total_rev*D('100'); shift=newshare-oldshare
            if abs(shift)>=D('0.5'):
                sig.append({'type':'PRODUCT_MIX_SHIFT','entity_type':'PRODUCT','entity_id':pid,'observed':newshare,'comparison':oldshare,'variance':shift,'unit':'PERCENTAGE_POINTS','materiality':'MEDIUM' if abs(shift)>=D('3') else 'LOW','evidence':f'Revenue mix moved from {oldshare}% to {newshare}% ({shift}pp). This is an observed portfolio mix shift, not evidence of why the mix changed or whether it is desirable.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin})
    out['PROD-02']=_execute(con,run,client,'PROD-02',m,e,'COMPLETED' if e!='UNAVAILABLE' else 'NOT_RUN',sorted(sig,key=lambda x:abs(D(x['variance'])),reverse=True)[:25],l)

    e,m,l=_eligibility(con,run,'PROD-03'); sig=[]
    if e!='UNAVAILABLE':
        for pid in set(pm)|set(cm):
            a=pm.get(pid,{'revenue':D('0'),'gp':D('0')}); b=cm.get(pid,{'revenue':D('0'),'gp':D('0')}); rd=b['revenue']-a['revenue']; gd=b['gp']-a['gp']
            if abs(rd)>=max(D('100'),abs(total_rev)*D('0.002')):
                state='NEW' if a['revenue']==0 and b['revenue']>0 else ('LOST' if a['revenue']>0 and b['revenue']==0 else ('GROWING' if rd>0 else 'DECLINING'))
                sig.append({'type':'PRODUCT_GROWTH_DECLINE','entity_type':'PRODUCT','entity_id':pid,'observed':b['revenue'],'comparison':a['revenue'],'variance':rd,'unit':'GBP','materiality':_materiality(rd,total_rev),'evidence':f'{state} product/service: revenue moved from {a["revenue"]} to {b["revenue"]}; Contribution 0 movement {gd}. Observed movement does not establish cause, lifecycle state or recoverable opportunity.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin})
    out['PROD-03']=_execute(con,run,client,'PROD-03',m,e,'COMPLETED' if e!='UNAVAILABLE' else 'NOT_RUN',sorted(sig,key=lambda x:abs(D(x['variance'])),reverse=True)[:25],l)

    e,m,l=_eligibility(con,run,'PROD-04'); sig=[]
    if e!='UNAVAILABLE' and cm:
        vals=sorted(((pid,x['revenue'],x['gp'],x['count']) for pid,x in cm.items()),key=lambda z:z[2],reverse=True)
        positive=max(total_gp,D('0')); cum=D('0'); n80=0
        if positive>0:
            for _,_,gp,_ in vals:
                cum+=gp; n80+=1
                if cum>=positive*D('0.8'): break
        tail=[x for x in vals if x[1] <= total_rev*D('0.01')] if total_rev else []
        tail_rev=sum((x[1] for x in tail),D('0')); tail_gp=sum((x[2] for x in tail),D('0')); tail_tx=sum((x[3] for x in tail),0)
        sig=[{'type':'PRODUCT_COMPLEXITY_DISTRIBUTION','observed':D(len(tail)),'comparison':D(len(vals)),'variance':tail_gp,'unit':'COUNT','materiality':'INFORMATIONAL','evidence':f'{len(tail)} of {len(vals)} products/services each contribute <=1% of current revenue; together they generate {tail_rev} revenue, {tail_gp} Contribution 0 across {tail_tx} transactions. {n80} products/services are required to reach 80% of aggregate Contribution 0. Long-tail position alone is not evidence that an item should be removed.','primitive':'ECON_CONTRIBUTION_0','lineage':lin}]
    out['PROD-04']=_execute(con,run,client,'PROD-04',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)

    e,m,l=_eligibility(con,run,'PROD-05'); sig=[]
    if e!='UNAVAILABLE':
        # Whitespace is restricted to products bought by meaningful peers; it is theoretical commercial space only.
        bycust=defaultdict(set); buyers=defaultdict(set); custrev=defaultdict(lambda:defaultdict(lambda:D('0')))
        for r in cur:
            c,p=r['customer_entity_id'],r['product_entity_id']
            if not c or not p: continue
            bycust[c].add(p); buyers[p].add(c); custrev[c][p]+=D(r['net_revenue'])
        active=set(bycust); min_buyers=max(2,int(len(active)*0.10)) if active else 2
        eligible_products={p for p,cs in buyers.items() if len(cs)>=min_buyers}
        spaces=[]
        for c,owned in bycust.items():
            missing=eligible_products-owned
            if missing:
                # peer median/average is intentionally not monetised as achievable revenue.
                spaces.append((c,len(missing),len(owned),len(eligible_products)))
        for c,miss,owned,universe in sorted(spaces,key=lambda x:x[1],reverse=True)[:25]:
            penetration=(D(owned)/D(universe)*D('100')) if universe else None
            sig.append({'type':'CUSTOMER_PRODUCT_WHITESPACE','entity_type':'CUSTOMER','entity_id':c,'observed':D(miss),'comparison':D(universe),'variance':penetration,'unit':'COUNT','materiality':'INFORMATIONAL','evidence':f'Customer currently buys {owned} of {universe} products/services with meaningful peer adoption; {miss} evidenced whitespace relationships remain. This is theoretical whitespace only: no addressability, customer need, capacity, price, probability, forecast revenue or opportunity value is inferred.','primitive':'CUSTOMER_REVENUE','lineage':lin})
    out['PROD-05']=_execute(con,run,client,'PROD-05',m,e,'COMPLETED' if e!='UNAVAILABLE' else 'NOT_RUN',sig,l or (None if sig else 'No meaningful peer-adoption whitespace identified'))
    return out

def pricing_diagnostics(con,run,client,dv):
    rows,(prev,cur,ps,pe,cs,mx)=_sales_context(con,client,dv)
    lin=[('DATASET_VERSION',dv['dataset_version_id'],'comparable realised transaction pricing')]
    out={}
    def cp(rs):
        z=defaultdict(lambda:{'u':D('0'),'r':D('0'),'n':0})
        for r in rs:
            c,p=r['customer_entity_id'],r['product_entity_id']
            if not c or not p or r['units'] in (None,'') or D(r['units'])<=0: continue
            q=z[(c,p)]; q['u']+=D(r['units']); q['r']+=D(r['net_revenue']); q['n']+=1
        return z
    def pp(rs):
        z=defaultdict(lambda:{'u':D('0'),'r':D('0'),'n':0})
        for r in rs:
            p=r['product_entity_id']
            if not p or r['units'] in (None,'') or D(r['units'])<=0: continue
            q=z[p]; q['u']+=D(r['units']); q['r']+=D(r['net_revenue']); q['n']+=1
        return z
    pc,cc=cp(prev),cp(cur); prodcur=pp(cur); prodprev=pp(prev)
    total=_sum(cur,'net_revenue')

    e,m,l=_eligibility(con,run,'PRI-01'); sig=[]
    if e!='UNAVAILABLE':
        for k in set(pc)&set(cc):
            a,b=pc[k],cc[k]; old=a['r']/a['u']; new=b['r']/b['u']; d=new-old; impact=d*b['u']
            if old and (abs(d/old)>=D('0.02')):
                c,p=k; sig.append({'type':'REALISED_PRICE_MOVEMENT','entity_type':'CUSTOMER','entity_id':c,'observed':new,'comparison':old,'variance':impact,'unit':'GBP','materiality':_materiality(impact,total),'evidence':f'Comparable customer-product realised unit price moved from {old} to {new}; current-volume mechanical revenue effect {impact}. This is realised price movement, not proof of list-price action, discount change or management causality.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin})
    out['PRI-01']=_execute(con,run,client,'PRI-01',m,e,'COMPLETED' if e!='UNAVAILABLE' else 'NOT_RUN',sorted(sig,key=lambda x:abs(D(x['variance'])),reverse=True)[:30],l)

    e,m,l=_eligibility(con,run,'PRI-02'); sig=[]
    if e!='UNAVAILABLE':
        byp=defaultdict(list)
        for (c,p),x in cc.items(): byp[p].append((c,x['r']/x['u'],x['u']))
        for p,vals in byp.items():
            if len(vals)<2: continue
            prices=[x[1] for x in vals]; lo,hi=min(prices),max(prices); mean=sum(prices,D('0'))/D(len(prices)); spread=(hi-lo)/mean*D('100') if mean else None
            if spread is not None and spread>=D('5'):
                sig.append({'type':'COMPARABLE_PRICE_DISPERSION','entity_type':'PRODUCT','entity_id':p,'observed':hi,'comparison':lo,'variance':spread,'unit':'PERCENT','materiality':'MEDIUM' if spread>=D('20') else 'LOW','evidence':f'Current realised unit prices across {len(vals)} customer relationships range from {lo} to {hi}; dispersion {spread}% of mean price. Different prices may reflect legitimate terms, volume, service, timing or strategy and are not automatically leakage.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin})
    out['PRI-02']=_execute(con,run,client,'PRI-02',m,e,'COMPLETED' if e!='UNAVAILABLE' else 'NOT_RUN',sorted(sig,key=lambda x:D(x['variance']),reverse=True)[:25],l)

    e,m,l=_eligibility(con,run,'PRI-03'); sig=[]
    if e!='UNAVAILABLE':
        refs={p:(x['r']/x['u']) for p,x in prodcur.items() if x['u']}
        for r in cur:
            p=r['product_entity_id']; u=D(r['units']) if r['units'] not in (None,'') else D('0')
            if not p or u<=0 or p not in refs: continue
            price=D(r['net_revenue'])/u; ref=refs[p]
            if ref and price < ref*D('0.90'):
                gap=(ref-price)*u
                sig.append({'type':'PRICE_LEAKAGE_SIGNAL','entity_type':'PRODUCT','entity_id':p,'observed':price,'comparison':ref,'variance':gap,'unit':'GBP','materiality':_materiality(gap,total),'evidence':f'Transaction realised price {price} is more than 10% below the current product weighted-average reference {ref}; mechanical historical gap {gap}. This does not establish an unauthorised discount, rebate error, entitlement, recoverability or opportunity. Explicit discount/rebate conclusions require D14 commercial evidence.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin})
        l=((l+'; ') if l else '')+'D14 detailed discounts/rebates not required for transaction signal method; explicit discount/rebate attribution withheld without D14'
    out['PRI-03']=_execute(con,run,client,'PRI-03',m,e,'COMPLETED' if e!='UNAVAILABLE' else 'NOT_RUN',sorted(sig,key=lambda x:D(x['variance']),reverse=True)[:30],l)

    e,m,l=_eligibility(con,run,'PRI-04'); sig=[]
    if e!='UNAVAILABLE':
        moved=0; comparable=0; effect=D('0')
        for p in set(prodprev)&set(prodcur):
            a,b=prodprev[p],prodcur[p]; old=a['r']/a['u'] if a['u'] else None; new=b['r']/b['u'] if b['u'] else None
            if old is None or new is None: continue
            comparable+=1
            if new>old: moved+=1; effect+=(new-old)*b['u']
        if comparable:
            coverage=D(moved)/D(comparable)*D('100')
            sig=[{'type':'REALISED_PRICE_INCREASE_COVERAGE','observed':coverage,'comparison':D(comparable),'variance':effect,'unit':'PERCENT','materiality':'INFORMATIONAL','evidence':f'{moved} of {comparable} comparable products/services show higher realised unit price; observed coverage {coverage}%, with mechanical current-volume price effect {effect}. Without D14 pricing campaign/history evidence this is not a measure of planned price-increase effectiveness or compliance.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin}]
        l=((l+'; ') if l else '')+'Campaign funnel/effectiveness requires D14 pricing history, intended increases or commercial terms; current method reports realised movement only'
    out['PRI-04']=_execute(con,run,client,'PRI-04',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)

    e,m,l=_eligibility(con,run,'PRI-05'); sig=[]
    if e!='UNAVAILABLE':
        disp=con.execute("SELECT COUNT(*) n FROM signal WHERE run_id=? AND test_id='PRI-02'",(run,)).fetchone()['n']
        leak=con.execute("SELECT COUNT(*) n FROM signal WHERE run_id=? AND test_id='PRI-03'",(run,)).fetchone()['n']
        if disp or leak:
            sig=[{'type':'PRICING_OPPORTUNITY_CANDIDATE_SET','observed':D(disp+leak),'comparison':D(disp),'variance':D(leak),'unit':'COUNT','materiality':'INFORMATIONAL','evidence':f'Pricing evidence contains {disp} dispersion signals and {leak} below-reference transaction signals. These are investigation candidates only. No theoretical gap is promoted to addressable or expected opportunity until comparability, contractual terms, customer relationship, volume response, mechanism and implementation constraints are evidenced.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin}]
    out['PRI-05']=_execute(con,run,client,'PRI-05',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l or (None if sig else 'No material pricing candidate signals identified'))
    return out

def workforce_diagnostics(con,run,client):
    out={}
    rows=con.execute("SELECT * FROM workforce_snapshot WHERE client_id=? AND snapshot_date=(SELECT MAX(snapshot_date) FROM workforce_snapshot WHERE client_id=?)",(client,client)).fetchall()
    lin=[('WORKFORCE_SNAPSHOT', r['workforce_snapshot_id'], 'latest evidenced workforce snapshot') for r in rows[:50]]
    def elig(tid):
        r=con.execute('SELECT * FROM test_eligibility WHERE run_id=? AND test_id=? ORDER BY assessed_at DESC LIMIT 1',(run,tid)).fetchone()
        if r: return r['eligibility_state'],r['selected_method'],r['limitation']
        return ('FULL','D11_WORKFORCE_SNAPSHOT',None) if rows else ('UNAVAILABLE',None,'D11 workforce/payroll evidence unavailable')
    def cost(r): return sum((D(r[x]) for x in ['base_salary','employer_oncost','commission','bonus','other_people_cost']),D('0'))
    fte=sum((D(r['fte']) for r in rows),D('0')); total_cost=sum((cost(r) for r in rows),D('0')); variable=sum((D(r['commission'])+D(r['bonus']) for r in rows),D('0'))
    e,m,l=elig('PEO-01'); sig=[]
    if e!='UNAVAILABLE' and fte:
        sig=[{'type':'TOTAL_PEOPLE_COST','observed':total_cost,'unit':'GBP','materiality':'INFORMATIONAL','evidence':f'Latest evidenced workforce contains {fte} FTE with fully loaded annual people cost {total_cost}. Variable commission/bonus is separately evidenced at {variable}.','primitive':None,'lineage':lin},{'type':'PEOPLE_COST_PER_FTE','observed':total_cost/fte,'unit':'GBP_PER_FTE','materiality':'INFORMATIONAL','evidence':f'Fully loaded people cost per evidenced FTE is {total_cost/fte}. This is a cost measure, not a productivity conclusion.','primitive':None,'lineage':lin}]
    plans=con.execute('SELECT * FROM commission_plan WHERE client_id=? AND active_flag=1',(client,)).fetchall()
    if sig and plans:
        sig.append({'type':'COMMISSION_PLAN_STRUCTURE','observed':D(len(plans)),'comparison':variable,'unit':'COUNT','materiality':'INFORMATIONAL','evidence':f'{len(plans)} active commission/incentive plan structures are evidenced alongside {variable} of variable pay. Plan structure and spend do not by themselves prove incentive effectiveness, incremental revenue causality or ROI.','primitive':None,'lineage':lin})
    out['PEO-01']=_execute(con,run,client,'PEO-01',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)

    e,m,l=elig('PEO-02'); sig=[]
    dv=_latest_sales_dv(con,client)
    if e!='UNAVAILABLE' and fte and dv:
        sr=con.execute("SELECT * FROM sales_transaction WHERE client_id=? AND dataset_version_id=? AND record_status='ACTIVE'",(client,dv['dataset_version_id'])).fetchall()
        if sr:
            _,cur,_,_,_,_=_windows(sr); rev=_sum(cur,'net_revenue'); contrib=rev-_sum(cur,'direct_cost')
            sig=[{'type':'REVENUE_PER_FTE','observed':rev/fte,'unit':'GBP_PER_FTE','materiality':'INFORMATIONAL','evidence':f'Comparable current-period revenue per evidenced FTE is {rev/fte}. Ratio does not prove individual employee productivity or causality.','primitive':'COMMERCIAL_NET_REVENUE','lineage':lin+[('DATASET_VERSION',dv['dataset_version_id'],'current sales evidence')]},{'type':'CONTRIBUTION_0_PER_FTE','observed':contrib/fte,'unit':'GBP_PER_FTE','materiality':'INFORMATIONAL','evidence':f'Comparable current-period Contribution 0 per evidenced FTE is {contrib/fte}. Cross-business or cross-role comparison requires economic comparability.','primitive':'ECON_CONTRIBUTION_0','lineage':lin+[('DATASET_VERSION',dv['dataset_version_id'],'current sales evidence')]}]
        else: l=((l+'; ') if l else '')+'No current sales evidence for output-per-FTE ratios'
    elif e!='UNAVAILABLE': l=((l+'; ') if l else '')+'Revenue/contribution per FTE requires D07 sales evidence'
    out['PEO-02']=_execute(con,run,client,'PEO-02',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)

    e,m,l=elig('PEO-03'); sig=[]
    if e!='UNAVAILABLE':
        groups=defaultdict(lambda:{'fte':D('0'),'cost':D('0'),'cap':D('0'),'used':D('0')})
        for r in rows:
            k=r['department'] or 'UNMAPPED'; g=groups[k]; g['fte']+=D(r['fte']); g['cost']+=cost(r)
            if r['practical_capacity_hours'] not in (None,''): g['cap']+=D(r['practical_capacity_hours'])
            if r['utilised_hours'] not in (None,''): g['used']+=D(r['utilised_hours'])
        for k,g in groups.items():
            util=(g['used']/g['cap']*D('100')) if g['cap'] else None
            sig.append({'type':'DEPARTMENT_WORKFORCE_ECONOMICS','entity_type':'DEPARTMENT','entity_id':k,'observed':g['cost'],'comparison':g['fte'],'variance':util,'unit':'GBP','materiality':'INFORMATIONAL','evidence':f'{k}: {g["fte"]} FTE, annual people cost {g["cost"]}'+(f', evidenced utilisation {util}%' if util is not None else '')+'. This does not rank departments or roles as more/less productive without comparable output drivers.','primitive':None,'lineage':lin})
    out['PEO-03']=_execute(con,run,client,'PEO-03',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)

    e,m,l=elig('PEO-04'); sig=[]; cap=used=D('0'); cap_rows=0
    if e!='UNAVAILABLE':
        for r in rows:
            if r['practical_capacity_hours'] not in (None,'') and r['utilised_hours'] not in (None,''):
                cap+=D(r['practical_capacity_hours']); used+=D(r['utilised_hours']); cap_rows+=1
        if cap:
            util=used/cap*D('100'); spare=max(cap-used,D('0'))
            sig=[{'type':'WORKFORCE_UTILISATION','observed':util,'comparison':cap,'variance':spare,'unit':'PERCENT','materiality':'INFORMATIONAL','evidence':f'Evidenced practical capacity is {cap} hours and utilised hours {used}, giving utilisation {util}% and {spare} unused evidenced hours across {cap_rows} records. Unused capacity is not a cash saving.','primitive':None,'lineage':lin}]
        else: l=((l+'; ') if l else '')+'Practical capacity/utilised-hours evidence unavailable; utilisation refused'
    out['PEO-04']=_execute(con,run,client,'PEO-04',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)

    e,m,l=elig('PEO-05'); sig=[]
    if e!='UNAVAILABLE' and cap and cap>used:
        spare=cap-used
        sig=[{'type':'WORKFORCE_CAPACITY_OPPORTUNITY_CANDIDATE','observed':spare,'unit':'HOURS','materiality':'INFORMATIONAL','evidence':f'{spare} evidenced practical hours are currently unused. This is capacity only: financial benefit remains £0 unless cost is removed, future hiring/contractor/overtime cost is demonstrably avoided, or additional profitable work is absorbed.','primitive':None,'lineage':lin}]
    out['PEO-05']=_execute(con,run,client,'PEO-05',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l or (None if sig else 'No evidenced workforce optimisation candidate'))
    return out

def supplier_overhead_diagnostics(con,run,client):
    out={}
    def elig(tid):
        r=con.execute("SELECT * FROM test_eligibility WHERE run_id=? AND test_id=? ORDER BY assessed_at DESC LIMIT 1",(run,tid)).fetchone()
        return (r['eligibility_state'],r['selected_method'],r['limitation']) if r else ('FULL','SUPPLIER_EVIDENCE',None)
    rows=con.execute("SELECT * FROM purchase_transaction WHERE client_id=? ORDER BY transaction_date",(client,)).fetchall()
    oh=con.execute("SELECT * FROM overhead_transaction WHERE client_id=? ORDER BY transaction_date",(client,)).fetchall()
    lin=[('PURCHASE_TRANSACTION','MULTIPLE','supplier/purchase evidence')] if rows else []
    e,m,l=elig('SUP-01'); sig=[]
    if e!='UNAVAILABLE' and rows:
        by=defaultdict(lambda:D('0')); total=D('0')
        for r in rows: by[r['supplier_key']]+=D(r['net_amount']); total+=D(r['net_amount'])
        for k,v in sorted(by.items(),key=lambda x:x[1],reverse=True):
            share=v/total*100 if total else D('0')
            sig.append({'type':'SUPPLIER_SPEND','entity_type':'SUPPLIER','entity_id':k,'observed':v,'comparison':share,'unit':'GBP','materiality':_materiality(v,total),'evidence':f'Supplier {k} evidenced spend is {v}, {share}% of captured purchase spend. High spend alone is not evidence of overspend.','primitive':None,'lineage':lin})
    out['SUP-01']=_execute(con,run,client,'SUP-01',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l or (None if sig else 'Purchase evidence unavailable'))
    e,m,l=elig('SUP-02'); sig=[]; comp=defaultdict(list)
    for r in rows:
        if r['item_key'] and r['unit_cost'] not in (None,''): comp[(r['supplier_key'],r['item_key'])].append(r)
    for (sup,item),rr in comp.items():
        if len(rr)>=2:
            rr=sorted(rr,key=lambda x:x['transaction_date']); a=D(rr[0]['unit_cost']); b=D(rr[-1]['unit_cost']); q=D(rr[-1]['quantity'] or '0'); delta=b-a; impact=delta*q
            if delta: sig.append({'type':'PURCHASE_PRICE_VARIANCE','entity_type':'SUPPLIER_ITEM','entity_id':f'{sup}|{item}','observed':delta,'comparison':impact,'unit':'GBP_PER_UNIT','materiality':'MEDIUM','evidence':f'Comparable unit cost moved from {a} to {b}; latest-volume mechanical PPV is {impact}. This proves observed price movement, not supplier cause, recoverability or customer-price recovery.','primitive':None,'lineage':lin})
    out['SUP-02']=_execute(con,run,client,'SUP-02',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l or (None if sig else 'Comparable item/unit-cost evidence unavailable'))
    e,m,l=elig('SUP-03'); sig=[]
    if rows:
        by=defaultdict(lambda:D('0')); total=D('0')
        for r in rows: by[r['supplier_key']]+=D(r['net_amount']); total+=D(r['net_amount'])
        masters={r['supplier_key']:r for r in con.execute("SELECT * FROM supplier_master WHERE client_id=?",(client,)).fetchall()}
        for k,v in sorted(by.items(),key=lambda x:x[1],reverse=True)[:5]:
            share=v/total*100 if total else D('0'); master=masters.get(k); dep=bool(master and (master['single_source_flag'] or (master['criticality'] or '').upper()=='CRITICAL'))
            sig.append({'type':'SUPPLIER_DEPENDENCY','entity_type':'SUPPLIER','entity_id':k,'observed':share,'comparison':v,'unit':'PERCENT','materiality':'HIGH' if share>=D('30') or dep else 'MEDIUM','evidence':f'{k} represents {share}% of captured spend'+(' and has evidenced critical/single-source dependency' if dep else '')+'. This is exposure evidence only; no disruption probability or expected loss is inferred.','primitive':None,'lineage':lin})
    out['SUP-03']=_execute(con,run,client,'SUP-03',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l or (None if sig else 'Supplier spend evidence unavailable'))
    e,m,l=elig('SUP-04'); sig=[]
    if oh:
        dates=sorted({r['transaction_date'][:7] for r in oh}); mid=max(1,len(dates)//2); early=set(dates[:mid]); cats=defaultdict(lambda:[D('0'),D('0')])
        for r in oh: cats[r['category']][0 if r['transaction_date'][:7] in early else 1]+=D(r['net_amount'])
        total=sum((abs(D(x['net_amount'])) for x in oh),D('0'))
        for cat,(a,b) in cats.items():
            change=b-a
            sig.append({'type':'OVERHEAD_COST_DRIFT','entity_type':'OVERHEAD_CATEGORY','entity_id':cat,'observed':b,'comparison':a,'variance':change,'unit':'GBP','materiality':_materiality(abs(change),total),'evidence':f'{cat} overhead spend changed from {a} to {b} across observed windows ({change}). Cost growth is not, by itself, waste or a saving opportunity.','primitive':None,'lineage':[('OVERHEAD_TRANSACTION','MULTIPLE','overhead evidence')]})
    out['SUP-04']=_execute(con,run,client,'SUP-04',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l or (None if sig else 'Overhead transaction evidence unavailable'))
    e,m,l=elig('SUP-05'); sig=[]; seen={}
    for r in list(rows)+list(oh):
        amount=D(r['net_amount']); inv=r['invoice_reference']; sup=r['supplier_key'] or 'UNKNOWN'; desc=r['description'] or ''; key=(sup,r['transaction_date'],str(amount),inv or desc)
        if key in seen: sig.append({'type':'DUPLICATE_LOOKING_SPEND','entity_type':'SUPPLIER','entity_id':sup,'observed':amount,'unit':'GBP','materiality':'MEDIUM','evidence':f'Two captured transactions share supplier/date/amount and invoice-or-description evidence ({sup}, {r["transaction_date"]}, {amount}). This is a forensic duplicate-looking case, not proof of duplicate payment or recoverable cash.','primitive':None,'lineage':lin})
        else: seen[key]=1
    out['SUP-05']=_execute(con,run,client,'SUP-05',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l or (None if sig else 'No duplicate-looking spend identified'))
    e,m,l=elig('SUP-06'); sig=[]
    prior=con.execute("SELECT * FROM signal WHERE run_id=? AND client_id=? AND test_id IN ('SUP-02','SUP-04','SUP-05')",(run,client)).fetchall()
    for r in prior: sig.append({'type':'SUPPLIER_OVERHEAD_OPPORTUNITY_CANDIDATE','entity_type':r['entity_type'],'entity_id':r['entity_id'],'observed':None,'unit':'GBP','materiality':r['materiality_state'],'evidence':f'{r["signal_type"]} supports investigation only. Addressable and expected benefit remain unquantified until mechanism, constraints and recovery basis are evidenced.','primitive':None,'lineage':[('SIGNAL',r['signal_id'],'candidate source')]})
    out['SUP-06']=_execute(con,run,client,'SUP-06',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l or (None if sig else 'No evidenced supplier/overhead candidate'))
    return out

def working_capital_diagnostics(con,run,client):
    out={}
    def latest(pid):
        return con.execute("SELECT * FROM primitive_result WHERE run_id=? AND client_id=? AND primitive_id=? AND result_status='VALID' ORDER BY calculated_at DESC LIMIT 1",(run,client,pid)).fetchone()
    def elig(tid,has):
        er=con.execute('SELECT * FROM test_eligibility WHERE run_id=? AND test_id=? ORDER BY assessed_at DESC LIMIT 1',(run,tid)).fetchone()
        return (er['eligibility_state'],er['selected_method'],er['limitation']) if er else (('FULL' if has else 'UNAVAILABLE'),'PRIMITIVE_OR_LEDGER_BASED',None if has else 'Required working-capital evidence unavailable')
    pids=['WC_DSO','WC_DIO','WC_DPO','WC_CCC','BS_ACCOUNTS_RECEIVABLE','AR_LEDGER_OUTSTANDING','AR_OVERDUE_OUTSTANDING','BS_ACCOUNTS_PAYABLE','AP_LEDGER_OUTSTANDING','AP_OVERDUE_OUTSTANDING','BS_INVENTORY','INVENTORY_SNAPSHOT_VALUE','AVAILABLE_CASH','BANK_CLOSING_CASH']
    vals={p:latest(p) for p in pids}
    # WC-01 cash conversion facts
    sig=[]
    for p in ['WC_DSO','WC_DIO','WC_DPO','WC_CCC']:
        r=vals[p]
        if r: sig.append({'type':p,'observed':D(r['numeric_value']),'unit':r['unit'],'materiality':'INFORMATIONAL','evidence':f'{p} = {r["numeric_value"]} {r["unit"]}; this is an evidenced working-capital measure, not by itself proof that cash is trapped or releasable.','primitive':p,'lineage':[('PRIMITIVE_RESULT',r['primitive_result_id'],'trusted primitive result')]})
    e,m,l=elig('WC-01',bool(sig)); out['WC-01']=_execute(con,run,client,'WC-01',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)
    # WC-02 receivables
    sig=[]
    for p in ['BS_ACCOUNTS_RECEIVABLE','AR_LEDGER_OUTSTANDING','AR_OVERDUE_OUTSTANDING']:
        r=vals[p]
        if r: sig.append({'type':p,'observed':D(r['numeric_value']),'unit':r['unit'],'materiality':'INFORMATIONAL','evidence':f'{p} = {r["numeric_value"]} {r["unit"]}. Outstanding/overdue receivables are cash exposure, not new profit and not automatically collectible cash release.','primitive':p,'lineage':[('PRIMITIVE_RESULT',r['primitive_result_id'],'trusted primitive result')]})
    # customer overdue concentration from ledger
    ar=con.execute('SELECT customer_key,SUM(CAST(outstanding_amount AS REAL)) amt FROM ar_invoice WHERE client_id=? AND outstanding_amount<>\'0\' AND due_date < date(\'now\') GROUP BY customer_key',(client,)).fetchall()
    for r in ar:
        if D(r['amt'])>0: sig.append({'type':'CUSTOMER_OVERDUE_AR','entity_type':'CUSTOMER','entity_id':r['customer_key'],'observed':D(r['amt']),'unit':'GBP','materiality':'MEDIUM','evidence':f'Customer has {r["amt"]} of overdue receivables in the captured ledger. This does not establish collectability, dispute cause, or incremental profit.','primitive':None,'lineage':[('AR_INVOICE','MULTIPLE','overdue ledger evidence')]})
    e,m,l=elig('WC-02',bool(sig)); out['WC-02']=_execute(con,run,client,'WC-02',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)
    # WC-03 payables
    sig=[]
    for p in ['BS_ACCOUNTS_PAYABLE','AP_LEDGER_OUTSTANDING','AP_OVERDUE_OUTSTANDING','WC_DPO']:
        r=vals[p]
        if r: sig.append({'type':p,'observed':D(r['numeric_value']),'unit':r['unit'],'materiality':'INFORMATIONAL','evidence':f'{p} = {r["numeric_value"]} {r["unit"]}. Supplier balances and DPO require contractual and relationship context; delaying payment is not automatically a cash opportunity.','primitive':p,'lineage':[('PRIMITIVE_RESULT',r['primitive_result_id'],'trusted primitive result')]})
    e,m,l=elig('WC-03',bool(sig)); out['WC-03']=_execute(con,run,client,'WC-03',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)
    # WC-04 inventory
    sig=[]
    for p in ['BS_INVENTORY','INVENTORY_SNAPSHOT_VALUE','WC_DIO']:
        r=vals[p]
        if r: sig.append({'type':p,'observed':D(r['numeric_value']),'unit':r['unit'],'materiality':'INFORMATIONAL','evidence':f'{p} = {r["numeric_value"]} {r["unit"]}. Inventory value or DIO is not the same as safely releasable cash; service level, replenishment, obsolescence and practical stock requirement must be evidenced.','primitive':p,'lineage':[('PRIMITIVE_RESULT',r['primitive_result_id'],'trusted primitive result')]})
    e,m,l=elig('WC-04',bool(sig)); out['WC-04']=_execute(con,run,client,'WC-04',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l or (None if sig else 'Inventory evidence unavailable or structurally not applicable'))
    # WC-05 liquidity
    sig=[]; cash=vals['AVAILABLE_CASH'] or vals['BANK_CLOSING_CASH']
    if cash: sig.append({'type':'AVAILABLE_CASH_POSITION','observed':D(cash['numeric_value']),'unit':'GBP','materiality':'INFORMATIONAL','evidence':f'Available cash evidenced at {cash["numeric_value"]}. This is not Available Liquidity unless documented facility headroom is separately evidenced, and it is not a cash forecast.','primitive':cash['primitive_id'],'lineage':[('PRIMITIVE_RESULT',cash['primitive_result_id'],'trusted cash result')]})
    e,m,l=elig('WC-05',bool(sig)); out['WC-05']=_execute(con,run,client,'WC-05',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)
    # WC-06 release candidates: deliberately unquantified unless mechanism evidence exists
    sig=[]
    for source in ['AR_OVERDUE_OUTSTANDING','AP_OVERDUE_OUTSTANDING','BS_INVENTORY','INVENTORY_SNAPSHOT_VALUE']:
        r=vals[source]
        if r and D(r['numeric_value'])>0:
            sig.append({'type':'WORKING_CAPITAL_RELEASE_CANDIDATE','entity_type':'WORKING_CAPITAL_COMPONENT','entity_id':source,'observed':None,'unit':'GBP','materiality':'MEDIUM','evidence':f'{source} provides evidence of working-capital exposure, but addressable cash release remains unquantified until cause, mechanism, operational guardrails and timing are evidenced. Cash release is not profit.','primitive':source,'lineage':[('PRIMITIVE_RESULT',r['primitive_result_id'],'candidate source')]})
    e,m,l=elig('WC-06',bool(sig)); out['WC-06']=_execute(con,run,client,'WC-06',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l or (None if sig else 'No evidenced working-capital release candidate'))
    # WC-07 synthesis: candidates only; no double count, no invented timing/benefit
    sig=[]
    prior=con.execute("SELECT * FROM signal WHERE run_id=? AND client_id=? AND test_id IN ('WC-02','WC-03','WC-04','WC-06') AND status='ACTIVE'",(run,client)).fetchall()
    candidate_sources=[r for r in prior if r['signal_type'] in ('WORKING_CAPITAL_RELEASE_CANDIDATE','CUSTOMER_OVERDUE_AR')]
    for r in candidate_sources:
        sig.append({'type':'CASH_OPTIMISATION_CANDIDATE','entity_type':r['entity_type'],'entity_id':r['entity_id'],'observed':None,'unit':'GBP','materiality':r['materiality_state'],'evidence':f'{r["signal_type"]} supports investigation. Expected cash release, timing and guardrails remain unquantified; collecting recognised revenue is not new profit and profit-to-cash manifestation must not be double counted.','primitive':None,'lineage':[('SIGNAL',r['signal_id'],'cash candidate source')]})
    e,m,l=elig('WC-07',bool(sig)); out['WC-07']=_execute(con,run,client,'WC-07',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l or (None if sig else 'No evidenced cash optimisation candidate'))
    return out


def forecasting_diagnostics(con,run,client):
    out={}
    def elig(test,available,method='L2_PLAN'):
        return ('FULL',method,None) if available else ('UNAVAILABLE',None,'Required D13/KPI evidence unavailable')
    # FCST-01 preserve plan version and compare monthly revenue plan with actual P&L revenue when available.
    plans=con.execute("SELECT * FROM plan_version WHERE client_id=? AND status='ACTIVE' ORDER BY created_date",(client,)).fetchall()
    actuals=con.execute("SELECT period,actual_value FROM actual_metric WHERE client_id=? AND metric_code='REVENUE' ORDER BY period",(client,)).fetchall()
    sig=[]
    if plans and actuals:
        pv=plans[-1]; lines=con.execute("SELECT * FROM plan_line WHERE client_id=? AND plan_version_id=? AND metric_code='REVENUE'",(client,pv['plan_version_id'])).fetchall()
        amap={r['period'][:7]:D(r['actual_value']) for r in actuals}; pmap={r['period'][:7]:D(r['amount']) for r in lines}
        common=sorted(set(amap)&set(pmap))
        if common:
            pa=sum((pmap[x] for x in common),D('0')); ac=sum((amap[x] for x in common),D('0')); var=ac-pa
            sig=[{'type':'PLAN_VS_ACTUAL_REVENUE','observed':ac,'comparison':pa,'variance':var,'unit':'GBP','materiality':_materiality(var,pa),'evidence':f'Actual revenue {ac} versus preserved {pv["plan_type"]} version {pv["version_name"]} {pa}; variance {var}. Variance is an observed difference, not an explanation of why performance differed.','primitive':'FIN_REVENUE','lineage':[('PLAN_VERSION',pv['plan_version_id'],'preserved plan version')]}]
    e,m,l=elig('FCST-01',bool(sig)); out['FCST-01']=_execute(con,run,client,'FCST-01',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)
    # FCST-02 compare every vintage to eventual actual, retaining signed errors and bias.
    vint=con.execute("SELECT * FROM forecast_vintage WHERE client_id=? AND metric_code='REVENUE' ORDER BY vintage_date",(client,)).fetchall(); sig=[]
    if vint and actuals:
        amap={r['period'][:7]:D(r['actual_value']) for r in actuals}; errors=[]; abs_errors=[]
        for v in vint:
            k=v['target_period'][:7]
            if k in amap:
                f=D(v['forecast_value']); a=amap[k]; errors.append(f-a); abs_errors.append(abs(f-a))
        if errors:
            me=sum(errors,D('0'))/D(len(errors)); mae=sum(abs_errors,D('0'))/D(len(abs_errors)); abase=sum((amap[v['target_period'][:7]] for v in vint if v['target_period'][:7] in amap),D('0'))/D(len(errors)); mape=(mae/abs(abase)*D('100')) if abase else None
            sig=[{'type':'FORECAST_MEAN_ERROR','observed':me,'unit':'GBP','materiality':'MEDIUM' if abs(me)>mae*D('.5') and mae else 'LOW','evidence':f'Mean signed forecast error is {me}; positive means historical over-forecasting, negative under-forecasting. This is historical bias evidence, not a future prediction.','primitive':None,'lineage':[]},{'type':'FORECAST_MAE','observed':mae,'comparison':mape,'unit':'GBP','materiality':'MEDIUM','evidence':f'Mean absolute forecast error is {mae}; indicative percentage error {mape if mape is not None else "not meaningful"}%. Historical error does not establish future certainty.','primitive':None,'lineage':[]}]
    e,m,l=elig('FCST-02',bool(sig),'L3_FORECAST_VINTAGE'); out['FCST-02']=_execute(con,run,client,'FCST-02',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)
    # FCST-03 KPI observations: show driver registry facts, no causal claims.
    ks=con.execute("SELECT * FROM kpi_observation WHERE client_id=? ORDER BY period,kpi_code",(client,)).fetchall(); sig=[]
    if ks:
        latest={}
        for k in ks: latest[k['kpi_code']]=k
        for k in latest.values():
            sig.append({'type':'KPI_DRIVER_OBSERVATION','entity_type':'KPI','entity_id':k['kpi_code'],'observed':D(k['value']),'unit':k['unit'],'materiality':'LOW','evidence':f'{k["kpi_name"]} latest observed value {k["value"]}. Driver class {k["driver_class"]}; linked outcome {k["linked_outcome"] or "not specified"}. Association/management relevance does not by itself prove causality.','primitive':None,'lineage':[]})
    e,m,l=elig('FCST-03',bool(sig),'L3_KPI'); out['FCST-03']=_execute(con,run,client,'FCST-03',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)
    # FCST-04 transparent scenario range from latest forecast; no probabilities.
    sig=[]
    if vint:
        latest_date=max(v['vintage_date'] for v in vint); lv=[v for v in vint if v['vintage_date']==latest_date]; base=sum((D(v['forecast_value']) for v in lv),D('0'))
        if base:
            downside=base*D('.90'); upside=base*D('1.10')
            sig=[{'type':'FORWARD_SCENARIO_RANGE','observed':base,'comparison':downside,'variance':upside-base,'unit':'GBP','materiality':'INFORMATIONAL','evidence':f'Illustrative management scenario around latest explicit forecast: base {base}, downside {downside} (-10%), upside {upside} (+10%). These are transparent sensitivity assumptions for decision support, not probabilities or predictions.','primitive':None,'lineage':[]}]
    e,m,l=elig('FCST-04',bool(sig),'L3_SCENARIO'); out['FCST-04']=_execute(con,run,client,'FCST-04',m,e,'COMPLETED' if sig else 'NOT_RUN',sig,l)
    return out


def risk_control_diagnostics(con,run,client):
    """Financial risk/control diagnostics. This is management decision support, not audit assurance."""
    out={}
    # RISK-01: reuse Trust Layer integrity and reconciliation evidence. Failure is evidence of weakness, not proof of misstatement.
    integ=con.execute("SELECT * FROM financial_integrity WHERE run_id=? AND client_id=? ORDER BY assessed_at",(run,client)).fetchall()
    rec=con.execute("SELECT * FROM reconciliation WHERE run_id=? AND client_id=? ORDER BY assessed_at",(run,client)).fetchall()
    xrec=con.execute("SELECT * FROM cross_source_reconciliation WHERE run_id=? AND client_id=? ORDER BY created_at",(run,client)).fetchall()
    sig=[]
    for r in integ:
        if r['integrity_state'] not in ('RELIABLE','PASS'):
            sig.append({'type':'FINANCIAL_INTEGRITY_WEAKNESS','entity_type':'DATA_DOMAIN','entity_id':r['data_domain'],'observed':None,'unit':'STATE','materiality':'HIGH' if r['integrity_state'] in ('MATERIALLY_CONSTRAINED','UNUSABLE','FAIL') else 'MEDIUM','evidence':f'{r["data_domain"]} integrity state is {r["integrity_state"]}: {r["basis"]}. This identifies a reliability/control concern; it is not an audit opinion and does not by itself prove financial misstatement or loss.','primitive':None,'lineage':[('FINANCIAL_INTEGRITY',r['integrity_id'],'trust-layer integrity evidence')]})
    for r in list(rec)+list(xrec):
        status=(r['status'] if 'status' in r.keys() else r['integrity_effect'])
        if status not in ('PASS','RELIABLE','NONE'):
            rid=(r['reconciliation_id'] if 'reconciliation_id' in r.keys() else r['cross_reconciliation_id'])
            typ=r['reconciliation_type']; residual=r['residual'] if 'residual' in r.keys() else None
            sig.append({'type':'RECONCILIATION_EXCEPTION','entity_type':'RECONCILIATION','entity_id':typ,'observed':D(residual) if residual not in (None,'') else None,'unit':'GBP','materiality':'HIGH' if status in ('FAIL','MATERIAL','MATERIALLY_CONSTRAINED') else 'MEDIUM','evidence':f'{typ} reconciliation status {status}; residual {residual}. An unreconciled difference requires investigation but does not establish error, misconduct or loss.','primitive':None,'lineage':[('RECONCILIATION',rid,'trust-layer reconciliation evidence')]})
    e='FULL' if (integ or rec or xrec) else 'UNAVAILABLE'; m='L1_TRUST_CONTROLS' if e=='FULL' else None
    out['RISK-01']=_execute(con,run,client,'RISK-01',m,e,'COMPLETED' if e=='FULL' else 'NOT_RUN',sig,None if e=='FULL' else 'No integrity/reconciliation evidence available')

    # RISK-02: explicit exceptions + forensic signals already detected elsewhere. Never infer fraud/error from anomaly.
    ex=con.execute("SELECT * FROM control_exception WHERE client_id=? AND status='OPEN' ORDER BY exception_date",(client,)).fetchall(); sig=[]
    for r in ex:
        amt=D(r['amount']) if r['amount'] not in (None,'') else None
        sig.append({'type':'CONTROL_PROCESS_EXCEPTION','entity_type':'PROCESS_AREA','entity_id':r['process_area'],'observed':amt,'unit':'GBP' if amt is not None else 'COUNT','materiality':'HIGH' if amt is not None and abs(amt)>=D('10000') else 'MEDIUM','evidence':f'{r["exception_type"]}: {r["description"]}. Recorded exception requires investigation. Exception/anomaly does not establish error, misconduct, fraud or financial loss.','primitive':None,'lineage':[('CONTROL_EXCEPTION',r['control_exception_id'],'explicit control exception evidence')]})
    forensic=con.execute("SELECT * FROM signal WHERE run_id=? AND client_id=? AND signal_type IN ('DUPLICATE_LOOKING_SPEND','NEGATIVE_TRANSACTION_MARGIN','ABNORMAL_TRANSACTION_MARGIN') AND status='ACTIVE'",(run,client)).fetchall()
    for r in forensic:
        sig.append({'type':'FORENSIC_EXCEPTION_SIGNAL','entity_type':r['entity_type'],'entity_id':r['entity_id'],'observed':D(r['observed_value']) if r['observed_value'] not in (None,'') else None,'unit':r['unit'],'materiality':r['materiality_state'],'evidence':f'{r["signal_type"]} is an investigation signal only. Anomaly does not establish error, misconduct, fraud or recoverable loss.','primitive':None,'lineage':[('SIGNAL',r['signal_id'],'existing forensic diagnostic signal')]})
    e='FULL' if (ex or forensic) else 'PARTIAL-A'; m='L1_EXCEPTION_SYNTHESIS'
    out['RISK-02']=_execute(con,run,client,'RISK-02',m,e,'COMPLETED',sig,None if sig else 'No material exception evidence identified in available sources')

    # RISK-03: exposure is not expected loss. Use explicit evidence plus concentration/dependency signals.
    exposures=con.execute("SELECT * FROM financial_exposure_evidence WHERE client_id=? ORDER BY exposure_date",(client,)).fetchall(); sig=[]
    for r in exposures:
        amt=D(r['amount_exposed']) if r['amount_exposed'] not in (None,'') else None
        sig.append({'type':'FINANCIAL_EXPOSURE','entity_type':'EXPOSURE_TYPE','entity_id':r['exposure_type'],'observed':amt,'comparison':D(r['concentration_pct']) if r['concentration_pct'] not in (None,'') else None,'unit':'GBP','materiality':'HIGH' if amt is not None and abs(amt)>=D('100000') else 'MEDIUM','evidence':f'{r["description"]}. Amount exposed {r["amount_exposed"]}; mitigation {r["mitigation_status"] or "not evidenced"}. Exposure is not expected loss; no probability or expected-loss value is inferred.','primitive':None,'lineage':[('FINANCIAL_EXPOSURE_EVIDENCE',r['exposure_evidence_id'],'explicit exposure evidence')]})
    deps=con.execute("SELECT * FROM signal WHERE run_id=? AND client_id=? AND signal_type IN ('TOP_CUSTOMER_CONCENTRATION','TOP5_CUSTOMER_CONCENTRATION','SUPPLIER_CONCENTRATION','SUPPLIER_DEPENDENCY') AND status='ACTIVE'",(run,client)).fetchall()
    for r in deps:
        sig.append({'type':'DEPENDENCY_EXPOSURE_SIGNAL','entity_type':r['entity_type'],'entity_id':r['entity_id'],'observed':D(r['observed_value']) if r['observed_value'] not in (None,'') else None,'unit':r['unit'],'materiality':r['materiality_state'],'evidence':f'{r["signal_type"]} evidences dependency/concentration. It does not establish disruption probability, expected loss or failure likelihood.','primitive':None,'lineage':[('SIGNAL',r['signal_id'],'dependency evidence')]})
    e='FULL' if exposures else ('PARTIAL-A' if deps else 'UNAVAILABLE'); m='L2_EXPOSURE' if exposures else ('L1_CONCENTRATION_EXPOSURE' if deps else None)
    out['RISK-03']=_execute(con,run,client,'RISK-03',m,e,'COMPLETED' if e!='UNAVAILABLE' else 'NOT_RUN',sig,None if e!='UNAVAILABLE' else 'No explicit or diagnostic exposure evidence available')

    # RISK-04: minimum effective governance. Candidate action != mandatory control; expected loss remains blank.
    sig=[]
    sources=con.execute("SELECT * FROM signal WHERE run_id=? AND client_id=? AND test_id IN ('RISK-01','RISK-02','RISK-03') AND status='ACTIVE' AND materiality_state IN ('MEDIUM','HIGH')",(run,client)).fetchall()
    for r in sources:
        if r['signal_type'] in ('FINANCIAL_INTEGRITY_WEAKNESS','RECONCILIATION_EXCEPTION'):
            action='Investigate and resolve the evidenced integrity/reconciliation weakness, documenting ownership and resolution.'; area='FINANCIAL_INTEGRITY'
        elif r['signal_type'] in ('CONTROL_PROCESS_EXCEPTION','FORENSIC_EXCEPTION_SIGNAL'):
            action='Investigate the exception, establish root cause, then strengthen only the control needed to prevent material recurrence.'; area='PROCESS_CONTROL'
        else:
            action='Review the exposure, existing mitigations and resilience options; decide whether to mitigate, monitor or consciously accept it.'; area='FINANCIAL_RESILIENCE'
        cid=id4('gov'); basis='Proportionate response to an evidenced medium/high signal; minimum effective governance, not maximum bureaucracy.'
        con.execute('INSERT INTO governance_action_candidate VALUES (?,?,?,?,?,?,?,?,?,?,?)',(cid,run,client,r['signal_id'],area,'REVIEW_STRENGTHEN_MONITOR_OR_ACCEPT',action,basis,None,'CANDIDATE',now()))
        sig.append({'type':'GOVERNANCE_ACTION_CANDIDATE','entity_type':'CONTROL_AREA','entity_id':area,'observed':None,'unit':'ACTION','materiality':r['materiality_state'],'evidence':f'{action} {basis} No expected-loss value is invented and management retains the decision to fix, monitor or accept the risk.','primitive':None,'lineage':[('SIGNAL',r['signal_id'],'evidenced risk/control source')]})
    e='FULL' if sources else 'PARTIAL-A'; m='L1_PROPORTIONATE_GOVERNANCE'
    out['RISK-04']=_execute(con,run,client,'RISK-04',m,e,'COMPLETED',sig,None if sig else 'No medium/high risk-control signals requiring a governance candidate')
    con.commit(); return out

def run_diagnostic_engine(con,run,client,sales_dataset_version_id=None):
    seed_registry(con); dv=con.execute('SELECT * FROM dataset_version WHERE dataset_version_id=?',(sales_dataset_version_id,)).fetchone() if sales_dataset_version_id else _latest_sales_dv(con,client)
    out={}
    if dv:
        out.update(revenue_diagnostics(con,run,client,dv)); out.update(extended_revenue_diagnostics(con,run,client,dv)); out.update(margin_diagnostics(con,run,client,dv)); out.update(customer_diagnostics(con,run,client,dv)); out.update(product_diagnostics(con,run,client,dv)); out.update(pricing_diagnostics(con,run,client,dv))
    else:
        for tid in ['REV-01','REV-02','REV-03','REV-04','REV-05','REV-06','GM-01','GM-02','GM-03','GM-04','GM-05','GM-06','GM-07','CUS-01','CUS-02','CUS-03','CUS-04','CUS-05','CUS-06','CUS-07','PROD-01','PROD-02','PROD-03','PROD-04','PROD-05','PRI-01','PRI-02','PRI-03','PRI-04','PRI-05']: out[tid]=_execute(con,run,client,tid,None,'UNAVAILABLE','NOT_RUN',[],'D07 unavailable')
    out.update(workforce_diagnostics(con,run,client)); out.update(supplier_overhead_diagnostics(con,run,client)); out.update(working_capital_diagnostics(con,run,client)); out.update(forecasting_diagnostics(con,run,client)); out.update(risk_control_diagnostics(con,run,client)); return out
