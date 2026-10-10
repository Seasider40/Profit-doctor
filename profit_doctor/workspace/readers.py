"""Read through existing owners; no source-trust configuration is invented here."""
import hashlib
from pathlib import Path
from profit_doctor.reasoning.domain.service import ScopeError


class OwnedEvidenceReader:
    """Trusted integration adapter, constructed by the host, never from HTTP JSON.

    readiness_factory returns the frozen EvidenceReadinessService for a scoped
    analytical run. scope_resolver returns the evidence-backed Scope for that
    result. Neither callback may create evidence or authenticate a source.
    """
    def __init__(self, legacy, *, readiness_factory=None, scope_resolver=None):
        self.legacy = legacy
        self.readiness_factory, self.scope_resolver = readiness_factory, scope_resolver

    def registration(self, engagement, receipt, version_id):
        row = self.legacy.execute('''SELECT d.client_id, f.client_id AS file_client,
            j.client_id AS job_client, v.ingestion_status, j.status AS job_status,
            f.source_file_id, f.file_hash, f.storage_location, f.immutable_flag
            FROM dataset_version v JOIN dataset d ON d.dataset_id=v.dataset_id
            JOIN source_file f ON f.source_file_id=v.source_file_id
            JOIN ingestion_job j ON j.ingestion_job_id=v.ingestion_job_id
            WHERE v.dataset_version_id=?''', (version_id,)).fetchone()
        if row is None or any(row[x] != engagement.client_id for x in ('client_id', 'file_client', 'job_client')):
            raise ScopeError('Registration missing or foreign')
        if row['ingestion_status'] != 'COMPLETED' or row['job_status'] != 'COMPLETED' or not row['immutable_flag']:
            raise ScopeError('Completed immutable registration required')
        path = Path(row['storage_location'])
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row['file_hash']:
            raise ScopeError('Registered retained bytes absent or changed')
        if row['file_hash'] != receipt.sha256:
            raise ScopeError('Different bytes require an existing qualified transformation lineage adapter; none supplied')
        return {'dataset_version_id': version_id, 'source_file_id': row['source_file_id'],
            'sha256': row['file_hash'], 'relation': 'EXACT_RECEIVED_BYTES',
            'scope_basis': 'CLIENT_REGISTRATION_ONLY_NOT_SEMANTIC_SCOPE', 'authority': 'NOT_ESTABLISHED_BY_REGISTRATION'}

    def readiness(self, engagement, readiness_id, *, current):
        if self.readiness_factory is None or self.scope_resolver is None:
            raise ScopeError('Existing readiness owner and evidence-backed scope resolver required')
        from profit_doctor.reasoning.production_evidence.readiness import EvidenceReadinessService
        owner = self.readiness_factory(engagement.client_id, engagement.run_ids)
        if not isinstance(owner, EvidenceReadinessService):
            raise ScopeError('Frozen governed readiness owner required')
        value = owner.get(readiness_id, current=current)
        if value.client_id != engagement.client_id or value.run_id not in engagement.run_ids:
            raise ScopeError('Readiness does not belong to selected client/run')
        if self.scope_resolver(value) != engagement.scope:
            raise ScopeError('Readiness evidence does not match declared engagement scope')
        return {'assessment': value.model_dump(mode='json'), 'view': 'CURRENT' if current else 'HISTORICAL',
            'limitation': 'Only the explicit scoped selection; no whole-company assurance'}

    def legacy_coverage(self, engagement, run_id):
        if run_id not in engagement.run_ids:
            raise ScopeError('Legacy run not selected by engagement')
        from profit_doctor.api.service import get_product_view_json
        value = get_product_view_json(self.legacy, run_id, engagement.client_id)
        return {'basis': 'LEGACY_DIAGNOSTIC_COVERAGE_NOT_GOVERNED_READINESS', 'run_id': run_id,
            'scope': 'Run/client checked; entity/period semantic equivalence is not established by this projection',
            'performance_diagnostics': value.get('performance_diagnostics'),
            'limitations': value.get('evidence_and_limitations')}


def production_reader(session, connection, operator):
    """Read existing owners with UNKNOWN authority by default; never enrol issuers.

    Current revalidation may refuse previously qualified records when their trust
    dependency is not configured here. Historical records retain their original
    meaning and are visibly historical, not silently accepted as current.
    """
    from .contracts import Scope
    from profit_doctor.reasoning.domain.contracts import Actor
    from profit_doctor.reasoning.production_evidence.service import ProductionEvidenceService
    from profit_doctor.reasoning.production_evidence.assessments import ProductionAssessmentService
    from profit_doctor.reasoning.production_evidence.ar_admission import ARProductionAdmission
    from profit_doctor.reasoning.production_evidence.ar_semantics import ARSemanticVerifier
    from profit_doctor.reasoning.production_evidence.readiness import EvidenceReadinessService
    owners = {}

    def owner(client_id, run_ids):
        if not run_ids:
            raise ScopeError('Explicit existing analytical run required')
        key = (client_id, tuple(run_ids))
        if key not in owners:
            production = ProductionEvidenceService(session, connection, client_id, run_ids[0],
                Actor(actor_type='HUMAN', source_authority='HUMAN_FD_JUDGEMENT', actor_id=operator.actor))
            assessments = ProductionAssessmentService(production, ar=ARProductionAdmission(ARSemanticVerifier(production)))
            owners[key] = EvidenceReadinessService(assessments)
        return owners[key]

    def scopes(readiness, value, kind):
        if kind == 'MONTHLY':
            source = value.semantic.manifest.scope
            return [Scope(entity_id=source.entity_id, ledger_id=source.ledger_id,
                period_start=source.period.start, period_end=source.period.end)]
        if kind == 'MARGIN':
            return scopes(readiness, readiness.production.get_monthly(value.revenue_owner_id), 'MONTHLY')
        if kind == 'TEMPORAL':
            result = []
            for item in value.result.basis.observations:
                if item.source_kind == 'MONTHLY_REVENUE':
                    result.extend(scopes(readiness, readiness.production.get_monthly(item.source_id), 'MONTHLY'))
                elif item.source_kind == 'MONTHLY_C0_MARGIN':
                    result.extend(scopes(readiness, readiness.assessments.monthly.margins.get_margin(item.source_id), 'MARGIN'))
                elif item.source_kind in ('IMPACT', 'ABSENCE'):
                    result.extend(scopes(readiness, readiness.assessments.ar.projections.get(item.observation_id), 'AR_PROJECTION'))
                elif item.source_kind == 'UNKNOWN':
                    result.extend(scopes(readiness, readiness.assessments.ar.unknowns.get(item.source_id), 'UNKNOWN'))
                else:
                    raise ScopeError('Unsupported owned temporal scope')
            if not result or len({(x.entity_id, x.ledger_id) for x in result}) != 1:
                raise ScopeError('Temporal owner has absent or conflicting scope')
            return [Scope(entity_id=result[0].entity_id, ledger_id=result[0].ledger_id,
                period_start=value.result.basis.window.start, period_end=value.result.basis.window.end)]
        source = value.evidence.scope if kind == 'AR_PROJECTION' else value.scope
        return [Scope(entity_id=source.entity_id, ledger_id=source.ledger_id,
            period_start=source.as_of, period_end=source.as_of)]

    def scope(value):
        readiness = next((x for x in owners.values() if x.client_id == value.client_id), None)
        if readiness is None or not value.references:
            raise ScopeError('No owned evidence from which to establish readiness scope')
        parts = []
        for ref in value.references:
            parts.extend(scopes(readiness, readiness._owner(ref, current=False), ref.kind))
        if not parts or len({(x.entity_id, x.ledger_id) for x in parts}) != 1:
            raise ScopeError('Readiness combines absent or conflicting organisational scopes')
        # A display envelope, not a completeness or comparability assertion.
        return Scope(entity_id=parts[0].entity_id, ledger_id=parts[0].ledger_id,
            period_start=min(x.period_start for x in parts), period_end=max(x.period_end for x in parts))

    return OwnedEvidenceReader(connection, readiness_factory=owner, scope_resolver=scope)
