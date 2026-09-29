"""Opt-in synthesis of existing canonical reasoning; caller owns transactions.

No raw source calculation, automatic Hypothesis assessment or legacy cutover.
History is evidence-at-assessment, not a promise that retained evidence is current.
"""
import json
from datetime import datetime
from decimal import Decimal
from sqlalchemy import insert, select, update
from profit_doctor.persistence import story_schema as tables, reasoning_schema as roots, hypothesis_schema
from profit_doctor.persistence import EngineRun
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import ReasoningObject, AuditEvent, EvidenceLink, EffectReference, now
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.hypothesis.service import HypothesisService, digest, semantics, measurements
from profit_doctor.reasoning.hypothesis.gaps import EvidenceGap
from .contracts import Story, StoryAssessment
from .registry import REGISTRY


def semantic_key(client, contract, fact):
    return json.dumps([client, contract.key, fact.scope.entity_type, fact.scope.entity_id,
        fact.scope.period_basis, fact.mapping_version], separators=(',', ':'))


class StoryService:
    def __init__(self, session, client_id, run_id, actor, source):
        self.hypotheses = HypothesisService(session, client_id, run_id, actor, source)
        self.graph = self.hypotheses.graph
        self.canonical, self.foundation = self.graph.canonical, self.graph.foundation
        self.session, self.client_id, self.run_id = session, client_id, run_id

    def get(self, object_id):
        row = self.session.execute(select(tables.story).where(tables.story.c.object_id == object_id,
            tables.story.c.client_id == self.client_id)).mappings().one_or_none()
        if row is None:
            raise ScopeError('Story missing or outside client scope')
        value = Story.from_json(row['document'])
        env = self.foundation.get_object(object_id)
        if (value.object_id, value.client_id, value.finding_id, value.revision) != (
                row['object_id'], row['client_id'], row['finding_id'], row['revision']):
            raise ScopeError('Story document disagrees with indexed scope')
        if (env.object_type, env.run_id, env.status, env.revision) != (
                'ECONOMIC_STORY', value.first_seen_run, value.status, value.revision):
            raise ScopeError('Story disagrees with foundation identity')
        if digest(value.evidence_snapshot) != value.evidence_digest:
            raise ScopeError('Story evidence snapshot digest mismatch')
        from profit_doctor.reasoning.canonical.contracts import CanonicalFact
        fact = CanonicalFact.model_validate(value.evidence_snapshot['facts'][0])
        key = semantic_key(self.client_id, REGISTRY[value.contract_key], fact)
        if value.semantic_key != key or identity('story',key) != object_id or env.lineage != self.hypotheses._lineage(value.finding_id):
            raise ScopeError('Story semantic identity or lineage mismatch')
        self.foundation._run(value.latest_seen_run)
        return value

    def history(self, object_id):
        current = self.get(object_id)
        values = []
        for row in self.session.execute(select(tables.story_revision).where(
                tables.story_revision.c.object_id == object_id,
                tables.story_revision.c.client_id == self.client_id).order_by(tables.story_revision.c.revision)).mappings().all():
            value = Story.from_json(row['document'])
            if (value.object_id, value.client_id, value.revision) != (object_id, self.client_id, row['revision']) or digest(value.evidence_snapshot) != value.evidence_digest:
                raise ScopeError('Story history envelope or evidence digest mismatch')
            values.append(value)
        if not values or values[-1] != current or [v.revision for v in values] != list(range(1,current.revision+1)):
            raise ScopeError('Story history missing or inconsistent; restore before replay')
        return tuple(values)

    def _links(self, finding_id, fact_id):
        links = {l.link_id:l for endpoint in (finding_id, fact_id) for l in self.graph.neighbours(endpoint)}
        # Downstream reasoning links are not new source evidence against their own origin.
        return tuple(l for _,l in sorted(links.items()) if all(self.foundation.get_object(oid).object_type not in
            ('HYPOTHESIS','INTERPRETATION','ECONOMIC_STORY') for oid in (l.source_id,l.target_id)))

    def _interpretations(self, finding, fact):
        result = []
        ids = tuple(self.session.scalars(select(hypothesis_schema.hypothesis.c.object_id).where(
            hypothesis_schema.hypothesis.c.finding_id == finding.object_id,
            hypothesis_schema.hypothesis.c.client_id == self.client_id).order_by(hypothesis_schema.hypothesis.c.object_id)))
        for oid in ids:
            if self.foundation.get_object(oid).run_id != self.run_id:
                continue
            h = self.hypotheses.get(oid)
            history = self.hypotheses.history(oid)
            if not history:
                raise RevisionConflict('Assess relevant Hypotheses before Story synthesis')
            interpretation = history[-1]
            # Reuse the frozen read-only search, never reassess/promote the Hypothesis.
            _, _, _, _, _, current = self.hypotheses._search(h)
            for key in ('finding','facts'):
                if digest(current[key]) != digest(interpretation.evidence_snapshot[key]):
                    raise RevisionConflict('Interpretation evidence changed; explicitly reassess before synthesis')
            old_links = interpretation.evidence_snapshot['links']
            def evidence_links(values):
                return sorted([v for v in values if all(self.foundation.get_object(v[k]).object_type not in
                    ('HYPOTHESIS','INTERPRETATION','ECONOMIC_STORY') for k in ('source_id','target_id'))], key=lambda v:v['link_id'])
            if digest(evidence_links(old_links)) != digest(evidence_links(current['links'])):
                raise RevisionConflict('Interpretation relationships changed; explicitly reassess')
            result.append(interpretation)
        return tuple(result)

    def synthesise(self, contract_key, finding_id, *, effect_ids=(), expected_revision=None):
        if contract_key not in REGISTRY:
            raise ValueError('Unknown or deferred Story Contract; no generic synthesis')
        contract = REGISTRY[contract_key]
        finding, fact = self.hypotheses._origin(finding_id)
        if finding.latest_seen_run != self.run_id:
            raise ScopeError('Use the latest explicit Finding observation; historical reads use Story history')
        if finding.finding_type != contract.finding_type:
            return StoryAssessment(outcome='NO_STORY', reasons=('Finding type is not eligible for this Story Contract',))
        key = semantic_key(self.client_id, contract, fact)
        oid = identity('story', key)
        exists = self.session.scalar(select(tables.story.c.object_id).where(tables.story.c.object_id == oid))
        old = self.get(oid) if exists else None
        if old:
            self.history(oid)
        if expected_revision is not None and (type(expected_revision) is not int or old is None or expected_revision != old.revision):
            raise RevisionConflict('Story revision changed')
        # A foundation identity without its typed state is not permission to regenerate history.
        if not old and self.session.scalar(select(roots.reasoning_object.c.object_id).where(roots.reasoning_object.c.object_id == oid)):
            raise RevisionConflict('Story payload missing; restore it before replay')
        node = self.graph.node(fact.object_id, observation_run=self.run_id)
        gaps = []
        def gap(kind, missing, reason):
            gaps.append(EvidenceGap(kind=kind, missing_evidence=missing, reason_required=reason,
                dimension='EVIDENCE', scope=fact.scope, investigation_request='Obtain governed evidence: '+missing,
                blocks='SUPPORT', related_objects=(finding_id,)))
        valid = node.eligible and node.ancestry.complete and all((fact.scope.period_from, fact.scope.period_to))
        if not valid:
            gap('INCOMPLETE_LINEAGE','Current FULL eligible evidence with complete ancestry and exact periods', 'Unknown or partial evidence cannot establish this condition Story')
        chars, corroboration, counter, fact_snapshot = {}, [], [], [fact.model_dump(mode='json')]
        ids = tuple(self.session.scalars(select(roots.reasoning_object.c.object_id).where(
            roots.reasoning_object.c.client_id == self.client_id, roots.reasoning_object.c.run_id == self.run_id,
            roots.reasoning_object.c.object_type == 'FACT').order_by(roots.reasoning_object.c.object_id)))
        for other_id in ids:
            other = self.canonical.get_fact(other_id)
            if other_id == fact.object_id or semantics(other) != semantics(fact) or (other.scope.entity_type,other.scope.entity_id) != (fact.scope.entity_type,fact.scope.entity_id):
                continue
            fact_snapshot.append(other.model_dump(mode='json'))
            characteristic = self.graph.characteristics(fact.object_id, other_id)
            chars[other_id] = characteristic
            other_node = self.graph.node(other_id, observation_run=self.run_id)
            if not other_node.eligible or not other_node.ancestry.complete or characteristic.temporal == 'INSUFFICIENT_PERIOD_INFORMATION':
                valid = False
                gap('INCOMPLETE_LINEAGE','Qualified comparable corroborating evidence','A relevant unknown/partial observation cannot be silently omitted')
            elif characteristic.temporal == 'SAME_COMPARABLE_PERIOD':
                if measurements(other) != measurements(fact):
                    counter.append(other_id)
                elif characteristic.independence == 'INDEPENDENT':
                    corroboration.append(other_id)
        links = self._links(finding_id, fact.object_id)
        contradictory = set(counter) | set(finding.contradictory_evidence)
        mitigating = set(finding.mitigating_evidence)
        for link in links:
            other = link.source_id if link.target_id in (finding_id,fact.object_id) else link.target_id
            if link.relationship_type == 'CONTRADICTS': contradictory.add(other)
            if link.relationship_type == 'MITIGATES': mitigating.add(other)
            if link.relationship_type == 'CONTEXTUALISES' and self.foundation.get_object(other).source_authority != 'SYSTEM_DERIVED':
                contradictory.add(other)  # Unverified challenge, never a verified causal Fact.
        if contradictory or mitigating:
            valid = False
            gap('CONFLICTING_EVIDENCE','Resolution of contradictory/mitigating evidence','Evidence tension prevents supported synthesis')
        if not corroboration:
            valid = False
            gap('SHARED_ANCESTRY','Independent exact reproduction','Shared, partially shared or indeterminate evidence is not independent corroboration')
        if not any(l.source_id == fact.object_id and l.target_id == finding_id and l.relationship_type == 'SUPPORTS' for l in links):
            valid = False
            gap('MISSING_EVIDENCE','Canonical Fact-to-Finding support link','The canonical significance lineage is required')
        measure = getattr(fact,contract.measure_slot)
        present = measure.value <= Decimal('-1') if contract_key == 'MARGIN_COMPRESSION' else measure.value >= Decimal('15')
        interpretations = self._interpretations(finding, fact)
        if present:
            valid = valid and finding.assessment.outcome == 'FINDING_CREATED'
            if not any(i.contract_key == 'INDEPENDENT_CORROBORATION' and i.outcome == 'SUPPORTED' for i in interpretations):
                valid = False
                gap('MISSING_EVIDENCE','Current supported evidence-quality Interpretation','Finding count alone cannot establish corroboration')
        else:
            valid = valid and finding.assessment.outcome in ('NOT_SIGNIFICANT','FINDING_CREATED')
        if not interpretations and old:
            # Explicit historical reasoning context; resolution below uses new independently verified Facts.
            interpretations = old.interpretations
        if not old and (not valid or not present or not interpretations):
            return StoryAssessment(outcome='NO_STORY', reasons=tuple(g.reason_required for g in gaps) or ('The qualified condition is absent',))
        mechanisms = [i for i in interpretations if i.hypothesis_class == 'ECONOMIC_MECHANISM']
        for interpretation in mechanisms:
            gaps.extend(interpretation.gaps)
        gap('UNSAFE_SEMANTICS','Separately qualified ECONOMIC_MECHANISM contract and supporting evidence',
            'Condition support does not establish WHY; no current mechanism contract permits positive support')
        effects = tuple(sorted(set(effect_ids)))
        for eid in effects:
            effect = self.foundation.get_effect(eid)
            if effect.run_id not in (None,self.run_id):
                raise ScopeError('EconomicEffect outside the observation run')
        status, transition = ('SUPPORTED' if valid and present else 'INVESTIGATING'), 'FIRST_OBSERVATION'
        if old:
            a,b = old.scope,fact.scope
            ordered = (old.latest_seen_run != self.run_id and all((a.period_from,a.period_to,b.period_from,b.period_to))
                and a.period_to < b.period_from and a.period_to-a.period_from == b.period_to-b.period_from
                and datetime.fromisoformat(self.session.get(EngineRun,old.latest_seen_run).started_at) < datetime.fromisoformat(self.session.get(EngineRun,self.run_id).started_at))
            transition = 'REASSESSMENT' if old.latest_seen_run == self.run_id else 'COMPARABLE_PERIOD' if ordered else 'NOT_COMPARABLE'
            if valid and ordered:
                if not present: status = 'RESOLVED'
                elif old.status == 'RESOLVED': transition = 'REOPENED'
                elif old.condition_present and old.status != 'INVESTIGATING':
                    prior = next(m for m in old.measurements if m.metric == measure.metric and m.unit == measure.unit)
                    direction = (measure.value > prior.value) - (measure.value < prior.value)
                    if contract_key == 'MARGIN_COMPRESSION': direction = -direction
                    status = {0:'PERSISTENT',1:'WORSENING',-1:'IMPROVING'}[direction]
            elif not present or old.status == 'RESOLVED': status = 'INVESTIGATING'
        snapshot = dict(finding=finding.model_dump(mode='json'), facts=fact_snapshot,
            characteristics={k:v.model_dump(mode='json') for k,v in chars.items()}, links=[l.model_dump(mode='json') for l in links],
            interpretations=[i.model_dump(mode='json') for i in interpretations], effect_ids=list(effects), run=self.run_id)
        fingerprint = digest(snapshot)
        if old and old.evidence_digest == fingerprint:
            return StoryAssessment(outcome='REPLAYED', story=old)
        if old and expected_revision is None:
            raise RevisionConflict('Changed Story evidence requires explicit expected_revision')
        value = Story(object_id=oid,client_id=self.client_id, first_seen_run=old.first_seen_run if old else self.run_id,
            latest_seen_run=self.run_id, finding_id=finding_id,contract_key=contract_key,semantic_key=key,scope=fact.scope,
            status=status,transition=transition,revision=old.revision+1 if old else 1,condition_present=present,
            measurements=tuple(m for m in measurements(fact) if m is not None), fact_ids=(fact.object_id,*sorted(corroboration)),
            relationship_ids=tuple(l.link_id for l in links),interpretations=interpretations,evidence_characteristics=chars,
            contradictory=tuple(sorted(contradictory)),mitigating=tuple(sorted(mitigating)),gaps=tuple(gaps),effect_ids=effects,
            evidence_snapshot=snapshot,evidence_digest=fingerprint)
        if old:
            env = self.foundation.get_object(oid)
            self.foundation.update_object(env.model_copy(update=dict(status=status,revision=value.revision,updated_at=now())))
            written = self.session.execute(update(tables.story).where(tables.story.c.object_id==oid,
                tables.story.c.revision==old.revision).values(revision=value.revision,document=value.to_json()))
            if written.rowcount != 1: raise RevisionConflict('Concurrent Story assessment')
        else:
            self.foundation.create_object(ReasoningObject(object_id=oid,client_id=self.client_id,run_id=self.run_id,
                object_type='ECONOMIC_STORY',source_authority='SYSTEM_DERIVED',status=status,lineage=self.hypotheses._lineage(finding_id)))
            self.session.execute(insert(tables.story).values(object_id=oid,client_id=self.client_id,finding_id=finding_id,revision=1,document=value.to_json()))
        self.session.execute(insert(tables.story_revision).values(object_id=oid,client_id=self.client_id,revision=value.revision,document=value.to_json()))
        self.foundation.append_audit(AuditEvent(client_id=self.client_id,run_id=self.run_id,object_id=oid,event_type='OBJECT_UPDATED',
            actor=self.foundation.actor,previous=old.model_dump(mode='json') if old else None,new=value.model_dump(mode='json')))
        for source in (finding_id, *value.fact_ids, *(i.object_id for i in interpretations)):
            lid = identity('story-evidence',source,oid)
            if not self.session.scalar(select(roots.evidence_link.c.link_id).where(roots.evidence_link.c.link_id==lid)):
                self.foundation.link_evidence(EvidenceLink(link_id=lid,client_id=self.client_id,run_id=self.run_id,
                    source_id=source,target_id=oid,source_authority='SYSTEM_DERIVED',relationship_type='CONTEXTUALISES',evidence_role='CONTEXTUAL'))
        for eid in effects:
            rid = identity('story-effect',oid,eid)
            if not self.session.scalar(select(roots.effect_reference.c.reference_id).where(roots.effect_reference.c.reference_id==rid)):
                self.foundation.reference_effect(EffectReference(reference_id=rid,client_id=self.client_id,run_id=self.run_id,object_id=oid,effect_id=eid))
        return StoryAssessment(outcome='REVISED' if old else 'CREATED',story=value)
