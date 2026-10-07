"""Narrow registered AR semantic views; raw source identities are never rewritten.

This checkpoint does not persist views or admit them to the temporal kernel.
The owner service revalidates retained production evidence before constructing a
view. Dataset comparability remains owned by the frozen v2.53 comparator.
"""
import csv
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from sqlalchemy import select

from profit_doctor.ingestion.northstar import sha256
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.dataset.contracts import DatasetAssertion, DatasetContract, DatasetCoverage
from profit_doctor.reasoning.domain.contracts import Contract, Identifier, LineageReference
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.receivables.contracts import Snapshot
from .absence import ARScope
from .reconciliation import exact_sum
from .semantics import RegisteredSemanticSource
from .service import ProductionEvidenceService


PROJECTION_DOMAIN = 'DERIVED_AR_SEMANTIC_VIEW_V255'
AR_FAMILY = 'ELIGIBLE_OPEN_RECEIVABLES_V255'


class ARSemanticEvidence(Contract):
    """Source-issued definition, not a caller's VERIFIED/comparable answer flag."""
    schema_version: Literal['AR-SEMANTIC-EVIDENCE-2.55.1'] = 'AR-SEMANTIC-EVIDENCE-2.55.1'
    scope: ARScope
    record_version_id: Identifier
    manifest_version_id: Identifier
    control_version_id: Identifier
    system_id: Identifier
    report_id: Identifier
    owner_kind: Literal['CASH_TRAPPED_IMPACT', 'ABSENT_VERIFIED']
    owner_id: Identifier
    population_definition: str = Field(min_length=1)
    inclusion_exclusion: str = Field(min_length=1)
    definition_reference: str = Field(min_length=1)
    family: Literal['OPEN_RECEIVABLES', 'UNKNOWN'] = 'UNKNOWN'
    balance_basis: Literal['OUTSTANDING_BALANCE', 'UNKNOWN'] = 'UNKNOWN'
    contractual_basis: Literal['CONTRACTUAL_DUE_DATE', 'UNKNOWN'] = 'UNKNOWN'
    time_basis: Literal['POINT_IN_TIME_STOCK', 'UNKNOWN'] = 'UNKNOWN'
    unit: Literal['MONEY', 'UNKNOWN'] = 'UNKNOWN'
    # Human declarations stay distinct and may contradict authenticated evidence.
    declarations: dict[str, str] = Field(default_factory=dict)
    revision: int = Field(default=1, strict=True, ge=1)
    predecessor_semantic_version_id: Identifier | None = None
    change_kind: Literal['ORIGINAL','CORRECTION','RESTATEMENT','SUPERSESSION','UNKNOWN'] = 'ORIGINAL'
    change_reference: str | None = None


class ARSemanticProjection(Contract):
    schema_version: Literal['AR-SEMANTIC-PROJECTION-2.55.1'] = 'AR-SEMANTIC-PROJECTION-2.55.1'
    projection_id: Identifier
    series_id: Identifier
    revision: int = Field(strict=True, ge=1)
    supersedes: Identifier | None = None
    status: Literal['QUALIFIED'] = 'QUALIFIED'
    client_id: Identifier
    run_id: Identifier
    owner_kind: Literal['CASH_TRAPPED_IMPACT', 'ABSENT_VERIFIED']
    owner_id: Identifier
    semantic_version_id: Identifier
    original_domain: str
    original_route: str
    original_refs: tuple[LineageReference, ...]
    manifest_version_id: Identifier
    control_version_id: Identifier
    evidence: ARSemanticEvidence
    contract: DatasetContract
    lineage: tuple[LineageReference, ...]
    limitations: tuple[str, ...] = (
        'Derived semantic comparability is not identical physical-source provenance.',
        'No Impact calculation, absence calculation or temporal admission is performed.',
        'No source-route equivalence is inferred without authenticated semantic evidence.',)

    @model_validator(mode='after')
    def envelope(self):
        if (self.client_id, self.run_id, self.projection_id) != (
                self.contract.client_id, self.contract.recorded_run_id, self.contract.contract_id):
            raise ScopeError('AR projection/contract envelope differs')
        if (self.revision,self.supersedes) != (self.contract.revision,self.contract.supersedes) or (
                (self.revision==1)!=(self.supersedes is None)):
            raise RevisionConflict('AR projection revision envelope differs')
        if (self.owner_kind, self.owner_id, self.manifest_version_id, self.control_version_id) != (
                self.evidence.owner_kind, self.evidence.owner_id, self.evidence.manifest_version_id,
                self.evidence.control_version_id):
            raise ScopeError('AR projection/evidence ownership differs')
        if self.evidence.scope.client_id != self.client_id or any(
                r.client_id != self.client_id for r in (*self.original_refs, *self.lineage)):
            raise ScopeError('AR projection lineage is foreign')
        if self.original_refs != (self.contract.source_dataset, self.contract.source_version, self.contract.source_file):
            raise ScopeError('AR projection must retain exact original source identities')
        if self.contract.source_data_domain != PROJECTION_DOMAIN or self.contract.family.verified_value != AR_FAMILY:
            raise ValueError('Only the governed derived AR semantic view is eligible')
        if self.original_domain == PROJECTION_DOMAIN or not self.original_domain or not self.original_route:
            raise ValueError('Original source domain/route must remain explicit')
        if any(r not in self.lineage for r in self.original_refs) or not self.lineage:
            raise ValueError('Original source lineage must remain in the derived view')
        if any(c.verified_value is None for c in self.contract.claims()):
            raise ValueError('Incomplete evidence cannot form a qualified AR semantic view')
        return self


class ARSemanticVerifier:
    """Registered owner/version IDs only. No supplied values or prior projections.

    Until durable history exists, same-date replacement claims deliberately refuse.
    This class is not yet wired into production temporal admission.
    """
    def __init__(self, production, *, impacts=None):
        if not isinstance(production, ProductionEvidenceService):
            raise ScopeError('Registered production evidence service required')
        self.production = production
        self.sources = RegisteredSemanticSource(production.connection, production.client_id,
                                               production.authority_resolver)
        self.impacts = impacts
        if impacts is not None:
            from profit_doctor.reasoning.impact.service import ImpactService
            if not isinstance(impacts, ImpactService) or impacts.session is not production.session or (
                    impacts.client_id, impacts.run_id) != (production.client_id, production.run_id):
                raise ScopeError('AR Impact provider must share caller client/run/session')

    def _evidence(self, version, *, require_authority=True):
        profile = 'production-evidence:ar-semantics-1'
        meta = self.sources.metadata(version, profile)
        with Path(meta['storage_location']).open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ['evidence']:
                raise ValueError('Exact registered evidence column required')
            rows = list(reader)
        if len(rows) != 1 or meta['row_count'] != 1 or set(rows[0]) != {'evidence'}:
            raise ValueError('Exactly one AR semantic evidence document required')
        evidence = ARSemanticEvidence.from_json(rows[0]['evidence'])
        if evidence.scope.client_id != self.production.client_id:
            raise ScopeError('Foreign AR semantic evidence')
        if sha256(Path(meta['storage_location'])) != meta['file_hash']:
            raise RevisionConflict('AR semantic evidence changed during read')
        if require_authority and self.sources.authority_resolver(self.production.client_id, version, profile, meta['file_hash']) != 'SOURCE_DATA':
            raise ScopeError('Authenticated source semantic authority required')
        return evidence, meta

    def verify(self, semantic_version_id):
        return self._verify(semantic_version_id)

    def _verify(self, semantic_version_id, *, previous=None, historical=False):
        if not isinstance(semantic_version_id, str) or not semantic_version_id:
            raise TypeError('Registered semantic version identity required')
        evidence, semantic_meta = self._evidence(semantic_version_id)
        p = self.production
        manifest, mm, ma = p.absence._document(evidence.manifest_version_id, 'ar-manifest')
        control, cm, ca = p.absence._document(evidence.control_version_id, 'ar-control')
        if (ma, ca) != ('SOURCE_DATA', 'SOURCE_DATA'):
            raise ScopeError('AR manifest/control source authority insufficient')
        if not (evidence.scope == manifest.scope == control.scope):
            raise ScopeError('AR semantic manifest/control scopes differ')
        if (manifest.record_version_id, manifest.system_id, manifest.report_id) != (
                evidence.record_version_id, evidence.system_id, evidence.report_id):
            raise ScopeError('Semantic evidence does not identify its registered manifest population')
        if evidence.owner_kind == 'ABSENT_VERIFIED':
            owner = p.get_absence(evidence.owner_id, current=not historical)
            if historical:
                prior_owner = p.get_absence(owner.supersedes) if owner.supersedes else None
                reproduced=p.absence.assess(*owner.source_versions,previous=prior_owner,zero_version=owner.zero_source_version_id)
                if reproduced!=owner:
                    raise RevisionConflict('Historical AR absence source no longer verifies')
            if owner.outcome != 'ABSENT_VERIFIED' or owner.scope != evidence.scope or owner.source_versions != (
                    evidence.record_version_id, evidence.manifest_version_id, evidence.control_version_id):
                raise ScopeError('Semantic evidence does not bind qualified absence source population')
            export, meta, authority = p.absence._document(evidence.record_version_id, 'ar-export')
            if authority != 'SOURCE_DATA':
                raise ScopeError('AR export authority insufficient')
            invoices, total = export.invoices, owner.total
        else:
            if self.impacts is None or self.impacts.receivables is None:
                raise ScopeError('Registered qualified receivables Impact provider required')
            from profit_doctor.persistence import impact_schema
            candidate = p.session.scalar(select(impact_schema.impact.c.candidate_id).where(
                impact_schema.impact.c.impact_id == evidence.owner_id,
                impact_schema.impact.c.client_id == p.client_id))
            if candidate is None:
                raise ScopeError('Qualified AR Impact owner missing or foreign')
            q = self.impacts.get(candidate, current=not historical)
            if q.outcome != 'QUALIFIED_IMPACT' or q.category != 'CASH_TRAPPED' or q.source.kind != 'RECEIVABLES':
                raise ScopeError('Only qualified production CASH_TRAPPED presence is eligible')
            if q.impact is None or q.impact.impact_id != evidence.owner_id:
                raise RevisionConflict('AR presence Impact has been superseded')
            snapshot = Snapshot.from_json(q.source_document)
            retained = self.impacts.receivables.get(snapshot.snapshot_id)
            if snapshot != retained or snapshot.origin != 'REAL_SOURCE' or snapshot.coverage != 'COMPLETE':
                raise ScopeError('Synthetic/partial/stale AR presence is ineligible')
            if (snapshot.client_id, snapshot.entity, snapshot.ledger_id, snapshot.as_of, snapshot.currency, snapshot.scope) != (
                    evidence.scope.client_id, evidence.scope.entity_id, evidence.scope.ledger_id,
                    evidence.scope.as_of, evidence.scope.currency, evidence.scope.population):
                raise ScopeError('AR presence semantic scope differs')
            if snapshot.dataset_version_id != evidence.record_version_id or snapshot.control_amount != control.amount:
                raise ScopeError('AR presence source/control binding differs')
            meta = dict(self.impacts.receivables.contexts.source.dataset(evidence.record_version_id))
            registration = p.connection.execute('''SELECT d.data_domain, j.status, j.client_id AS job_client,
                r.client_id AS run_client FROM dataset_version v JOIN dataset d ON d.dataset_id=v.dataset_id
                JOIN ingestion_job j ON j.ingestion_job_id=v.ingestion_job_id JOIN engine_run r ON r.run_id=j.run_id
                WHERE v.dataset_version_id=?''', (evidence.record_version_id,)).fetchone()
            if registration is None or registration['status'] != 'COMPLETED' or (
                    registration['job_client'], registration['run_client']) != (p.client_id, p.client_id):
                raise ScopeError('AR snapshot registration ownership incomplete')
            meta['data_domain'] = registration['data_domain']
            if meta['data_domain'] != 'D04_AR_SNAPSHOT':
                raise ScopeError('Unsupported production presence transport')
            authority = self.sources.authority_resolver(p.client_id, evidence.record_version_id,
                meta['logical_dataset_key'], meta['file_hash'])
            if authority != 'SOURCE_DATA':
                raise ScopeError('AR snapshot authority insufficient')
            invoices, total = snapshot.invoices, snapshot.total
        if evidence.family != 'OPEN_RECEIVABLES' or evidence.balance_basis != 'OUTSTANDING_BALANCE' or (
                evidence.contractual_basis != 'CONTRACTUAL_DUE_DATE' or evidence.time_basis != 'POINT_IN_TIME_STOCK'
                or evidence.unit != 'MONEY'):
            raise ScopeError('AR definition/family/time/unit insufficient')
        if manifest.open_items is None or set(manifest.open_items) != {(i.customer_id, i.invoice_id) for i in invoices} or manifest.excluded_items:
            raise ScopeError('Complete AR membership not proven')
        if manifest.extraction_boundary != evidence.scope.population or manifest.extraction_as_of != evidence.scope.as_of:
            raise ScopeError('AR extraction boundary/date differs')
        if control.basis != 'AR_OPEN_ITEM_CONTROL' or total != control.amount or exact_sum(i.outstanding for i in invoices) != total:
            raise ScopeError('AR control reconciliation not established')
        if meta['file_hash'] == cm['file_hash']:
            raise ScopeError('Independent source-supported AR control required')
        if previous:
            if previous.client_id!=p.client_id or previous.evidence.scope!=evidence.scope or previous.evidence.system_id!=evidence.system_id:
                raise ScopeError('AR projection predecessor has different economic scope')
            if evidence.revision!=previous.revision+1 or evidence.predecessor_semantic_version_id!=previous.semantic_version_id or (
                    evidence.change_kind not in ('CORRECTION','RESTATEMENT','SUPERSESSION') or not evidence.change_reference):
                raise RevisionConflict('Explicit source-supported semantic revision authority required')
            original_version=previous.original_refs[1].source_id
            if manifest.record_version_id!=original_version and (manifest.predecessor_version_id!=original_version or
                    manifest.change_kind not in ('CORRECTION','RESTATEMENT','SUPERSESSION') or not manifest.change_reference):
                raise RevisionConflict('Explicit source-supported AR population replacement required')
        elif manifest.change_kind != 'ORIGINAL' or not manifest.change_reference or manifest.predecessor_version_id or (
                evidence.revision!=1 or evidence.predecessor_semantic_version_id or evidence.change_kind!='ORIGINAL'):
            raise RevisionConflict('AR projection replacement requires durable verified revision history')
        # Never select one competing original snapshot by timestamp or row order.
        roots = set()
        rows = p.connection.execute('''SELECT v.dataset_version_id FROM dataset_version v JOIN dataset d
            ON d.dataset_id=v.dataset_id WHERE d.client_id=? AND d.logical_dataset_key=? AND v.ingestion_status='COMPLETED' ''',
            (p.client_id, 'production-evidence:ar-manifest-1')).fetchall()
        for (version,) in rows:
            candidate, _, _ = p.absence._document(version, 'ar-manifest')
            if candidate.scope == manifest.scope and candidate.system_id == manifest.system_id and candidate.predecessor_version_id is None:
                roots.add(candidate.record_version_id)
        root_version=previous.original_refs[1].source_id if previous else evidence.record_version_id
        if previous:
            # Resolve raw source ancestry, not semantic timestamps. The service
            # supplies the immutable predecessor chain; source roots remain one.
            root_version=None
            for (version,) in rows:
                candidate,_,_=p.absence._document(version,'ar-manifest')
                if candidate.scope==manifest.scope and candidate.system_id==manifest.system_id and candidate.predecessor_version_id is None:
                    root_version=candidate.record_version_id
        if len(roots)!=1 or roots!={root_version}:
            raise RevisionConflict('AR same-date source authority unresolved')
        original = self.sources.refs(evidence.record_version_id, meta)
        refs = tuple(dict.fromkeys((*original, *self.sources.refs(evidence.manifest_version_id, mm),
            *self.sources.refs(evidence.control_version_id, cm), *self.sources.refs(semantic_version_id, semantic_meta),
            *(owner.lineage if evidence.owner_kind=='ABSENT_VERIFIED' else ()))))
        def claim(value):
            return DatasetAssertion(verified_value=value, verification_authority='SOURCE_DATA', verification_evidence=refs)
        period = {'start': evidence.scope.as_of, 'end': evidence.scope.as_of, 'basis': 'POINT_IN_TIME', 'nature': 'STOCK'}
        values = dict(family=AR_FAMILY, population=evidence.population_definition,
            inclusion_exclusion=evidence.inclusion_exclusion,
            coverage=DatasetCoverage(period=period, completeness='COMPLETE', coverage_basis='AUTHENTICATED_AR_MANIFEST_AND_CONTROL_V255').model_dump(mode='json'),
            definition={'reference': evidence.definition_reference, 'balance': evidence.balance_basis,
                'due_basis': evidence.contractual_basis, 'condition': 'FROZEN_CASH_TRAPPED_QUALIFICATION'},
            organisational_scope={'entity': evidence.scope.entity_id, 'ledger': evidence.scope.ledger_id},
            currency=evidence.scope.currency, unit=evidence.unit, time_basis=evidence.time_basis,
            source_provider={'semantic_view': 'AR-SEMANTIC-PROJECTION-2.55.1', 'system': evidence.system_id},
            revision_relationship=evidence.change_kind if previous else 'NEW_OBSERVATION')
        for key, declared in evidence.declarations.items():
            if key not in values or declared != values[key]:
                raise ScopeError('AR source evidence contradicts declaration: '+key)
        digest = hashlib.sha256((evidence.to_json()+manifest.to_json()+control.to_json()+meta['file_hash']).encode()).hexdigest()
        identifier = identity('ar-semantic-projection-2.55.1', p.client_id, evidence.owner_kind,
            evidence.owner_id, semantic_version_id, digest)
        created = p.connection.execute('SELECT started_at FROM ingestion_job WHERE ingestion_job_id=?',
                                      (semantic_meta['ingestion_job_id'],)).fetchone()[0]
        contract = DatasetContract(contract_id=identifier, client_id=p.client_id, recorded_run_id=p.run_id,
            source_dataset=original[0], source_version=original[1], source_file=original[2],
            source_file_sha256=meta['file_hash'], source_capture_id=meta['ingestion_job_id'],
            logical_dataset_key=meta['logical_dataset_key'], source_data_domain=PROJECTION_DOMAIN,
            source_digest=digest, revision=previous.revision+1 if previous else 1,
            supersedes=previous.projection_id if previous else None,
            revision_target_contract_id=previous.projection_id if previous else None, observed_row_count=len(invoices),
            observed_period_from=evidence.scope.as_of.isoformat(), observed_period_to=evidence.scope.as_of.isoformat(),
            created_at=datetime.fromisoformat(created), **{key: claim(value) for key, value in values.items()})
        return ARSemanticProjection(projection_id=identifier,
            series_id=identity('ar-semantic-series-v255',p.client_id,evidence.scope.to_json(),evidence.system_id),
            revision=contract.revision,supersedes=contract.supersedes, client_id=p.client_id, run_id=p.run_id,
            owner_kind=evidence.owner_kind, owner_id=evidence.owner_id, semantic_version_id=semantic_version_id,
            original_domain=meta['data_domain'], original_route=meta['logical_dataset_key'], original_refs=original,
            manifest_version_id=evidence.manifest_version_id, control_version_id=evidence.control_version_id,
            evidence=evidence, contract=contract, lineage=refs)
