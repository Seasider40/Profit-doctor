"""Typed Story snapshots. Text is a deterministic projection, never authority."""
from typing import Literal
from pydantic import Field, model_validator
from profit_doctor.reasoning.domain.contracts import Contract, Identifier, ConfidenceProfile, MaterialityProfile
from profit_doctor.reasoning.canonical.contracts import ReportingScope, Measurement, CanonicalFact, CanonicalFinding
from profit_doctor.reasoning.hypothesis.contracts import Interpretation
from profit_doctor.reasoning.hypothesis.gaps import EvidenceGap
from profit_doctor.reasoning.graph.contracts import Characteristics
from .registry import REGISTRY, Resolution


class Story(Contract):
    schema_version: Literal['ES-2.47.1'] = 'ES-2.47.1'
    object_id: Identifier
    client_id: Identifier
    first_seen_run: Identifier
    latest_seen_run: Identifier
    finding_id: Identifier
    contract_key: str
    contract_version: Literal['SC-2.47.1'] = 'SC-2.47.1'
    semantic_key: str
    scope: ReportingScope
    resolution: Resolution = Resolution.CONDITION_STORY
    mechanism_state: Literal['UNRESOLVED'] = 'UNRESOLVED'
    status: Literal['SUPPORTED', 'INVESTIGATING', 'IMPROVING', 'WORSENING', 'PERSISTENT', 'RESOLVED']
    transition: Literal['FIRST_OBSERVATION', 'REASSESSMENT', 'COMPARABLE_PERIOD', 'REOPENED', 'NOT_COMPARABLE']
    revision: int = Field(default=1, strict=True, ge=1)
    condition_present: bool
    measurements: tuple[Measurement, ...]
    fact_ids: tuple[Identifier, ...]
    relationship_ids: tuple[Identifier, ...]
    interpretations: tuple[Interpretation, ...]
    evidence_characteristics: dict[str, Characteristics]
    contradictory: tuple[Identifier, ...] = ()
    mitigating: tuple[Identifier, ...] = ()
    gaps: tuple[EvidenceGap, ...]
    effect_ids: tuple[Identifier, ...] = ()
    confidence: ConfidenceProfile = Field(default_factory=ConfidenceProfile)
    materiality: MaterialityProfile = Field(default_factory=MaterialityProfile)
    evidence_snapshot: dict
    evidence_digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    limitations: tuple[str, ...] = (
        'Condition only; no economic mechanism, expected loss, benefit or Opportunity is established.',
        'Independence describes retained provenance, not statistical independence or absence of copying.',
        'Resolved means the specified condition is absent in qualified comparable evidence; not restoration of historical profit.',
    )

    @model_validator(mode='after')
    def governed(self):
        if self.contract_key not in REGISTRY:
            raise ValueError('Unknown or deferred Story Contract')
        if self.resolution != Resolution.CONDITION_STORY:
            raise ValueError('Positive mechanism-resolved Stories require a separately qualified mechanism contract')
        if self.confidence != ConfidenceProfile() or self.materiality != MaterialityProfile():
            raise ValueError('No confidence uplift or calculated Story materiality is qualified')
        if not self.fact_ids or not self.measurements or not self.interpretations or not self.gaps or not self.limitations:
            raise ValueError('Evidence, interpretations, mechanism gaps and limitations must remain explicit')
        if self.status == 'RESOLVED' and self.condition_present:
            raise ValueError('A present condition cannot be resolved')
        if self.status in ('SUPPORTED','IMPROVING','WORSENING','PERSISTENT') and not self.condition_present:
            raise ValueError('A supported Story requires its condition')
        origin = CanonicalFact.model_validate(self.evidence_snapshot['facts'][0])
        finding = CanonicalFinding.model_validate(self.evidence_snapshot['finding'])
        if (origin.client_id,origin.run_id,origin.scope) != (self.client_id,self.latest_seen_run,self.scope):
            raise ValueError('Story scope disagrees with its evidence snapshot')
        if finding.object_id != self.finding_id or finding.finding_type != REGISTRY[self.contract_key].finding_type:
            raise ValueError('Story family disagrees with its canonical Finding')
        if self.measurements != tuple(m for m in (origin.observed,origin.comparison,origin.derived) if m is not None):
            raise ValueError('Story measurements must preserve exact canonical semantics')
        return self


class StoryAssessment(Contract):
    outcome: Literal['CREATED', 'REVISED', 'REPLAYED', 'NO_STORY']
    reasons: tuple[str, ...] = ()
    story: Story | None = None


def project(story: Story):
    story = Story.from_json(story.to_json())
    contract = REGISTRY[story.contract_key]
    return dict(title=contract.title, condition=contract.condition if story.condition_present else
        'The specified condition is absent in this observation; see lifecycle and evidence limitations.',
        condition_present=story.condition_present, status=story.status, resolution=story.resolution.value,
        scope=story.scope.model_dump(mode='json'), measurements=[m.model_dump(mode='json') for m in story.measurements],
        mechanism_state=story.mechanism_state, evidence=[*story.fact_ids],
        interpretations=[dict(id=i.object_id, hypothesis_class=i.hypothesis_class.value, outcome=i.outcome) for i in story.interpretations],
        evidence_characteristics={k:v.model_dump(mode='json') for k,v in sorted(story.evidence_characteristics.items())},
        contradictory=list(story.contradictory), mitigating=list(story.mitigating),
        gaps=[g.model_dump(mode='json') for g in story.gaps],
        investigation_requirements=sorted({g.investigation_request for g in story.gaps}),
        limitations=list(story.limitations))
