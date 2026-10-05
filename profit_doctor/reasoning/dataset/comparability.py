"""Deterministic, dimensional dataset comparability; no score or metric inspection."""
from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timezone
import hashlib
import json

from profit_doctor.reasoning.bridge.qualification import Coverage, Period, ReportingBasis
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import LineageReference
from profit_doctor.reasoning.domain.vocabulary import SourceAuthority
from profit_doctor.reasoning.domain.service import ScopeError
from .contracts import (AssessmentOutcome, ComparabilityDimension, DatasetAssertion,
    DatasetComparability, DatasetContract, DatasetCoverage, DatasetRevisionRelationship,
    DimensionResult, DimensionState, TemporalEvidenceRole)


CLAIM_DIMENSIONS = {
    ComparabilityDimension.DATASET_FAMILY: 'family',
    ComparabilityDimension.SOURCE_LINEAGE: 'source_provider',
    ComparabilityDimension.POPULATION: 'population',
    ComparabilityDimension.INCLUSION_EXCLUSION: 'inclusion_exclusion',
    ComparabilityDimension.DEFINITION: 'definition',
    ComparabilityDimension.ORGANISATIONAL_SCOPE: 'organisational_scope',
    ComparabilityDimension.CURRENCY: 'currency',
    ComparabilityDimension.UNIT: 'unit',
    ComparabilityDimension.TIME_BASIS: 'time_basis',
}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _evidence(contract, assertion):
    return tuple(dict.fromkeys((contract.source_dataset, contract.source_version, contract.source_file,
                                *assertion.verification_evidence)))


def _assertion(left_contract, right_contract, dimension, field):
    left = getattr(left_contract, field)
    right = getattr(right_contract, field)
    left_ev, right_ev = _evidence(left_contract, left), _evidence(right_contract, right)
    for assertion, refs in ((left, left_ev), (right, right_ev)):
        if assertion.declared_value is not None and assertion.verified_value is not None:
            if _canonical(assertion.declared_value) != _canonical(assertion.verified_value):
                return DimensionResult(state=DimensionState.MISMATCH,
                    reason=f'{dimension.value}_DECLARATION_CONTRADICTED_BY_VERIFIED_EVIDENCE',
                    left_evidence=left_ev, right_evidence=right_ev)
    lv = left.verified_value if left.verified_value is not None else left.declared_value
    rv = right.verified_value if right.verified_value is not None else right.declared_value
    if lv is None or rv is None:
        return DimensionResult(state=DimensionState.INSUFFICIENT_EVIDENCE,
            reason=f'{dimension.value}_UNKNOWN', left_evidence=left_ev, right_evidence=right_ev)
    if _canonical(lv) != _canonical(rv):
        return DimensionResult(state=DimensionState.MISMATCH,
            reason=f'{dimension.value}_DIFFERS', left_evidence=left_ev, right_evidence=right_ev)
    fully_verified = (left.verified_value is not None and right.verified_value is not None)
    return DimensionResult(state=DimensionState.MATCH if fully_verified else DimensionState.LIMITED_MATCH,
        reason=f'{dimension.value}_MATCH' if fully_verified else f'{dimension.value}_MATCHES_BY_DECLARATION_ONLY',
        left_evidence=left_ev, right_evidence=right_ev,
        limitations=() if fully_verified else ('One or both matching values are human declarations, not independently verified.',))


def _valid_period(period: Period) -> bool:
    if not period.start or not period.end or period.basis == ReportingBasis.UNKNOWN:
        return False
    if period.start > period.end:
        return False
    if period.basis == ReportingBasis.MONTHLY:
        return period.start.day == 1 and period.end.day == monthrange(period.end.year, period.end.month)[1]
    if period.basis == ReportingBasis.QUARTERLY:
        months = (period.start.month - 1) // 3
        return (period.start.day == 1 and months * 3 + 1 == period.start.month
                and period.end.year == period.start.year
                and period.end.month == period.start.month + 2
                and period.end.day == monthrange(period.end.year, period.end.month)[1])
    if period.basis == ReportingBasis.ANNUAL:
        return period.start.month == 1 and period.start.day == 1 and period.end.month == 12 and period.end.day == 31 and period.start.year == period.end.year
    if period.basis == ReportingBasis.POINT_IN_TIME:
        return period.start == period.end
    if period.basis == ReportingBasis.ROLLING:
        return period.convention is not None
    return False


def _coverage(left_contract, right_contract):
    dimension = ComparabilityDimension.COVERAGE
    left_claim, right_claim = left_contract.coverage, right_contract.coverage
    left_ev, right_ev = _evidence(left_contract, left_claim), _evidence(right_contract, right_claim)
    for assertion in (left_claim, right_claim):
        if (assertion.declared_value is not None and assertion.verified_value is not None
                and _canonical(assertion.declared_value) != _canonical(assertion.verified_value)):
            return DimensionResult(state=DimensionState.MISMATCH, reason='COVERAGE_DECLARATION_CONTRADICTED_BY_VERIFIED_EVIDENCE',
                left_evidence=left_ev, right_evidence=right_ev)
    left_raw = left_claim.verified_value if left_claim.verified_value is not None else left_claim.declared_value
    right_raw = right_claim.verified_value if right_claim.verified_value is not None else right_claim.declared_value
    if left_raw is None or right_raw is None:
        return DimensionResult(state=DimensionState.INSUFFICIENT_EVIDENCE, reason='COVERAGE_UNKNOWN',
            left_evidence=left_ev, right_evidence=right_ev)
    try:
        left = DatasetCoverage.model_validate(left_raw)
        right = DatasetCoverage.model_validate(right_raw)
    except Exception:
        return DimensionResult(state=DimensionState.INSUFFICIENT_EVIDENCE, reason='COVERAGE_STRUCTURE_INVALID_OR_UNKNOWN',
            left_evidence=left_ev, right_evidence=right_ev)
    if left.completeness == Coverage.UNKNOWN or right.completeness == Coverage.UNKNOWN:
        return DimensionResult(state=DimensionState.INSUFFICIENT_EVIDENCE, reason='COVERAGE_COMPLETENESS_UNKNOWN',
            left_evidence=left_ev, right_evidence=right_ev)
    if left.completeness != right.completeness:
        return DimensionResult(state=DimensionState.MISMATCH, reason='COMPLETE_AND_PARTIAL_COVERAGE_DIFFER',
            left_evidence=left_ev, right_evidence=right_ev)
    if left.coverage_basis != right.coverage_basis:
        return DimensionResult(state=DimensionState.MISMATCH, reason='COVERAGE_BASIS_DIFFERS',
            left_evidence=left_ev, right_evidence=right_ev)
    if not _valid_period(left.period) or not _valid_period(right.period):
        return DimensionResult(state=DimensionState.INSUFFICIENT_EVIDENCE, reason='COVERED_PERIOD_OR_BASIS_INVALID',
            left_evidence=left_ev, right_evidence=right_ev)
    if (left.period.basis, left.period.nature, left.period.convention) != (right.period.basis, right.period.nature, right.period.convention):
        return DimensionResult(state=DimensionState.MISMATCH, reason='COVERED_PERIOD_BASIS_DIFFERS',
            left_evidence=left_ev, right_evidence=right_ev)
    if left.period.start == right.period.start and left.period.end == right.period.end:
        # Same reporting interval may be a restatement/replacement, but never a
        # second time observation. The temporal role below retains that distinction.
        return DimensionResult(state=DimensionState.MATCH if left_claim.verified_value and right_claim.verified_value else DimensionState.LIMITED_MATCH,
            reason='SAME_PERIOD_CONTRACTS_REQUIRE_REVISION_CLASSIFICATION', left_evidence=left_ev, right_evidence=right_ev,
            limitations=('Same-period datasets are not separate time observations.',))
    if left.period.start <= right.period.end and right.period.start <= left.period.end:
        return DimensionResult(state=DimensionState.MISMATCH, reason='COVERED_PERIODS_OVERLAP',
            left_evidence=left_ev, right_evidence=right_ev)
    limited = (left_claim.verified_value is None or right_claim.verified_value is None
               or left.completeness == Coverage.PARTIAL
               )
    reason = 'EQUIVALENT_PARTIAL_COVERAGE' if left.completeness == Coverage.PARTIAL else (
        'COVERAGE_BASIS_MATCHES_BY_DECLARATION_ONLY' if limited else 'COMPLETE_COVERAGE_AND_PERIOD_BASIS_MATCH')
    return DimensionResult(state=DimensionState.LIMITED_MATCH if limited else DimensionState.MATCH,
        reason=reason, left_evidence=left_ev, right_evidence=right_ev,
        limitations=('Matched coverage is partial or declaration-only.',) if limited else ())


def _source(left, right):
    dimension = ComparabilityDimension.SOURCE_LINEAGE
    result = _assertion(left, right, dimension, 'source_provider')
    if left.source_data_domain != right.source_data_domain:
        return result.model_copy(update={'state': DimensionState.MISMATCH, 'reason':'SOURCE_DATA_DOMAIN_DIFFERS'})
    return result


def _revision(left, right):
    dimension = ComparabilityDimension.REVISION_RELATIONSHIP
    base = _assertion(left, right, dimension, 'revision_relationship')
    values = [c.revision_relationship.verified_value if c.revision_relationship.verified_value is not None
              else c.revision_relationship.declared_value for c in (left, right)]
    if any(v is None for v in values):
        return DimensionResult(state=DimensionState.INSUFFICIENT_EVIDENCE, reason='REVISION_RELATIONSHIP_UNKNOWN',
            left_evidence=base.left_evidence, right_evidence=base.right_evidence), TemporalEvidenceRole.INDETERMINATE
    rels = [str(v) for v in values]
    revisions = {DatasetRevisionRelationship.RESTATEMENT.value, DatasetRevisionRelationship.CORRECTION.value,
        DatasetRevisionRelationship.SUPERSESSION.value, DatasetRevisionRelationship.PARTIAL_REPLACEMENT.value}
    if any(r in revisions for r in rels):
        return DimensionResult(state=DimensionState.LIMITED_MATCH, reason='EXPLICIT_REVISION_IS_NOT_A_NEW_TIME_OBSERVATION',
            left_evidence=base.left_evidence, right_evidence=base.right_evidence,
            limitations=('A correction/restatement/replacement remains evidence about an existing dataset period.',)), TemporalEvidenceRole.REVISION_ONLY
    if any(r != DatasetRevisionRelationship.NEW_OBSERVATION.value for r in rels):
        return DimensionResult(state=DimensionState.INSUFFICIENT_EVIDENCE, reason='REVISION_RELATIONSHIP_NOT_QUALIFIED',
            left_evidence=base.left_evidence, right_evidence=base.right_evidence), TemporalEvidenceRole.INDETERMINATE
    verified = all(c.revision_relationship.verified_value is not None for c in (left, right))
    periods = []
    for c in (left, right):
        raw = c.coverage.verified_value or c.coverage.declared_value
        try:
            periods.append(DatasetCoverage.model_validate(raw).period)
        except Exception:
            periods.append(None)
    distinct = (periods[0] is not None and periods[1] is not None
                and (periods[0].start, periods[0].end) != (periods[1].start, periods[1].end))
    if not verified or not distinct:
        role = TemporalEvidenceRole.INDETERMINATE
        reason = 'NEW_OBSERVATION_IS_DECLARED_ONLY' if not verified else 'SAME_OR_UNKNOWN_PERIOD_IS_NOT_NEW_TIME_EVIDENCE'
    else:
        role = TemporalEvidenceRole.NEW_OBSERVATION
        reason = 'SOURCE_VERIFIED_NEW_OBSERVATIONS_IN_DISTINCT_PERIODS'
    return DimensionResult(state=DimensionState.MATCH if verified and distinct else DimensionState.LIMITED_MATCH,
        reason=reason, left_evidence=base.left_evidence, right_evidence=base.right_evidence,
        limitations=() if verified and distinct else ('A declaration alone cannot establish new temporal evidence.',)), role


def assess_dataset_comparability(left: DatasetContract, right: DatasetContract, *,
                                 assessment_id: str | None = None, run_id: str | None = None,
                                 assessed_at: datetime | None = None) -> DatasetComparability:
    """Assess two immutable contracts. This evaluator never reads calculated metrics."""
    if left.client_id != right.client_id:
        raise ScopeError('Cross-client dataset comparison is prohibited')
    if left.contract_id == right.contract_id:
        raise ValueError('A contract cannot be compared with itself')
    dimensions = {dimension: _assertion(left, right, dimension, field)
                  for dimension, field in CLAIM_DIMENSIONS.items()}
    dimensions[ComparabilityDimension.COVERAGE] = _coverage(left, right)
    dimensions[ComparabilityDimension.SOURCE_LINEAGE] = _source(left, right)
    dimensions[ComparabilityDimension.REVISION_RELATIONSHIP], role = _revision(left, right)
    states = [value.state for value in dimensions.values()]
    outcome = (AssessmentOutcome.NOT_COMPARABLE if DimensionState.MISMATCH in states else
        AssessmentOutcome.INSUFFICIENT_EVIDENCE if DimensionState.INSUFFICIENT_EVIDENCE in states else
        AssessmentOutcome.COMPARABLE_WITH_LIMITATIONS if DimensionState.LIMITED_MATCH in states else
        AssessmentOutcome.COMPARABLE)
    limitations = tuple(sorted({limitation for result in dimensions.values() for limitation in result.limitations}))
    pair = tuple(sorted((left.contract_id, right.contract_id)))
    identifier = assessment_id or identity('dataset-comparability-2.53.1', left.client_id, pair, 'DATASET-COMPARABILITY-2.53.1')
    return DatasetComparability(assessment_id=identifier, client_id=left.client_id,
        run_id=run_id or left.recorded_run_id, left_contract_id=left.contract_id,
        right_contract_id=right.contract_id, outcome=outcome, temporal_evidence_role=role,
        dimensions=dimensions, limitations=limitations, assessed_at=assessed_at or datetime.now(timezone.utc))
