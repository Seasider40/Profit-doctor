"""Explicit typed AR admission. Registered owners are reverified at kernel entry."""
import json
from profit_doctor.persistence import production_history_schema as tables

from profit_doctor.reasoning.bridge.qualification import Period
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.temporal.contracts import ContractKey, Window
from profit_doctor.reasoning.temporal.engine import _evaluate_sequence
from .ar_semantics import ARSemanticProjection, ARSemanticVerifier
from .temporal import ProductionObservation, ProductionAbsenceEvidence, ProductionTemporalInput, ProductionTemporalResult
from .history import ARProjectionService, UnknownObservationService, UnknownObservation


class ARProductionAdmission:
    """Not an authority flag: this owner resolves and revalidates every premise.

    Qualified projections retain their original source routes and authoritative
    revision chains. The shared evaluator does not promote refused premises.
    """
    def __init__(self, verifier):
        if not isinstance(verifier, ARSemanticVerifier):
            raise ScopeError('Registered AR semantic verifier required')
        self.verifier = verifier
        self.projections=ARProjectionService(verifier)
        self.unknowns=UnknownObservationService(self.projections)

    def observation(self, semantic_version_id):
        view = self.projections.capture(semantic_version_id)
        return self._observation(view)

    def _observation(self, view, *, historical=False):
        p = self.verifier.production
        scope = view.evidence.scope
        scope_key = json.dumps([scope.entity_id, scope.ledger_id,
            scope.population, scope.currency], separators=(',',':'))
        if view.owner_kind == 'ABSENT_VERIFIED':
            owner = p.get_absence(view.owner_id,current=not historical)
            proof = ProductionAbsenceEvidence(client_id=p.client_id,as_of=scope.as_of,
                scope_key=scope_key,population=view.contract.population.verified_value,
                complete_population_verified=True,control_reconciled=True,
                contractual_and_status_review_complete=True,no_unresolved_classifications=True,
                condition_absence_verified=True,evidence=view.lineage)
            kind, presence, value, revision = 'ABSENCE','ABSENT_VERIFIED',None,owner.revision
        else:
            from sqlalchemy import select
            from profit_doctor.persistence import impact_schema
            candidate = p.session.scalar(select(impact_schema.impact.c.candidate_id).where(
                impact_schema.impact.c.impact_id==view.owner_id,impact_schema.impact.c.client_id==p.client_id))
            q = self.verifier.impacts.get(candidate,current=not historical)
            proof = None
            kind, presence, value, revision = 'IMPACT','PRESENT',q.impact.amount.value,q.impact.revision
        return ProductionObservation(observation_id=view.projection_id,client_id=p.client_id,run_id=p.run_id,
            source_kind=kind,source_id=view.owner_id,source_revision=revision,scope_key=scope_key,
            period=Period.model_validate(view.contract.coverage.verified_value['period']),dataset=view.contract,
            metric='cash_trapped_receivables',unit='CURRENCY',currency=scope.currency,value=value,
            presence=presence,absence=proof,lineage=view.lineage,source_snapshot=view.to_json())

    def unknown(self, unknown_id):
        value=self.unknowns.get(unknown_id,current=True)
        scope=value.scope
        scope_key=json.dumps([scope.entity_id,scope.ledger_id,scope.population,scope.currency],separators=(',',':'))
        return ProductionObservation(observation_id=value.unknown_id,client_id=value.client_id,run_id=value.run_id,
            source_kind='UNKNOWN',source_id=value.unknown_id,source_revision=value.revision,scope_key=scope_key,
            period=Period(start=scope.as_of,end=scope.as_of,basis='POINT_IN_TIME',nature='STOCK'),
            metric='cash_trapped_receivables',unit='CURRENCY',currency=scope.currency,presence='UNKNOWN',
            lineage=value.lineage,source_snapshot=value.to_json())

    def validate(self, basis):
        if basis.origin != 'QUALIFIED_PRODUCTION_V255' or basis.contract_key != ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE:
            raise ScopeError('AR admission is restricted to its qualified production lifecycle boundary')
        if basis.client_id != self.verifier.production.client_id:
            raise ScopeError('AR admission client differs')
        for observation in basis.observations:
            if observation.source_kind=='UNKNOWN':
                value=UnknownObservation.from_json(observation.source_snapshot)
                if self.unknown(value.unknown_id).to_json()!=observation.to_json():
                    raise RevisionConflict('Unknown observation differs from its owned refusal')
                continue
            view = ARSemanticProjection.from_json(observation.source_snapshot)
            loaded=self.projections.get(view.projection_id)
            latest=self.projections.latest_id(tables.projection,
                'projection_id',loaded.series_id)
            historical=latest!=loaded.projection_id
            if historical and latest not in {o.observation_id for o in basis.observations}:
                raise RevisionConflict('Superseded AR source requires its complete authoritative replacement chain')
            previous=self.projections.get(loaded.supersedes) if loaded.supersedes else None
            reproduced=self.verifier._verify(loaded.semantic_version_id,previous=previous,historical=historical)
            if reproduced!=loaded:raise RevisionConflict('AR projection history no longer matches retained sources')
            expected = self._observation(loaded,historical=historical)
            if expected.to_json() != observation.to_json():
                raise RevisionConflict('AR observation differs from current registered owner/projection evidence')

    def evaluate(self, window, semantic_version_ids, *, unknown_ids=()):
        window = Window.from_json(window.to_json())
        if len(set(semantic_version_ids)) != len(semantic_version_ids):
            raise ValueError('Duplicate semantic evidence versions')
        if len(set(unknown_ids))!=len(unknown_ids):raise ValueError('Duplicate unknown observations')
        observations=[]
        seen=set()
        for version in sorted(semantic_version_ids):
            current=self.projections.capture(version)
            observations.append(self._observation(current));seen.add(current.projection_id)
            previous=current.supersedes
            while previous and previous not in seen:
                prior=self.projections.get(previous)
                observations.append(self._observation(prior,historical=True));seen.add(previous);previous=prior.supersedes
        observations.extend(self.unknown(value) for value in sorted(unknown_ids))
        observations=tuple(observations)
        subject = identity('production-ar-temporal-subject',self.verifier.production.client_id,
            sorted({o.scope_key for o in observations}))
        basis = ProductionTemporalInput(contract_key=ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE,
            client_id=self.verifier.production.client_id,subject_id=subject,window=window,observations=observations)
        basis = ProductionTemporalInput.from_json(basis.to_json())
        return _evaluate_sequence(basis,result_model=ProductionTemporalResult,ar_admission=self)
