"""Opt-in governed assessment. No downstream cutover or automatic causal edges.

Caller owns source connection, Session and the complete transaction. Every
assessment searches retained evidence, including unlinked counter-evidence.
"""
import hashlib
import json
from sqlalchemy import insert, select, update
from profit_doctor.persistence import reasoning_schema as foundation_tables
from profit_doctor.persistence import hypothesis_schema as tables
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import ReasoningObject, LineageReference, EvidenceLink, AuditEvent, now
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.graph.service import EvidenceGraph
from .contracts import Hypothesis, Interpretation
from .gaps import EvidenceGap
from .registry import REGISTRY, CHECKS


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def measurements(fact):
    # Decimal numeric equality, not lexical equality of lossless JSON strings.
    return fact.observed, fact.comparison, fact.derived


def semantics(fact):
    return tuple((v.metric, v.unit, v.basis, v.currency) if v else None for v in (fact.observed, fact.comparison, fact.derived))


class HypothesisService:
    def __init__(self, session, client_id, run_id, actor, source):
        self.graph = EvidenceGraph(session, client_id, run_id, actor, source)
        self.canonical, self.foundation = self.graph.canonical, self.graph.foundation
        self.session, self.client_id, self.run_id = session, client_id, run_id

    def _origin(self, finding_id):
        finding = self.canonical.get_finding(finding_id)
        observations = [o for o in finding.observations if o.run_id == self.run_id]
        if len(observations) != 1:
            raise ScopeError('One explicit Finding observation in the analytical run is required')
        fact = self.canonical.get_fact(observations[0].fact_id)
        return finding, fact

    def _lineage(self, object_id):
        obj = self.foundation.get_object(object_id)
        return (LineageReference(kind='DERIVED_ANCESTOR', store='CANONICAL', resource='reasoning_object_v243',
            source_id=object_id, client_id=self.client_id, run_id=obj.run_id),)

    def _link(self, source_id, target_id, relationship, role):
        lid = identity('hypothesis-link', source_id, target_id, relationship)
        if not self.session.scalar(select(foundation_tables.evidence_link.c.link_id).where(foundation_tables.evidence_link.c.link_id == lid)):
            source = self.foundation.get_object(source_id)
            self.foundation.link_evidence(EvidenceLink(link_id=lid, client_id=self.client_id, run_id=self.run_id,
                source_id=source_id, target_id=target_id, source_authority=source.source_authority,
                relationship_type=relationship, evidence_role=role))

    def generate(self, finding_id):
        finding, fact = self._origin(finding_id)
        if finding.assessment.outcome != 'FINDING_CREATED' or not self.graph.node(finding_id).eligible:
            raise ValueError('Generation requires an eligible canonical Finding, not a bare identity')
        result = []
        for c in REGISTRY.values():
            if finding.finding_type not in c.findings:
                continue
            oid = identity('hypothesis', self.client_id, self.run_id, finding_id, c.key, c.version)
            if self.session.scalar(select(tables.hypothesis.c.object_id).where(tables.hypothesis.c.object_id == oid)):
                result.append(self.get(oid))
                continue
            value = Hypothesis(object_id=oid, client_id=self.client_id, run_id=self.run_id, finding_id=finding_id,
                contract_key=c.key, hypothesis_class=c.hypothesis_class, role=c.role, proposition=c.proposition,
                scope=fact.scope, requirements=c.requirements)
            self.foundation.create_object(ReasoningObject(object_id=oid, client_id=self.client_id, run_id=self.run_id,
                object_type='HYPOTHESIS', source_authority='SYSTEM_DERIVED', status='GENERATED',
                period_from=fact.scope.period_from, period_to=fact.scope.period_to, lineage=self._lineage(finding_id)))
            self.session.execute(insert(tables.hypothesis).values(object_id=oid, client_id=self.client_id,
                finding_id=finding_id, revision=1, document=value.to_json()))
            self._link(finding_id, oid, 'CONTEXTUALISES', 'CONDITION')
            result.append(value)
        return tuple(result)

    def get(self, object_id):
        row = self.session.execute(select(tables.hypothesis).where(tables.hypothesis.c.object_id == object_id,
            tables.hypothesis.c.client_id == self.client_id)).mappings().one_or_none()
        if row is None:
            raise ScopeError('Hypothesis missing or outside client scope')
        value = Hypothesis.from_json(row['document'])
        env = self.foundation.get_object(object_id)
        if (value.object_id, value.client_id, value.finding_id, value.revision) != (
                row['object_id'], row['client_id'], row['finding_id'], row['revision']):
            raise ScopeError('Hypothesis document disagrees with indexed scope')
        if (env.object_type, env.run_id, env.revision, env.status, env.period_from, env.period_to, env.lineage) != (
                'HYPOTHESIS', value.run_id, value.revision, value.status, value.scope.period_from,
                value.scope.period_to, self._lineage(value.finding_id)) or value.run_id != self.run_id:
            raise ScopeError('Hypothesis disagrees with foundation identity or requested run')
        finding, fact = self._origin(value.finding_id)
        if finding.finding_type not in REGISTRY[value.contract_key].findings or value.scope != fact.scope:
            raise ScopeError('Hypothesis origin or scope changed')
        return value

    def peers(self, object_id):
        h = self.get(object_id)
        ids = self.session.scalars(select(tables.hypothesis.c.object_id).where(
            tables.hypothesis.c.client_id == self.client_id, tables.hypothesis.c.finding_id == h.finding_id)
            .order_by(tables.hypothesis.c.object_id))
        return tuple(self.get(oid) for oid in ids if oid != object_id and
                     self.foundation.get_object(oid).run_id == self.run_id)

    def history(self, hypothesis_id):
        h = self.get(hypothesis_id)
        rows = self.session.execute(select(tables.interpretation).where(
            tables.interpretation.c.hypothesis_id == h.object_id,
            tables.interpretation.c.client_id == self.client_id).order_by(tables.interpretation.c.revision)).mappings()
        result = []
        for row in rows:
            value = Interpretation.from_json(row['document'])
            if (value.object_id, value.client_id, value.hypothesis_id, value.revision) != (
                    row['object_id'], row['client_id'], row['hypothesis_id'], row['revision']):
                raise ScopeError('Interpretation document disagrees with indexed scope')
            if (value.hypothesis_class, value.proposition, value.contract_key, value.run_id) != (
                    h.hypothesis_class, h.proposition, h.contract_key, h.run_id):
                raise ScopeError('Interpretation changes its Hypothesis semantics')
            env = self.foundation.get_object(value.object_id)
            if env.object_type != 'INTERPRETATION' or env.run_id != self.run_id or env.revision < value.revision:
                raise ScopeError('Interpretation foundation mismatch')
            expected_digest = digest({'evidence': value.evidence_snapshot, 'contract': value.contract_key,
                'version': value.contract_version, 'checks': value.checks,
                'gaps': [g.model_dump(mode='json') for g in value.gaps]})
            if value.evidence_digest != expected_digest:
                raise ScopeError('Interpretation evidence snapshot digest mismatch')
            result.append(value)
        if result:
            latest = result[-1]
            env = self.foundation.get_object(latest.object_id)
            if (env.revision, env.status, h.status) != (latest.revision, latest.outcome, latest.outcome):
                raise ScopeError('Current assessment state disagrees with foundation or Hypothesis')
        return tuple(result)

    def _gap(self, h, kind, missing, reason, blocks='SUPPORT'):
        return EvidenceGap(kind=kind, missing_evidence=missing, reason_required=reason,
            dimension='CUSTOMER_PRODUCT_PERIOD' if h.hypothesis_class == 'ECONOMIC_MECHANISM' else 'EVIDENCE',
            scope=h.scope, investigation_request='Obtain governed evidence: ' + missing,
            blocks=blocks, related_objects=(h.finding_id,))

    def _search(self, h):
        finding, anchor = self._origin(h.finding_id)
        checks = dict.fromkeys(CHECKS, 'PASS')
        gaps, candidates, context, snapshot = [], [], [], {'finding': finding.model_dump(mode='json'), 'facts': [], 'links': []}
        try:
            anchor_node = self.graph.node(anchor.object_id)
            origin_ok = anchor_node.eligible and finding.assessment.outcome == 'FINDING_CREATED'
            if not anchor_node.ancestry.complete:
                checks['LINEAGE'] = 'GAP'
                gaps.append(self._gap(h, 'INCOMPLETE_LINEAGE', 'Complete origin ancestry', 'Unknown source paths cannot establish the proposed evidence quality', 'BOTH'))
        except (ScopeError, RevisionConflict):
            origin_ok = False
        if not origin_ok:
            checks['ORIGIN_CURRENT'] = 'GAP'
            gaps.append(self._gap(h, 'MISSING_EVIDENCE', 'Current eligible Finding observation', 'The condition changed or its source cannot be verified', 'BOTH'))
        # Scan all retained same-run Facts, not just selected supporting links.
        t = foundation_tables.reasoning_object
        ids = tuple(self.session.scalars(select(t.c.object_id).where(t.c.client_id == self.client_id,
            t.c.run_id == self.run_id, t.c.object_type == 'FACT').order_by(t.c.object_id)))
        for oid in ids:
            fact = self.canonical.get_fact(oid)
            snapshot['facts'].append(fact.model_dump(mode='json'))
            if oid == anchor.object_id or (fact.scope.entity_type, fact.scope.entity_id) != (h.scope.entity_type, h.scope.entity_id):
                continue
            if semantics(fact) != semantics(anchor):
                continue
            try:
                node = self.graph.node(oid)
                chars = self.graph.characteristics(anchor.object_id, oid)
                snapshot['facts'].append({'object_id': oid, 'node': node.model_dump(mode='json'), 'characteristics': chars.model_dump(mode='json')})
                candidates.append((fact, node, chars, measurements(fact) == measurements(anchor)))
            except (ScopeError, RevisionConflict):
                checks['LINEAGE'] = 'GAP'
                gaps.append(self._gap(h, 'INCOMPLETE_LINEAGE', 'Current source and ancestry', 'A relevant Fact cannot be revalidated', 'BOTH'))
        # Inspect declared contradictions/context in either orientation, preserving authority.
        link_ids = set()
        for endpoint in (h.finding_id, anchor.object_id):
            for link in self.graph.neighbours(endpoint):
                if link.link_id in link_ids:
                    continue
                link_ids.add(link.link_id)
                snapshot['links'].append(link.model_dump(mode='json'))
                if link.relationship_type in ('CONTRADICTS', 'MITIGATES', 'CONTEXTUALISES'):
                    other = link.source_id if link.target_id == endpoint else link.target_id
                    other_object = self.foundation.get_object(other)
                    if other_object.object_type in ('HYPOTHESIS', 'INTERPRETATION'):
                        continue
                    context.append(other)
                    if link.relationship_type == 'CONTEXTUALISES' and other_object.source_authority == 'SYSTEM_DERIVED':
                        continue
                    checks['COUNTER_EVIDENCE'] = 'GAP'
                    gaps.append(self._gap(h, 'CONFLICTING_EVIDENCE', 'Resolution of declared contextual/counter-evidence',
                        'Declared evidence is not silently promoted to verified contradiction'))
        snapshot['links'].sort(key=lambda x: x['link_id'])
        snapshot['checks_origin'] = origin_ok
        return anchor, candidates, tuple(sorted(set(context))), checks, gaps, snapshot

    def assess(self, hypothesis_id, *, expected_revision=None):
        h = self.get(hypothesis_id)
        if expected_revision is not None and (type(expected_revision) is not int or expected_revision != h.revision):
            raise RevisionConflict('Hypothesis revision changed')
        anchor, candidates, context, checks, gaps, snapshot = self._search(h)
        peers = tuple(p.object_id for p in self.peers(h.object_id))
        snapshot['alternatives'] = list(peers)
        support, counter = [], []
        outcome = 'UNRESOLVED'
        if h.hypothesis_class == 'ECONOMIC_MECHANISM':
            checks['SEGMENTATION'] = 'GAP'
            checks['ALTERNATIVES'] = 'GAP'
            for requirement in h.requirements:
                gaps.append(self._gap(h, 'UNSAFE_SEMANTICS', requirement,
                    'Frozen canonical mappings/graph do not establish this mechanism requirement; correlation and portfolio residual cannot repair it', 'BOTH'))
        else:
            eligible = [(f,n,c,equal) for f,n,c,equal in candidates if n.eligible and n.authority == 'SYSTEM_DERIVED' and n.ancestry.complete]
            comparable = [(f,n,c,equal) for f,n,c,equal in eligible if c.temporal == 'SAME_COMPARABLE_PERIOD']
            matching = [(f,n,c) for f,n,c,equal in comparable if equal]
            conflicting = [(f,n,c) for f,n,c,equal in comparable if not equal and c.independence == 'INDEPENDENT']
            if any(not equal and c.independence != 'INDEPENDENT' for f,n,c,equal in comparable):
                checks['COUNTER_EVIDENCE'] = 'GAP'
                gaps.append(self._gap(h, 'CONFLICTING_EVIDENCE', 'Resolution of disagreeing shared/unknown-source measurements', 'Disagreement cannot be omitted merely because it is not independent'))
            if h.contract_key == 'INDEPENDENT_CORROBORATION':
                support = [f.object_id for f,n,c in matching if c.independence == 'INDEPENDENT']
                counter = [f.object_id for f,n,c in conflicting]
                outcome = 'CONTRADICTED' if counter else 'SUPPORTED' if support else 'PLAUSIBLE' if matching else 'UNRESOLVED'
                if not support:
                    checks['SHARED_ANCESTRY'] = 'GAP'
                    gaps.append(self._gap(h, 'SHARED_ANCESTRY', 'Independent exact comparable reproduction', 'Shared/unknown ancestry cannot establish independent corroboration'))
            elif h.contract_key == 'SHARED_CORROBORATION':
                shared = ('SAME_ANCESTRY', 'SUBSTANTIALLY_SHARED')
                support = [f.object_id for f,n,c in matching if c.independence in shared]
                counter = [f.object_id for f,n,c in matching if c.independence == 'INDEPENDENT']
                partial = any(c.independence == 'PARTIALLY_SHARED' for f,n,c in matching)
                outcome = 'SUPPORTED' if support else 'PLAUSIBLE' if partial else 'CONTRADICTED' if matching and len(counter) == len(matching) else 'UNRESOLVED'
            else:
                related = {x['source_id'] for x in snapshot['links']} | {x['target_id'] for x in snapshot['links']}
                relevant = [(f,n,c) for f,n,c,equal in eligible if f.object_id in related]
                support = [f.object_id for f,n,c in relevant if all((f.scope.period_from, f.scope.period_to, h.scope.period_from, h.scope.period_to)) and c.temporal in ('PRECEDES','FOLLOWS','OVERLAPS','NOT_COMPARABLE')]
                counter = [f.object_id for f,n,c in relevant if c.temporal == 'SAME_COMPARABLE_PERIOD']
                # Existential mismatch is not refuted by a different comparable pair.
                outcome = 'SUPPORTED' if support else 'CONTRADICTED' if relevant and len(counter) == len(relevant) else 'UNRESOLVED'
            if len(eligible) != len(candidates):
                checks['LINEAGE'] = 'GAP'
                gaps.append(self._gap(h, 'INCOMPLETE_LINEAGE', 'Eligible complete ancestry for relevant evidence', 'Partial/unknown evidence cannot be silently omitted from disconfirmation'))
            if not candidates or any(not all((f.scope.period_from,f.scope.period_to,h.scope.period_from,h.scope.period_to)) for f,n,c,e in candidates):
                checks['TEMPORAL'] = 'GAP'
                gaps.append(self._gap(h, 'INCOMPARABLE_PERIODS', 'Exact comparable reporting periods', 'Unknown dates do not prove temporal comparability or inconsistency', 'BOTH'))
            if outcome == 'SUPPORTED' and (any(v == 'GAP' for v in checks.values()) or any(g.blocks in ('SUPPORT','BOTH') for g in gaps)):
                outcome = 'UNRESOLVED'
            if outcome == 'CONTRADICTED' and any(g.blocks in ('CONTRADICTION','BOTH') for g in gaps):
                outcome = 'UNRESOLVED'
        if checks['ORIGIN_CURRENT'] != 'PASS':
            outcome = 'UNRESOLVED'
        if not support and not counter and not gaps:
            gaps.append(self._gap(h, 'MISSING_EVIDENCE', 'Qualified evidence required by this contract', 'No proposition-specific support or disconfirmation is available', 'BOTH'))
        snapshot['origin_fact'] = anchor.model_dump(mode='json')
        fingerprint = digest({'evidence': snapshot, 'contract': h.contract_key, 'version': h.contract_version,
            'checks': checks, 'gaps': [g.model_dump(mode='json') for g in gaps]})
        prior = self.history(h.object_id)
        if prior and prior[-1].evidence_digest == fingerprint:
            return prior[-1]
        if prior and expected_revision is None:
            raise RevisionConflict('Changed evidence requires explicit expected_revision; history is preserved')
        iid = identity('interpretation', h.object_id)
        value = Interpretation(object_id=iid, client_id=self.client_id, run_id=self.run_id,
            hypothesis_id=h.object_id, hypothesis_class=h.hypothesis_class, proposition=h.proposition,
            contract_key=h.contract_key, revision=len(prior)+1, outcome=outcome,
            supporting=tuple(sorted(support)), contradictory=tuple(sorted(counter)), contextual=context,
            alternatives=peers, gaps=tuple(gaps), checks=checks, evidence_snapshot=snapshot, evidence_digest=fingerprint)
        if prior:
            env = self.foundation.get_object(iid)
            self.foundation.update_object(env.model_copy(update=dict(revision=env.revision+1, status=outcome, updated_at=now())))
        else:
            self.foundation.create_object(ReasoningObject(object_id=iid, client_id=self.client_id, run_id=self.run_id,
                object_type='INTERPRETATION', source_authority='SYSTEM_DERIVED', status=outcome, lineage=self._lineage(h.object_id)))
        self.session.execute(insert(tables.interpretation).values(object_id=iid, revision=value.revision,
            client_id=self.client_id, hypothesis_id=h.object_id, document=value.to_json()))
        revised = h.model_copy(update=dict(status=outcome, revision=h.revision+1))
        env = self.foundation.get_object(h.object_id)
        self.foundation.update_object(env.model_copy(update=dict(revision=env.revision+1, status=outcome, updated_at=now())))
        result = self.session.execute(update(tables.hypothesis).where(tables.hypothesis.c.object_id == h.object_id,
            tables.hypothesis.c.revision == h.revision).values(revision=revised.revision, document=revised.to_json()))
        if result.rowcount != 1:
            raise RevisionConflict('Concurrent Hypothesis assessment')
        self.foundation.append_audit(AuditEvent(client_id=self.client_id, run_id=self.run_id, object_id=iid,
            event_type='OBJECT_UPDATED', actor=self.foundation.actor,
            previous=prior[-1].model_dump(mode='json') if prior else None, new=value.model_dump(mode='json')))
        # Links describe assessment evidence; they do not certify mechanism/causal direction.
        self._link(h.object_id, iid, 'CONTEXTUALISES', 'CONTEXTUAL')
        for ids, relation, role in ((support,'SUPPORTS','SUPPORTING'), (counter,'CONTRADICTS','CONTRADICTORY'), (context,'CONTEXTUALISES','CONTEXTUAL')):
            for oid in ids:
                self._link(oid, iid, relation, role)
        return value
