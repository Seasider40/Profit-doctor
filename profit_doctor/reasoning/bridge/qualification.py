"""BIQ-2.48.1: explicit comparability checks, not evidence certification.

The pure evaluator checks a resolved evidence description. It cannot establish
that supplied claims are true. Application callers use BridgeInputResolver,
which accepts Fact identities, not caller assertions of coverage/comparability.
No result from this module is a financial Bridge or a persisted reasoning object.
"""
from datetime import date
from calendar import monthrange
from enum import StrEnum
import hashlib
from typing import Literal

from pydantic import Field, model_validator

from profit_doctor.reasoning.canonical.contracts import Measurement
from profit_doctor.reasoning.domain.contracts import Contract, Identifier, LineageReference


class BridgeFamily(StrEnum):
    REVENUE_BRIDGE = 'REVENUE_BRIDGE'
    MARGIN_OR_PROFIT_BRIDGE = 'MARGIN_OR_PROFIT_BRIDGE'
    PROFIT_TO_CASH_BRIDGE = 'PROFIT_TO_CASH_BRIDGE'
    WORKING_CAPITAL_BRIDGE = 'WORKING_CAPITAL_BRIDGE'
    COST_TO_OUTPUT_BRIDGE = 'COST_TO_OUTPUT_BRIDGE'


class Outcome(StrEnum):
    QUALIFIED = 'QUALIFIED'
    PARTIALLY_QUALIFIED = 'PARTIALLY_QUALIFIED'
    INSUFFICIENT_EVIDENCE = 'INSUFFICIENT_EVIDENCE'
    INCOMPARABLE = 'INCOMPARABLE'
    INVALID = 'INVALID'


class ReportingBasis(StrEnum):
    MONTHLY = 'MONTHLY'
    QUARTERLY = 'QUARTERLY'
    ANNUAL = 'ANNUAL'
    YTD = 'YTD'
    ROLLING = 'ROLLING'
    POINT_IN_TIME = 'POINT_IN_TIME'
    OTHER_GOVERNED = 'OTHER_GOVERNED'
    UNKNOWN = 'UNKNOWN'


class Coverage(StrEnum):
    COMPLETE = 'COMPLETE'
    PARTIAL = 'PARTIAL'
    UNKNOWN = 'UNKNOWN'


class VersionRelationship(StrEnum):
    COMPATIBLE = 'COMPATIBLE'
    RESTATED_COMPATIBLE = 'RESTATED_COMPATIBLE'
    SUPERSEDED = 'SUPERSEDED'
    INCOMPATIBLE = 'INCOMPATIBLE'
    UNKNOWN = 'UNKNOWN'


class Period(Contract):
    start: date | None = None
    end: date | None = None
    basis: ReportingBasis = ReportingBasis.UNKNOWN
    convention: str | None = Field(default=None, min_length=1)
    nature: Literal['FLOW', 'STOCK', 'RATE', 'UNKNOWN'] = 'UNKNOWN'
    # Bounds, when known, are inclusive. Unknown boundaries are never split.
    @property
    def duration_days(self):
        return (self.end - self.start).days + 1 if self.start and self.end else None

    @model_validator(mode='after')
    def valid_bounds(self):
        if self.start and self.end and self.start > self.end:
            raise ValueError('Reversed period')
        if self.basis == ReportingBasis.POINT_IN_TIME and self.start and self.end and self.start != self.end:
            raise ValueError('Point-in-time evidence has one date')
        return self


class RetainedSource(Contract):
    """Context recovered from source rows; not certified slot-period semantics."""
    reference: str = Field(min_length=1)
    period_from: date | None = None
    period_to: date | None = None
    version_number: int | None = None
    ingestion_status: str | None = None
    primitive_id: str | None = None
    method_id: str | None = None
    result_status: str | None = None
    row_count: int | None = None


class Endpoint(Contract):
    fact_id: Identifier
    client_id: Identifier
    run_id: Identifier
    measurement: Measurement
    entity_type: str | None = None
    entity_id: str | None = None
    # Same entity does not imply the same product/customer population.
    segment_basis: str | None = Field(default=None, min_length=1)
    economic_basis: str | None = Field(default=None, min_length=1)
    period: Period = Field(default_factory=Period)
    coverage: Coverage = Coverage.UNKNOWN
    coverage_evidence: tuple[LineageReference, ...] = ()
    source_versions: tuple[str, ...] = ()
    retained_sources: tuple[RetainedSource, ...] = ()
    lineage: tuple[LineageReference, ...]
    lineage_complete: bool = False
    source_snapshot: str = Field(pattern='^[a-f0-9]{64}$')
    eligible: bool = False
    limitations: tuple[str, ...] = ()

    @model_validator(mode='after')
    def scope(self):
        if (self.entity_type is None) != (self.entity_id is None):
            raise ValueError('Entity kind and identity must be retained together')
        if any(r.client_id != self.client_id for r in self.lineage + self.coverage_evidence):
            raise ValueError('Foreign endpoint lineage')
        return self


class ComparisonInput(Contract):
    contract_version: Literal['BIQ-2.48.1'] = 'BIQ-2.48.1'
    family: BridgeFamily
    opening: Endpoint
    closing: Endpoint
    version_relationship: VersionRelationship = VersionRelationship.UNKNOWN
    version_evidence: tuple[LineageReference, ...] = ()
    # Explicitly identifies the policy establishing compatibility/restatement.
    version_basis: str | None = Field(default=None, min_length=1)


class Qualification(Contract):
    contract_version: Literal['BIQ-2.48.1'] = 'BIQ-2.48.1'
    assessment_id: str = Field(pattern='^biq_[a-f0-9]{60}$')
    input: ComparisonInput
    outcome: Outcome
    gaps: tuple[str, ...]
    # Full input snapshot is retained; changed evidence has a different identity.
    # This is immutable assessment serialization, not a database history writer.

    @model_validator(mode='after')
    def consistent_result(self):
        outcome, gaps = _evaluate(self.input)
        if (self.outcome, self.gaps, self.assessment_id) != (outcome, gaps, _identity(self.input)):
            raise ValueError('Qualification result disagrees with its evidence descriptor')
        return self


# An allowlist of endpoint measures, not a generic financial fallback. Composite
# working-capital and cross-metric bridges need separate qualified contracts.
MEASURES = {
    BridgeFamily.REVENUE_BRIDGE: {('revenue', 'CURRENCY', 'FLOW')},
    BridgeFamily.MARGIN_OR_PROFIT_BRIDGE: {
        ('contribution_0', 'CURRENCY', 'FLOW'),
        ('contribution_0_margin', 'PERCENTAGE', 'RATE')},
}


def _evaluate(value):
    a, b = value.opening, value.closing
    invalid, mismatch, missing, partial = [], [], [], []
    if value.family not in MEASURES:
        missing.append('FAMILY_CONTRACT_NOT_QUALIFIED')
    else:
        for endpoint in (a, b):
            key = (endpoint.measurement.metric, endpoint.measurement.unit.value, endpoint.period.nature)
            if endpoint.period.nature == 'UNKNOWN':
                missing.append('MEASURE_NATURE_UNKNOWN')
            elif key not in MEASURES[value.family]:
                mismatch.append('METRIC_UNIT_OR_STOCK_FLOW_NOT_ALLOWED')
    if a.client_id != b.client_id:
        invalid.append('CLIENT_MISMATCH')
    if any(r.client_id != a.client_id for r in value.version_evidence):
        invalid.append('VERSION_EVIDENCE_CLIENT_MISMATCH')
    if (a.entity_type, a.entity_id) != (b.entity_type, b.entity_id):
        mismatch.append('ENTITY_SCOPE_MISMATCH')
    if (a.measurement.metric, a.measurement.unit, a.measurement.currency) != (
            b.measurement.metric, b.measurement.unit, b.measurement.currency):
        mismatch.append('METRIC_UNIT_CURRENCY_MISMATCH')
    for name in ('segment_basis', 'economic_basis'):
        left, right = getattr(a, name), getattr(b, name)
        if left is None or right is None:
            missing.append(name.upper() + '_UNKNOWN')
        elif left != right:
            mismatch.append(name.upper() + '_MISMATCH')
    for endpoint in (a, b):
        if not endpoint.eligible:
            invalid.append('SOURCE_NOT_ELIGIBLE')
        if not endpoint.lineage or not endpoint.lineage_complete:
            missing.append('LINEAGE_INCOMPLETE')
        if not endpoint.source_versions:
            missing.append('SOURCE_VERSION_UNKNOWN')
        if endpoint.coverage == Coverage.UNKNOWN or not endpoint.coverage_evidence:
            missing.append('COVERAGE_NOT_ESTABLISHED')
        if endpoint.coverage == Coverage.PARTIAL:
            partial.append('PARTIAL_COVERAGE')
        if endpoint.limitations:
            partial.append('SOURCE_LIMITATIONS')
        p = endpoint.period
        if not all((p.start, p.end, p.convention)) or p.basis == ReportingBasis.UNKNOWN:
            missing.append('PERIOD_BASIS_NOT_ESTABLISHED')
        elif p.basis in (ReportingBasis.MONTHLY, ReportingBasis.QUARTERLY, ReportingBasis.ANNUAL):
            months = {ReportingBasis.MONTHLY: 1, ReportingBasis.QUARTERLY: 3, ReportingBasis.ANNUAL: 12}[p.basis]
            expected_end_month = p.start.month + months - 1
            calendar_valid = (p.start.day == 1 and (p.start.month - 1) % months == 0 and
                expected_end_month <= 12 and p.end.year == p.start.year and
                p.end.month == expected_end_month and p.end.day == monthrange(p.end.year, p.end.month)[1])
            if not calendar_valid:
                mismatch.append('PERIOD_NOT_FULL_CALENDAR_INTERVAL')
        else:
            missing.append('REPORTING_CONVENTION_POLICY_NOT_QUALIFIED')
    if (a.period.basis, a.period.convention, a.period.nature) != (
            b.period.basis, b.period.convention, b.period.nature):
        mismatch.append('REPORTING_BASIS_MISMATCH')
    if a.period.end and b.period.start and a.period.end >= b.period.start:
        mismatch.append('PERIODS_NOT_ORDERED_AND_DISJOINT')
    if a.period.duration_days and b.period.duration_days and a.period.duration_days != b.period.duration_days:
        mismatch.append('DURATION_MISMATCH_NO_NORMALISATION')
    if value.version_relationship in (VersionRelationship.SUPERSEDED, VersionRelationship.INCOMPATIBLE):
        mismatch.append('SOURCE_VERSION_INCOMPATIBLE')
    elif value.version_relationship == VersionRelationship.UNKNOWN or not value.version_evidence or not value.version_basis:
        missing.append('VERSION_RESTATEMENT_BASIS_NOT_ESTABLISHED')
    gaps = tuple(sorted(set(invalid + mismatch + missing + partial)))
    outcome = (Outcome.INVALID if invalid else Outcome.INCOMPARABLE if mismatch else
               Outcome.INSUFFICIENT_EVIDENCE if missing else Outcome.PARTIALLY_QUALIFIED if partial else Outcome.QUALIFIED)
    return outcome, gaps


def _identity(value):
    return 'biq_' + hashlib.sha256(value.to_json().encode()).hexdigest()[:60]


def qualify(value: ComparisonInput) -> Qualification:
    """Evaluate explicit descriptors; does not resolve or certify source claims."""
    value = ComparisonInput.from_json(value.to_json())
    outcome, gaps = _evaluate(value)
    return Qualification(assessment_id=_identity(value), input=value, outcome=outcome, gaps=gaps)
