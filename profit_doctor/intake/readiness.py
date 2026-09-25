"""v2.38 product-grade upload readiness and diagnostic coverage explanation.
Deterministic projection only: explains what an uploaded workbook can support and what evidence would unlock more analysis.
"""
from __future__ import annotations
from pathlib import Path
from profit_doctor.intake.workbook import intake_assessment

READINESS_VERSION='UIR-2.38'
DOMAIN_NAMES={
'D01_PNL':'P&L / Management Accounts','D02_BALANCE_SHEET':'Balance Sheet','D03_TRIAL_BALANCE':'Trial Balance / GL',
'D04_AR':'Sales Ledger / AR','D05_AP':'Purchase Ledger / AP','D06_CASH':'Cash / Bank','D07_SALES':'Sales Transactions',
'D08_CUSTOMER':'Customer Master','D09_PRODUCT':'Product / Service Master','D10_MARGIN':'Direct Cost / Transaction Margin',
'D11_WORKFORCE':'Payroll / Workforce','D12_INVENTORY':'Inventory','D13_FORECAST':'Budget / Forecast','D14_PRICING':'Pricing / Discounts / Rebates',
'D15_CRM':'CRM / Pipeline / Win-Loss','D16_OPERATIONS':'Operational / Capacity KPIs','D17_CONTRACTS':'Contracts / Commercial Terms','D18_CONTROLS':'Approvals / Control Evidence'}

# Owner-friendly evidence requests. These are requirements/options, not invented availability.
NEXT_DATA=[
 ('D07_SALES','Detailed sales transactions','Unlock deeper revenue, customer, product and margin diagnostics.'),
 ('D10_MARGIN','Transaction-level direct cost / margin','Supports stronger customer/product contribution and leakage analysis.'),
 ('D13_FORECAST','Budget, forecast and KPI history','Unlocks forecast accuracy, bias, drivers and forward scenario diagnostics.'),
 ('D14_PRICING','Price history, discounts and rebates','Unlocks price realisation, dispersion and pricing-effectiveness analysis.'),
 ('D15_CRM','CRM pipeline, opportunities and win/loss','Unlocks pipeline, conversion and commercial forward-looking analysis.'),
 ('D16_OPERATIONS','Operational capacity and utilisation','Strengthens productivity/capacity conclusions where source units are reliable.')]

def build_upload_readiness(workbook:str|Path, review:dict|None=None):
    a=intake_assessment(workbook)
    available=set(a['available_domains'])
    sheets=[]
    for m in a['mappings']:
        sheets.append({'sheet':m['sheet'],'domain':m['domain'],'domain_label':DOMAIN_NAMES.get(m['domain'],m['domain']),
                       'mapping_confidence':m['mapping_confidence'],'requires_human_confirmation':m['requires_human_confirmation']})
    controls=[{'control':r['control'],'status':r['status'],'difference':r.get('difference'),'basis':r.get('basis')} for r in a['reconciliations']]
    failed=[x for x in controls if x['status']=='FAIL']
    coverage=None
    if review:
        pd=review.get('performance_diagnostics',{})
        coverage={'total':pd.get('total',56),'completed':len(pd.get('completed',[])),'partial':len(pd.get('partial',[])),
                  'unavailable':len(pd.get('unavailable',[])),'completed_tests':pd.get('completed',[]),'partial_tests':pd.get('partial',[])}
    next_data=[{'domain':c,'request':label,'why_it_matters':why} for c,label,why in NEXT_DATA if c not in available]
    # No vanity score: state is a factual readiness descriptor driven by controls/confirmation needs.
    if failed: state='ANALYSIS_WITH_CONTROL_LIMITATIONS'
    elif any(x['requires_human_confirmation'] for x in sheets): state='ANALYSIS_WITH_MAPPING_CONFIRMATION'
    else: state='READY_FOR_EVIDENCED_ANALYSIS'
    return {'version':READINESS_VERSION,'readiness_state':state,'integrity_state':a['integrity_state'],
            'available_domains':sorted(available),'sheets':sheets,'controls':controls,'failed_controls':[x['control'] for x in failed],
            'diagnostic_coverage':coverage,'recommended_next_data':next_data,
            'guardrails':['This is not a universal data-quality score.','Missing data reduces coverage; it does not invalidate supported diagnostics.',
                          'Failed reconciliations are control exceptions, not assumed losses or savings.','Human confirmation is required where semantic mapping is ambiguous.']}
