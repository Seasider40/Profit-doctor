"""Versioned corroboration policy and explicit temporal refusal."""
from typing import Literal
from profit_doctor.reasoning.domain.contracts import Contract
from profit_doctor.reasoning.hypothesis.contracts import Interpretation
from profit_doctor.reasoning.priority.contracts import Dimension


class AttentionEvidence(Contract):
    policy: Literal['ATTENTION-EVIDENCE-2.52.1'] = 'ATTENTION-EVIDENCE-2.52.1'
    interpretation: Interpretation | None = None
    unavailable_reason: str = 'No current qualified independent-corroboration Interpretation'
    temporal_policy: Literal['TEMPORAL-REFUSAL-2.52.1'] = 'TEMPORAL-REFUSAL-2.52.1'
    limitations: tuple[str, ...] = (
        'STRONG means exact corroboration under the existing evidence-quality contract only.',
        'No claim of population completeness, accounting reconciliation, causality or confidence uplift.',
        'Independence is retained provenance independence; undocumented copying remains possible.',
        'Commercial population comparability and restatement basis remain unqualified.',
    )

    def strength(self):
        i = self.interpretation
        if i is None:
            return Dimension(reason=self.unavailable_reason)
        if i.contract_key != 'INDEPENDENT_CORROBORATION' or i.hypothesis_class != 'EVIDENCE_QUALITY':
            raise ValueError('Only the named evidence-quality contract may establish corroboration')
        refs = tuple(sorted(set((i.object_id, *i.supporting, *i.contradictory, *i.contextual))))
        if i.contradictory or any(g.kind == 'CONFLICTING_EVIDENCE' for g in i.gaps):
            return Dimension(state='CONFLICTED', evidence=refs,
                reason='Retained counter-evidence or unresolved challenge blocks selective corroboration')
        if i.outcome == 'SUPPORTED':
            return Dimension(state='STRONG', evidence=refs,
                reason='Exact independently sourced reproduction with mandatory disconfirmation completed; proposition-scoped corroboration only')
        return Dimension(evidence=refs, reason='Independent corroboration not established: '+i.outcome)

    def temporal(self):
        return Dimension(reason='Commercial population coverage, per-measurement context and revision comparability are not qualified; repeated observations and dataset versions cannot establish recurrence')
