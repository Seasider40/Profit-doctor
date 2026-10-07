"""Positive zero-population proof, separately owned from absence classification."""
from typing import Literal
from pydantic import Field, model_validator

from profit_doctor.persistence import production_history_schema as tables
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import Contract, Identifier, LineageReference, FinancialDecimal
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from .absence import ARScope, ARExport, ARManifest, ARControl, ReceivablesAbsenceService


class ZeroAREvidence(Contract):
    schema_version: Literal['ZERO-AR-SOURCE-2.55.1']='ZERO-AR-SOURCE-2.55.1'
    scope: ARScope
    system_id: Identifier
    report_id: Identifier
    export_version_id: Identifier
    manifest_version_id: Identifier
    control_version_id: Identifier
    extraction_id: Identifier
    extraction_status: Literal['COMPLETED','FAILED','UNKNOWN']='UNKNOWN'
    source_reference: str=Field(min_length=1)
    population_record_count: int=Field(strict=True,ge=0)
    revision: int=Field(strict=True,ge=1,default=1)
    predecessor_source_version_id: Identifier|None=None
    change_kind: Literal['ORIGINAL','CORRECTION','RESTATEMENT','SUPERSESSION','UNKNOWN']='ORIGINAL'
    change_reference: str|None=None


class ZeroARPopulation(Contract):
    schema_version: Literal['ZERO-AR-POPULATION-2.55.1']='ZERO-AR-POPULATION-2.55.1'
    zero_id: Identifier
    series_id: Identifier
    client_id: Identifier
    run_id: Identifier
    status: Literal['ZERO_AR_VERIFIED']='ZERO_AR_VERIFIED'
    revision: int=Field(strict=True,ge=1)
    supersedes: Identifier|None=None
    source_version_id: Identifier
    scope: ARScope
    proof: ZeroAREvidence
    export: ARExport
    manifest: ARManifest
    control: ARControl
    total: FinancialDecimal
    lineage: tuple[LineageReference,...]=Field(min_length=1)
    limitations: tuple[str,...]=('Underlying zero open-AR population; not an Impact or absence-state owner.',)

    @model_validator(mode='after')
    def positive_proof(self):
        if self.total!=0 or self.control.amount!=0 or self.export.invoices or self.export.reviews or self.manifest.open_items!=():
            raise ValueError('Zero AR requires explicit empty complete membership and exact zero control')
        if self.proof.extraction_status!='COMPLETED' or self.proof.population_record_count!=0:
            raise ValueError('Positive completed zero-population extraction evidence required')
        if not (self.scope==self.proof.scope==self.export.scope==self.manifest.scope==self.control.scope):
            raise ScopeError('Zero AR evidence scopes differ')
        if self.client_id!=self.scope.client_id or any(r.client_id!=self.client_id for r in self.lineage):
            raise ScopeError('Foreign zero AR source evidence')
        if (self.revision==1)!=(self.supersedes is None):raise RevisionConflict('Zero AR revision envelope differs')
        return self


class ZeroARSourceQualifier:
    def __init__(self, connection, client_id, run_id, authority_resolver=None):
        self.reader=ReceivablesAbsenceService(connection,client_id,run_id,authority_resolver)
        self.client_id,self.run_id=client_id,run_id

    def qualify(self, source_version_id, *, ancestry=()):
        if source_version_id in ancestry:raise RevisionConflict('Cyclic zero source revision authority')
        proof,pm,pa=self.reader._document(source_version_id,'ar-zero')
        export,em,ea=self.reader._document(proof.export_version_id,'ar-export')
        manifest,mm,ma=self.reader._document(proof.manifest_version_id,'ar-manifest')
        control,cm,ca=self.reader._document(proof.control_version_id,'ar-control')
        if (pa,ea,ma,ca)!=('SOURCE_DATA',)*4:raise ScopeError('Authenticated zero AR source/manifest/control required')
        if not (proof.scope==export.scope==manifest.scope==control.scope):raise ScopeError('Zero AR evidence scope differs')
        if (proof.system_id,proof.report_id,proof.export_version_id)!=(manifest.system_id,manifest.report_id,manifest.record_version_id) or (
                export.system_id,export.report_id)!=(proof.system_id,proof.report_id):
            raise ScopeError('Zero AR proof does not bind its exact source export')
        if proof.extraction_status!='COMPLETED' or proof.population_record_count!=0 or export.invoices or export.reviews or (
                manifest.open_items!=() or manifest.excluded_items or control.amount!=0 or control.basis!='AR_OPEN_ITEM_CONTROL'):
            raise ScopeError('Complete zero AR population/control not proven')
        if manifest.extraction_boundary!=proof.scope.population or manifest.extraction_as_of!=proof.scope.as_of:
            raise ScopeError('Zero AR extraction boundary/reporting date differs')
        if em['file_hash']==cm['file_hash']:raise ScopeError('Independent zero AR control evidence required')
        previous=None
        if proof.revision==1:
            if proof.predecessor_source_version_id or proof.change_kind!='ORIGINAL' or (
                    manifest.change_kind!='ORIGINAL' or not manifest.change_reference or manifest.predecessor_version_id):
                raise RevisionConflict('Zero AR initial source authority differs')
        else:
            if not proof.predecessor_source_version_id or proof.change_kind not in ('CORRECTION','RESTATEMENT','SUPERSESSION') or not proof.change_reference:
                raise RevisionConflict('Zero AR replacement requires explicit authenticated authority')
            previous=self.qualify(proof.predecessor_source_version_id,ancestry=(*ancestry,source_version_id))
            if proof.revision!=previous.revision+1 or proof.scope!=previous.scope or proof.system_id!=previous.proof.system_id:
                raise RevisionConflict('Zero AR revision scope/predecessor differs')
            if proof.export_version_id!=previous.proof.export_version_id and (
                    manifest.predecessor_version_id!=previous.proof.export_version_id or
                    manifest.change_kind!=proof.change_kind or manifest.change_reference!=proof.change_reference):
                raise RevisionConflict('Zero AR source replacement manifest authority differs')
        roots=set()
        rows=self.reader.connection.execute('''SELECT v.dataset_version_id FROM dataset_version v JOIN dataset d
            ON d.dataset_id=v.dataset_id WHERE d.client_id=? AND d.logical_dataset_key=? AND v.ingestion_status='COMPLETED' ''',
            (self.client_id,'production-evidence:ar-manifest-1')).fetchall()
        for (version,) in rows:
            candidate,_,_=self.reader._document(version,'ar-manifest')
            if candidate.scope==proof.scope and candidate.system_id==proof.system_id and candidate.predecessor_version_id is None:
                roots.add(candidate.record_version_id)
        root=previous
        while root and root.proof.predecessor_source_version_id:
            root=self.qualify(root.proof.predecessor_source_version_id,ancestry=(*ancestry,source_version_id))
        if roots!={root.proof.export_version_id if root else proof.export_version_id}:
            raise RevisionConflict('Zero AR duplicate source authority unresolved')
        refs=tuple(dict.fromkeys(r for version,meta in ((proof.export_version_id,em),(proof.manifest_version_id,mm),
            (proof.control_version_id,cm),(source_version_id,pm)) for r in self.reader.sources.refs(version,meta)))
        series=identity('zero-ar-population-series-v255',self.client_id,proof.scope.to_json(),proof.system_id)
        identifier=identity('zero-ar-population-v255',source_version_id,proof.to_json(),export.to_json(),manifest.to_json(),control.to_json())
        return ZeroARPopulation(zero_id=identifier,series_id=series,client_id=self.client_id,run_id=self.run_id,
            revision=proof.revision,supersedes=previous.zero_id if previous else None,
            source_version_id=source_version_id,scope=proof.scope,proof=proof,export=export,
            manifest=manifest,control=control,total='0',lineage=refs)


class ZeroARPopulationService:
    def __init__(self, production):
        from .history import ProductionHistory
        self.history=ProductionHistory(production)
        self.qualifier=ZeroARSourceQualifier(production.connection,production.client_id,production.run_id,production.authority_resolver)

    def capture(self, source_version_id):
        value=self.qualifier.qualify(source_version_id)
        existing=self.history.latest_id(tables.zero,'zero_id',value.series_id)
        if existing:
            old=self.get(existing)
            if old==value:return old
            if value.supersedes!=existing:raise RevisionConflict('Zero AR same-date replacement needs qualified revision evidence')
        elif value.supersedes:
            raise RevisionConflict('Zero AR predecessor must already be independently owned')
        with self.history.atomic():self.history.persist(tables.zero,'zero_id',value)
        return value

    def get(self, zero_id, *, current=False):
        value,_=self.history.load(tables.zero,'zero_id',zero_id,ZeroARPopulation)
        if current and self.history.latest_id(tables.zero,'zero_id',value.series_id)!=zero_id:
            raise RevisionConflict('Superseded zero population remains historical')
        if current and self.qualifier.qualify(value.source_version_id)!=value:
            raise RevisionConflict('Zero AR retained source evidence changed')
        return value
