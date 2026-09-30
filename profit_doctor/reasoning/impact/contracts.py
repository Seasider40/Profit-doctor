"""Candidates are not Impacts. Synthetic qualification is never production evidence."""
from datetime import date
from decimal import localcontext
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator
from profit_doctor.reasoning.domain.contracts import (
    Contract, Identifier, FinancialDecimal, ConfidenceProfile, MaterialityProfile,
)
from profit_doctor.reasoning.domain.vocabulary import ImpactType, OverlapType


class Outcome(StrEnum):
    QUALIFIED_IMPACT = 'QUALIFIED_IMPACT'
    INSUFFICIENT_EVIDENCE = 'INSUFFICIENT_EVIDENCE'
    NOT_APPLICABLE = 'NOT_APPLICABLE'
    HELD = 'HELD'


class Dimension(StrEnum):
    PROFIT_PNL = 'PROFIT_PNL'
    CASH = 'CASH'
    CAPITAL_RISK = 'CAPITAL_RISK'
    FUTURE_EXPOSURE = 'FUTURE_EXPOSURE'
    POTENTIAL_UPSIDE = 'POTENTIAL_UPSIDE'
    REALISED_BENEFIT = 'REALISED_BENEFIT'


DIMENSIONS = {
    ImpactType.OBSERVED_LOSS: Dimension.PROFIT_PNL,
    ImpactType.RUN_RATE_LEAKAGE: Dimension.PROFIT_PNL,
    ImpactType.CASH_TRAPPED: Dimension.CASH,
    ImpactType.AVOIDABLE_COST: Dimension.PROFIT_PNL,
    ImpactType.CAPITAL_AT_RISK: Dimension.CAPITAL_RISK,
    ImpactType.FUTURE_EXPOSURE: Dimension.FUTURE_EXPOSURE,
    ImpactType.VALUE_CREATION_POTENTIAL: Dimension.POTENTIAL_UPSIDE,
    ImpactType.REALISED_BENEFIT: Dimension.REALISED_BENEFIT,
}


def precision(values):
    """Exact decimal addition/subtraction budget, including carry for every term."""
    values = tuple(values)
    return max(60, max(v.adjusted() for v in values) - min(v.as_tuple().exponent for v in values)
               + len(str(len(values))) + 2)


class Lifecycle(StrEnum):
    CANDIDATE = 'CANDIDATE'
    QUANTIFIED = 'QUANTIFIED'
    SUPPORTED = 'SUPPORTED'
    MONITORING = 'MONITORING'
    SUPERSEDED = 'SUPERSEDED'
    INVALIDATED = 'INVALIDATED'
    REALISED = 'REALISED'


class Counterfactual(Contract):
    basis: Literal['SYNTHETIC_OPERATIONAL_REQUIREMENT']
    required: FinancialDecimal = Field(ge=0)
    scope: str = Field(min_length=1)
    as_of: date
    rationale: str = Field(min_length=1)
    evidence: tuple[str, ...] = Field(min_length=1)
    assumptions: tuple[str, ...] = Field(min_length=1)


class SyntheticBasis(Contract):
    """Resolved by a trusted test-fixture owner, never a production evidence writer.

    This release has no production positive-qualification provider. All amounts
    derived from this contract retain SYNTHETIC domain through totals and storage.
    """
    domain: Literal['SYNTHETIC'] = 'SYNTHETIC'
    fixture_key: Identifier
    client_id: Identifier
    run_id: Identifier
    consequence_key: Identifier
    metric: Literal['net_trade_working_capital'] = 'net_trade_working_capital'
    scope: str = Field(min_length=1)
    as_of: date
    currency: Literal['GBP'] = 'GBP'
    coverage: Literal['COMPLETE', 'PARTIAL']
    observed: FinancialDecimal = Field(ge=0)
    counterfactual: Counterfactual
    limitations: tuple[str, ...] = ('Synthetic contract evidence only; not Golden Manufacturing or production qualification.',)

    @model_validator(mode='after')
    def comparable_requirement(self):
        if (self.scope, self.as_of) != (self.counterfactual.scope, self.counterfactual.as_of):
            raise ValueError('Required and observed positions must share scope and as-of')
        return self


class Source(Contract):
    kind: Literal['BRIDGE', 'REASONING', 'SYNTHETIC']
    source_id: Identifier


class ImpactAmount(Contract):
    value: FinancialDecimal = Field(gt=0)
    currency: Literal['GBP'] = 'GBP'
    basis: Literal['COUNTERFACTUAL_EXCESS_STOCK'] = 'COUNTERFACTUAL_EXCESS_STOCK'
    observed: FinancialDecimal
    counterfactual: Counterfactual
    as_of: date
    scope: str = Field(min_length=1)
    coverage: Literal['COMPLETE', 'PARTIAL']
    calculation: Literal['observed - required'] = 'observed - required'
    # No range is invented when the fixture provides exact Decimal inputs.
    uncertainty: Literal['EXACT_FIXTURE_INPUTS_ONLY'] = 'EXACT_FIXTURE_INPUTS_ONLY'

    @model_validator(mode='after')
    def arithmetic(self):
        with localcontext() as ctx:
            ctx.prec = precision((self.value, self.observed, self.counterfactual.required))
            if self.value != self.observed - self.counterfactual.required:
                raise ValueError('Amount disagrees with governed counterfactual')
        if (self.scope, self.as_of) != (self.counterfactual.scope, self.counterfactual.as_of):
            raise ValueError('Counterfactual period/scope mismatch')
        return self


class QualifiedImpact(Contract):
    schema_version: Literal['EI-2.49.1'] = 'EI-2.49.1'
    contract: Literal['SYNTHETIC_EXCESS_WC_1'] = 'SYNTHETIC_EXCESS_WC_1'
    domain: Literal['SYNTHETIC'] = 'SYNTHETIC'
    impact_id: Identifier
    candidate_id: Identifier
    revision: int = Field(strict=True, ge=1)
    client_id: Identifier
    run_id: Identifier
    effect_id: Identifier
    category: Literal[ImpactType.CASH_TRAPPED] = ImpactType.CASH_TRAPPED
    dimension: Literal[Dimension.CASH] = Dimension.CASH
    status: Literal[Lifecycle.QUANTIFIED] = Lifecycle.QUANTIFIED
    amount: ImpactAmount
    confidence: ConfidenceProfile = Field(default_factory=ConfidenceProfile)
    materiality: MaterialityProfile
    limitations: tuple[str, ...] = Field(min_length=1)


class Qualification(Contract):
    schema_version: Literal['IQ-2.49.1'] = 'IQ-2.49.1'
    candidate_id: Identifier
    revision: int = Field(strict=True, ge=1)
    client_id: Identifier
    run_id: Identifier
    source: Source
    source_document: str
    domain: Literal['PRODUCTION', 'SYNTHETIC']
    category: ImpactType
    outcome: Outcome
    available: tuple[str, ...]
    missing: tuple[str, ...]
    required_counterfactual: str
    blockers: tuple[str, ...]
    effect_ids: tuple[Identifier, ...] = ()
    overlap: OverlapType = OverlapType.UNKNOWN_OVERLAP
    impact: QualifiedImpact | None = None

    @model_validator(mode='after')
    def boundary(self):
        if (self.outcome == Outcome.QUALIFIED_IMPACT) != (self.impact is not None):
            raise ValueError('Only qualified assessments contain Impacts')
        if self.impact:
            i = self.impact
            if (self.candidate_id, self.revision, self.client_id, self.run_id, self.category, self.domain) != (
                i.candidate_id, i.revision, i.client_id, i.run_id, i.category, i.domain):
                raise ValueError('Impact and qualification disagree')
            if self.blockers or self.missing or self.effect_ids != (i.effect_id,):
                raise ValueError('Qualified Impact has blockers or inconsistent effect')
        elif not self.blockers:
            raise ValueError('Unqualified assessment must explain its outcome')
        if (self.source.kind == 'SYNTHETIC') != (self.domain == 'SYNTHETIC'):
            raise ValueError('Synthetic and production evidence cannot be relabelled')
        return self


class Aggregation(Contract):
    domain: Literal['PRODUCTION', 'SYNTHETIC']
    dimension: Dimension
    category: ImpactType
    currency: Literal['GBP'] = 'GBP'
    status: Literal['TOTAL', 'EMPTY', 'NOT_SAFELY_AGGREGATABLE']
    total: FinancialDecimal | None = None
    included: tuple[Identifier, ...] = ()
    excluded: tuple[Identifier, ...] = ()
    blockers: tuple[str, ...] = ()
