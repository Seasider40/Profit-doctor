import sqlite3
import atexit
from pathlib import Path

SCHEMA = r'''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS client (
  client_id TEXT PRIMARY KEY, client_name TEXT NOT NULL, base_currency TEXT NOT NULL DEFAULT 'GBP',
  business_model TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS engine_run (
  run_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id), run_type TEXT NOT NULL,
  started_at TEXT NOT NULL, completed_at TEXT, status TEXT NOT NULL, previous_run_id TEXT,
  baseline_run_id TEXT, engine_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ingestion_job (
  ingestion_job_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES engine_run(run_id),
  client_id TEXT NOT NULL REFERENCES client(client_id), started_at TEXT NOT NULL, completed_at TEXT,
  status TEXT NOT NULL, error_detail TEXT
);
CREATE TABLE IF NOT EXISTS source_file (
  source_file_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id),
  original_filename TEXT NOT NULL, storage_location TEXT NOT NULL, file_hash TEXT NOT NULL,
  file_size INTEGER NOT NULL, immutable_flag INTEGER NOT NULL DEFAULT 1, uploaded_at TEXT NOT NULL,
  UNIQUE(client_id,file_hash)
);
CREATE TABLE IF NOT EXISTS dataset (
  dataset_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id),
  source_file_id TEXT NOT NULL REFERENCES source_file(source_file_id), data_domain TEXT NOT NULL,
  logical_dataset_key TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(client_id, logical_dataset_key)
);
CREATE TABLE IF NOT EXISTS dataset_version (
  dataset_version_id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL REFERENCES dataset(dataset_id),
  ingestion_job_id TEXT NOT NULL REFERENCES ingestion_job(ingestion_job_id), source_file_id TEXT NOT NULL REFERENCES source_file(source_file_id),
  version_number INTEGER NOT NULL, row_count INTEGER, period_from TEXT, period_to TEXT,
  ingestion_status TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(dataset_id,version_number)
);
CREATE TABLE IF NOT EXISTS entity (
  entity_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id), entity_type TEXT NOT NULL,
  canonical_name TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ACTIVE'
);
CREATE TABLE IF NOT EXISTS entity_alias (
  entity_alias_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id),
  entity_id TEXT NOT NULL REFERENCES entity(entity_id), source_file_id TEXT,
  source_entity_key TEXT NOT NULL, source_entity_name TEXT, match_method TEXT NOT NULL,
  match_confidence TEXT NOT NULL, UNIQUE(client_id, source_entity_key, entity_id)
);
CREATE TABLE IF NOT EXISTS sales_transaction (
  sales_transaction_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id),
  source_transaction_key TEXT NOT NULL, transaction_date TEXT NOT NULL,
  customer_entity_id TEXT REFERENCES entity(entity_id), product_entity_id TEXT REFERENCES entity(entity_id),
  units TEXT, unit_price TEXT, unit_cost TEXT, net_revenue TEXT, direct_cost TEXT,
  source_gross_profit TEXT, cts TEXT, source_contribution TEXT,
  dataset_version_id TEXT NOT NULL REFERENCES dataset_version(dataset_version_id), source_row_reference INTEGER NOT NULL,
  record_status TEXT NOT NULL DEFAULT 'ACTIVE', UNIQUE(client_id, dataset_version_id, source_transaction_key)
);
CREATE TABLE IF NOT EXISTS primitive_registry (
  primitive_id TEXT PRIMARY KEY, primitive_name TEXT NOT NULL, definition TEXT NOT NULL,
  primitive_family TEXT NOT NULL, stock_flow_rate TEXT NOT NULL, unit_type TEXT NOT NULL,
  additivity_type TEXT NOT NULL, version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS primitive_result (
  primitive_result_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES engine_run(run_id),
  client_id TEXT NOT NULL REFERENCES client(client_id), primitive_id TEXT NOT NULL REFERENCES primitive_registry(primitive_id),
  method_id TEXT NOT NULL, period_from TEXT, period_to TEXT, dimension_type TEXT, dimension_entity_id TEXT,
  numeric_value TEXT, unit TEXT NOT NULL, result_status TEXT NOT NULL, calculated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS calculation_lineage (
  lineage_id TEXT PRIMARY KEY, primitive_result_id TEXT NOT NULL REFERENCES primitive_result(primitive_result_id),
  source_object_type TEXT NOT NULL, source_object_id TEXT NOT NULL, relationship_type TEXT NOT NULL,
  scope_definition TEXT
);
CREATE TABLE IF NOT EXISTS ingestion_error (
  ingestion_error_id TEXT PRIMARY KEY, ingestion_job_id TEXT NOT NULL REFERENCES ingestion_job(ingestion_job_id),
  dataset_name TEXT, source_row_reference INTEGER, error_code TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_event (
  audit_event_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id), run_id TEXT NOT NULL REFERENCES engine_run(run_id),
  event_type TEXT NOT NULL, object_type TEXT NOT NULL, object_id TEXT, detail TEXT, created_at TEXT NOT NULL
);
'''

def connect(path):
    con = sqlite3.connect(Path(path))
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.executescript(SCHEMA)
    return con

TRUST_SCHEMA = r'''
CREATE TABLE IF NOT EXISTS data_availability (
  availability_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
  data_domain TEXT NOT NULL, availability_state TEXT NOT NULL, history_months INTEGER,
  row_count INTEGER, period_from TEXT, period_to TEXT, evidence_object_id TEXT, assessed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS data_quality_assessment (
  quality_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
  data_domain TEXT NOT NULL, quality_state TEXT NOT NULL, completeness_pct TEXT,
  validity_pct TEXT, uniqueness_pct TEXT, timeliness_state TEXT, limitations TEXT, assessed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mapping_coverage (
  mapping_coverage_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
  data_domain TEXT NOT NULL, mapping_type TEXT NOT NULL, mapped_rows INTEGER NOT NULL,
  total_rows INTEGER NOT NULL, coverage_pct TEXT, economic_coverage_pct TEXT, assessed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reconciliation (
  reconciliation_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
  reconciliation_type TEXT NOT NULL, left_object TEXT NOT NULL, right_object TEXT NOT NULL,
  left_value TEXT, right_value TEXT, residual TEXT, status TEXT NOT NULL, limitation TEXT, assessed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS financial_integrity (
  integrity_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
  data_domain TEXT NOT NULL, integrity_state TEXT NOT NULL, basis TEXT NOT NULL, limitation TEXT, assessed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS economic_coverage (
  economic_coverage_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
  test_id TEXT NOT NULL, denominator_type TEXT NOT NULL, covered_amount TEXT,
  total_amount TEXT, coverage_pct TEXT, limitation TEXT, assessed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS test_eligibility (
  eligibility_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
  test_id TEXT NOT NULL, applicability TEXT NOT NULL, eligibility_state TEXT NOT NULL,
  selected_method TEXT, quality_state TEXT, integrity_state TEXT, economic_coverage_pct TEXT,
  limitation TEXT, assessed_at TEXT NOT NULL, UNIQUE(run_id,test_id)
);
CREATE TABLE IF NOT EXISTS blind_spot (
  blind_spot_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
  object_type TEXT NOT NULL, object_id TEXT NOT NULL, description TEXT NOT NULL,
  materiality_state TEXT NOT NULL, assessed_at TEXT NOT NULL
);
'''

_original_connect = connect
def connect(path):
    con = _original_connect(path)
    con.executescript(TRUST_SCHEMA)
    return con

ACCOUNTING_SCHEMA = r'''
CREATE TABLE IF NOT EXISTS account (
 account_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id), account_code TEXT NOT NULL,
 account_name TEXT NOT NULL, account_type TEXT NOT NULL, UNIQUE(client_id,account_code)
);
CREATE TABLE IF NOT EXISTS trial_balance (
 trial_balance_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id), period_end TEXT NOT NULL,
 account_id TEXT NOT NULL REFERENCES account(account_id), debit TEXT NOT NULL, credit TEXT NOT NULL,
 dataset_version_id TEXT NOT NULL REFERENCES dataset_version(dataset_version_id), source_row_reference INTEGER NOT NULL,
 UNIQUE(client_id,dataset_version_id,period_end,account_id)
);
CREATE TABLE IF NOT EXISTS financial_statement_line (
 statement_line_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id), statement_type TEXT NOT NULL,
 period_end TEXT NOT NULL, line_code TEXT NOT NULL, line_name TEXT NOT NULL, amount TEXT NOT NULL,
 dataset_version_id TEXT NOT NULL REFERENCES dataset_version(dataset_version_id), source_row_reference INTEGER NOT NULL,
 UNIQUE(client_id,dataset_version_id,statement_type,period_end,line_code)
);
CREATE TABLE IF NOT EXISTS ar_invoice (
 ar_invoice_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id), source_invoice_key TEXT NOT NULL,
 customer_key TEXT, invoice_date TEXT NOT NULL, due_date TEXT NOT NULL, original_amount TEXT NOT NULL,
 outstanding_amount TEXT NOT NULL, dataset_version_id TEXT NOT NULL REFERENCES dataset_version(dataset_version_id), source_row_reference INTEGER NOT NULL,
 UNIQUE(client_id,dataset_version_id,source_invoice_key)
);
CREATE TABLE IF NOT EXISTS ap_invoice (
 ap_invoice_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id), source_invoice_key TEXT NOT NULL,
 supplier_key TEXT, invoice_date TEXT NOT NULL, due_date TEXT NOT NULL, original_amount TEXT NOT NULL,
 outstanding_amount TEXT NOT NULL, dataset_version_id TEXT NOT NULL REFERENCES dataset_version(dataset_version_id), source_row_reference INTEGER NOT NULL,
 UNIQUE(client_id,dataset_version_id,source_invoice_key)
);

CREATE TABLE IF NOT EXISTS inventory_snapshot (
 inventory_snapshot_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id), snapshot_date TEXT NOT NULL,
 product_key TEXT NOT NULL, quantity_on_hand TEXT, inventory_value TEXT NOT NULL,
 dataset_version_id TEXT NOT NULL REFERENCES dataset_version(dataset_version_id), source_row_reference INTEGER NOT NULL,
 UNIQUE(client_id,dataset_version_id,snapshot_date,product_key)
);
CREATE TABLE IF NOT EXISTS bank_transaction (
 bank_transaction_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id), source_transaction_key TEXT NOT NULL,
 transaction_date TEXT NOT NULL, amount TEXT NOT NULL, balance TEXT, dataset_version_id TEXT NOT NULL REFERENCES dataset_version(dataset_version_id),
 source_row_reference INTEGER NOT NULL, UNIQUE(client_id,dataset_version_id,source_transaction_key)
);
'''
_prev_connect = connect
def connect(path):
    con = _prev_connect(path)
    con.executescript(ACCOUNTING_SCHEMA)
    return con


SPRINT3_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS primitive_method (
  method_id TEXT PRIMARY KEY, primitive_id TEXT NOT NULL REFERENCES primitive_registry(primitive_id),
  method_name TEXT NOT NULL, method_level TEXT NOT NULL, required_domains TEXT NOT NULL,
  calculation_version TEXT NOT NULL, active_flag INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS primitive_dependency (
  primitive_id TEXT NOT NULL REFERENCES primitive_registry(primitive_id),
  depends_on_primitive_id TEXT NOT NULL REFERENCES primitive_registry(primitive_id),
  relationship_type TEXT NOT NULL DEFAULT 'REQUIRES',
  PRIMARY KEY (primitive_id, depends_on_primitive_id)
);
CREATE TABLE IF NOT EXISTS primitive_execution (
  primitive_execution_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES engine_run(run_id),
  client_id TEXT NOT NULL REFERENCES client(client_id), primitive_id TEXT NOT NULL REFERENCES primitive_registry(primitive_id),
  method_id TEXT, execution_status TEXT NOT NULL, limitation TEXT, executed_at TEXT NOT NULL
);
"""
_prev_connect_s3 = connect
def connect(path):
    con = _prev_connect_s3(path)
    con.executescript(SPRINT3_SCHEMA)
    return con

DIAGNOSTIC_SCHEMA = r'''
CREATE TABLE IF NOT EXISTS test_registry (
 test_id TEXT PRIMARY KEY, test_name TEXT NOT NULL, core_question TEXT NOT NULL,
 objective TEXT NOT NULL, version TEXT NOT NULL, status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS test_execution (
 test_execution_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 test_id TEXT NOT NULL, method_id TEXT, eligibility_state TEXT NOT NULL,
 execution_status TEXT NOT NULL, signal_count INTEGER NOT NULL DEFAULT 0,
 limitation TEXT, started_at TEXT NOT NULL, completed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS signal (
 signal_id TEXT PRIMARY KEY, test_execution_id TEXT NOT NULL, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 test_id TEXT NOT NULL, signal_type TEXT NOT NULL, entity_type TEXT, entity_id TEXT,
 period_from TEXT, period_to TEXT, observed_value TEXT, comparison_value TEXT, variance_value TEXT,
 unit TEXT, materiality_state TEXT NOT NULL, status TEXT NOT NULL, evidence_summary TEXT NOT NULL,
 source_primitive_id TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS diagnostic_lineage (
 diagnostic_lineage_id TEXT PRIMARY KEY, signal_id TEXT NOT NULL, source_object_type TEXT NOT NULL,
 source_object_id TEXT NOT NULL, relationship_type TEXT NOT NULL, scope_definition TEXT
);
'''

_prev_connect_diagnostic = connect
def connect(path):
    con = _prev_connect_diagnostic(path)
    con.executescript(DIAGNOSTIC_SCHEMA)
    return con

REASONING_SCHEMA = r'''
CREATE TABLE IF NOT EXISTS context_event (
 context_event_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, context_type TEXT NOT NULL,
 entity_type TEXT, entity_id TEXT, period_from TEXT, period_to TEXT, description TEXT NOT NULL,
 source_type TEXT NOT NULL, validity_state TEXT NOT NULL DEFAULT 'CURRENT', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS suppression_result (
 suppression_result_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 signal_id TEXT NOT NULL, suppression_type TEXT NOT NULL, rule_id TEXT NOT NULL,
 reason TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS persistence_profile (
 persistence_profile_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 signal_id TEXT NOT NULL, persistence_state TEXT NOT NULL, evidence_summary TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence_bundle (
 evidence_bundle_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 primary_signal_id TEXT NOT NULL, bundle_type TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence_bundle_item (
 evidence_bundle_item_id TEXT PRIMARY KEY, evidence_bundle_id TEXT NOT NULL,
 object_type TEXT NOT NULL, object_id TEXT NOT NULL, relationship_type TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fact (
 fact_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 evidence_bundle_id TEXT NOT NULL, fact_type TEXT NOT NULL, statement TEXT NOT NULL,
 numeric_value TEXT, unit TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS interpretation (
 interpretation_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 evidence_bundle_id TEXT NOT NULL, interpretation_text TEXT NOT NULL,
 interpretation_status TEXT NOT NULL, confidence_state TEXT NOT NULL,
 uncertainty_text TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS finding_candidate (
 finding_candidate_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 evidence_bundle_id TEXT NOT NULL, finding_type TEXT NOT NULL, title TEXT NOT NULL,
 materiality_state TEXT NOT NULL, confidence_state TEXT NOT NULL,
 candidate_status TEXT NOT NULL, management_question TEXT, next_step TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS finding (
 finding_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, finding_type TEXT NOT NULL,
 title TEXT NOT NULL, status TEXT NOT NULL, first_run_id TEXT NOT NULL, last_run_id TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS finding_version (
 finding_version_id TEXT PRIMARY KEY, finding_id TEXT NOT NULL, run_id TEXT NOT NULL,
 finding_candidate_id TEXT NOT NULL, fact_summary TEXT NOT NULL, interpretation_summary TEXT NOT NULL,
 why_it_matters TEXT NOT NULL, materiality_state TEXT NOT NULL, confidence_state TEXT NOT NULL,
 management_question TEXT, next_step TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fd_review_queue (
 fd_review_queue_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 object_type TEXT NOT NULL, object_id TEXT NOT NULL, queue_reason TEXT NOT NULL,
 priority_state TEXT NOT NULL, review_status TEXT NOT NULL, created_at TEXT NOT NULL
);
'''

_prev_connect_reasoning = connect
def connect(path):
    con = _prev_connect_reasoning(path)
    con.executescript(REASONING_SCHEMA)
    return con

REASONING_HARDENING_SCHEMA = r'''
CREATE TABLE IF NOT EXISTS finding_cluster (
 finding_cluster_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 cluster_key TEXT NOT NULL, cluster_type TEXT NOT NULL, primary_signal_id TEXT NOT NULL,
 member_count INTEGER NOT NULL, rationale TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(run_id, cluster_key)
);
CREATE TABLE IF NOT EXISTS finding_cluster_member (
 finding_cluster_member_id TEXT PRIMARY KEY, finding_cluster_id TEXT NOT NULL,
 signal_id TEXT NOT NULL, relationship_type TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(finding_cluster_id, signal_id)
);
CREATE TABLE IF NOT EXISTS contradictory_evidence (
 contradictory_evidence_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 evidence_bundle_id TEXT NOT NULL, object_type TEXT NOT NULL, object_id TEXT NOT NULL,
 contradiction_type TEXT NOT NULL, description TEXT NOT NULL, effect_on_interpretation TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS management_attention_budget (
 attention_budget_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 max_primary_items INTEGER NOT NULL, eligible_findings INTEGER NOT NULL,
 queued_primary_items INTEGER NOT NULL, deferred_items INTEGER NOT NULL,
 policy_version TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(run_id)
);
CREATE TABLE IF NOT EXISTS finding_identity (
 finding_identity_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, identity_key TEXT NOT NULL,
 finding_id TEXT NOT NULL, first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
 UNIQUE(client_id, identity_key)
);
'''
_prev_connect_reasoning_hardening = connect
def connect(path):
    con = _prev_connect_reasoning_hardening(path)
    con.executescript(REASONING_HARDENING_SCHEMA)
    return con

ECONOMIC_SCHEMA = r'''
CREATE TABLE IF NOT EXISTS economic_story (
 economic_story_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, story_key TEXT NOT NULL,
 story_type TEXT NOT NULL, title TEXT NOT NULL, status TEXT NOT NULL,
 first_run_id TEXT NOT NULL, last_run_id TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(client_id, story_key)
);
CREATE TABLE IF NOT EXISTS economic_story_object (
 economic_story_object_id TEXT PRIMARY KEY, economic_story_id TEXT NOT NULL,
 object_type TEXT NOT NULL, object_id TEXT NOT NULL, relationship_type TEXT NOT NULL,
 created_at TEXT NOT NULL, UNIQUE(economic_story_id, object_type, object_id, relationship_type)
);
CREATE TABLE IF NOT EXISTS economic_impact (
 impact_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 economic_story_id TEXT NOT NULL, impact_type TEXT NOT NULL, primary_economic_measure TEXT NOT NULL,
 entity_type TEXT, entity_id TEXT, period_from TEXT, period_to TEXT, amount TEXT,
 currency TEXT NOT NULL, attribution_state TEXT NOT NULL, calculation_basis TEXT NOT NULL,
 status TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS economic_exposure (
 exposure_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 economic_story_id TEXT NOT NULL, exposure_type TEXT NOT NULL, entity_type TEXT, entity_id TEXT,
 amount TEXT, currency TEXT NOT NULL, exposure_pathway TEXT NOT NULL, evidence_basis TEXT NOT NULL,
 status TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS economic_baseline (
 economic_baseline_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 economic_story_id TEXT NOT NULL, baseline_type TEXT NOT NULL, period_from TEXT, period_to TEXT,
 amount TEXT, currency TEXT NOT NULL, definition TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recovery_envelope (
 recovery_envelope_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 economic_story_id TEXT NOT NULL, benefit_type TEXT NOT NULL, time_basis TEXT NOT NULL,
 maximum_supported_recovery TEXT, currency TEXT NOT NULL, evidence_basis TEXT NOT NULL,
 status TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS opportunity_candidate (
 opportunity_candidate_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 economic_story_id TEXT NOT NULL, finding_id TEXT NOT NULL, mechanism_id TEXT,
 purpose TEXT NOT NULL, benefit_type TEXT NOT NULL, economic_baseline_id TEXT,
 theoretical_amount TEXT, addressable_amount TEXT, expected_amount TEXT, currency TEXT NOT NULL,
 availability_state TEXT NOT NULL, candidate_status TEXT NOT NULL, limitation TEXT,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS opportunity (
 opportunity_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 economic_story_id TEXT NOT NULL, finding_id TEXT NOT NULL, mechanism_id TEXT NOT NULL,
 purpose TEXT NOT NULL, benefit_type TEXT NOT NULL, economic_baseline_id TEXT NOT NULL,
 theoretical_amount TEXT, addressable_amount TEXT, expected_amount TEXT, currency TEXT NOT NULL,
 availability_state TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS opportunity_relationship (
 opportunity_relationship_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 left_opportunity_id TEXT NOT NULL, right_opportunity_id TEXT NOT NULL,
 relationship_type TEXT NOT NULL, overlap_amount TEXT, evidence_basis TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(run_id,left_opportunity_id,right_opportunity_id,relationship_type)
);
CREATE TABLE IF NOT EXISTS economic_resolution (
 economic_resolution_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 finding_id TEXT NOT NULL, economic_story_id TEXT NOT NULL, resolution_state TEXT NOT NULL,
 impact_count INTEGER NOT NULL, exposure_count INTEGER NOT NULL, candidate_count INTEGER NOT NULL,
 opportunity_count INTEGER NOT NULL, limitation TEXT, created_at TEXT NOT NULL,
 UNIQUE(run_id,finding_id)
);
'''
_prev_connect_economic = connect
def connect(path):
    con = _prev_connect_economic(path)
    con.executescript(ECONOMIC_SCHEMA)
    return con

MANAGEMENT_BENEFIT_SCHEMA = r'''
CREATE TABLE IF NOT EXISTS decision (
 decision_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 economic_story_id TEXT, opportunity_id TEXT, risk_id TEXT, issue TEXT NOT NULL,
 selected_course TEXT NOT NULL, rationale TEXT NOT NULL, owner TEXT,
 status TEXT NOT NULL, decided_at TEXT NOT NULL, review_date TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS action (
 action_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 decision_id TEXT NOT NULL, opportunity_id TEXT, action_type TEXT NOT NULL,
 description TEXT NOT NULL, owner TEXT, target_date TEXT, status TEXT NOT NULL,
 expected_effect TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS action_progress (
 action_progress_id TEXT PRIMARY KEY, action_id TEXT NOT NULL, run_id TEXT NOT NULL,
 progress_state TEXT NOT NULL, note TEXT, recorded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS benefit_event (
 benefit_event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 opportunity_id TEXT NOT NULL, action_id TEXT NOT NULL, event_type TEXT NOT NULL,
 event_date TEXT NOT NULL, evidence_basis TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS benefit_leg (
 benefit_leg_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 benefit_event_id TEXT NOT NULL, opportunity_id TEXT NOT NULL, action_id TEXT NOT NULL,
 benefit_type TEXT NOT NULL, period_from TEXT, period_to TEXT,
 gross_amount TEXT NOT NULL, implementation_cost TEXT NOT NULL, ongoing_cost TEXT NOT NULL,
 adverse_effect TEXT NOT NULL, net_amount TEXT NOT NULL, currency TEXT NOT NULL,
 attribution_state TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS benefit_observation (
 benefit_observation_id TEXT PRIMARY KEY, benefit_leg_id TEXT NOT NULL, run_id TEXT NOT NULL,
 observed_amount TEXT NOT NULL, currency TEXT NOT NULL, evidence_basis TEXT NOT NULL,
 observed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS benefit_retention (
 benefit_retention_id TEXT PRIMARY KEY, benefit_leg_id TEXT NOT NULL, run_id TEXT NOT NULL,
 retained_amount TEXT NOT NULL, currency TEXT NOT NULL, retention_state TEXT NOT NULL,
 evidence_basis TEXT NOT NULL, assessed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS benefit_relationship (
 benefit_relationship_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 left_benefit_leg_id TEXT NOT NULL, right_benefit_leg_id TEXT NOT NULL,
 relationship_type TEXT NOT NULL, overlap_amount TEXT, evidence_basis TEXT NOT NULL,
 created_at TEXT NOT NULL
);
'''
_prev_connect_management = connect
def connect(path):
    con = _prev_connect_management(path)
    con.executescript(MANAGEMENT_BENEFIT_SCHEMA)
    return con

GATE3_SCHEMA = r'''
CREATE TABLE IF NOT EXISTS business_model_config_runtime (
 client_id TEXT PRIMARY KEY, business_model_type TEXT NOT NULL, inventory_applicability TEXT NOT NULL DEFAULT 'AUTO',
 revenue_semantics_enabled INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revenue_type_definition (
 revenue_type_code TEXT PRIMARY KEY, revenue_type_name TEXT NOT NULL, cadence_type TEXT NOT NULL,
 recurring_flag INTEGER NOT NULL, default_margin_profile TEXT, active_flag INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS product_revenue_semantics (
 client_id TEXT NOT NULL, product_key TEXT NOT NULL, revenue_type_code TEXT NOT NULL,
 effective_from TEXT, effective_to TEXT, evidence_basis TEXT NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(client_id, product_key, revenue_type_code, effective_from)
);
CREATE TABLE IF NOT EXISTS cross_source_reconciliation (
 cross_reconciliation_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 reconciliation_type TEXT NOT NULL, period_end TEXT, left_source TEXT NOT NULL, right_source TEXT NOT NULL,
 left_value TEXT, right_value TEXT, residual TEXT, tolerance TEXT, status TEXT NOT NULL,
 integrity_effect TEXT NOT NULL, limitation TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS opportunity_mechanism_evidence (
 mechanism_evidence_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 opportunity_candidate_id TEXT NOT NULL, mechanism_id TEXT NOT NULL, evidence_type TEXT NOT NULL,
 evidence_basis TEXT NOT NULL, addressability_basis TEXT, recovery_basis TEXT, confidence_state TEXT NOT NULL,
 status TEXT NOT NULL, created_at TEXT NOT NULL
);
'''
_prev_connect_gate3 = connect
def connect(path):
    con = _prev_connect_gate3(path)
    con.executescript(GATE3_SCHEMA)
    return con

WORKFORCE_SCHEMA = r'''
CREATE TABLE IF NOT EXISTS workforce_snapshot (
 workforce_snapshot_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, snapshot_date TEXT NOT NULL,
 employee_key TEXT NOT NULL, department TEXT, role_name TEXT, fte TEXT NOT NULL,
 base_salary TEXT NOT NULL, employer_oncost TEXT NOT NULL DEFAULT '0', commission TEXT NOT NULL DEFAULT '0',
 bonus TEXT NOT NULL DEFAULT '0', other_people_cost TEXT NOT NULL DEFAULT '0',
 practical_capacity_hours TEXT, utilised_hours TEXT, evidence_basis TEXT NOT NULL,
 UNIQUE(client_id,snapshot_date,employee_key)
);
CREATE TABLE IF NOT EXISTS commission_plan (
 commission_plan_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, plan_name TEXT NOT NULL,
 plan_type TEXT NOT NULL, basis_type TEXT NOT NULL, target_rate TEXT, threshold_value TEXT,
 cap_value TEXT, department TEXT, role_name TEXT, evidence_basis TEXT NOT NULL, active_flag INTEGER NOT NULL DEFAULT 1
);
'''
_prev_connect_workforce = connect
def connect(path):
    con = _prev_connect_workforce(path)
    con.executescript(WORKFORCE_SCHEMA)
    return con

SUPPLIER_SCHEMA = r'''
CREATE TABLE IF NOT EXISTS supplier_master (
 supplier_key TEXT NOT NULL, client_id TEXT NOT NULL, supplier_name TEXT, category TEXT, criticality TEXT,
 contracted_terms_days INTEGER, single_source_flag INTEGER NOT NULL DEFAULT 0, evidence_basis TEXT,
 PRIMARY KEY(client_id,supplier_key));
CREATE TABLE IF NOT EXISTS purchase_transaction (
 purchase_transaction_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, transaction_date TEXT NOT NULL,
 supplier_key TEXT NOT NULL, category TEXT, item_key TEXT, description TEXT, quantity TEXT,
 net_amount TEXT NOT NULL, unit_cost TEXT, invoice_reference TEXT, recurring_reference TEXT, evidence_basis TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS overhead_transaction (
 overhead_transaction_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, transaction_date TEXT NOT NULL,
 supplier_key TEXT, category TEXT NOT NULL, description TEXT, net_amount TEXT NOT NULL,
 invoice_reference TEXT, recurring_reference TEXT, evidence_basis TEXT NOT NULL);
'''
_prev_connect_supplier = connect
def connect(path):
    con = _prev_connect_supplier(path)
    con.executescript(SUPPLIER_SCHEMA)
    return con

FORECAST_SCHEMA = r'''
CREATE TABLE IF NOT EXISTS plan_version (
 plan_version_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, plan_type TEXT NOT NULL, version_name TEXT NOT NULL,
 created_date TEXT NOT NULL, effective_from TEXT, effective_to TEXT, status TEXT NOT NULL DEFAULT 'ACTIVE', evidence_basis TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plan_line (
 plan_line_id TEXT PRIMARY KEY, plan_version_id TEXT NOT NULL, client_id TEXT NOT NULL, period TEXT NOT NULL,
 metric_code TEXT NOT NULL, entity_type TEXT, entity_id TEXT, amount TEXT NOT NULL, unit TEXT NOT NULL DEFAULT 'GBP', evidence_basis TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS actual_metric (
 actual_metric_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, period TEXT NOT NULL, metric_code TEXT NOT NULL, actual_value TEXT NOT NULL, unit TEXT NOT NULL DEFAULT 'GBP', evidence_basis TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS forecast_vintage (
 forecast_vintage_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, vintage_date TEXT NOT NULL, target_period TEXT NOT NULL,
 metric_code TEXT NOT NULL, forecast_value TEXT NOT NULL, unit TEXT NOT NULL DEFAULT 'GBP', evidence_basis TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS kpi_observation (
 kpi_observation_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, period TEXT NOT NULL, kpi_code TEXT NOT NULL,
 kpi_name TEXT NOT NULL, value TEXT NOT NULL, unit TEXT NOT NULL, driver_class TEXT NOT NULL,
 linked_outcome TEXT, evidence_basis TEXT NOT NULL
);
'''
_prev_connect_forecast = connect
def connect(path):
    con = _prev_connect_forecast(path)
    con.executescript(FORECAST_SCHEMA)
    return con

RISK_CONTROL_SCHEMA = r'''
CREATE TABLE IF NOT EXISTS control_evidence (
 control_evidence_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, evidence_date TEXT NOT NULL,
 control_area TEXT NOT NULL, control_name TEXT NOT NULL, control_status TEXT NOT NULL,
 severity TEXT, amount_exposed TEXT, evidence_basis TEXT NOT NULL, management_response TEXT
);
CREATE TABLE IF NOT EXISTS control_exception (
 control_exception_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, exception_date TEXT NOT NULL,
 process_area TEXT NOT NULL, exception_type TEXT NOT NULL, description TEXT NOT NULL,
 amount TEXT, repeat_key TEXT, evidence_basis TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'OPEN'
);
CREATE TABLE IF NOT EXISTS financial_exposure_evidence (
 exposure_evidence_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, exposure_date TEXT NOT NULL,
 exposure_type TEXT NOT NULL, description TEXT NOT NULL, amount_exposed TEXT,
 concentration_pct TEXT, mitigation_status TEXT, evidence_basis TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS governance_action_candidate (
 governance_candidate_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 source_signal_id TEXT, control_area TEXT NOT NULL, action_type TEXT NOT NULL,
 proposed_action TEXT NOT NULL, proportionality_basis TEXT NOT NULL, expected_loss TEXT,
 status TEXT NOT NULL DEFAULT 'CANDIDATE', created_at TEXT NOT NULL
);
'''
_prev_connect_risk = connect
def connect(path):
    con = _prev_connect_risk(path)
    con.executescript(RISK_CONTROL_SCHEMA)
    return con

# v2.7 canonical connection factory. Historical wrapper definitions above are retained
# for migration traceability, but runtime connection creation now has one explicit path.
ALL_SCHEMAS = (
    SCHEMA, TRUST_SCHEMA, ACCOUNTING_SCHEMA, SPRINT3_SCHEMA, DIAGNOSTIC_SCHEMA,
    REASONING_SCHEMA, REASONING_HARDENING_SCHEMA, ECONOMIC_SCHEMA,
    MANAGEMENT_BENEFIT_SCHEMA, GATE3_SCHEMA, WORKFORCE_SCHEMA, SUPPLIER_SCHEMA,
    FORECAST_SCHEMA, RISK_CONTROL_SCHEMA,
)

class ProfitDoctorSQLiteConnection(sqlite3.Connection):
    """SQLite dev/test connection with legacy-fixture cleanup."""
    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

def connect(path):
    con = sqlite3.connect(Path(path), factory=ProfitDoctorSQLiteConnection)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA busy_timeout=5000')
    for schema in ALL_SCHEMAS:
        con.executescript(schema)
    return con

# v2.7 fast schema bootstrap for ephemeral SQLite databases used by tests/dev.
# This replaces repeated execution of ~90 DDL statements on every new database.
_SCHEMA_TEMPLATE = None
_SCHEMA_TEMPLATE_URI = 'file:profit_doctor_schema_template?mode=memory&cache=shared'

def _close_schema_template():
    global _SCHEMA_TEMPLATE
    if _SCHEMA_TEMPLATE is not None:
        _SCHEMA_TEMPLATE.close()
        _SCHEMA_TEMPLATE = None

atexit.register(_close_schema_template)

def _schema_template():
    global _SCHEMA_TEMPLATE
    if _SCHEMA_TEMPLATE is None:
        t = sqlite3.connect(_SCHEMA_TEMPLATE_URI, uri=True, factory=ProfitDoctorSQLiteConnection)
        t.row_factory = sqlite3.Row
        t.execute('PRAGMA foreign_keys=ON')
        for schema in ALL_SCHEMAS:
            t.executescript(schema)
        _SCHEMA_TEMPLATE = t
    return _SCHEMA_TEMPLATE


def connect(path):
    p = Path(path)
    existed_with_schema = p.exists() and p.stat().st_size > 0
    con = sqlite3.connect(p, factory=ProfitDoctorSQLiteConnection)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA busy_timeout=5000')
    if not existed_with_schema:
        _schema_template().backup(con)
        con.commit()
    else:
        # Existing databases may predate the latest schema; idempotent migration bootstrap.
        for schema in ALL_SCHEMAS:
            con.executescript(schema)
    return con

# v2.40 D15 CRM / Pipeline / Win-Loss canonical domain.
CRM_SCHEMA = r'''
CREATE TABLE IF NOT EXISTS crm_opportunity (
 opportunity_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id),
 source_opportunity_key TEXT NOT NULL, opportunity_name TEXT NOT NULL, customer_entity_id TEXT,
 owner_key TEXT, created_date TEXT NOT NULL, expected_close_date TEXT, actual_close_date TEXT,
 stage TEXT NOT NULL, status TEXT NOT NULL, amount TEXT, currency TEXT NOT NULL DEFAULT 'GBP',
 probability_pct TEXT, lost_reason TEXT, source_system TEXT, evidence_note TEXT,
 UNIQUE(client_id,source_opportunity_key)
);
CREATE TABLE IF NOT EXISTS crm_stage_history (
 stage_history_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id), opportunity_id TEXT NOT NULL REFERENCES crm_opportunity(opportunity_id),
 changed_at TEXT NOT NULL, from_stage TEXT, to_stage TEXT NOT NULL, evidence_note TEXT
);
CREATE TABLE IF NOT EXISTS crm_activity (
 activity_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES client(client_id), opportunity_id TEXT NOT NULL REFERENCES crm_opportunity(opportunity_id),
 activity_date TEXT NOT NULL, activity_type TEXT NOT NULL, outcome TEXT, evidence_note TEXT
);
CREATE TABLE IF NOT EXISTS crm_analysis_result (
 analysis_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, client_id TEXT NOT NULL,
 metric_code TEXT NOT NULL, dimension_type TEXT, dimension_key TEXT, observed_value TEXT, unit TEXT NOT NULL,
 evidence_summary TEXT NOT NULL, limitation TEXT, calculated_at TEXT NOT NULL
);
'''
# Extend the canonical schema bundle and rebuild the shared template lazily.
ALL_SCHEMAS = ALL_SCHEMAS + (CRM_SCHEMA,)
if _SCHEMA_TEMPLATE is not None:
    _SCHEMA_TEMPLATE.close(); _SCHEMA_TEMPLATE = None
