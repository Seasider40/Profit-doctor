"""Versioned production admission to the shared frozen temporal sequence kernel.

Only owned, revalidated registered-source evidence enters this service. No
production value is relabelled synthetic, or misrepresented as a diagnostic Fact.
"""
import hashlib
import json
from typing import Literal


from profit_doctor.reasoning.bridge.qualification import Period
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.dataset.contracts import DatasetAssertion, DatasetContract, DatasetCoverage
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.temporal.contracts import (
    Observation, TemporalInput, TemporalResult, ContractKey, Window, AbsenceEvidence,
)
from profit_doctor.reasoning.temporal.engine import _evaluate_sequence
from .margin import MarginQualificationService
from .monthly import MonthlyMeasurementService
from .service import ProductionEvidenceService, equivalent


class ProductionAbsenceEvidence(AbsenceEvidence):
    origin: Literal['QUALIFIED_PRODUCTION_V255'] = 'QUALIFIED_PRODUCTION_V255'


class ProductionObservation(Observation):
    source_kind: Literal['MONTHLY_REVENUE', 'MONTHLY_C0_MARGIN', 'IMPACT', 'ABSENCE', 'UNKNOWN']
    absence: ProductionAbsenceEvidence | None = None


class ProductionTemporalInput(TemporalInput):
    origin: Literal['QUALIFIED_PRODUCTION_V255'] = 'QUALIFIED_PRODUCTION_V255'
    observations: tuple[ProductionObservation, ...]


class ProductionTemporalResult(TemporalResult):
    schema_version: Literal['PRODUCTION-TEMPORAL-2.55.1'] = 'PRODUCTION-TEMPORAL-2.55.1'
    basis: ProductionTemporalInput


def _claim(value, lineage):
    return DatasetAssertion(verified_value=value, verification_authority='SYSTEM_DERIVED', verification_evidence=lineage)


class ProductionTemporalService:
    """Registered owner IDs and explicit window only; no evidence/result injection."""
    def __init__(self, production, margins=None):
        if not isinstance(production, ProductionEvidenceService):
            raise ScopeError('Registered production evidence owner required')
        self.production, self.session = production, production.session
        self.client_id, self.run_id = production.client_id, production.run_id
        self.margins = margins or MarginQualificationService(production)
        if not isinstance(self.margins, MarginQualificationService) or self.margins.production is not production:
            raise ScopeError('Margin owner must share the production boundary')

    def _monthly(self, identifier, *, historical=False):
        value = self.production.get_monthly(identifier, current=not historical)
        if historical:
            old = self.production.get_monthly(value.supersedes) if value.supersedes else None
            versions = value.semantic.source_versions
            reproduced = MonthlyMeasurementService(self.production.connection, self.client_id, value.run_id,
                self.production.authority_resolver).qualify(*versions[:3], mapping_version=versions[3], family=value.family, previous=old)
            if reproduced.outcome != 'QUALIFIED' or not equivalent(value, reproduced.value):
                raise RevisionConflict('Historical monthly source no longer verifies')
        return value

    def _scope(self, scope):
        return json.dumps([scope.entity_id, scope.ledger_id, scope.population, scope.currency], separators=(',', ':'))

    def _revenue(self, identifier, *, historical=False):
        value = self._monthly(identifier, historical=historical)
        if value.family != 'REVENUE' or value.qualification_contract != 'MONTHLY_REVENUE_1':
            raise ScopeError('Only separately owned monthly Revenue is eligible')
        return ProductionObservation(observation_id=value.measurement_id, client_id=self.client_id, run_id=value.run_id,
            source_kind='MONTHLY_REVENUE', source_id=value.measurement_id, source_revision=value.revision,
            scope_key=self._scope(value.semantic.manifest.scope), period=value.context.period, dataset=value.semantic.contract,
            metric='revenue', unit='CURRENCY', currency='GBP', value=value.measurement.value,
            context_binding_id=self.production.contexts.lookup(value.context.origin).binding_id,
            lineage=value.lineage, source_snapshot=value.to_json())

    def _margin(self, identifier, *, historical=False):
        value = self.margins.get_margin(identifier, current=not historical)
        binding = self.margins.get_binding(value.binding_id, current=not historical)
        revenue = self._monthly(binding.revenue_owner_id, historical=historical)
        contribution = self._monthly(binding.contribution_owner_id, historical=historical)
        if historical:
            from .component import binding_reasons
            proof, row, authority = self.margins.sources.proof(binding.proof_version_id)
            old = self.margins.get_binding(binding.supersedes) if binding.supersedes else None
            reasons = tuple(sorted(set((*binding_reasons(proof, authority, revenue, contribution, self.production.connection),
                *self.margins._revision_reasons(proof, old), *self.margins._root_reasons(proof, revenue, contribution)))))
            if proof != binding.proof or row['file_hash'] != binding.proof_digest or reasons != binding.reasons:
                raise RevisionConflict('Historical component binding no longer verifies')
        raw = revenue.semantic.contract
        prior = self.margins.get_margin(value.supersedes) if value.supersedes else None
        period = Period(start=revenue.context.period.start, end=revenue.context.period.end, basis='MONTHLY', nature='RATE')
        lineage = value.lineage
        # This is an explicitly identified derived contract projection, not a
        # mutation of either source Dataset Contract or CMC. It retains both
        # source documents through the binding and its component owner lineage.
        projection = raw.model_copy(update={
            'contract_id': identity('margin-dataset-projection-v255', value.margin_id),
            'revision': value.revision,
            'supersedes': identity('margin-dataset-projection-v255', prior.margin_id) if prior else None,
            'revision_target_contract_id': identity('margin-dataset-projection-v255', prior.margin_id) if prior else None,
            'source_digest': hashlib.sha256(value.to_json().encode()).hexdigest(),
            'unit': _claim('PERCENTAGE', lineage), 'currency': _claim('N/A', lineage),
            'definition': _claim({'contract': value.qualification_contract,
                'revenue_family': raw.family.verified_value, 'contribution_family': contribution.semantic.contract.family.verified_value,
                'revenue': revenue.semantic.chart.model_dump(mode='json',
                exclude={'scope', 'effective_from', 'effective_to'}), 'contribution': contribution.semantic.chart.model_dump(mode='json',
                exclude={'scope', 'effective_from', 'effective_to'})}, lineage),
            'coverage': _claim(DatasetCoverage(period=period, completeness='COMPLETE', coverage_basis=raw.coverage.verified_value['coverage_basis']).model_dump(mode='json'), lineage),
            'revision_relationship': _claim('CORRECTION' if prior else 'NEW_OBSERVATION', lineage),
        })
        projection = DatasetContract.from_json(projection.to_json())
        return ProductionObservation(observation_id=value.margin_id, client_id=self.client_id, run_id=value.run_id,
            source_kind='MONTHLY_C0_MARGIN', source_id=value.margin_id, source_revision=value.revision,
            scope_key=self._scope(revenue.semantic.manifest.scope), period=period, dataset=projection,
            metric='contribution_0_margin', unit='PERCENTAGE', value=value.measurement.value if value.measurement else None,
            context_binding_id=self.production.contexts.lookup(value.context.origin).binding_id if value.context else None,
            lineage=lineage, source_snapshot=value.to_json())

    def evaluate(self, contract_key, window, *, monthly_ids=(), margin_ids=(), absence_ids=(), impact_ids=()):
        key = ContractKey(contract_key)
        if key == ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE:
            raise ScopeError('SOURCE_SUPPORTED_AR_DATASET_PROVIDER_REQUIRED')
        window = Window.from_json(window.to_json())
        groups = (monthly_ids, margin_ids, absence_ids, impact_ids)
        if any(len(set(ids)) != len(ids) for ids in groups):
            raise ValueError('Duplicate requested owner identities')
        allowed = ((True, False, False, False) if key == ContractKey.REVENUE_DESCRIPTIVE_TRAJECTORY else
            (False, True, False, False) if key == ContractKey.CONTRIBUTION_0_MARGIN_TRAJECTORY else (False, False, True, True))
        if any(ids and not permission for ids, permission in zip(groups, allowed)):
            raise ScopeError('Wrong measurement owner for production temporal contract')
        observations = []
        for ids, read, get in ((monthly_ids, self._revenue, self.production.get_monthly),
                              (margin_ids, self._margin, self.margins.get_margin)):
            seen = set()
            for identifier in sorted(ids):
                observations.append(read(identifier))
                seen.add(identifier)
                previous = get(identifier).supersedes
                while previous:
                    if previous in seen:
                        break
                    seen.add(previous)
                    observations.append(read(previous, historical=True))
                    previous = get(previous).supersedes
        scope_keys = {o.scope_key for o in observations}
        subject = identity('production-temporal-subject', self.client_id, key.value, sorted(scope_keys))
        basis = ProductionTemporalInput(contract_key=key, client_id=self.client_id, subject_id=subject,
            window=window, observations=tuple(sorted(observations, key=lambda o: o.observation_id)))
        basis = ProductionTemporalInput.from_json(basis.to_json())
        return _evaluate_sequence(basis, result_model=ProductionTemporalResult,
            measurement_kinds=('MONTHLY_REVENUE', 'MONTHLY_C0_MARGIN'),
            measurement_families=('SALES_TRANSACTIONS', 'GENERAL_LEDGER'))
