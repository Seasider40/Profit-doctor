"""Separately owned source-derived calendar-month measurements; no temporal uplift."""
from typing import Literal
from pydantic import Field, model_validator

from profit_doctor.reasoning.canonical.contracts import Measurement
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import Contract, Identifier, FinancialDecimal, LineageReference
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.measurement.contracts import MeasurementContext, MeasurementSlot
from .semantics import SemanticAssessment, SemanticVerificationService
from .source import RegisteredAccountingSource
from .reconciliation import exact_sum


class MonthlyMeasurement(Contract):
    schema_version: Literal['MONTHLY-2.55.1'] = 'MONTHLY-2.55.1'
    qualification_contract: Literal['MONTHLY_REVENUE_1', 'MONTHLY_CONTRIBUTION_0_1']
    measurement_id: Identifier
    series_id: Identifier
    client_id: Identifier
    run_id: Identifier
    family: Literal['REVENUE', 'CONTRIBUTION_0']
    measurement: Measurement
    revenue: FinancialDecimal
    direct_cost: FinancialDecimal | None = None
    context: MeasurementContext
    semantic: SemanticAssessment
    lineage: tuple[LineageReference, ...] = Field(min_length=1)
    revision: int = Field(strict=True, ge=1)
    supersedes: Identifier | None = None
    source_authority: Literal['SYSTEM_DERIVED'] = 'SYSTEM_DERIVED'
    limitations: tuple[str, ...] = ('Source-derived monthly measurement, not a diagnostic Fact, Impact or temporal assessment.',)

    @model_validator(mode='after')
    def ownership(self):
        scope = self.semantic.manifest.scope
        if (scope.client_id,scope.entity_id,scope.ledger_id,scope.period,scope.currency) != (
                self.client_id,self.context.entity_id,self.context.segment_scope,self.context.period,self.context.currency):
            raise ScopeError('Monthly context must preserve the qualified source scope')
        if self.semantic.contract.client_id != self.client_id or self.semantic.contract.recorded_run_id != self.run_id:
            raise ScopeError('Monthly semantic assessment belongs to another client/run')
        claims=self.semantic.contract.claims()
        dimensions={'family','source_provider','population','inclusion_exclusion','coverage','definition',
            'organisational_scope','currency','unit','time_basis','revision_relationship'}
        if any(state != 'VERIFIED' for state in self.semantic.states.values()) or set(self.semantic.states) != dimensions:
            raise ValueError('All dimensional prerequisites must be verified')
        if any(claim.verified_value is None or (claim.declared_value is not None and
                claim.declared_value != claim.verified_value) for claim in claims):
            raise ValueError('Monthly owner cannot accept missing or contradictory dimensional verification')
        coverage=self.semantic.contract.coverage.verified_value
        if not isinstance(coverage,dict) or coverage.get('completeness') != 'COMPLETE':
            raise ValueError('Monthly owner requires complete coverage')
        if self.context.coverage != 'COMPLETE' or self.context.source_version != self.semantic.contract.source_version:
            raise ValueError('Monthly context must preserve coverage and source version')
        if self.context.source_version not in self.lineage or self.context.lineage != self.lineage:
            raise ValueError('Monthly source lineage is incomplete')
        if self.context.origin != MeasurementSlot(store='CANONICAL',resource='canonical_monthly_measurement',
                source_id=self.measurement_id,slot='amount'):
            raise ValueError('Monthly context requires its separate value owner')
        if (self.context.client_id,self.context.run_id) != (self.client_id,self.run_id):
            raise ScopeError('Monthly context scope differs')
        if self.context.period.basis != 'MONTHLY' or self.context.period.nature != 'FLOW':
            raise ValueError('Rolling diagnostic measurements cannot be monthly owners')
        if self.context.unit != self.measurement.unit or self.context.currency != self.measurement.currency:
            raise ValueError('Monthly value and context units disagree')
        if self.measurement.metric != self.family or self.measurement.basis != 'CALENDAR_MONTH':
            raise ValueError('Monthly metric/basis disagrees with owner')
        if self.family == 'REVENUE':
            if self.direct_cost is not None or self.measurement.value != self.revenue or self.qualification_contract != 'MONTHLY_REVENUE_1':
                raise ValueError('Revenue owner cannot include C0 semantics')
        elif self.direct_cost is None or self.measurement.value != exact_sum((self.revenue,self.direct_cost.copy_negate())) or self.qualification_contract != 'MONTHLY_CONTRIBUTION_0_1':
            raise ValueError('Contribution 0 is exactly Revenue minus governed direct costs')
        if any(r.client_id != self.client_id for r in self.lineage):
            raise ScopeError('Foreign monthly lineage')
        return self


class MonthlyResult(Contract):
    outcome: Literal['QUALIFIED', 'REFUSED']
    blockers: tuple[str, ...] = ()
    value: MonthlyMeasurement | None = None


class MonthlyMeasurementService:
    """Accept registered identities only; re-derive semantics and values on every call.

    Internal evaluator: history is supplied by the trusted durable owner service.
    ProductionEvidenceService is the public registered-ID-only boundary. No caller
    amount, origin flag or caller-assessed contract is accepted there.
    """
    def __init__(self, connection, client_id, run_id, authority_resolver=None):
        self.semantic = SemanticVerificationService(connection,client_id,run_id,authority_resolver)
        self.connection,self.client_id,self.run_id = connection,client_id,run_id

    def qualify(self, record_version, control_version, manifest_version, *, mapping_version,
                family, previous=None, declarations=()):
        if family not in ('REVENUE','CONTRIBUTION_0'):
            raise ValueError('Unknown monthly measurement family')
        if previous is not None:
            previous = MonthlyMeasurement.from_json(previous.to_json())
            if previous.client_id != self.client_id or previous.family != family:
                raise ScopeError('Monthly predecessor belongs to another owner')
        evidence = self.semantic.assess(record_version,control_version,manifest_version,
            mapping_version=mapping_version,declarations=declarations,previous=previous.semantic if previous else None)
        blockers = [key+':'+state for key,state in evidence.states.items() if state != 'VERIFIED']
        c = evidence.contract
        if c.coverage.verified_value is None or c.coverage.verified_value.get('completeness') != 'COMPLETE':
            blockers.append('COMPLETE_POPULATION_REQUIRED')
        expected = 'NET_REVENUE' if family == 'REVENUE' else 'REVENUE_MINUS_DIRECT_COST'
        if evidence.mapping is None or evidence.mapping.definition != expected:
            blockers.append('QUALIFIED_FAMILY_DEFINITION_REQUIRED')
        if family == 'REVENUE' and evidence.mapping and (
                evidence.mapping.direct_cost_accounts or evidence.chart is None or evidence.chart.cost_basis != 'NOT_APPLICABLE'):
            blockers.append('REVENUE_DEFINITION_MUST_NOT_INCLUDE_DIRECT_COST_MAPPING')
        scope = evidence.manifest.scope
        if scope.currency != 'GBP' or scope.period.nature != 'FLOW' or scope.period.basis != 'MONTHLY':
            blockers.append('MONTHLY_FLOW_GBP_REQUIRED')
        if evidence.manifest.predecessor_version_id == record_version:
            blockers.append('SOURCE_VERSION_CANNOT_SUPERSEDE_ITSELF')
        if blockers:
            return MonthlyResult(outcome='REFUSED',blockers=tuple(blockers))
        rows = RegisteredAccountingSource(self.connection,self.client_id).read(record_version)
        revenue = exact_sum(r.amount for r in rows if r.account_code in evidence.mapping.revenue_accounts)
        costs = exact_sum(r.amount for r in rows if r.account_code in evidence.mapping.direct_cost_accounts) if family == 'CONTRIBUTION_0' else None
        amount = revenue if costs is None else exact_sum((revenue,costs.copy_negate()))
        series = identity('monthly-owner-2.55.1',self.client_id,family,scope.to_json())
        if previous and previous.series_id != series:
            raise ScopeError('Different month/scope requires a new owner, not a revision')
        if previous and previous.semantic == evidence:
            return MonthlyResult(outcome='QUALIFIED',value=previous)
        if previous and c.revision_relationship.verified_value not in ('RESTATEMENT','CORRECTION','SUPERSESSION'):
            raise RevisionConflict('Changed monthly evidence requires authoritative source revision')
        revision = previous.revision+1 if previous else 1
        mid = identity('monthly-measurement-2.55.1',series,evidence.evidence_digest,revision)
        import hashlib
        measurement = Measurement(metric=family,value=amount,unit='CURRENCY',currency='GBP',basis='CALENDAR_MONTH')
        origin_digest = hashlib.sha256(measurement.to_json().encode()).hexdigest()
        lineage = tuple(dict.fromkeys((*c.family.verification_evidence,*c.definition.verification_evidence)))
        context = MeasurementContext(client_id=self.client_id,run_id=self.run_id,
            origin=MeasurementSlot(store='CANONICAL',resource='canonical_monthly_measurement',source_id=mid,slot='amount'),
            origin_digest=origin_digest,metric=family,unit='CURRENCY',currency='GBP',economic_basis=expected,
            entity_type='ENTITY',entity_id=scope.entity_id,segment_scope=scope.ledger_id,
            period=scope.period,coverage='COMPLETE',coverage_basis=evidence.manifest.boundary,
            source_version=c.source_version,lineage=lineage,source_locator=evidence.manifest.extraction_id,
            capture_method='QUALIFIED_MONTHLY_SOURCE_V255',supersedes=previous.context.context_id if previous else None,
            limitations=('Separate monthly owner; does not replace rolling REV-01/GM-01.',))
        return MonthlyResult(outcome='QUALIFIED',value=MonthlyMeasurement(measurement_id=mid,series_id=series,
            client_id=self.client_id,run_id=self.run_id,family=family,measurement=measurement,revenue=revenue,direct_cost=costs,
            context=context,semantic=evidence,lineage=lineage,revision=revision,
            supersedes=previous.measurement_id if previous else None,
            qualification_contract='MONTHLY_REVENUE_1' if family == 'REVENUE' else 'MONTHLY_CONTRIBUTION_0_1'))
