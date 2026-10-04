"""Read-only evidence provider over existing owning services and immutable history.

No hypothesis generation/reassessment, context invention or additional tables.
The caller must explicitly assess Interpretations through their owning service.
"""
import json
from sqlalchemy import select
from profit_doctor.persistence import hypothesis_schema as tables
from profit_doctor.reasoning.domain.service import ScopeError
from profit_doctor.reasoning.hypothesis.contracts import Interpretation
from profit_doctor.reasoning.hypothesis.service import HypothesisService, digest
from profit_doctor.reasoning.priority.contracts import Dimension
from profit_doctor.reasoning.priority.service import PriorityService
from .contracts import AttentionEvidence


class AttentionPriorityService(PriorityService):
    def __init__(self, canonical, run_id, opportunities=None):
        super().__init__(canonical, run_id, opportunities)
        self.hypotheses = HypothesisService(self.session, self.client_id, run_id,
            canonical.foundation.actor, canonical.source)

    def _evidence(self, kind, source_id):
        if kind != 'FINDING':
            return AttentionEvidence(unavailable_reason='No qualified Opportunity evidence-strength provider; collection eligibility does not establish general corroboration')
        ids = self.session.scalars(select(tables.hypothesis.c.object_id).where(
            tables.hypothesis.c.client_id == self.client_id,
            tables.hypothesis.c.finding_id == source_id)).all()
        candidates = []
        for oid in ids:
            obj = self.canonical.foundation.get_object(oid)
            if obj.run_id != self.run_id:
                continue
            h = self.hypotheses.get(oid)
            if h.contract_key == 'INDEPENDENT_CORROBORATION':
                candidates.append(h)
        if not candidates:
            return AttentionEvidence()
        if len(candidates) != 1:
            raise ScopeError('Ambiguous corroboration owner')
        h = candidates[0]
        history = self.hypotheses.history(h.object_id)
        if not history:
            return AttentionEvidence()
        latest = history[-1]
        # Reuse the frozen mandatory evidence search without invoking its writer.
        anchor, _, _, checks, gaps, snapshot = self.hypotheses._search(h)
        snapshot['alternatives'] = [peer.object_id for peer in self.hypotheses.peers(h.object_id)]
        snapshot['origin_fact'] = anchor.model_dump(mode='json')
        if (snapshot != latest.evidence_snapshot
                or any(v != 'PASS' and latest.checks[k] != v for k, v in checks.items())
                or any(g not in latest.gaps for g in gaps)):
            return AttentionEvidence(unavailable_reason='Corroboration evidence changed; explicit owning-service disconfirmation/reassessment required')
        return AttentionEvidence(interpretation=latest)

    def _basis(self, kind, source_id):
        base = super()._basis(kind, source_id)
        evidence = self._evidence(kind, source_id)
        strength = evidence.strength()
        # A declared Finding contradiction remains visible even without an Interpretation.
        if base.evidence_strength.state == 'CONFLICTED':
            strength = base.evidence_strength
        snapshot = json.dumps({'attention': evidence.model_dump(mode='json'),
            'source': json.loads(base.source_snapshot)}, sort_keys=True, separators=(',', ':'))
        return base.model_copy(update=dict(evidence_strength=strength,
            persistence=evidence.temporal(), source_snapshot=snapshot,
            limitations=base.limitations + evidence.limitations))

    def _validate_basis(self, basis, subject, run_id):
        raw = json.loads(basis.source_snapshot)
        if 'attention' not in raw:
            return super()._validate_basis(basis, subject, run_id)
        if any(getattr(basis, n).state != 'NOT_ASSESSED' for n in
                ('materiality', 'urgency', 'controllability', 'persistence')):
            raise ScopeError('Unqualified attention dimension')
        evidence = AttentionEvidence.model_validate(raw['attention'])
        if evidence.limitations != AttentionEvidence().limitations:
            raise ScopeError('Attention limitations cannot be removed')
        expected = evidence.strength()
        if subject['source_kind'] == 'FINDING':
            finding = raw['source']['finding']
            if finding['object_id'] != subject['source_id'] or finding['client_id'] != self.client_id:
                raise ScopeError('Attention source scope mismatch')
            if finding['contradictory_evidence']:
                expected = Dimension(state='CONFLICTED', evidence=tuple(finding['contradictory_evidence']),
                    reason='Declared counter-evidence remains unresolved')
        elif evidence.interpretation is not None:
            raise ScopeError('Opportunity cannot borrow Finding corroboration')
        i = evidence.interpretation
        if i is not None:
            if (i.evidence_snapshot.get('finding') != raw['source']['finding']
                    or i.evidence_snapshot.get('origin_fact') not in raw['source']['facts']):
                raise ScopeError('Attention proof does not describe this source snapshot')
            # Read exact immutable revision, not mutable current-source state.
            row = self.session.execute(select(tables.interpretation).where(
                tables.interpretation.c.object_id == i.object_id,
                tables.interpretation.c.revision == i.revision,
                tables.interpretation.c.client_id == self.client_id)).mappings().one_or_none()
            hrow = self.session.execute(select(tables.hypothesis).where(
                tables.hypothesis.c.object_id == i.hypothesis_id,
                tables.hypothesis.c.client_id == self.client_id)).mappings().one_or_none()
            if (row is None or hrow is None or Interpretation.from_json(row['document']) != i
                    or row['hypothesis_id'] != i.hypothesis_id or hrow['finding_id'] != subject['source_id']
                    or i.client_id != self.client_id or i.run_id != run_id):
                raise ScopeError('Attention proof is not its scoped immutable Interpretation')
            fingerprint = digest({'evidence': i.evidence_snapshot, 'contract': i.contract_key,
                'version': i.contract_version, 'checks': i.checks,
                'gaps': [g.model_dump(mode='json') for g in i.gaps]})
            if fingerprint != i.evidence_digest:
                raise ScopeError('Attention Interpretation digest mismatch')
        if basis.evidence_strength != expected or basis.persistence != evidence.temporal():
            raise ScopeError('Attention dimensions disagree with governed proof')
