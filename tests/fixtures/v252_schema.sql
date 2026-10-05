-- Frozen v2.52 PostgreSQL-compatible schema represented in SQLite; Alembic 0014.
BEGIN TRANSACTION;
CREATE TABLE action_v2 (
	action_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	decision_id VARCHAR(64) NOT NULL,
	opportunity_id VARCHAR(64) NOT NULL,
	description TEXT NOT NULL,
	status VARCHAR(32) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (action_id),
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(decision_id) REFERENCES decision_v2 (decision_id) ON DELETE RESTRICT,
	FOREIGN KEY(opportunity_id) REFERENCES opportunity_v2 (opportunity_id) ON DELETE RESTRICT
);
CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL,
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO "alembic_version" VALUES('0014_priority_decision');
CREATE TABLE benefit_leg_v2 (
	benefit_leg_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	opportunity_id VARCHAR(64) NOT NULL,
	action_id VARCHAR(64) NOT NULL,
	benefit_type VARCHAR(64) NOT NULL,
	gross_amount VARCHAR(80) NOT NULL,
	implementation_cost VARCHAR(80) NOT NULL,
	ongoing_cost VARCHAR(80) NOT NULL,
	adverse_effect VARCHAR(80) NOT NULL,
	net_amount VARCHAR(80) NOT NULL,
	currency VARCHAR(3) NOT NULL,
	attribution_state VARCHAR(40) NOT NULL,
	status VARCHAR(32) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (benefit_leg_id),
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(opportunity_id) REFERENCES opportunity_v2 (opportunity_id) ON DELETE RESTRICT,
	FOREIGN KEY(action_id) REFERENCES action_v2 (action_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_adviser_decision (
	subject_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	assessment_revision INTEGER NOT NULL,
	request_id VARCHAR(64) NOT NULL,
	choice VARCHAR(24) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (subject_id, revision),
	CONSTRAINT uq_adviser_request UNIQUE (client_id, request_id),
	FOREIGN KEY(subject_id, assessment_revision, client_id) REFERENCES canonical_priority_assessment (subject_id, revision, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_bridge_audit (
	event_id VARCHAR(64) NOT NULL,
	snapshot_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (event_id),
	FOREIGN KEY(snapshot_id, client_id) REFERENCES canonical_bridge_snapshot (snapshot_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_bridge_input (
	snapshot_id VARCHAR(64) NOT NULL,
	binding_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	role VARCHAR(32) NOT NULL,
	PRIMARY KEY (snapshot_id, binding_id),
	FOREIGN KEY(snapshot_id, client_id) REFERENCES canonical_bridge_snapshot (snapshot_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(binding_id, client_id) REFERENCES canonical_measurement_binding (binding_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_bridge_snapshot (
	snapshot_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	series_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	prior_id VARCHAR(64),
	document TEXT NOT NULL,
	PRIMARY KEY (snapshot_id),
	CONSTRAINT uq_bridge_snapshot_client UNIQUE (snapshot_id, client_id),
	CONSTRAINT uq_bridge_series_revision UNIQUE (client_id, series_id, revision),
	FOREIGN KEY(prior_id, client_id) REFERENCES canonical_bridge_snapshot (snapshot_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_collection_evidence (
	evidence_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	impact_id VARCHAR(64) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (evidence_id),
	CONSTRAINT uq_collection_evidence_client UNIQUE (evidence_id, client_id),
	FOREIGN KEY(impact_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(impact_id) REFERENCES canonical_impact (impact_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_fact_v244 (
	object_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (object_id),
	FOREIGN KEY(object_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_finding_v244 (
	object_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (object_id),
	FOREIGN KEY(object_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_hypothesis (
	object_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	finding_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (object_id),
	FOREIGN KEY(object_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(finding_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_impact (
	impact_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	candidate_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	effect_id VARCHAR(64) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (impact_id),
	FOREIGN KEY(impact_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(candidate_id, revision, client_id) REFERENCES canonical_impact_qualification (candidate_id, revision, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(effect_id, client_id) REFERENCES economic_effect_v243 (effect_id, client_id) ON DELETE RESTRICT,
	CONSTRAINT uq_impact_qualification_result UNIQUE (candidate_id, revision)
);
CREATE TABLE canonical_impact_qualification (
	candidate_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	bridge_id VARCHAR(64),
	source_object_id VARCHAR(64),
	document TEXT NOT NULL,
	PRIMARY KEY (candidate_id, revision),
	CONSTRAINT uq_impact_qualification_client UNIQUE (candidate_id, revision, client_id),
	FOREIGN KEY(bridge_id, client_id) REFERENCES canonical_bridge_snapshot (snapshot_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(source_object_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_impact_qualification_audit (
	event_id VARCHAR(64) NOT NULL,
	candidate_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (event_id),
	FOREIGN KEY(candidate_id, revision, client_id) REFERENCES canonical_impact_qualification (candidate_id, revision, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_interpretation_revision (
	object_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	hypothesis_id VARCHAR(64) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (object_id, revision),
	FOREIGN KEY(object_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(hypothesis_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_measurement_audit (
	event_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	context_id VARCHAR(64) NOT NULL,
	binding_id VARCHAR(64),
	created_at VARCHAR(40) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (event_id),
	FOREIGN KEY(context_id, client_id) REFERENCES canonical_measurement_context (context_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(binding_id, client_id) REFERENCES canonical_measurement_binding (binding_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_measurement_binding (
	binding_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	context_id VARCHAR(64) NOT NULL,
	parent_binding_id VARCHAR(64),
	owner_key VARCHAR(255) NOT NULL,
	owner_digest VARCHAR(64) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (binding_id),
	CONSTRAINT uq_measurement_binding_client UNIQUE (binding_id, client_id),
	CONSTRAINT uq_measurement_owner_snapshot UNIQUE (client_id, owner_key, owner_digest),
	FOREIGN KEY(context_id, client_id) REFERENCES canonical_measurement_context (context_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(parent_binding_id, client_id) REFERENCES canonical_measurement_binding (binding_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_measurement_context (
	context_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	supersedes VARCHAR(64),
	document TEXT NOT NULL,
	PRIMARY KEY (context_id),
	CONSTRAINT uq_measurement_context_client UNIQUE (context_id, client_id),
	FOREIGN KEY(supersedes, client_id) REFERENCES canonical_measurement_context (context_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_opportunity (
	opportunity_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	candidate_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (opportunity_id),
	CONSTRAINT uq_opportunity_assessment_result UNIQUE (candidate_id, revision),
	FOREIGN KEY(opportunity_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(candidate_id, revision, client_id) REFERENCES canonical_opportunity_assessment (candidate_id, revision, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_opportunity_assessment (
	candidate_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	evidence_id VARCHAR(64),
	document TEXT NOT NULL,
	PRIMARY KEY (candidate_id, revision),
	CONSTRAINT uq_opportunity_assessment_client UNIQUE (candidate_id, revision, client_id),
	FOREIGN KEY(candidate_id, client_id) REFERENCES canonical_opportunity_candidate (candidate_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(evidence_id, client_id) REFERENCES canonical_collection_evidence (evidence_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_opportunity_audit (
	event_id VARCHAR(64) NOT NULL,
	candidate_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (event_id),
	FOREIGN KEY(candidate_id, client_id) REFERENCES canonical_opportunity_candidate (candidate_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_opportunity_candidate (
	candidate_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	impact_id VARCHAR(64) NOT NULL,
	effect_id VARCHAR(64) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (candidate_id),
	CONSTRAINT uq_opportunity_candidate_client UNIQUE (candidate_id, client_id),
	FOREIGN KEY(candidate_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(impact_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(effect_id, client_id) REFERENCES economic_effect_v243 (effect_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(impact_id) REFERENCES canonical_impact (impact_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_priority_assessment (
	subject_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (subject_id, revision),
	CONSTRAINT uq_priority_assessment_client UNIQUE (subject_id, revision, client_id),
	FOREIGN KEY(subject_id, client_id) REFERENCES canonical_priority_subject (subject_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_priority_audit (
	event_id VARCHAR(64) NOT NULL,
	subject_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (event_id),
	FOREIGN KEY(subject_id, client_id) REFERENCES canonical_priority_subject (subject_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_priority_subject (
	subject_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	source_id VARCHAR(64) NOT NULL,
	source_kind VARCHAR(32) NOT NULL,
	PRIMARY KEY (subject_id),
	CONSTRAINT uq_priority_subject_client UNIQUE (subject_id, client_id),
	CONSTRAINT uq_priority_source UNIQUE (source_id, client_id, source_kind),
	FOREIGN KEY(source_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_receivable_invoice (
	owner_id VARCHAR(64) NOT NULL,
	snapshot_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (owner_id),
	FOREIGN KEY(snapshot_id, client_id) REFERENCES canonical_receivables_snapshot (snapshot_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_receivables_audit (
	event_id VARCHAR(64) NOT NULL,
	snapshot_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (event_id),
	FOREIGN KEY(snapshot_id, client_id) REFERENCES canonical_receivables_snapshot (snapshot_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_receivables_impact_source (
	candidate_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	snapshot_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	PRIMARY KEY (candidate_id, revision),
	FOREIGN KEY(snapshot_id, client_id) REFERENCES canonical_receivables_snapshot (snapshot_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(candidate_id, revision, client_id) REFERENCES canonical_impact_qualification (candidate_id, revision, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_receivables_snapshot (
	snapshot_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	series_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	previous_id VARCHAR(64),
	document TEXT NOT NULL,
	PRIMARY KEY (snapshot_id),
	CONSTRAINT uq_ar_snapshot_client UNIQUE (snapshot_id, client_id),
	CONSTRAINT uq_ar_series_revision UNIQUE (client_id, series_id, revision),
	FOREIGN KEY(previous_id, client_id) REFERENCES canonical_receivables_snapshot (snapshot_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_semantic_revision_v244 (
	revision_id VARCHAR(64) NOT NULL,
	object_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (revision_id),
	FOREIGN KEY(object_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT,
	CONSTRAINT uq_canonical_semantic_revision UNIQUE (object_id, revision)
);
CREATE TABLE canonical_story (
	object_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	finding_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (object_id),
	FOREIGN KEY(object_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(finding_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE canonical_story_revision (
	object_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (object_id, revision),
	FOREIGN KEY(object_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE client (
	client_id VARCHAR(64) NOT NULL,
	client_name VARCHAR(255) NOT NULL,
	base_currency VARCHAR(3) NOT NULL,
	business_model VARCHAR(64),
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (client_id)
);
CREATE TABLE decision_v2 (
	decision_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	opportunity_id VARCHAR(64) NOT NULL,
	selected_course TEXT NOT NULL,
	rationale TEXT NOT NULL,
	status VARCHAR(32) NOT NULL,
	decided_at VARCHAR(40) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (decision_id),
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(opportunity_id) REFERENCES opportunity_v2 (opportunity_id) ON DELETE RESTRICT
);
CREATE TABLE diagnostic_lineage_v2 (
	diagnostic_lineage_id VARCHAR(64) NOT NULL,
	signal_id VARCHAR(64) NOT NULL,
	source_object_type VARCHAR(64) NOT NULL,
	source_object_id VARCHAR(128) NOT NULL,
	relationship_type VARCHAR(64) NOT NULL,
	scope_definition TEXT,
	PRIMARY KEY (diagnostic_lineage_id),
	FOREIGN KEY(signal_id) REFERENCES signal_v2 (signal_id) ON DELETE CASCADE
);
CREATE TABLE economic_effect_v243 (
	effect_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64),
	schema_version VARCHAR(32) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (effect_id),
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	CONSTRAINT uq_rd_effect_client UNIQUE (effect_id, client_id)
);
CREATE TABLE economic_exposure_v2 (
	exposure_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	economic_story_id VARCHAR(64) NOT NULL,
	exposure_type VARCHAR(64) NOT NULL,
	amount VARCHAR(80),
	currency VARCHAR(3) NOT NULL,
	exposure_pathway TEXT NOT NULL,
	evidence_basis TEXT NOT NULL,
	status VARCHAR(32) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (exposure_id),
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(economic_story_id) REFERENCES economic_story_v2 (economic_story_id) ON DELETE RESTRICT
);
CREATE TABLE economic_impact_v2 (
	impact_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	economic_story_id VARCHAR(64) NOT NULL,
	impact_type VARCHAR(64) NOT NULL,
	primary_economic_measure VARCHAR(64) NOT NULL,
	amount VARCHAR(80),
	currency VARCHAR(3) NOT NULL,
	attribution_state VARCHAR(40) NOT NULL,
	calculation_basis TEXT NOT NULL,
	status VARCHAR(32) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (impact_id),
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(economic_story_id) REFERENCES economic_story_v2 (economic_story_id) ON DELETE RESTRICT
);
CREATE TABLE economic_story_v2 (
	economic_story_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	story_key VARCHAR(255) NOT NULL,
	story_type VARCHAR(32) NOT NULL,
	title VARCHAR(255) NOT NULL,
	status VARCHAR(32) NOT NULL,
	first_run_id VARCHAR(64) NOT NULL,
	last_run_id VARCHAR(64) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (economic_story_id),
	CONSTRAINT uq_story_v2_client_key UNIQUE (client_id, story_key),
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(first_run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(last_run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT
);
CREATE TABLE effect_overlap_v243 (
	overlap_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64),
	schema_version VARCHAR(32) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	document TEXT NOT NULL,
	source_effect_id VARCHAR(64) NOT NULL,
	target_effect_id VARCHAR(64) NOT NULL,
	overlap_type VARCHAR(32) NOT NULL,
	pair_key VARCHAR(140) NOT NULL,
	PRIMARY KEY (overlap_id),
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(source_effect_id, client_id) REFERENCES economic_effect_v243 (effect_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(target_effect_id, client_id) REFERENCES economic_effect_v243 (effect_id, client_id) ON DELETE RESTRICT,
	CONSTRAINT uq_rd_effect_overlap_pair UNIQUE (client_id, pair_key)
);
CREATE TABLE effect_reference_v243 (
	reference_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64),
	schema_version VARCHAR(32) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	document TEXT NOT NULL,
	object_id VARCHAR(64) NOT NULL,
	effect_id VARCHAR(64) NOT NULL,
	PRIMARY KEY (reference_id),
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(effect_id, client_id) REFERENCES economic_effect_v243 (effect_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(object_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	CONSTRAINT uq_rd_object_effect UNIQUE (object_id, effect_id)
);
CREATE TABLE engine_run (
	run_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_type VARCHAR(32) NOT NULL,
	started_at VARCHAR(40) NOT NULL,
	completed_at VARCHAR(40),
	status VARCHAR(32) NOT NULL,
	previous_run_id VARCHAR(64),
	baseline_run_id VARCHAR(64),
	engine_version VARCHAR(32) NOT NULL,
	PRIMARY KEY (run_id),
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT
);
CREATE TABLE evidence_graph_record (
	link_id VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	source_id VARCHAR(64) NOT NULL,
	target_id VARCHAR(64) NOT NULL,
	document TEXT NOT NULL,
	PRIMARY KEY (link_id, revision),
	FOREIGN KEY(source_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(target_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(link_id) REFERENCES evidence_link_v243 (link_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT
);
CREATE TABLE evidence_link_v243 (
	link_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64),
	schema_version VARCHAR(32) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	document TEXT NOT NULL,
	source_id VARCHAR(64) NOT NULL,
	target_id VARCHAR(64) NOT NULL,
	relationship_type VARCHAR(32) NOT NULL,
	PRIMARY KEY (link_id),
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(source_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(target_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT
);
CREATE TABLE finding_v2 (
	finding_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	finding_type VARCHAR(32) NOT NULL,
	title VARCHAR(255) NOT NULL,
	status VARCHAR(32) NOT NULL,
	first_run_id VARCHAR(64) NOT NULL,
	last_run_id VARCHAR(64) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (finding_id),
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(first_run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(last_run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT
);
CREATE TABLE opportunity_candidate_v2 (
	opportunity_candidate_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	economic_story_id VARCHAR(64) NOT NULL,
	finding_id VARCHAR(64) NOT NULL,
	mechanism_id VARCHAR(64),
	purpose VARCHAR(32) NOT NULL,
	benefit_type VARCHAR(64) NOT NULL,
	theoretical_amount VARCHAR(80),
	addressable_amount VARCHAR(80),
	expected_amount VARCHAR(80),
	currency VARCHAR(3) NOT NULL,
	availability_state VARCHAR(32) NOT NULL,
	candidate_status VARCHAR(40) NOT NULL,
	limitation TEXT,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (opportunity_candidate_id),
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(economic_story_id) REFERENCES economic_story_v2 (economic_story_id) ON DELETE RESTRICT,
	FOREIGN KEY(finding_id) REFERENCES finding_v2 (finding_id) ON DELETE RESTRICT
);
CREATE TABLE opportunity_relationship_v2 (
	relationship_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	from_opportunity_id VARCHAR(64) NOT NULL,
	to_opportunity_id VARCHAR(64) NOT NULL,
	pair_key VARCHAR(140) NOT NULL,
	relationship_type VARCHAR(32) NOT NULL,
	overlap_amount VARCHAR(80),
	evidence_basis TEXT NOT NULL,
	PRIMARY KEY (relationship_id),
	CONSTRAINT uq_opportunity_relationship_pair UNIQUE (client_id, run_id, pair_key, relationship_type),
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT
);
CREATE TABLE opportunity_v2 (
	opportunity_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	economic_story_id VARCHAR(64) NOT NULL,
	finding_id VARCHAR(64) NOT NULL,
	mechanism_id VARCHAR(64) NOT NULL,
	purpose VARCHAR(32) NOT NULL,
	benefit_type VARCHAR(64) NOT NULL,
	theoretical_amount VARCHAR(80),
	addressable_amount VARCHAR(80) NOT NULL,
	expected_amount VARCHAR(80) NOT NULL,
	currency VARCHAR(3) NOT NULL,
	availability_state VARCHAR(32) NOT NULL,
	status VARCHAR(32) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (opportunity_id),
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(economic_story_id) REFERENCES economic_story_v2 (economic_story_id) ON DELETE RESTRICT,
	FOREIGN KEY(finding_id) REFERENCES finding_v2 (finding_id) ON DELETE RESTRICT
);
CREATE TABLE primitive_result_v2 (
	primitive_result_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	primitive_id VARCHAR(64) NOT NULL,
	method_id VARCHAR(64) NOT NULL,
	numeric_value VARCHAR(80),
	unit VARCHAR(32) NOT NULL,
	result_status VARCHAR(32) NOT NULL,
	calculated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (primitive_result_id),
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT
);
CREATE TABLE reasoning_audit_event_v243 (
	event_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64),
	schema_version VARCHAR(32) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	document TEXT NOT NULL,
	object_id VARCHAR(64),
	effect_id VARCHAR(64),
	event_type VARCHAR(40) NOT NULL,
	PRIMARY KEY (event_id),
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(effect_id, client_id) REFERENCES economic_effect_v243 (effect_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(object_id, client_id) REFERENCES reasoning_object_v243 (object_id, client_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT
);
CREATE TABLE reasoning_object_v243 (
	object_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64),
	schema_version VARCHAR(32) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	document TEXT NOT NULL,
	object_type VARCHAR(32) NOT NULL,
	source_authority VARCHAR(32) NOT NULL,
	revision INTEGER NOT NULL,
	PRIMARY KEY (object_id),
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	CONSTRAINT uq_rd_object_client UNIQUE (object_id, client_id)
);
CREATE TABLE signal_v2 (
	signal_id VARCHAR(64) NOT NULL,
	test_execution_id VARCHAR(64),
	run_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	test_id VARCHAR(32) NOT NULL,
	signal_type VARCHAR(80) NOT NULL,
	entity_type VARCHAR(64),
	entity_id VARCHAR(128),
	period_from VARCHAR(40),
	period_to VARCHAR(40),
	observed_value VARCHAR(80),
	comparison_value VARCHAR(80),
	variance_value VARCHAR(80),
	unit VARCHAR(32),
	materiality_state VARCHAR(32) NOT NULL,
	status VARCHAR(32) NOT NULL,
	evidence_summary TEXT NOT NULL,
	source_primitive_id VARCHAR(64),
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (signal_id),
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT
);
CREATE TABLE test_execution_v2 (
	test_execution_id VARCHAR(64) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	client_id VARCHAR(64) NOT NULL,
	test_id VARCHAR(32) NOT NULL,
	method_id VARCHAR(80),
	eligibility_state VARCHAR(32) NOT NULL,
	execution_status VARCHAR(32) NOT NULL,
	signal_count INTEGER NOT NULL,
	limitation TEXT,
	started_at VARCHAR(40) NOT NULL,
	completed_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (test_execution_id),
	FOREIGN KEY(run_id) REFERENCES engine_run (run_id) ON DELETE RESTRICT,
	FOREIGN KEY(client_id) REFERENCES client (client_id) ON DELETE RESTRICT
);
CREATE INDEX ix_engine_run_client_id ON engine_run (client_id);
CREATE INDEX ix_opportunity_relationship_v2_client_id ON opportunity_relationship_v2 (client_id);
CREATE INDEX ix_opportunity_relationship_v2_run_id ON opportunity_relationship_v2 (run_id);
CREATE INDEX ix_primitive_result_v2_run_id ON primitive_result_v2 (run_id);
CREATE INDEX ix_primitive_result_v2_client_id ON primitive_result_v2 (client_id);
CREATE INDEX ix_signal_v2_test_execution_id ON signal_v2 (test_execution_id);
CREATE INDEX ix_signal_v2_client_id ON signal_v2 (client_id);
CREATE INDEX ix_signal_v2_run_id ON signal_v2 (run_id);
CREATE INDEX ix_finding_v2_client_id ON finding_v2 (client_id);
CREATE INDEX ix_economic_story_v2_client_id ON economic_story_v2 (client_id);
CREATE INDEX ix_test_execution_v2_run_id ON test_execution_v2 (run_id);
CREATE INDEX ix_test_execution_v2_client_id ON test_execution_v2 (client_id);
CREATE INDEX ix_test_execution_v2_test_id ON test_execution_v2 (test_id);
CREATE INDEX ix_diagnostic_lineage_v2_signal_id ON diagnostic_lineage_v2 (signal_id);
COMMIT;
