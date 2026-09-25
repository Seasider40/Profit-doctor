"""Profit Doctor Real SME Qualification Programme v1.
Defines the controlled validation matrix and fail-closed acceptance rules.
Synthetic cases are preparation for, not substitutes for, anonymised real-SME evidence.
"""
from dataclasses import dataclass

BUSINESS_MODELS=("PRODUCT_DISTRIBUTION","PROFESSIONAL_SERVICES","SUBSCRIPTION","PROJECT_CONTRACT","HOSPITALITY_TRANSACTIONAL","HYBRID")
DATA_STATES=("L1_CORE","L1_MESSY","L2_ENHANCED","L3_ADVANCED")
VERDICTS=("PASS","CONDITIONAL","FAIL")

@dataclass(frozen=True)
class SMECase:
    case_id:str; business_model:str; data_state:str; turnover_band:str; challenge:str; expected_behaviour:str

CASES=(
 SMECase('SME-001','PRODUCT_DISTRIBUTION','L1_CORE','1m-5m','Clean accounting core; no detailed commercial data','Deliver useful core health check and refuse unsupported deep commercial claims'),
 SMECase('SME-002','PRODUCT_DISTRIBUTION','L2_ENHANCED','5m-10m','Customer/product margin, inventory and supplier data with credit notes','Reconcile economics; distinguish margin impact, stock exposure and cash release'),
 SMECase('SME-003','PROFESSIONAL_SERVICES','L1_CORE','1m-5m','No inventory; uneven monthly billing','Treat inventory diagnostics as N/A and avoid false stock/cash findings'),
 SMECase('SME-004','PROFESSIONAL_SERVICES','L2_ENHANCED','5m-10m','Payroll, utilisation and departments available','Analyse capacity without converting unused hours into savings'),
 SMECase('SME-005','SUBSCRIPTION','L2_ENHANCED','1m-10m','Recurring revenue, churn/reactivation and deferred timing','Separate recurring visibility from forecast certainty'),
 SMECase('SME-006','SUBSCRIPTION','L3_ADVANCED','5m-10m','CRM pipeline and forecast history disagree with accounting actuals','Prefer authoritative actuals; expose forecast bias without predicting outcomes'),
 SMECase('SME-007','PROJECT_CONTRACT','L1_MESSY','1m-5m','Irregular invoicing, WIP/timing and sparse customer transactions','Avoid interpreting billing timing as underlying growth without evidence'),
 SMECase('SME-008','PROJECT_CONTRACT','L2_ENHANCED','5m-10m','Project contribution and cost-to-serve available','Use evidenced contribution definitions and preserve allocation caveats'),
 SMECase('SME-009','HOSPITALITY_TRANSACTIONAL','L1_CORE','0.5m-5m','High transaction count but accounting-only core supplied','Deliver Level-1 value and state transaction insight is unavailable'),
 SMECase('SME-010','HOSPITALITY_TRANSACTIONAL','L2_ENHANCED','1m-10m','Covers/transactions, labour and direct costs','Use activity drivers without treating correlation as causality'),
 SMECase('SME-011','HYBRID','L1_MESSY','1m-10m','AR/BS mismatch, duplicate IDs, missing bank and malformed rows','Constrain/refuse affected tests; never silently repair material evidence'),
 SMECase('SME-012','HYBRID','L3_ADVANCED','5m-10m','Rich but contradictory finance/CRM/pricing/operations data','Preserve source precedence, surface contradictions and refuse false precision'),
)

GATES=(
 'SOURCE_TRACEABILITY','ACCOUNTING_RECONCILIATION','ELIGIBILITY_DEGRADATION','BUSINESS_MODEL_APPLICABILITY',
 'ECONOMIC_CLASSIFICATION','ANTI_DOUBLE_COUNTING','NUMERIC_REPRODUCIBILITY','CAUSAL_LANGUAGE',
 'MANAGEMENT_USEFULNESS','FD_REVIEW_AGREEMENT','CLIENT_ISOLATION','REPEATABILITY'
)

RELEASE_RULES={
 'material_numeric_error':'FAIL',
 'unsupported_opportunity_value':'FAIL',
 'cross_client_contamination':'FAIL',
 'double_counted_benefit':'FAIL',
 'unsupported_causal_claim':'FAIL',
 'silent_material_data_repair':'FAIL',
 'missing_material_limitation':'FAIL',
 'non_material_wording_issue':'CONDITIONAL',
}

def validate_programme():
    ids=[c.case_id for c in CASES]
    assert len(ids)==len(set(ids))==12
    assert set(c.business_model for c in CASES)==set(BUSINESS_MODELS)
    assert {'L1_CORE','L1_MESSY','L2_ENHANCED','L3_ADVANCED'} <= set(c.data_state for c in CASES)
    assert len(GATES)==12
    assert all(v in VERDICTS for v in RELEASE_RULES.values())
    return True
