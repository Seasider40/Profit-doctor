"""Class-scoped propositions and immutable interpretation revisions."""
from typing import Literal
from pydantic import Field, model_validator
from profit_doctor.reasoning.domain.contracts import Contract, Identifier, ConfidenceProfile
from profit_doctor.reasoning.canonical.contracts import ReportingScope
from .gaps import EvidenceGap
from .registry import HypothesisClass, CandidateRole, REGISTRY

Outcome = Literal['SUPPORTED', 'PLAUSIBLE', 'UNRESOLVED', 'CONTRADICTED']


class Hypothesis(Contract):
    schema_version: Literal['HI-2.46.1'] = 'HI-2.46.1'
    object_id: Identifier
    client_id: Identifier
    run_id: Identifier
    finding_id: Identifier
    contract_key: str
    contract_version: Literal['HC-2.46.1'] = 'HC-2.46.1'
    hypothesis_class: HypothesisClass
    role: CandidateRole
    proposition: str
    scope: ReportingScope
    requirements: tuple[str, ...]
    status: Literal['GENERATED', 'SUPPORTED', 'PLAUSIBLE', 'UNRESOLVED', 'CONTRADICTED'] = 'GENERATED'
    revision: int = Field(default=1, strict=True, ge=1)
    confidence: ConfidenceProfile = Field(default_factory=ConfidenceProfile)

    @model_validator(mode='after')
    def governed(self):
        c = REGISTRY.get(self.contract_key)
        if c is None or (self.contract_version, self.hypothesis_class, self.role, self.proposition, self.requirements) != (
                c.version, c.hypothesis_class, c.role, c.proposition, c.requirements):
            raise ValueError('Unknown or altered governed Hypothesis contract')
        if self.confidence != ConfidenceProfile():
            raise ValueError('No confidence uplift is qualified in this release')
        return self


class Interpretation(Contract):
    schema_version: Literal['HI-2.46.1'] = 'HI-2.46.1'
    object_id: Identifier
    client_id: Identifier
    run_id: Identifier
    hypothesis_id: Identifier
    hypothesis_class: HypothesisClass
    proposition: str
    contract_key: str
    contract_version: Literal['HC-2.46.1'] = 'HC-2.46.1'
    revision: int = Field(default=1, strict=True, ge=1)
    outcome: Outcome
    supporting: tuple[Identifier, ...] = ()
    contradictory: tuple[Identifier, ...] = ()
    contextual: tuple[Identifier, ...] = ()
    alternatives: tuple[Identifier, ...] = ()
    gaps: tuple[EvidenceGap, ...] = ()
    checks: dict[str, Literal['PASS', 'GAP', 'CONFLICT', 'NOT_APPLICABLE']]
    evidence_snapshot: dict
    evidence_digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    confidence: ConfidenceProfile = Field(default_factory=ConfidenceProfile)
    limitations: tuple[str, ...] = (
        'Outcome applies only to the named class and proposition; not a causal conclusion.',
        'Independence applies to retained provenance; undocumented copying is not excluded.',
        'Search covers retained client/run evidence, not an exhaustive search of the world.',
    )

    @model_validator(mode='after')
    def boundary(self):
        c = REGISTRY.get(self.contract_key)
        if c is None or (self.hypothesis_class, self.proposition, self.contract_version) != (c.hypothesis_class, c.proposition, c.version):
            raise ValueError('Interpretation cannot change Hypothesis class or proposition')
        if set(self.checks) != set(c.disconfirmation):
            raise ValueError('Every mandatory disconfirmation check must be retained')
        if self.confidence != ConfidenceProfile() or not self.limitations:
            raise ValueError('No confidence uplift or unqualified interpretation')
        if self.outcome == 'SUPPORTED':
            if any(v not in ('PASS', 'NOT_APPLICABLE') for v in self.checks.values()) or not self.supporting:
                raise ValueError('Support requires evidence and completed disconfirmation')
            if any(g.blocks in ('SUPPORT', 'BOTH') for g in self.gaps):
                raise ValueError('An evidence gap blocks support')
        if self.outcome == 'CONTRADICTED' and (not self.contradictory or any(g.blocks in ('CONTRADICTION', 'BOTH') for g in self.gaps)):
            raise ValueError('Contradiction requires qualified counter-evidence')
        if self.hypothesis_class == 'ECONOMIC_MECHANISM' and self.outcome != 'UNRESOLVED':
            raise ValueError('Current mechanism contracts have unresolved semantic prerequisites')
        return self
