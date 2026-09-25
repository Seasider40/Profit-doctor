"""v2.34 product API/service boundary.
UI callers consume this module rather than persistence tables.
"""
from .view_models import ProductView
from profit_doctor.management.output_spec import build_management_output

API_VERSION='PVM-2.34'

def get_product_view(con, run_id:str, client_id:str)->ProductView:
    raw=build_management_output(con,run_id,client_id)
    raw['api_version']=API_VERSION
    return ProductView.model_validate(raw)

def get_product_view_json(con, run_id:str, client_id:str)->dict:
    """JSON-safe frontend payload. Numeric financial amounts remain strings to preserve decimal exactness."""
    return get_product_view(con,run_id,client_id).model_dump(mode='json')

def _assert_run_client(con, run_id:str, client_id:str):
    row=con.execute('SELECT client_id FROM engine_run WHERE run_id=?',(run_id,)).fetchone()
    if row is None or row['client_id'] != client_id:
        raise ValueError('Run/client scope mismatch')

def _signal_evidence(con, signal_id:str, run_id:str, client_id:str):
    row=con.execute('''SELECT s.*,tr.test_name,tr.core_question FROM signal s
                      LEFT JOIN test_registry tr ON tr.test_id=s.test_id
                      WHERE s.signal_id=? AND s.run_id=? AND s.client_id=?''',(signal_id,run_id,client_id)).fetchone()
    if row is None: return None
    from .view_models import SignalEvidence
    return SignalEvidence(signal_id=row['signal_id'],test_id=row['test_id'],test_name=row['test_name'],core_question=row['core_question'],
        signal_type=row['signal_type'],entity_type=row['entity_type'],entity_id=row['entity_id'],observed_value=row['observed_value'],
        comparison_value=row['comparison_value'],variance_value=row['variance_value'],unit=row['unit'],materiality_state=row['materiality_state'],evidence_summary=row['evidence_summary'])

def get_priority_detail(con, run_id:str, client_id:str, theme_key:str):
    """Stable UI drill-down: management issue -> diagnostics/evidence -> action -> opportunity."""
    _assert_run_client(con,run_id,client_id)
    a=con.execute('SELECT * FROM management_attention_item WHERE run_id=? AND client_id=? AND theme_key=?',(run_id,client_id,theme_key)).fetchone()
    if a is None: raise KeyError(f'Priority not found: {theme_key}')
    evrows=con.execute("SELECT object_id FROM management_attention_evidence WHERE attention_item_id=? AND object_type='SIGNAL' ORDER BY object_id",(a['attention_item_id'],)).fetchall()
    evidence=[x for x in (_signal_evidence(con,r['object_id'],run_id,client_id) for r in evrows) if x is not None]
    actions=[dict(x) for x in con.execute('SELECT * FROM management_action_candidate WHERE run_id=? AND client_id=? AND attention_item_id=? ORDER BY created_at',(run_id,client_id,a['attention_item_id'])).fetchall()]
    opps=[dict(x) for x in con.execute('SELECT * FROM profit_cash_opportunity_register WHERE run_id=? AND client_id=? AND attention_item_id=? ORDER BY created_at',(run_id,client_id,a['attention_item_id'])).fetchall()]
    from .view_models import PriorityDetail,RecommendedAction,OpportunityItem
    action_models=[RecommendedAction(theme=x['theme_key'],action_type=x['action_type'],recommended_action=x['recommended_action'],evidence_required=x['evidence_required'],owner_role=x['owner_role'],state=x['action_state'],limitation=x['limitation']) for x in actions]
    opp_models=[OpportunityItem(theme=x['theme_key'],purpose=x['purpose'],benefit_type=x['benefit_type'],availability=x['availability_state'],economic_state=x['economic_state'],currency=x['currency'],theoretical=x['theoretical_amount'],addressable=x['addressable_amount'],expected=x['expected_amount'],recommended_action=x['recommended_action'],evidence_required=x['evidence_required'],limitation=x['limitation']) for x in opps]
    return PriorityDetail(run_id=run_id,client_id=client_id,attention_item_id=a['attention_item_id'],rank=a['rank_order'],theme=a['theme_key'],title=a['title'],management_question=a['management_question'],rationale=a['rationale'],next_step=a['next_step'],limitation=a['limitation'],supporting_evidence=evidence,diagnostic_ids=sorted(set(x.test_id for x in evidence)),recommended_actions=action_models,opportunities=opp_models)

def get_diagnostic_detail(con, run_id:str, client_id:str, test_id:str):
    _assert_run_client(con,run_id,client_id)
    ex=con.execute('''SELECT te.*,tr.test_name,tr.core_question,tr.objective FROM test_execution te JOIN test_registry tr ON tr.test_id=te.test_id
                      WHERE te.run_id=? AND te.client_id=? AND te.test_id=? ORDER BY te.completed_at DESC LIMIT 1''',(run_id,client_id,test_id)).fetchone()
    if ex is None: raise KeyError(f'Diagnostic not found: {test_id}')
    sigs=con.execute('SELECT signal_id FROM signal WHERE run_id=? AND client_id=? AND test_id=? ORDER BY created_at,signal_id',(run_id,client_id,test_id)).fetchall()
    evidence=[x for x in (_signal_evidence(con,r['signal_id'],run_id,client_id) for r in sigs) if x is not None]
    from .view_models import DiagnosticDetail
    return DiagnosticDetail(run_id=run_id,client_id=client_id,test_id=test_id,test_name=ex['test_name'],core_question=ex['core_question'],objective=ex['objective'],eligibility_state=ex['eligibility_state'],execution_status=ex['execution_status'],method_id=ex['method_id'],limitation=ex['limitation'],signals=evidence)
