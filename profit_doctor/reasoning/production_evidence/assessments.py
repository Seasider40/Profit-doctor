"""Append-only production temporal assessments; arithmetic belongs to v2.54."""
from pydantic import model_validator
from sqlalchemy import insert,select

from profit_doctor.persistence import production_history_schema as tables
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import LineageReference
from profit_doctor.reasoning.domain.service import ScopeError,RevisionConflict
from profit_doctor.reasoning.temporal.contracts import Assessment,ContractKey
from .temporal import ProductionTemporalResult,ProductionTemporalService
from .ar_admission import ARProductionAdmission
from .history import ProductionHistory


class ProductionAssessment(Assessment):
    result: ProductionTemporalResult
    lineage: tuple[LineageReference,...]=()

    @model_validator(mode='after')
    def production_only(self):
        if self.result.basis.origin!='QUALIFIED_PRODUCTION_V255':raise ScopeError('Synthetic result cannot become production history')
        if any(ref.client_id!=self.client_id for ref in self.lineage):raise ScopeError('Foreign assessment lineage')
        return self


class ProductionAssessmentService(ProductionHistory):
    def __init__(self, production, *, monthly=None, ar=None):
        super().__init__(production)
        self.monthly=monthly or ProductionTemporalService(production)
        if not isinstance(self.monthly,ProductionTemporalService) or self.monthly.production is not production:
            raise ScopeError('Production temporal measurement boundary differs')
        if ar is not None and (not isinstance(ar,ARProductionAdmission) or ar.verifier.production is not production):
            raise ScopeError('Production AR admission boundary differs')
        self.ar=ar

    def assess(self, contract_key, window, *, monthly_ids=(), margin_ids=(), semantic_version_ids=(), unknown_ids=()):
        key=ContractKey(contract_key)
        if key==ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE:
            if self.ar is None or monthly_ids or margin_ids:raise ScopeError('Only the typed registered AR boundary is eligible')
            result=self.ar.evaluate(window,semantic_version_ids,unknown_ids=unknown_ids)
        else:
            if semantic_version_ids or unknown_ids:raise ScopeError('AR owners cannot enter measurement trajectory')
            result=self.monthly.evaluate(key,window,monthly_ids=monthly_ids,margin_ids=margin_ids)
        series=identity('production-temporal-series-v255',self.client_id,key.value,result.basis.subject_id,window.to_json())
        old_id=self.latest_id(tables.temporal,'assessment_id',series)
        old=self.get(old_id) if old_id else None
        if old and old.result==result:return old
        refs=tuple(dict.fromkeys(ref for observation in result.basis.observations for ref in observation.lineage))
        value=ProductionAssessment(assessment_id=identity('production-temporal-v255',series,result.to_json()),series_id=series,
            subject_id=result.basis.subject_id,client_id=self.client_id,run_id=self.run_id,
            revision=old.revision+1 if old else 1,supersedes=old_id,result=result,lineage=refs)
        with self.atomic():
            self.persist(tables.temporal,'assessment_id',value)
            for observation in result.basis.observations:
                relationship=self._relationship(observation)
                self.session.execute(insert(tables.temporal_reference).values(assessment_id=value.assessment_id,
                    reference_id=identity('production-temporal-ref',value.assessment_id,observation.observation_id),
                    client_id=self.client_id,**relationship))
        return value

    @staticmethod
    def _relationship(observation):
        if observation.source_kind=='MONTHLY_REVENUE':return {'monthly_id':observation.source_id}
        if observation.source_kind=='MONTHLY_C0_MARGIN':return {'margin_id':observation.source_id}
        if observation.source_kind=='UNKNOWN':return {'unknown_id':observation.source_id}
        if observation.source_kind in ('IMPACT','ABSENCE'):return {'projection_id':observation.observation_id}
        raise ScopeError('Unknown production assessment owner kind')

    def get(self, assessment_id, *, current=False):
        value,_=self.load(tables.temporal,'assessment_id',assessment_id,ProductionAssessment)
        expected={tuple(sorted(self._relationship(o).items())) for o in value.result.basis.observations}
        rows=self.session.execute(select(tables.temporal_reference).where(
            tables.temporal_reference.c.assessment_id==assessment_id,tables.temporal_reference.c.client_id==self.client_id)).mappings().all()
        keys=('monthly_id','margin_id','projection_id','unknown_id','zero_id')
        actual={tuple((key,row[key]) for key in keys if row[key] is not None) for row in rows}
        if actual!=expected or len(rows)!=len(value.result.basis.observations):raise ScopeError('Assessment owner-reference graph differs')
        if current:
            if self.latest_id(tables.temporal,'assessment_id',value.series_id)!=assessment_id:
                raise RevisionConflict('Superseded temporal assessment remains historical')
            key=value.result.basis.contract_key
            if key==ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE:
                if self.ar is None:raise ScopeError('Registered AR admission required for current assessment')
                self.ar.validate(value.result.basis)
                from profit_doctor.reasoning.temporal.engine import _evaluate_sequence
                reproduced=_evaluate_sequence(value.result.basis,result_model=ProductionTemporalResult,ar_admission=self.ar)
                if reproduced!=value.result:raise RevisionConflict('Retained lifecycle result differs from frozen evaluator')
            else:
                # Current source revalidation happens before replay. Historical
                # predecessors are reproduced by the existing measurement owner.
                observations=value.result.basis.observations
                superseded=set()
                for o in observations:
                    owner=(self.production.get_monthly(o.source_id) if o.source_kind=='MONTHLY_REVENUE'
                        else self.monthly.margins.get_margin(o.source_id))
                    if owner.supersedes:superseded.add(owner.supersedes)
                ids=tuple(o.source_id for o in observations if o.source_id not in superseded)
                reproduced=self.monthly.evaluate(key,value.result.basis.window,
                    monthly_ids=ids if key==ContractKey.REVENUE_DESCRIPTIVE_TRAJECTORY else (),
                    margin_ids=ids if key==ContractKey.CONTRIBUTION_0_MARGIN_TRAJECTORY else ())
                if reproduced!=value.result:raise RevisionConflict('Temporal assessment source basis changed')
        return value
