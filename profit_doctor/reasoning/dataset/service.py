"""Opt-in immutable capture, declaration, comparison and audit service."""
import json

from sqlalchemy import insert, select

from profit_doctor.persistence import dataset_schema as tables
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import Actor, now
from profit_doctor.reasoning.domain.service import FoundationService, RevisionConflict, ScopeError
from profit_doctor.reasoning.domain.vocabulary import SourceAuthority
from .comparability import assess_dataset_comparability
from .contracts import (DatasetAssertion, DatasetComparability, DatasetContract,
    DatasetCoverage, DatasetFamily, DatasetRevisionRelationship, json_value)
from .source import LegacyDatasetSource


DECLARABLE_FIELDS = frozenset({'family', 'population', 'inclusion_exclusion', 'coverage', 'definition',
    'organisational_scope', 'currency', 'unit', 'time_basis', 'revision_relationship', 'source_provider'})
REVISION_ONLY = {DatasetRevisionRelationship.RESTATEMENT.value, DatasetRevisionRelationship.CORRECTION.value,
    DatasetRevisionRelationship.SUPERSESSION.value, DatasetRevisionRelationship.PARTIAL_REPLACEMENT.value}


class DatasetContractService:
    """Caller owns the SQLAlchemy Session, both transactions and legacy connection."""

    def __init__(self, session, client_id, run_id, actor, legacy_connection):
        self.session, self.client_id, self.run_id = session, client_id, run_id
        self.actor = Actor.from_json(actor.to_json())
        self.source = LegacyDatasetSource(legacy_connection, client_id)
        self.foundation = FoundationService(session, client_id, self.actor, self.source.resolve)
        if run_id is None:
            raise ScopeError('Dataset contract operations require a client-scoped run')
        self.foundation._run(run_id)

    @staticmethod
    def _audit(event_type, value, *, actor=None, assessment=None, fields=()):
        subject = value.contract_id if value is not None else assessment.assessment_id
        event_id = identity('dataset-audit-2.53.1', event_type, subject)
        document = {'event_type': event_type, 'actor': actor.model_dump(mode='json') if actor else None,
            'contract_id': value.contract_id if value else None,
            'assessment_id': assessment.assessment_id if assessment else None,
            'fields': sorted(fields), 'supersedes': value.supersedes if value else None}
        return dict(event_id=event_id, client_id=(value.client_id if value else assessment.client_id),
            contract_id=value.contract_id if value else None,
            assessment_id=assessment.assessment_id if assessment else None,
            event_type=event_type, created_at=now().isoformat(),
            document=json.dumps(document, sort_keys=True, separators=(',', ':')))

    def _validate_contract(self, value):
        value = DatasetContract.from_json(value.to_json())
        if value.client_id != self.client_id:
            raise ScopeError('Dataset contract is outside the client scope')
        self.foundation._run(value.recorded_run_id)
        self.foundation._run(self.run_id)
        for ref in (value.source_dataset, value.source_version, value.source_file):
            self.foundation._lineage(ref)
        return value

    def _get_contract(self, contract_id):
        row = self.session.execute(select(tables.dataset_contract).where(
            tables.dataset_contract.c.contract_role == 'RAW',
            tables.dataset_contract.c.contract_id == contract_id,
            tables.dataset_contract.c.client_id == self.client_id)).mappings().one_or_none()
        if row is None:
            raise ScopeError('Dataset contract is missing or foreign')
        value = DatasetContract.from_json(row['document'])
        if (value.contract_id, value.client_id, value.recorded_run_id, value.source_version.source_id,
                value.revision, value.supersedes) != (row['contract_id'], row['client_id'], row['run_id'],
                row['source_version_id'], row['revision'], row['supersedes']):
            raise ScopeError('Dataset contract document disagrees with its indexed envelope')
        return self._validate_contract(value)

    def get_contract(self, contract_id, *, current=False):
        value = self._get_contract(contract_id)
        if current:
            current_source = self.source.capture_sales(value.source_version.source_id)
            if current_source['snapshot_digest'] != value.source_digest:
                raise RevisionConflict('Dataset contract no longer matches its retained source snapshot')
        return value

    def capture_sales(self, dataset_version_id):
        source = self.source.capture_sales(dataset_version_id)
        version_ref = self.source_ref('DATASET_VERSION', 'dataset_version', dataset_version_id)
        dataset_ref = self.source_ref('DATASET', 'dataset', source['dataset_id'])
        file_ref = self.source_ref('SOURCE_FILE', 'source_file', source['source_file_id'])
        existing = self.session.execute(select(tables.dataset_contract).where(
            tables.dataset_contract.c.contract_role == 'RAW',
            tables.dataset_contract.c.client_id == self.client_id,
            tables.dataset_contract.c.source_version_id == dataset_version_id,
            tables.dataset_contract.c.revision == 1)).mappings().one_or_none()
        if existing:
            value = self._get_contract(existing['contract_id'])
            if value.source_digest != source['snapshot_digest']:
                raise RevisionConflict('Dataset version was already captured with a different source snapshot')
            return value
        provider = source['logical_dataset_key'].split(':', 1)[0]
        value = DatasetContract(contract_id=identity('dataset-contract-2.53.1', self.client_id,
                dataset_version_id, 1, source['snapshot_digest']), client_id=self.client_id,
            recorded_run_id=self.run_id, source_dataset=dataset_ref, source_version=version_ref,
            source_file=file_ref, source_file_sha256=source['file_hash'],
            source_capture_id=source['ingestion_job_id'], logical_dataset_key=source['logical_dataset_key'],
            source_data_domain=source['data_domain'], source_digest=source['snapshot_digest'], revision=1,
            family=DatasetAssertion(verified_value=DatasetFamily.SALES_TRANSACTIONS.value,
                verification_authority=SourceAuthority.SYSTEM_DERIVED, verification_evidence=(dataset_ref, version_ref)),
            source_provider=DatasetAssertion(verified_value=provider, verification_authority=SourceAuthority.SYSTEM_DERIVED,
                verification_evidence=(dataset_ref, version_ref)),
            observed_row_count=source['observed_row_count'], observed_period_from=source['observed_period_from'],
            observed_period_to=source['observed_period_to'], created_at=now())
        self._persist_contract(value, 'CONTRACT_CAPTURED')
        return value

    def source_ref(self, kind, resource, source_id):
        from profit_doctor.reasoning.domain.contracts import LineageReference
        from profit_doctor.reasoning.domain.vocabulary import LineageKind
        kind_value = LineageKind(kind)
        return LineageReference(kind=kind_value, store='LEGACY_SQLITE', resource=resource,
            source_id=source_id, client_id=self.client_id)

    def _persist_contract(self, value, event_type, *, actor=None, fields=()):
        self._validate_contract(value)
        self.session.execute(insert(tables.dataset_contract).values(contract_id=value.contract_id,
            client_id=value.client_id, run_id=value.recorded_run_id, source_version_id=value.source_version.source_id,
            revision=value.revision, supersedes=value.supersedes, document=value.to_json()))
        self.session.execute(insert(tables.dataset_audit).values(**self._audit(event_type, value, actor=actor, fields=fields)))
        return value

    def declare(self, contract_id, declarations, *, actor, revision_target_contract_id=None):
        if not isinstance(declarations, dict) or not declarations or set(declarations) - DECLARABLE_FIELDS:
            raise ValueError('Declarations must use explicit governed Dataset Contract dimensions')
        actor = Actor.from_json(actor.to_json())
        if actor.actor_id is None or actor.actor_type.value not in ('HUMAN', 'MANAGEMENT'):
            raise ValueError('Dataset declarations require an identified human or management actor')
        if actor.source_authority not in (SourceAuthority.MANAGEMENT_ASSERTION, SourceAuthority.HUMAN_FD_JUDGEMENT):
            raise ValueError('Declaration authority must remain human-provided')
        previous = self.get_contract(contract_id, current=True)
        latest = self.session.execute(select(tables.dataset_contract).where(
            tables.dataset_contract.c.contract_role == 'RAW',
            tables.dataset_contract.c.client_id == self.client_id,
            tables.dataset_contract.c.source_version_id == previous.source_version.source_id
        ).order_by(tables.dataset_contract.c.revision.desc()).limit(1)).mappings().one()
        normalized = {key: json_value(value) for key, value in declarations.items()}
        if latest['contract_id'] != previous.contract_id:
            current = self._get_contract(latest['contract_id'])
            replay = current.supersedes == previous.contract_id and all(
                getattr(current, key).declared_by == actor and
                getattr(current, key).declared_value == value for key, value in normalized.items())
            if revision_target_contract_id is not None:
                replay = replay and current.revision_target_contract_id == revision_target_contract_id
            if replay:
                return current
            raise RevisionConflict('Only the latest immutable contract revision may be declared')
        target_id = revision_target_contract_id
        if 'revision_relationship' in normalized:
            normalized['revision_relationship'] = str(normalized['revision_relationship'])
            if normalized['revision_relationship'] in REVISION_ONLY and target_id is None:
                raise ValueError('Restatement/correction/replacement requires an explicit prior contract')
            if normalized['revision_relationship'] not in REVISION_ONLY and target_id is not None:
                raise ValueError('Revision target is only valid for an explicit correction or replacement')
            if normalized['revision_relationship'] not in REVISION_ONLY:
                target_id = None
        else:
            target_id = previous.revision_target_contract_id
        if target_id:
            target = self.get_contract(target_id)
            if (target.client_id, target.logical_dataset_key, target.source_data_domain) != (
                    previous.client_id, previous.logical_dataset_key, previous.source_data_domain):
                raise ScopeError('Revision target must be the same client and governed dataset family')
        # Exact replay by the same actor and values returns the current revision.
        replay = all(getattr(previous, key).declared_by == actor and
            getattr(previous, key).declared_value == value for key, value in normalized.items())
        if replay and previous.revision_target_contract_id == target_id:
            return previous
        declared_at = now()
        claims = {}
        for key, value in normalized.items():
            claims[key] = DatasetAssertion(declared_value=value,
                declaration_authority=actor.source_authority, declared_by=actor,
                declared_at=declared_at,
                verified_value=getattr(previous, key).verified_value,
                verification_authority=getattr(previous, key).verification_authority,
                verification_evidence=getattr(previous, key).verification_evidence)
        updated = previous.model_copy(update=claims)
        revision = previous.revision + 1
        created_at = now()
        candidate = updated.model_copy(update=dict(contract_id='pending', recorded_run_id=self.run_id,
            revision=revision, supersedes=previous.contract_id, revision_target_contract_id=target_id,
            created_at=created_at))
        semantic = candidate.model_dump(mode='json', exclude={'contract_id', 'created_at'})
        candidate = candidate.model_copy(update={'contract_id': identity('dataset-contract-2.53.1',
            self.client_id, candidate.source_version.source_id, revision, semantic)})
        candidate = DatasetContract.from_json(candidate.to_json())
        return self._persist_contract(candidate, 'DECLARATION_RECORDED', actor=actor, fields=normalized)

    def _get_assessment(self, assessment_id):
        row = self.session.execute(select(tables.dataset_comparability).where(
            tables.dataset_comparability.c.assessment_id == assessment_id,
            tables.dataset_comparability.c.client_id == self.client_id)).mappings().one_or_none()
        if row is None:
            raise ScopeError('Dataset comparability assessment is missing or foreign')
        value = DatasetComparability.from_json(row['document'])
        expected = (value.assessment_id, value.client_id, value.run_id, value.left_contract_id,
            value.right_contract_id, value.policy_version, value.outcome.value)
        actual = (row['assessment_id'], row['client_id'], row['run_id'], row['left_contract_id'],
            row['right_contract_id'], row['policy_version'], row['outcome'])
        if expected != actual:
            raise ScopeError('Comparability document disagrees with its indexed envelope')
        return value

    def compare(self, left_contract_id, right_contract_id):
        left = self.get_contract(left_contract_id, current=True)
        right = self.get_contract(right_contract_id, current=True)
        if left.client_id != right.client_id or left.client_id != self.client_id:
            raise ScopeError('Cross-client dataset comparison is prohibited')
        left, right = sorted((left, right), key=lambda c: c.contract_id)
        existing = self.session.execute(select(tables.dataset_comparability).where(
            tables.dataset_comparability.c.client_id == self.client_id,
            tables.dataset_comparability.c.left_contract_id == left.contract_id,
            tables.dataset_comparability.c.right_contract_id == right.contract_id,
            tables.dataset_comparability.c.policy_version == 'DATASET-COMPARABILITY-2.53.1')).mappings().one_or_none()
        if existing:
            return self._get_assessment(existing['assessment_id'])
        result = assess_dataset_comparability(left, right, run_id=self.run_id)
        self.session.execute(insert(tables.dataset_comparability).values(assessment_id=result.assessment_id,
            client_id=result.client_id, run_id=result.run_id, left_contract_id=result.left_contract_id,
            right_contract_id=result.right_contract_id, policy_version=result.policy_version,
            outcome=result.outcome.value, document=result.to_json()))
        self.session.execute(insert(tables.dataset_audit).values(**self._audit('COMPARABILITY_ASSESSED', None, assessment=result)))
        return result

    def audit_events(self, *, contract_id=None, assessment_id=None):
        if (contract_id is None) == (assessment_id is None):
            raise ValueError('Select exactly one dataset contract or assessment')
        if contract_id:
            self.get_contract(contract_id)
            statement = select(tables.dataset_audit).where(tables.dataset_audit.c.contract_id == contract_id,
                tables.dataset_audit.c.client_id == self.client_id)
        else:
            self._get_assessment(assessment_id)
            statement = select(tables.dataset_audit).where(tables.dataset_audit.c.assessment_id == assessment_id,
                tables.dataset_audit.c.client_id == self.client_id)
        return tuple(json.loads(row['document']) for row in self.session.execute(statement.order_by(
            tables.dataset_audit.c.created_at, tables.dataset_audit.c.event_id)).mappings())
