"""Evidence capability readiness, not economic interpretation or a universal score."""
from enum import StrEnum
import hashlib
import json
from typing import Literal
from pydantic import Field, model_validator
from sqlalchemy import insert,select

from profit_doctor.persistence import production_history_schema as tables
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import Contract, Identifier, LineageReference
from profit_doctor.reasoning.domain.service import ScopeError,RevisionConflict
from profit_doctor.reasoning.temporal.contracts import ContractKey
from .assessments import ProductionAssessmentService
from .history import ProductionHistory,UnknownObservationService
from .zero import ZeroARPopulationService


class ReadinessDomain(StrEnum):
    CORE_ACCOUNTING_EVIDENCE='CORE_ACCOUNTING_EVIDENCE'
    REVENUE_MONTHLY_MEASUREMENT='REVENUE_MONTHLY_MEASUREMENT'
    CONTRIBUTION_0_MONTHLY_MEASUREMENT='CONTRIBUTION_0_MONTHLY_MEASUREMENT'
    CONTRIBUTION_0_MARGIN_MEASUREMENT='CONTRIBUTION_0_MARGIN_MEASUREMENT'
    RECEIVABLES_SNAPSHOT='RECEIVABLES_SNAPSHOT'
    RECEIVABLES_ABSENCE='RECEIVABLES_ABSENCE'
    REVENUE_TEMPORAL='REVENUE_TEMPORAL'
    CONTRIBUTION_0_TEMPORAL='CONTRIBUTION_0_TEMPORAL'
    RECEIVABLES_LIFECYCLE='RECEIVABLES_LIFECYCLE'


class ReadinessStatus(StrEnum):
    VERIFIED='VERIFIED'
    DECLARED='DECLARED'
    PARTIAL='PARTIAL'
    INSUFFICIENT='INSUFFICIENT'
    NOT_PROVIDED='NOT_PROVIDED'
    CONFLICTED='CONFLICTED'


class ReadinessReference(Contract):
    kind: Literal['MONTHLY','MARGIN','ABSENCE','AR_PROJECTION','TEMPORAL','ZERO','UNKNOWN']
    owner_id: Identifier


class EvidenceReadiness(Contract):
    schema_version: Literal['EVIDENCE-READINESS-2.55.1']='EVIDENCE-READINESS-2.55.1'
    readiness_id: Identifier
    series_id: Identifier
    client_id: Identifier
    run_id: Identifier
    revision: int=Field(strict=True,ge=1)
    supersedes: Identifier|None=None
    domain: ReadinessDomain
    status: ReadinessStatus
    references: tuple[ReadinessReference,...]
    basis_digest: str=Field(pattern='^[a-f0-9]{64}$')
    lineage: tuple[LineageReference,...]=()
    satisfied_prerequisites: tuple[str,...]
    missing_prerequisites: tuple[str,...]
    conflicts: tuple[str,...]
    capabilities_unlocked: tuple[str,...]
    capabilities_refused: tuple[str,...]
    limitations: tuple[str,...]=('Only the explicit scoped evidence selection is assessed; not all company evidence.',
        'No analytical conclusion, economic value, recommendation or confidence uplift is implied.')

    @model_validator(mode='after')
    def governed(self):
        if (self.revision==1)!=(self.supersedes is None):raise RevisionConflict('Readiness requires its predecessor')
        if any(ref.client_id!=self.client_id for ref in self.lineage):raise ScopeError('Foreign readiness evidence')
        if self.status=='VERIFIED' and (self.missing_prerequisites or self.conflicts or not self.references):
            raise ValueError('Verified readiness requires owned evidence without gaps/conflicts')
        if self.status!='VERIFIED' and self.capabilities_unlocked:
            raise ValueError('Unqualified readiness cannot unlock its domain capability')
        return self


class EvidenceReadinessService(ProductionHistory):
    ALLOWED={
        ReadinessDomain.CORE_ACCOUNTING_EVIDENCE:{'MONTHLY'},
        ReadinessDomain.REVENUE_MONTHLY_MEASUREMENT:{'MONTHLY'},
        ReadinessDomain.CONTRIBUTION_0_MONTHLY_MEASUREMENT:{'MONTHLY'},
        ReadinessDomain.CONTRIBUTION_0_MARGIN_MEASUREMENT:{'MARGIN'},
        ReadinessDomain.RECEIVABLES_SNAPSHOT:{'ABSENCE','AR_PROJECTION','ZERO'},
        ReadinessDomain.RECEIVABLES_ABSENCE:{'ABSENCE','UNKNOWN','ZERO'},
        ReadinessDomain.REVENUE_TEMPORAL:{'TEMPORAL'},
        ReadinessDomain.CONTRIBUTION_0_TEMPORAL:{'TEMPORAL'},
        ReadinessDomain.RECEIVABLES_LIFECYCLE:{'TEMPORAL','UNKNOWN'},}
    COLUMNS={'MONTHLY':'monthly_id','MARGIN':'margin_id','ABSENCE':'absence_id','AR_PROJECTION':'projection_id',
        'ZERO':'zero_id','TEMPORAL':'temporal_id','UNKNOWN':'unknown_id'}

    def __init__(self, assessments):
        if not isinstance(assessments,ProductionAssessmentService):raise ScopeError('Registered production assessment owner required')
        super().__init__(assessments.production)
        self.assessments=assessments

    def _owner(self, ref, *, current):
        if ref.kind=='MONTHLY':return self.production.get_monthly(ref.owner_id,current=current)
        if ref.kind=='MARGIN':return self.assessments.monthly.margins.get_margin(ref.owner_id,current=current)
        if ref.kind=='ABSENCE':return self.production.get_absence(ref.owner_id,current=current)
        if ref.kind=='TEMPORAL':return self.assessments.get(ref.owner_id,current=current)
        if ref.kind=='ZERO':return ZeroARPopulationService(self.production).get(ref.owner_id,current=current)
        if self.assessments.ar is None:raise ScopeError('Registered AR evidence boundary required')
        if ref.kind=='AR_PROJECTION':return self.assessments.ar.projections.get(ref.owner_id,current=current)
        return self.assessments.ar.unknowns.get(ref.owner_id,current=current)

    def _classify(self, domain, ref, value):
        if ref.kind=='MONTHLY':
            family={'REVENUE_MONTHLY_MEASUREMENT':'REVENUE','CONTRIBUTION_0_MONTHLY_MEASUREMENT':'CONTRIBUTION_0'}.get(domain)
            if family and value.family!=family:raise ScopeError('Wrong monthly measurement family')
            if domain==ReadinessDomain.CORE_ACCOUNTING_EVIDENCE:
                return ReadinessStatus.PARTIAL,('FULL_ACCOUNTING_PACK_SCOPE_NOT_ESTABLISHED',)
            return ReadinessStatus.VERIFIED,()
        if ref.kind=='MARGIN':
            return (ReadinessStatus.VERIFIED,()) if value.status=='QUALIFIED' else (ReadinessStatus.INSUFFICIENT,value.reasons)
        if ref.kind=='ZERO':
            return (ReadinessStatus.VERIFIED,()) if domain==ReadinessDomain.RECEIVABLES_SNAPSHOT else (
                ReadinessStatus.INSUFFICIENT,('DISTINCT_QUALIFIED_ABSENCE_OWNER_REQUIRED',))
        if ref.kind=='AR_PROJECTION':return ReadinessStatus.VERIFIED,()
        if ref.kind=='UNKNOWN':return ReadinessStatus.INSUFFICIENT,value.missing_prerequisites
        if ref.kind=='ABSENCE':
            if domain==ReadinessDomain.RECEIVABLES_ABSENCE:
                return (ReadinessStatus.VERIFIED,()) if value.outcome=='ABSENT_VERIFIED' else (
                    ReadinessStatus.CONFLICTED if value.difference!=0 else ReadinessStatus.INSUFFICIENT,
                    value.blockers or ('QUALIFYING_BALANCES_PRESENT_ABSENCE_NOT_ESTABLISHED',))
            source=self.production.absence
            export,em,ea=source._document(value.source_versions[0],'ar-export')
            manifest,_,ma=source._document(value.source_versions[1],'ar-manifest')
            control,_,ca=source._document(value.source_versions[2],'ar-control')
            if (ea,ma,ca)!=('SOURCE_DATA',)*3:
                return (ReadinessStatus.DECLARED if 'MANAGEMENT_ASSERTION' in (ea,ma,ca) else ReadinessStatus.INSUFFICIENT,
                    ('AUTHENTICATED_AR_SOURCE_AUTHORITY_REQUIRED',))
            if value.difference!=0:return ReadinessStatus.CONFLICTED,('AR_CONTROL_MISMATCH',)
            if manifest.open_items is None:return ReadinessStatus.INSUFFICIENT,('COMPLETE_MEMBERSHIP_REQUIRED',)
            if set(manifest.open_items)!={(i.customer_id,i.invoice_id) for i in export.invoices} or manifest.excluded_items:
                return ReadinessStatus.PARTIAL,('COMPLETE_MEMBERSHIP_REQUIRED',)
            if not export.invoices and value.zero_population_id is None:
                return ReadinessStatus.INSUFFICIENT,('POSITIVE_ZERO_POPULATION_PROOF_REQUIRED',)
            if any(b in value.blockers for b in ('SNAPSHOT_REVISION_AUTHORITY_UNRESOLVED','EXTRACTION_BOUNDARY_OR_DATE_UNVERIFIED')):
                return ReadinessStatus.CONFLICTED,('AR_SOURCE_SCOPE_OR_REVISION_AUTHORITY_UNRESOLVED',)
            return ReadinessStatus.VERIFIED,()
        key={ReadinessDomain.REVENUE_TEMPORAL:ContractKey.REVENUE_DESCRIPTIVE_TRAJECTORY,
            ReadinessDomain.CONTRIBUTION_0_TEMPORAL:ContractKey.CONTRIBUTION_0_MARGIN_TRAJECTORY,
            ReadinessDomain.RECEIVABLES_LIFECYCLE:ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE}[domain]
        if value.result.basis.contract_key!=key:raise ScopeError('Wrong temporal contract for readiness')
        minimum=2 if domain==ReadinessDomain.RECEIVABLES_LIFECYCLE else 3
        if value.result.sequence!='QUALIFIED' or len(value.result.included)<minimum:
            return ReadinessStatus.INSUFFICIENT,('SUFFICIENT_COMPLETE_COMPARABLE_OBSERVATIONS_REQUIRED',)
        return ReadinessStatus.VERIFIED,()

    def _derive(self, domain, references):
        refs=tuple(ReadinessReference.from_json(ref.to_json()) for ref in references)
        if len(set((r.kind,r.owner_id) for r in refs))!=len(refs):raise ValueError('Duplicate readiness evidence')
        if any(r.kind not in self.ALLOWED[domain] for r in refs):raise ScopeError('Wrong evidence kind for readiness domain')
        statuses=[];missing=[];conflicts=[];lineage=[];basis=[]
        for ref in sorted(refs,key=lambda r:(r.kind,r.owner_id)):
            historical=self._owner(ref,current=False)  # establishes actual scoped ownership first
            lineage.extend(historical.lineage)
            try:
                current=self._owner(ref,current=True)
            except (ScopeError,RevisionConflict) as error:
                status=ReadinessStatus.CONFLICTED;why=(str(error),)
                basis.append((ref.to_json(),historical.to_json(),why))
            else:
                status,why=self._classify(domain,ref,current)
                basis.append((ref.to_json(),current.to_json(),why))
            statuses.append(status)
            (conflicts if status==ReadinessStatus.CONFLICTED else missing).extend(why)
        priority=(ReadinessStatus.CONFLICTED,ReadinessStatus.INSUFFICIENT,ReadinessStatus.PARTIAL,ReadinessStatus.DECLARED)
        status=next((s for s in priority if s in statuses),ReadinessStatus.VERIFIED) if refs else ReadinessStatus.NOT_PROVIDED
        if not refs:missing.append('REGISTERED_OWNED_EVIDENCE_NOT_PROVIDED')
        digest=hashlib.sha256(json.dumps([domain.value,basis],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return refs,status,tuple(dict.fromkeys(lineage)),tuple(sorted(set(missing))),tuple(sorted(set(conflicts))),digest

    def assess(self, domain, references=()):
        domain=ReadinessDomain(domain)
        refs,status,lineage,missing,conflicts,digest=self._derive(domain,references)
        series=identity('evidence-readiness-series-v255',self.client_id,domain.value)
        old_id=self.latest_id(tables.readiness,'readiness_id',series)
        old=self.get(old_id) if old_id else None
        if old and old.basis_digest==digest:return old
        value=EvidenceReadiness(readiness_id=identity('evidence-readiness-v255',series,digest),series_id=series,
            client_id=self.client_id,run_id=self.run_id,revision=old.revision+1 if old else 1,supersedes=old_id,
            domain=domain,status=status,references=refs,basis_digest=digest,lineage=lineage,
            satisfied_prerequisites=('CURRENT_REGISTERED_OWNERS_REVALIDATED',) if status=='VERIFIED' else (),
            missing_prerequisites=missing,conflicts=conflicts,
            capabilities_unlocked=(domain.value,) if status=='VERIFIED' else (),
            capabilities_refused=() if status=='VERIFIED' else (domain.value,))
        with self.atomic():
            self.persist(tables.readiness,'readiness_id',value)
            for ref in refs:
                self.session.execute(insert(tables.readiness_reference).values(readiness_id=value.readiness_id,
                    reference_id=identity('evidence-readiness-reference',ref.kind,ref.owner_id),client_id=self.client_id,
                    **{self.COLUMNS[ref.kind]:ref.owner_id}))
        return value

    def get(self, readiness_id, *, current=False):
        value,_=self.load(tables.readiness,'readiness_id',readiness_id,EvidenceReadiness)
        rows=self.session.execute(select(tables.readiness_reference).where(
            tables.readiness_reference.c.readiness_id==readiness_id,tables.readiness_reference.c.client_id==self.client_id)).mappings().all()
        actual={tuple((column,row[column]) for column in self.COLUMNS.values() if row[column] is not None) for row in rows}
        expected={((self.COLUMNS[ref.kind],ref.owner_id),) for ref in value.references}
        if actual!=expected or len(rows)!=len(value.references):raise ScopeError('Readiness evidence-reference graph differs')
        if current:
            if self.latest_id(tables.readiness,'readiness_id',value.series_id)!=readiness_id:
                raise RevisionConflict('Superseded readiness remains historical')
            *_,digest=self._derive(value.domain,value.references)
            if digest!=value.basis_digest:raise RevisionConflict('Readiness evidence changed; explicit reassessment required')
        return value
