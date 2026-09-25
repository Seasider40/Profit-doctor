"""v2.34 typed product view models.
These models are a presentation boundary: they validate/project v2.33 output and never create economics.
"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class StrictModel(BaseModel):
    model_config=ConfigDict(extra='forbid', frozen=True)

class KPI(StrictModel):
    label:str; value:str; unit:str|None=None; primitive_id:str
class Coverage(StrictModel):
    completed:int; total:int; not_completed:int
class ExecutiveHealthCheck(StrictModel):
    headline:str; kpis:list[KPI]; diagnostic_coverage:Coverage; control_failures:int; guardrail:str
class ManagementPriority(StrictModel):
    rank:int; theme:str; title:str; issue_type:str; priority:str; confidence:str
    management_question:str; rationale:str; next_step:str; limitation:str|None=None
class OpportunityItem(StrictModel):
    theme:str; purpose:str; benefit_type:str; availability:str; economic_state:str; currency:str|None=None
    theoretical:str|None=None; addressable:str|None=None; expected:str|None=None
    recommended_action:str; evidence_required:str; limitation:str|None=None
class PortfolioHeadline(StrictModel):
    recurring_profit_expected:str|None=None; one_off_cash_release_expected:str|None=None
    combined_total:None=None; rule:str
class OpportunityRegister(StrictModel):
    items:list[OpportunityItem]; portfolio_headline:PortfolioHeadline
class DiagnosticUnavailable(StrictModel):
    test_id:str; limitation:str|None=None
class PerformanceDiagnostics(StrictModel):
    completed:list[str]; partial:list[str]; unavailable:list[DiagnosticUnavailable]
class RecommendedAction(StrictModel):
    theme:str; action_type:str; recommended_action:str; evidence_required:str; owner_role:str|None=None; state:str; limitation:str|None=None
class Reconciliation(StrictModel):
    reconciliation_type:str; status:str; residual:float|int|str|None=None; left_object:str|None=None; right_object:str|None=None
    left_value:float|int|str|None=None; right_value:float|int|str|None=None; limitation:str|None=None
class DataMIMaturity(StrictModel):
    control_reconciliations:list[Reconciliation]; coverage:Coverage; message:str
class BenefitProgress(StrictModel):
    status:str; realised:None|str=None; verified:None|str=None; retained:None|str=None; rule:str
class EvidenceLimitations(StrictModel):
    reconciliations:list[Reconciliation]; principles:list[str]
class ProductView(BaseModel):
    model_config=ConfigDict(extra='forbid', frozen=True)
    spec_version:str; api_version:Literal['PVM-2.34']='PVM-2.34'; run_id:str; client_id:str; section_order:list[str]
    executive_health_check:ExecutiveHealthCheck
    management_attention:list[ManagementPriority]=Field(min_length=0,max_length=7)
    opportunity_register:OpportunityRegister
    performance_diagnostics:PerformanceDiagnostics
    recommended_actions:list[RecommendedAction]
    data_mi_maturity:DataMIMaturity
    benefit_progress:BenefitProgress
    evidence_and_limitations:EvidenceLimitations

class SignalEvidence(StrictModel):
    signal_id:str; test_id:str; test_name:str|None=None; core_question:str|None=None
    signal_type:str; entity_type:str|None=None; entity_id:str|None=None
    observed_value:str|None=None; comparison_value:str|None=None; variance_value:str|None=None; unit:str|None=None
    materiality_state:str; evidence_summary:str

class PriorityDetail(StrictModel):
    run_id:str; client_id:str; attention_item_id:str; rank:int; theme:str; title:str
    management_question:str; rationale:str; next_step:str; limitation:str|None=None
    supporting_evidence:list[SignalEvidence]; diagnostic_ids:list[str]
    recommended_actions:list[RecommendedAction]; opportunities:list[OpportunityItem]

class DiagnosticDetail(StrictModel):
    run_id:str; client_id:str; test_id:str; test_name:str; core_question:str; objective:str
    eligibility_state:str; execution_status:str; method_id:str|None=None; limitation:str|None=None
    signals:list[SignalEvidence]
