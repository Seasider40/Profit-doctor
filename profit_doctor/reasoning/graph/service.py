"""Explicit scoped EvidenceLink governance, not an automatic reasoning engine.

The caller owns both stores and the transaction. Snapshot changes fail closed;
relationships never silently overwrite the evidence on which they were recorded.
"""
from sqlalchemy import insert, select, or_
from profit_doctor.persistence import reasoning_schema as foundation_tables
from profit_doctor.persistence.graph_schema import graph_record
from profit_doctor.reasoning.canonical.service import CanonicalService, identity
from profit_doctor.reasoning.canonical.contracts import ReportingScope
from profit_doctor.reasoning.canonical.registry import REGISTRY
from profit_doctor.reasoning.domain.contracts import AuditEvent, EvidenceLink
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from .ancestry import AncestryReader
from .contracts import Ancestry, Node, Characteristics, GraphRecord, SeriesBasis


ROLES = {'SUPPORTS': 'SUPPORTING', 'CONTRADICTS': 'CONTRADICTORY', 'QUANTIFIES': 'QUANTIFICATION',
         'CONTEXTUALISES': 'CONTEXTUAL', 'MITIGATES': 'MITIGATING',
         'TEMPORALLY_PRECEDES': 'TEMPORAL', 'CO_MOVES_WITH': 'TEMPORAL'}
HUMAN = {'MANAGEMENT_ASSERTION', 'HUMAN_FD_JUDGEMENT', 'LEGACY_UNCLASSIFIED'}


def temporal(left, right):
    a, b = left.scope, right.scope
    if (a.entity_type, a.entity_id, a.period_basis) != (b.entity_type, b.entity_id, b.period_basis):
        return 'NOT_COMPARABLE'
    if not all((a.period_from, a.period_to, b.period_from, b.period_to)):
        return 'INSUFFICIENT_PERIOD_INFORMATION'
    if (a.period_from, a.period_to) == (b.period_from, b.period_to):
        return 'SAME_COMPARABLE_PERIOD'
    if a.period_to < b.period_from:
        return 'PRECEDES'
    if b.period_to < a.period_from:
        return 'FOLLOWS'
    return 'OVERLAPS'


class EvidenceGraph:
    def __init__(self, session, client_id, run_id, actor, source):
        self.canonical = CanonicalService(session, client_id, actor, source)
        self.foundation = self.canonical.foundation
        self.foundation._run(run_id)
        if run_id is None:
            raise ScopeError('Graph operations require an explicit recording run')
        self.session, self.client_id, self.run_id = session, client_id, run_id
        self.source, self.reader = source, AncestryReader(source)

    def node(self, object_id, *, observation_run=None):
        obj = self.foundation.get_object(object_id)
        if obj.object_type == 'FACT':
            fact = self.canonical.get_fact(object_id)
            for ref in fact.lineage:
                self.foundation._lineage(ref)
            _, _, _, digest = self.source.read(fact.source_signal_id)
            if digest != fact.source_digest:
                raise RevisionConflict('Owning Signal changed since canonicalisation')
            if observation_run is not None and observation_run != fact.run_id:
                raise ScopeError('Fact is outside requested observation run')
            return Node(object_id=object_id, revision=fact.revision, run_id=fact.run_id, object_type='FACT',
                authority=obj.source_authority, scope=fact.scope, ancestry=self.reader.read(fact.lineage),
                confidence=fact.confidence, eligible=fact.state == 'OBSERVED' and fact.eligibility == 'FULL' and not fact.limitations)
        if obj.object_type == 'FINDING':
            finding = self.canonical.get_finding(object_id)
            run = observation_run or self.run_id
            observations = [o for o in finding.observations if o.run_id == run]
            if len(observations) != 1:
                raise ScopeError('Finding requires one explicit observation for the requested run')
            fact_node = self.node(observations[0].fact_id, observation_run=run)
            return fact_node.model_copy(update=dict(object_id=object_id, revision=finding.revision, object_type='FINDING',
                confidence=finding.assessment.confidence,
                eligible=fact_node.eligible and finding.assessment.outcome == 'FINDING_CREATED'))
        if obj.object_type != 'SIGNAL':
            raise ValueError('Graph scope is evidence Signals, canonical Facts and Findings only')
        if observation_run is not None and observation_run != obj.run_id:
            raise ScopeError('Signal is outside requested run')
        if obj.run_id is None:
            raise ScopeError('Evidence requires a retained analytical run')
        for ref in obj.lineage:
            self.foundation._lineage(ref)
        scope = ReportingScope(entity_type=obj.entity.resource if obj.entity else None,
            entity_id=obj.entity.source_id if obj.entity else None,
            period_from=obj.period_from, period_to=obj.period_to,
            period_basis='Foundation evidence period; comparability unqualified')
        signal_refs = [r for r in obj.lineage if r.store == 'LEGACY_SQLITE' and
                       r.kind == 'DERIVED_ANCESTOR' and r.resource == 'signal']
        if obj.source_authority == 'SYSTEM_DERIVED' and len(signal_refs) == 1:
            signal, _, _, _ = self.source.read(signal_refs[0].source_id)
            if signal['run_id'] != obj.run_id:
                raise ScopeError('Signal envelope disagrees with source run')
            mapping = REGISTRY.get((signal['test_id'], signal['signal_type']))
            scope = ReportingScope(entity_type=signal['entity_type'], entity_id=signal['entity_id'],
                period_from=signal['period_from'], period_to=signal['period_to'],
                period_basis=mapping.period_basis if mapping else 'Unmapped Signal period; comparability unqualified')
        ancestry = self.reader.read(obj.lineage) if obj.lineage else Ancestry(unresolved=('no-lineage',))
        return Node(object_id=object_id, revision=obj.revision, run_id=obj.run_id, object_type='SIGNAL',
            authority=obj.source_authority, scope=scope, ancestry=ancestry,
            confidence=obj.confidence, eligible=False)

    def characteristics(self, source_id, target_id, *, source_run=None, target_run=None):
        a = self.node(source_id, observation_run=source_run)
        b = self.node(target_id, observation_run=target_run)
        x, y = a.ancestry, b.ancestry
        refs = tuple(sorted(set(x.references) & set(y.references)))
        datasets = tuple(sorted(set(x.datasets) & set(y.datasets)))
        files = tuple(sorted(set(x.source_files) & set(y.source_files)))
        independent = 'INDETERMINATE'
        reason = 'Incomplete ancestry, ineligible evidence or unverified authority; no corroboration assumed'
        if x.complete and y.complete and a.eligible and b.eligible and a.authority == b.authority == 'SYSTEM_DERIVED':
            roots_a, roots_b = set(x.datasets or x.source_files), set(y.datasets or y.source_files)
            if roots_a == roots_b:
                independent, reason = 'SAME_ANCESTRY', 'Identical resolved provenance roots at retained granularity'
            elif roots_a & roots_b:
                if roots_a < roots_b or roots_b < roots_a:
                    independent, reason = 'SUBSTANTIALLY_SHARED', 'One resolved root set wholly contains the other; no numeric weighting'
                else:
                    independent, reason = 'PARTIALLY_SHARED', 'Resolved root sets intersect and each has additional roots'
            elif files or set(x.primitives) & set(y.primitives) or set(x.records) & set(y.records):
                independent, reason = 'SUBSTANTIALLY_SHARED', 'Different dataset roots retain shared source evidence or analytical ancestry'
            else:
                independent, reason = 'INDEPENDENT', 'Disjoint resolved datasets and source roots; provenance independence only, not statistical or causal independence'
        links = self.session.execute(select(foundation_tables.evidence_link.c.link_id).where(
            foundation_tables.evidence_link.c.client_id == self.client_id,
            foundation_tables.evidence_link.c.relationship_type == 'CONTRADICTS',
            or_(foundation_tables.evidence_link.c.target_id == source_id, foundation_tables.evidence_link.c.target_id == target_id))).all()
        return Characteristics(independence=independent, independence_basis=reason,
            shared_references=refs, shared_datasets=datasets, shared_source_files=files,
            source_authorities=(a.authority, b.authority), lineage_complete=(x.complete, y.complete),
            temporal=temporal(a, b), contradiction_present=bool(links),
            data_confidence=(a.confidence.data_confidence, b.confidence.data_confidence))

    def _series(self, source_id, target_id, basis):
        basis = SeriesBasis.from_json(basis.to_json())
        if basis.source_facts[-1] != source_id or basis.target_facts[-1] != target_id:
            raise ValueError('Co-movement endpoints must be final aligned Facts')
        sides = []
        periods = []
        for ids in (basis.source_facts, basis.target_facts):
            facts, values, windows = [], [], []
            for oid in ids:
                node = self.node(oid)
                fact = self.canonical.get_fact(oid)
                value = getattr(fact, basis.slot)
                if not node.eligible or not node.ancestry.complete or value is None:
                    raise ValueError('Co-movement requires eligible measured Facts with complete ancestry')
                if not fact.scope.period_from or not fact.scope.period_to:
                    raise ValueError('Co-movement requires exact periods')
                facts.append(fact)
                values.append(value.value)
                windows.append((fact.scope.period_from, fact.scope.period_to))
                first = facts[0]
                first_value = getattr(first, basis.slot)
                if (fact.diagnostic, fact.signal_type, fact.mapping_version, fact.scope.entity_type, fact.scope.entity_id,
                    fact.scope.period_basis, value.metric, value.unit, value.basis, value.currency) != (
                    first.diagnostic, first.signal_type, first.mapping_version, first.scope.entity_type, first.scope.entity_id,
                    first.scope.period_basis, first_value.metric, first_value.unit, first_value.basis, first_value.currency):
                    raise ValueError('Series changes meaning or entity')
            if any(windows[i-1][1] >= windows[i][0] for i in range(1, len(windows))):
                raise ValueError('Periods must be ordered and non-overlapping')
            if len({end-start for start,end in windows}) != 1:
                raise ValueError('Period lengths differ')
            # Comparisons preserve Decimal precision without subtracting/rounding.
            directions = [(values[i] > values[i-1]) - (values[i] < values[i-1]) for i in range(1, len(values))]
            if 0 in directions:
                raise ValueError('Constant observations do not establish co-movement')
            sides.append(directions)
            periods.append(windows)
        if periods[0] != periods[1] or sides[0] != sides[1]:
            raise ValueError('Aligned series must have matching nonzero directions')
        return basis

    def link(self, source_id, target_id, relationship, rationale, *, series=None, source_run=None, target_run=None, expected_revision=None):
        if relationship not in ROLES or source_id == target_id or not rationale.strip():
            raise ValueError('Unsupported relationship, self-link or missing explicit basis')
        if relationship == 'CO_MOVES_WITH' and target_id < source_id:
            source_id, target_id, source_run, target_run = target_id, source_id, target_run, source_run
            if series:
                series = series.model_copy(update=dict(source_facts=series.target_facts, target_facts=series.source_facts))
        a, b = self.node(source_id, observation_run=source_run), self.node(target_id, observation_run=target_run)
        if (a.scope.entity_type, a.scope.entity_id) != (b.scope.entity_type, b.scope.entity_id):
            raise ScopeError('Cross-entity relationships require a future qualified segmentation contract')
        if a.authority in HUMAN and relationship not in ('CONTEXTUALISES', 'CONTRADICTS', 'MITIGATES'):
            raise ValueError('Human context cannot become verified system corroboration')
        if relationship == 'TEMPORALLY_PRECEDES' and (temporal(a,b) != 'PRECEDES' or not a.eligible or not b.eligible):
            raise ValueError('Temporal precedence requires comparable eligible periods')
        if relationship == 'CO_MOVES_WITH':
            if series is None:
                raise ValueError('Co-movement requires at least four aligned observations per series')
            if temporal(a, b) != 'SAME_COMPARABLE_PERIOD':
                raise ValueError('Series endpoints must have comparable period bases')
            series = self._series(source_id, target_id, series)
        elif series is not None:
            raise ValueError('Series basis belongs to co-movement only')
        c = self.characteristics(source_id, target_id, source_run=source_run, target_run=target_run)
        # Existing canonical links are reused, never copied into another graph.
        matches = list(self.session.scalars(select(foundation_tables.evidence_link.c.link_id).where(
            foundation_tables.evidence_link.c.client_id == self.client_id,
            foundation_tables.evidence_link.c.source_id == source_id,
            foundation_tables.evidence_link.c.target_id == target_id,
            foundation_tables.evidence_link.c.relationship_type == relationship)))
        if len(matches) > 1:
            raise RevisionConflict('Existing duplicate links require explicit reconciliation')
        lid = matches[0] if matches else identity('evidence-graph', self.client_id, source_id, target_id, relationship)
        record = GraphRecord(link_id=lid, client_id=self.client_id, run_id=self.run_id,
            source_id=source_id, target_id=target_id, relationship=relationship, rationale=rationale,
            source_revision=a.revision, target_revision=b.revision, characteristics=c, series=series,
            source_snapshot=a, target_snapshot=b)
        stored = self.session.scalar(select(graph_record.c.link_id).where(graph_record.c.link_id == lid))
        if stored:
            old = self.get(lid)
            if expected_revision is not None and (type(expected_revision) is not int or expected_revision != old.revision):
                raise RevisionConflict('Relationship revision changed; reload before revising')
            # Evidence tensions can change after adding a link; snapshots stay historical.
            comparable = record.model_copy(update={'characteristics': old.characteristics, 'run_id': old.run_id,
                'created_at': old.created_at, 'revision': old.revision})
            if comparable != old:
                if expected_revision is None:
                    raise RevisionConflict('Recorded basis changed; explicit expected_revision required')
            elif expected_revision is None:
                return old
            elif record.characteristics == old.characteristics:
                return old
            record = record.model_copy(update={'revision': old.revision + 1})
        elif expected_revision is not None:
            raise RevisionConflict('Cannot revise a missing relationship record')
        if matches and not stored:
            existing = self.foundation.get_link(lid)
            was_governed = any(isinstance(event.new, dict) and
                isinstance(event.new.get('graph_record'), dict) and event.new['graph_record'].get('link_id') == lid
                for event in self.foundation.audit_events(object_id=target_id))
            if existing.metadata.get('graph_schema') or was_governed:
                raise RevisionConflict('Governance payload missing; restore after downgrade before replay')
        elif not matches:
            self.foundation.link_evidence(EvidenceLink(link_id=lid, client_id=self.client_id, run_id=self.run_id,
                source_id=source_id, target_id=target_id, relationship_type=relationship,
                evidence_role=ROLES[relationship], source_authority=a.authority,
                metadata={'graph_schema': 'EG-2.45.1', 'basis': rationale}))
        self.session.execute(insert(graph_record).values(link_id=lid, revision=record.revision, client_id=self.client_id, run_id=self.run_id,
            source_id=source_id, target_id=target_id, document=record.to_json()))
        self.foundation.append_audit(AuditEvent(client_id=self.client_id, run_id=self.run_id, object_id=target_id,
            event_type='EVIDENCE_LINKED', actor=self.foundation.actor,
            previous={'graph_record': old.model_dump(mode='json')} if stored else None,
            new={'graph_record': record.model_dump(mode='json')}))
        return record

    def get(self, link_id, *, revision=None):
        stmt = select(graph_record).where(graph_record.c.link_id == link_id, graph_record.c.client_id == self.client_id)
        if revision is not None:
            if type(revision) is not int or revision < 1:
                raise ValueError('Revision must be a positive integer')
            stmt = stmt.where(graph_record.c.revision == revision)
        row = self.session.execute(stmt.order_by(graph_record.c.revision.desc()).limit(1)).mappings().one_or_none()
        if row is None:
            raise ScopeError('Graph record missing or foreign')
        value = GraphRecord.from_json(row['document'])
        for key in ('link_id', 'revision', 'client_id', 'run_id', 'source_id', 'target_id'):
            if getattr(value, key) != row[key]:
                raise ScopeError('Graph document disagrees with indexed scope')
        link = self.foundation.get_link(link_id)
        if (value.source_id, value.target_id, value.relationship) != (link.source_id, link.target_id, link.relationship_type):
            raise ScopeError('Graph extension disagrees with EvidenceLink')
        if value.source_snapshot.authority != link.source_authority:
            raise ScopeError('Graph source authority changed')
        for run in (value.run_id, value.source_snapshot.run_id, value.target_snapshot.run_id):
            self.foundation._run(run)
        return value

    def history(self, link_id):
        self.foundation.get_link(link_id)
        return tuple(self.get(link_id, revision=revision) for revision in self.session.scalars(
            select(graph_record.c.revision).where(graph_record.c.link_id == link_id,
                graph_record.c.client_id == self.client_id).order_by(graph_record.c.revision)))

    def freshness(self, link_id):
        """Historical relationships are not silently presented as current proof."""
        record = self.get(link_id)
        try:
            current = (self.node(record.source_id, observation_run=record.source_snapshot.run_id),
                       self.node(record.target_id, observation_run=record.target_snapshot.run_id))
        except (ScopeError, RevisionConflict):
            return 'UNRESOLVED'
        return 'CURRENT' if current == (record.source_snapshot, record.target_snapshot) else 'STALE'

    def neighbours(self, object_id, *, relationship=None, direction='both', run_id=None):
        self.foundation.get_object(object_id)
        if direction not in ('both', 'incoming', 'outgoing') or relationship is not None and relationship not in ROLES:
            raise ValueError('Unknown graph query')
        t = foundation_tables.evidence_link
        stmt = select(t.c.link_id).where(t.c.client_id == self.client_id)
        stmt = stmt.where(t.c.target_id == object_id if direction == 'incoming' else
                          t.c.source_id == object_id if direction == 'outgoing' else
                          or_(t.c.source_id == object_id, t.c.target_id == object_id))
        if relationship:
            stmt = stmt.where(t.c.relationship_type == relationship)
        else:
            stmt = stmt.where(t.c.relationship_type.in_(ROLES))
        if run_id is not None:
            self.foundation._run(run_id)
            recorded = select(graph_record.c.link_id).where(graph_record.c.client_id == self.client_id,
                graph_record.c.run_id == run_id)
            stmt = stmt.where(or_(t.c.run_id == run_id, t.c.link_id.in_(recorded)))
        return tuple(self.foundation.get_link(lid) for lid in self.session.scalars(stmt.order_by(t.c.link_id)))

    def nodes(self, *, entity=None, period=None, family=None, authority=None, run_id=None):
        run = run_id or self.run_id
        self.foundation._run(run)
        result = []
        t = foundation_tables.reasoning_object
        for oid in self.session.scalars(select(t.c.object_id).where(t.c.client_id == self.client_id,
                t.c.object_type.in_(['FACT', 'FINDING', 'SIGNAL'])).order_by(t.c.object_id)):
            obj = self.foundation.get_object(oid)
            if obj.object_type == 'FINDING':
                finding = self.canonical.get_finding(oid)
                if not any(o.run_id == run for o in finding.observations):
                    continue
            elif obj.run_id != run:
                continue
            node = self.node(oid, observation_run=run)
            if entity is not None and (node.scope.entity_type, node.scope.entity_id) != entity:
                continue
            if period is not None and (node.scope.period_from, node.scope.period_to) != period:
                continue
            if family is not None and family not in node.ancestry.diagnostic_families:
                continue
            if authority is not None and node.authority != authority:
                continue
            result.append(node)
        return tuple(result)

    def independent_evidence(self, object_id, candidates):
        # No diagnostic counting and no promotion into confidence dimensions.
        return tuple(oid for oid in sorted(set(candidates)) if oid != object_id and
                     self.characteristics(object_id, oid).independence == 'INDEPENDENT')
