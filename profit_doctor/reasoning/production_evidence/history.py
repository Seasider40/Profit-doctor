"""Caller-owned, append-only production ownership; no service commits or closes."""
from sqlalchemy import insert, select
from contextlib import contextmanager
from typing import Literal
from pydantic import Field, model_validator

from profit_doctor.persistence import production_history_schema as tables, dataset_schema
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import AuditEvent, Contract, Identifier, LineageReference
from profit_doctor.reasoning.domain.service import FoundationService, ScopeError, RevisionConflict
from .ar_semantics import ARSemanticProjection, ARSemanticVerifier
from .absence import ARScope


class ProductionHistory:
    def __init__(self, production):
        self.production=production
        self.session,self.client_id,self.run_id=production.session,production.client_id,production.run_id

    def latest_id(self, table, key, series):
        return self.session.scalar(select(table.c[key]).where(table.c.client_id==self.client_id,
            table.c.series_id==series).order_by(table.c.revision.desc()).limit(1))

    def load(self, table, key, identifier, model):
        row=self.session.execute(select(table).where(table.c[key]==identifier,
            table.c.client_id==self.client_id)).mappings().one_or_none()
        if row is None:raise ScopeError('Production history missing or foreign')
        value=model.from_json(row['document'])
        if (getattr(value,key),value.series_id,value.client_id,value.run_id,value.revision,value.supersedes)!= (
                row[key],row['series_id'],row['client_id'],row['run_id'],row['revision'],row['supersedes']):
            raise ScopeError('Production history indexed envelope differs')
        FoundationService(self.session,self.client_id,self.production.actor)._run(value.run_id)
        return value,row

    def persist(self, table, key, value, **relationships):
        FoundationService(self.session,self.client_id,self.production.actor)._run(value.run_id)
        if value.client_id!=self.client_id:raise ScopeError('Foreign production history')
        previous=self.latest_id(table,key,value.series_id)
        if previous!=value.supersedes:raise RevisionConflict('Production history predecessor changed')
        self.session.execute(insert(table).values(**{key:getattr(value,key)},series_id=value.series_id,
            client_id=value.client_id,run_id=value.run_id,revision=value.revision,supersedes=value.supersedes,
            document=value.to_json(),**relationships))
        event=AuditEvent(event_id=identity('production-history-audit-v255',getattr(value,key)),
            object_id=getattr(value,key),client_id=self.client_id,run_id=value.run_id,actor=self.production.actor,
            event_type='OBJECT_SUPERSEDED' if value.supersedes else 'OBJECT_CREATED',
            previous={'predecessor':value.supersedes} if value.supersedes else None,
            new={'owner':getattr(value,key),'revision':value.revision},lineage=value.lineage,
            rationale={'boundary':'Separately owned production evidence; no downstream publication'})
        self.session.execute(insert(tables.audit).values(event_id=event.event_id,client_id=self.client_id,
            created_at=event.created_at.isoformat(),document=event.to_json(),**{key:getattr(value,key)}))

    @contextmanager
    def atomic(self):
        connection=self.session.connection()
        if connection.dialect.name=='sqlite' and not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql('BEGIN')
        with self.session.begin_nested():yield


class ARProjectionService(ProductionHistory):
    """Persist source-derived semantic views in the existing Dataset Contract store."""
    def __init__(self, verifier):
        if not isinstance(verifier,ARSemanticVerifier):raise ScopeError('Registered AR verifier required')
        super().__init__(verifier.production)
        self.verifier=verifier

    def capture(self, semantic_version_id):
        evidence,_=self.verifier._evidence(semantic_version_id)
        series=identity('ar-semantic-series-v255',self.client_id,evidence.scope.to_json(),evidence.system_id)
        old_id=self.latest_id(tables.projection,'projection_id',series)
        old=self.get(old_id) if old_id else None
        if old and old.semantic_version_id==semantic_version_id:
            return self.get(old_id,current=True)
        value=self.verifier._verify(semantic_version_id,previous=old)
        with self.atomic():
            self.session.execute(insert(dataset_schema.dataset_contract).values(contract_id=value.projection_id,
                client_id=self.client_id,run_id=value.run_id,source_version_id=value.contract.source_version.source_id,
                contract_role='AR_SEMANTIC_PROJECTION',revision=value.revision,supersedes=value.supersedes,
                document=value.contract.to_json()))
            self.persist(tables.projection,'projection_id',value,contract_id=value.projection_id,
                impact_id=value.owner_id if value.owner_kind=='CASH_TRAPPED_IMPACT' else None,
                absence_id=value.owner_id if value.owner_kind=='ABSENT_VERIFIED' else None)
        return value


    def get(self, projection_id, *, current=False):
        value,row=self.load(tables.projection,'projection_id',projection_id,ARSemanticProjection)
        if (row['contract_id'],row['impact_id'],row['absence_id']) != (value.projection_id,
                value.owner_id if value.owner_kind=='CASH_TRAPPED_IMPACT' else None,
                value.owner_id if value.owner_kind=='ABSENT_VERIFIED' else None):
            raise ScopeError('AR projection indexed relationships differ')
        contract=self.session.execute(select(dataset_schema.dataset_contract).where(
            dataset_schema.dataset_contract.c.contract_id==value.projection_id,
            dataset_schema.dataset_contract.c.client_id==self.client_id)).mappings().one_or_none()
        if contract is None or (contract['document'],contract['contract_role'],contract['source_version_id'],contract['revision'],contract['supersedes']) != (
                value.contract.to_json(),'AR_SEMANTIC_PROJECTION',value.contract.source_version.source_id,value.revision,value.supersedes):
            raise ScopeError('AR projection Dataset Contract differs from its authoritative store')
        if current:
            if self.latest_id(tables.projection,'projection_id',value.series_id)!=projection_id:
                raise RevisionConflict('Superseded AR projection is historical')
            previous=self.get(value.supersedes) if value.supersedes else None
            reproduced=self.verifier._verify(value.semantic_version_id,previous=previous)
            if reproduced!=value:raise RevisionConflict('Current AR projection source/semantics changed')
        return value


class UnknownObservation(Contract):
    schema_version: Literal['PRODUCTION-UNKNOWN-2.55.1']='PRODUCTION-UNKNOWN-2.55.1'
    unknown_id: Identifier
    series_id: Identifier
    client_id: Identifier
    run_id: Identifier
    revision: int=Field(strict=True,ge=1)
    supersedes: Identifier|None=None
    scope: ARScope
    attempted_family: Literal['CASH_TRAPPED_RECEIVABLES']='CASH_TRAPPED_RECEIVABLES'
    semantic_version_id: Identifier
    attempted_owner_id: Identifier
    reasons: tuple[str,...]=Field(min_length=1)
    missing_prerequisites: tuple[str,...]=Field(min_length=1)
    lineage: tuple[LineageReference,...]=Field(min_length=1)
    limitations: tuple[str,...]=('Refusal evidence is not an Impact, amount or absence conclusion.',)

    @model_validator(mode='after')
    def scoped(self):
        if self.scope.client_id!=self.client_id or any(r.client_id!=self.client_id for r in self.lineage):
            raise ScopeError('Unknown observation evidence is foreign')
        if (self.revision==1)!=(self.supersedes is None):
            raise RevisionConflict('Unknown revision requires its predecessor')
        return self


class UnknownObservationService(ProductionHistory):
    """A receipt derived from a failed registered qualification, never a caller state."""
    def __init__(self, projections):
        if not isinstance(projections,ARProjectionService):raise ScopeError('Registered projection owner required')
        super().__init__(projections.production)
        self.projections=projections

    def capture(self, semantic_version_id):
        return self._capture(semantic_version_id,write=True)

    def _capture(self, semantic_version_id, *, write):
        evidence,meta=self.projections.verifier._evidence(semantic_version_id,require_authority=False)
        # Failed owned absence qualification is a legitimate retained source of
        # UNKNOWN. Missing/foreign owners cannot be supplied as a substitute.
        if evidence.owner_kind!='ABSENT_VERIFIED':
            raise ScopeError('Unknown production owner requires an existing scoped refusal assessment')
        owner=self.production.get_absence(evidence.owner_id,current=True)
        if owner.scope!=evidence.scope or owner.source_versions!=(evidence.record_version_id,
                evidence.manifest_version_id,evidence.control_version_id):
            raise ScopeError('Unknown refusal does not own the requested source population')
        try:
            series_projection=identity('ar-semantic-series-v255',self.client_id,evidence.scope.to_json(),evidence.system_id)
            projection_id=self.latest_id(tables.projection,'projection_id',series_projection)
            projection=self.projections.get(projection_id) if projection_id else None
            predecessor=(self.projections.get(projection.supersedes) if projection and projection.supersedes else None
                ) if projection and projection.semantic_version_id==semantic_version_id else projection
            self.projections.verifier._verify(semantic_version_id,previous=predecessor)
        except (ScopeError,RevisionConflict) as error:
            reason=str(error)
        else:raise ValueError('Qualified projection cannot be relabelled UNKNOWN')
        series=identity('production-unknown-series-v255',self.client_id,evidence.scope.to_json(),evidence.system_id)
        previous_id=self.latest_id(tables.unknown,'unknown_id',series)
        previous=self.get(previous_id) if previous_id else None
        refs=tuple(dict.fromkeys((*owner.lineage,*self.projections.verifier.sources.refs(semantic_version_id,meta))))
        digest=identity('production-unknown-basis-v255',semantic_version_id,meta['file_hash'],owner.to_json(),reason)
        if previous and previous.unknown_id==identity('production-unknown-v255',series,digest):return previous
        value=UnknownObservation(unknown_id=identity('production-unknown-v255',series,digest),series_id=series,
            client_id=self.client_id,run_id=self.run_id,revision=previous.revision+1 if previous else 1,
            supersedes=previous_id,scope=evidence.scope,semantic_version_id=semantic_version_id,
            attempted_owner_id=owner.assessment_id,reasons=tuple(dict.fromkeys((*owner.blockers,reason))),
            missing_prerequisites=(reason,),lineage=refs)
        if write:
            with self.atomic():self.persist(tables.unknown,'unknown_id',value)
        return value

    def get(self, unknown_id, *, current=False):
        value,_=self.load(tables.unknown,'unknown_id',unknown_id,UnknownObservation)
        if current:
            if self.latest_id(tables.unknown,'unknown_id',value.series_id)!=unknown_id:
                raise RevisionConflict('Superseded UNKNOWN is historical')
            if self._capture(value.semantic_version_id,write=False)!=value:
                raise RevisionConflict('Unknown refusal basis changed')
        return value
