"""Owning canonical sources only; caller-owned writes and explicit human input.

The domain evaluator accepts synthetic qualification inputs. This persistence
boundary never accepts a caller-supplied PriorityBasis or PriorityResult.
"""
import json
from sqlalchemy import insert, select
from profit_doctor.persistence import priority_schema as tables
from profit_doctor.reasoning.canonical.service import CanonicalService, identity
from profit_doctor.reasoning.domain.contracts import now
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.opportunity.service import OpportunityService
from .contracts import Assessment, AdviserRequest, Decision, Dimension, EconomicBasis, PriorityBasis
from .engine import evaluate


class PriorityService:
    def __init__(self, canonical, run_id, opportunities=None):
        if not isinstance(canonical, CanonicalService):
            raise ScopeError('Canonical Finding owner required')
        self.canonical, self.session = canonical, canonical.session
        self.client_id, self.run_id = canonical.client_id, run_id
        canonical.foundation._run(run_id)
        if run_id is None:
            raise ScopeError('A run is required')
        if opportunities is not None and (not isinstance(opportunities, OpportunityService)
                or opportunities.session is not self.session
                or (opportunities.client_id, opportunities.run_id) != (self.client_id, run_id)):
            raise ScopeError('Opportunity owner must share the caller session and scope')
        self.opportunities = opportunities

    def _basis(self, kind, source_id):
        if kind == 'FINDING':
            finding = self.canonical.get_finding(source_id)
            if finding.latest_seen_run != self.run_id:
                raise ScopeError('Finding is not current in this run')
            facts = [self.canonical.get_fact(o.fact_id) for o in finding.observations]
            for fact in facts:
                if fact.state != 'OBSERVED' or self.canonical.source.read(fact.source_signal_id)[3] != fact.source_digest:
                    raise RevisionConflict('Finding source is invalidated, superseded or changed')
            snapshot = json.dumps({'finding':finding.model_dump(mode='json'),
                'facts':[f.model_dump(mode='json') for f in facts]}, sort_keys=True, separators=(',', ':'))
            basis = dict(origin='CANONICAL', source_snapshot=snapshot,
                confidence=finding.assessment.confidence,
                materiality_profile=finding.assessment.materiality,
                economic=EconomicBasis(kind='OBSERVED_MEASUREMENTS', dimension='MEASUREMENT',
                    evidence=tuple(f.object_id for f in facts),
                    limitations=('Finding significance is not an economic loss or capture valuation.',)))
            if finding.contradictory_evidence:
                basis['evidence_strength'] = Dimension(state='CONFLICTED',
                    evidence=finding.contradictory_evidence, reason='Declared counter-evidence remains unresolved')
            return PriorityBasis(**basis)
        if kind == 'OPPORTUNITY':
            if self.opportunities is None:
                raise ScopeError('Opportunity owner required')
            q = self.opportunities.get(source_id, current=True)
            if q.opportunity_id is None:
                raise ScopeError('Only a current qualified Opportunity may enter priority')
            return PriorityBasis(origin='CANONICAL', source_snapshot=q.to_json(), confidence=q.confidence,
                economic=EconomicBasis(kind='INDICATIVE_CAPTURE_RANGE', low=q.low, high=q.high,
                    central=q.central, currency=q.currency, dimension=q.dimension,
                    horizon_days=q.candidate.horizon_days, evidence=(q.opportunity_id, q.evidence_id),
                    limitations=q.limitations), limitations=(
                        'Addressability is retained in the source; it does not establish general controllability.',
                        'Overdue balances do not establish imminent liquidity pressure.',))
        raise ScopeError('Only canonical FINDING and qualified OPPORTUNITY sources are accepted')

    def _savepoint(self):
        connection = self.session.connection()
        if connection.dialect.name == 'sqlite' and not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql('BEGIN')
        return self.session.begin_nested()

    def _row(self, table, subject_id, revision=None):
        query = select(table).where(table.c.subject_id == subject_id, table.c.client_id == self.client_id)
        if revision is not None:
            query = query.where(table.c.revision == revision)
        if 'revision' in table.c:
            query = query.order_by(table.c.revision.desc()).limit(1)
        return self.session.execute(query).mappings().one_or_none()

    def _subject(self, subject_id):
        row = self._row(tables.subject, subject_id)
        if row is None:
            raise ScopeError('Missing or foreign priority subject')
        if identity('priority', self.client_id, row['source_kind'], row['source_id']) != subject_id:
            raise ScopeError('Priority identity envelope mismatch')
        return row

    def _audit(self, subject_id, event, old, new, actor):
        document = json.dumps(dict(event=event, previous=old, new=new,
            actor=actor.model_dump(mode='json')), sort_keys=True, separators=(',', ':'))
        self.session.execute(insert(tables.audit).values(
            event_id=identity('priority-audit', subject_id, document), subject_id=subject_id,
            client_id=self.client_id, created_at=now().isoformat(), document=document))

    def assess(self, kind, source_id, *, expected_revision=None):
        basis = self._basis(kind, source_id)
        proposed = evaluate(basis)
        subject_id = identity('priority', self.client_id, kind, source_id)
        oldrow = self._row(tables.assessment, subject_id)
        old = self.get(subject_id) if oldrow else None
        if old and old.result == proposed and old.run_id == self.run_id:
            return old
        if expected_revision != (old.revision if old else None):
            raise RevisionConflict('Changed priority requires its explicit predecessor revision')
        value = Assessment(subject_id=subject_id, client_id=self.client_id, run_id=self.run_id,
            revision=old.revision+1 if old else 1, result=proposed)
        with self._savepoint():
            if old is None:
                self.session.execute(insert(tables.subject).values(subject_id=subject_id,
                    client_id=self.client_id, source_id=source_id, source_kind=kind))
            self.session.execute(insert(tables.assessment).values(subject_id=subject_id,
                revision=value.revision, client_id=self.client_id, run_id=self.run_id,
                created_at=value.created_at.isoformat(), document=value.to_json()))
            self._audit(subject_id, 'PRIORITY_ASSESSED', old.to_json() if old else None,
                value.to_json(), self.canonical.foundation.actor)
        return value

    def get(self, subject_id, revision=None, *, current=False):
        subject = self._subject(subject_id)
        row = self._row(tables.assessment, subject_id, revision)
        if row is None:
            raise ScopeError('Missing priority revision')
        value = Assessment.from_json(row['document'])
        if (value.subject_id, value.revision, value.client_id, value.run_id, value.created_at.isoformat()) != (
                subject_id, row['revision'], self.client_id, row['run_id'], row['created_at']):
            raise ScopeError('Priority envelope mismatch')
        if value.result.basis.origin != 'CANONICAL' or evaluate(value.result.basis) != value.result:
            raise ScopeError('Unqualified priority result')
        # No assessed future-provider inputs may be smuggled into stored production history.
        b = value.result.basis
        if any(getattr(b, n).state != 'NOT_ASSESSED' for n in ('materiality','urgency','controllability','persistence')) or b.evidence_strength.state not in ('NOT_ASSESSED','CONFLICTED'):
            raise ScopeError('No production provider is qualified for these dimensions')
        if current:
            latest = self._row(tables.assessment, subject_id)
            if latest['revision'] != value.revision or value.run_id != self.run_id or self._basis(subject['source_kind'], subject['source_id']) != b:
                raise RevisionConflict('Priority is historical or its source changed; reassessment required')
        return value

    def decide(self, subject_id, assessment_revision, request, *, expected_revision=None):
        request = AdviserRequest.from_json(request.to_json())
        # Idempotent replay preserves the original decision even after reassessment.
        replay = self.session.execute(select(tables.decision).where(
            tables.decision.c.client_id == self.client_id, tables.decision.c.request_id == request.request_id)).mappings().one_or_none()
        if replay:
            value = self.get_decision(replay['subject_id'], replay['revision'])
            if (value.subject_id, value.assessment_revision, value.request) != (subject_id, assessment_revision, request):
                raise RevisionConflict('Decision request identity reused with different content')
            return value
        self.get(subject_id, assessment_revision, current=True)
        old = self.get_decision(subject_id)
        if expected_revision != (old.revision if old else None):
            raise RevisionConflict('Decision change requires explicit predecessor')
        value = Decision(subject_id=subject_id, client_id=self.client_id,
            revision=old.revision+1 if old else 1, assessment_revision=assessment_revision, request=request)
        with self._savepoint():
            self.session.execute(insert(tables.decision).values(subject_id=subject_id, client_id=self.client_id,
                revision=value.revision, assessment_revision=assessment_revision, request_id=request.request_id,
                choice=request.choice, created_at=value.created_at.isoformat(), document=value.to_json()))
            self._audit(subject_id, 'ADVISER_DECIDED', old.to_json() if old else None, value.to_json(), request.actor)
        return value

    def get_decision(self, subject_id, revision=None):
        self._subject(subject_id)
        row = self._row(tables.decision, subject_id, revision)
        if row is None:
            if revision is not None:
                raise ScopeError('Missing decision revision')
            return None
        value = Decision.from_json(row['document'])
        if (value.subject_id, value.client_id, value.revision, value.assessment_revision,
                value.request.request_id, value.request.choice, value.created_at.isoformat()) != (
                subject_id, self.client_id, row['revision'], row['assessment_revision'],
                row['request_id'], row['choice'], row['created_at']):
            raise ScopeError('Decision envelope mismatch')
        self.get(subject_id, value.assessment_revision)
        return value

    def history(self, subject_id):
        self._subject(subject_id)
        assessments = tuple(self.get(subject_id, r) for r in self.session.scalars(select(tables.assessment.c.revision)
            .where(tables.assessment.c.subject_id == subject_id).order_by(tables.assessment.c.revision)))
        decisions = tuple(self.get_decision(subject_id, r) for r in self.session.scalars(select(tables.decision.c.revision)
            .where(tables.decision.c.subject_id == subject_id).order_by(tables.decision.c.revision)))
        return assessments, decisions

    def holding(self, choice):
        if choice not in ('ACCEPT','INVESTIGATE','REJECT'):
            raise ValueError('Unknown holding area')
        result = []
        for key in self.session.scalars(select(tables.subject.c.subject_id)
                .where(tables.subject.c.client_id == self.client_id).order_by(tables.subject.c.subject_id)):
            decision = self.get_decision(key)
            if decision and decision.request.choice == choice:
                assessment = self.get(key)
                try:
                    self.get(key, current=True)
                    source_current = True
                except (RevisionConflict, ScopeError):
                    source_current = False
                result.append(dict(subject=dict(self._subject(key)), assessment=assessment, decision=decision,
                    source_current=source_current,
                    reassessed_since_decision=assessment.revision != decision.assessment_revision))
        return tuple(result)
