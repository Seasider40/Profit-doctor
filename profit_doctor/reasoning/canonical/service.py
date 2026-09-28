"""Opt-in semantic writer. Caller owns both source and destination transactions.

Uniqueness races fail closed: rollback/retry the caller's complete transaction.
No source mutation, legacy promotion, downstream cutover or autonomous commit.
"""
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, localcontext

from sqlalchemy import insert, select, update

from profit_doctor.persistence import EngineRun
from profit_doctor.persistence import canonical_schema as tables
from profit_doctor.reasoning.domain.contracts import AuditEvent, EvidenceLink, ReasoningObject
from profit_doctor.reasoning.domain.service import FoundationService, RevisionConflict, ScopeError
from .contracts import (CanonicalFact, CanonicalFinding, CanonicalisationResult, FindingAssessment,
                        FindingObservation, Measurement, ReportingScope)
from .registry import REGISTRY, REFUSALS, ZERO_DENOMINATOR_GUARDS, Unit


def identity(*parts):
    return 'cf_' + hashlib.sha256(json.dumps(parts, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:60]


class CanonicalService:
    def __init__(self, session, client_id, actor, source):
        if source.client_id != client_id:
            raise ScopeError('Source and destination client scope must agree')
        self.session, self.client_id, self.source = session, client_id, source
        self.foundation = FoundationService(session, client_id, actor, source.resolve)

    def _get(self, table, object_id, contract):
        row = self.session.execute(select(table).where(table.c.object_id == object_id,
                                    table.c.client_id == self.client_id)).mappings().one_or_none()
        if row is None:
            raise ScopeError('Semantic object missing or outside client scope')
        value = contract.from_json(row['document'])
        envelope = self.foundation.get_object(object_id)
        if (value.object_id, value.client_id, value.revision) != (row['object_id'], row['client_id'], row['revision']):
            raise ScopeError('Semantic document disagrees with indexed scope')
        expected = 'FACT' if contract is CanonicalFact else 'FINDING'
        if envelope.object_type != expected or envelope.revision != value.revision:
            raise ScopeError('Semantic extension disagrees with foundation identity')
        if contract is CanonicalFact and (value.run_id, value.lineage, value.scope.period_from, value.scope.period_to) != (
                envelope.run_id, envelope.lineage, envelope.period_from, envelope.period_to):
            raise ScopeError('Fact origin disagrees with foundation identity')
        if contract is CanonicalFinding and value.first_seen_run != envelope.run_id:
            raise ScopeError('Finding origin disagrees with foundation identity')
        return value

    def get_fact(self, object_id):
        return self._get(tables.fact, object_id, CanonicalFact)

    def get_finding(self, object_id):
        return self._get(tables.finding, object_id, CanonicalFinding)

    def history(self, object_id):
        self.foundation.get_object(object_id)
        return tuple(self.session.scalars(select(tables.history.c.document).where(
            tables.history.c.object_id == object_id, tables.history.c.client_id == self.client_id)
            .order_by(tables.history.c.revision)))

    def _write(self, table, value, old=None):
        value = type(value).from_json(value.to_json())
        row = dict(object_id=value.object_id, client_id=value.client_id,
                   revision=value.revision, document=value.to_json())
        if old is None:
            self.session.execute(insert(table).values(**row))
        else:
            result = self.session.execute(update(table).where(table.c.object_id == old.object_id,
                table.c.client_id == self.client_id, table.c.revision == old.revision).values(**row))
            if result.rowcount != 1:
                raise RevisionConflict('Semantic revision changed concurrently')
        self.session.execute(insert(tables.history).values(**row,
            revision_id=identity(value.object_id, value.revision)))

    def _audit(self, object_id, event_type, previous, new):
        self.foundation.append_audit(AuditEvent(client_id=self.client_id, object_id=object_id,
            event_type=event_type, actor=self.foundation.actor, previous=previous, new=new))

    def canonicalise(self, signal_id, *, supersedes=None, correction_rationale=None):
        signal, execution, refs, digest = self.source.read(signal_id)
        mapping = REGISTRY.get((signal['test_id'], signal['signal_type']))
        if mapping is None:
            reason = REFUSALS.get(signal['signal_type'], (None, 'Unknown producer/Signal combination; no fallback'))[1]
            return CanonicalisationResult(outcome='UNMAPPED', reason=reason)
        eligibility = execution['eligibility_state']
        if signal['status'] != 'ACTIVE' or execution['execution_status'] != 'COMPLETED' or eligibility not in ('FULL', 'PARTIAL-A', 'PARTIAL-B', 'PARTIAL-C'):
            return CanonicalisationResult(outcome='REFUSED', reason='Inactive, incomplete or ineligible source')
        if signal['unit'] != mapping.source_unit or signal['entity_type'] != mapping.entity_type:
            return CanonicalisationResult(outcome='REFUSED', reason='Source unit or entity type violates mapping')
        if len(refs) < 3:
            return CanonicalisationResult(outcome='REFUSED', reason='Source ancestry is absent')
        guarded = ZERO_DENOMINATOR_GUARDS.get((signal['test_id'], signal['signal_type']))
        if guarded:
            field = {'observed': 'observed_value', 'comparison': 'comparison_value', 'derived': 'variance_value'}[guarded]
            if signal[field] is not None and Decimal(signal[field]).is_zero():
                return CanonicalisationResult(outcome='REFUSED', reason='Zero may be an undefined-denominator sentinel; denominator evidence is required')
        oid = identity(self.client_id, signal['run_id'], signal_id, mapping.version)
        measurements = []
        for spec, key in zip(mapping.slots, ('observed_value', 'comparison_value', 'variance_value')):
            value = signal[key]
            if spec is None and value is not None or spec is not None and spec.required and value is None:
                return CanonicalisationResult(outcome='REFUSED', reason='Missing required or unexpectedly populated measurement')
            measurements.append(None if value is None else Measurement(metric=spec.metric, value=value,
                unit=spec.unit, currency='GBP' if spec.unit in (Unit.CURRENCY, Unit.CURRENCY_PER_FTE, Unit.CURRENCY_PER_UNIT) else None, basis=spec.basis))
        if supersedes:
            prior = self.get_fact(supersedes)
            if (prior.mapping_version == mapping.version or prior.source_signal_id != signal_id
                    or prior.run_id != signal['run_id'] or prior.state != 'OBSERVED'
                    or not correction_rationale or not correction_rationale.strip()):
                return CanonicalisationResult(outcome='REFUSED', reason='Correction requires an observed same-source predecessor, new mapping and rationale')
        fact = CanonicalFact(object_id=oid, client_id=self.client_id, run_id=signal['run_id'], supersedes=supersedes,
            source_signal_id=signal_id, source_digest=digest, diagnostic=signal['test_id'], signal_type=signal['signal_type'],
            mapping_version=mapping.version, family=mapping.family,
            scope=ReportingScope(entity_type=signal['entity_type'], entity_id=signal['entity_id'],
                period_from=signal['period_from'], period_to=signal['period_to'], period_basis=mapping.period_basis),
            observed=measurements[0], comparison=measurements[1], derived=measurements[2],
            eligibility=eligibility, limitations=tuple(x for x in [execution['limitation']] if x), lineage=refs)
        existing = self.session.scalar(select(tables.fact.c.object_id).where(tables.fact.c.object_id == oid))
        if existing:
            old = self.get_fact(oid)
            if old.source_digest != digest:
                return CanonicalisationResult(outcome='REFUSED', reason='Source mutated under a stable identity; preserve history and review correction')
            return CanonicalisationResult(outcome='REPLAYED', reason='Existing mapping/source identity', fact=old)
        # A surviving foundation identity after semantic downgrade cannot be
        # silently reused or reconstructed: require a controlled restore.
        self.foundation.create_object(ReasoningObject(object_id=oid, object_type='FACT', client_id=self.client_id,
            run_id=fact.run_id, source_authority='SYSTEM_DERIVED', lineage=refs,
            period_from=fact.scope.period_from, period_to=fact.scope.period_to))
        self._write(tables.fact, fact)
        source_id = identity('source-signal', self.client_id, fact.run_id, signal_id)
        from profit_doctor.persistence import reasoning_schema
        if not self.session.scalar(select(reasoning_schema.reasoning_object.c.object_id).where(
                reasoning_schema.reasoning_object.c.object_id == source_id)):
            self.foundation.create_object(ReasoningObject(object_id=source_id, object_type='SIGNAL',
                client_id=self.client_id, run_id=fact.run_id, source_authority='SYSTEM_DERIVED', lineage=refs))
        self.foundation.link_evidence(EvidenceLink(link_id=identity(source_id, oid, 'SUPPORTS'),
            client_id=self.client_id, run_id=fact.run_id, source_id=source_id, target_id=oid,
            source_authority='SYSTEM_DERIVED', relationship_type='SUPPORTS', evidence_role='SUPPORTING'))
        self._audit(oid, 'OBJECT_UPDATED', None, fact.model_dump(mode='json'))
        if supersedes:
            self.invalidate(supersedes, correction_rationale, superseded_by=oid)
        return CanonicalisationResult(outcome='CREATED', reason='Explicit typed source mapping', fact=fact)

    def invalidate(self, object_id, rationale, *, superseded_by=None):
        if not rationale or not rationale.strip():
            raise ValueError('Correction requires rationale')
        old = self.get_fact(object_id)
        if old.state != 'OBSERVED':
            raise RevisionConflict('Only an observed Fact can be invalidated/superseded')
        if superseded_by:
            replacement = self.get_fact(superseded_by)
            if (replacement.source_signal_id != old.source_signal_id or replacement.run_id != old.run_id
                    or replacement.mapping_version == old.mapping_version or replacement.state != 'OBSERVED'):
                raise ValueError('Supersession requires a different qualified mapping for the same source')
        envelope = self.foundation.get_object(object_id)
        self.foundation.update_object(envelope.model_copy(update=dict(revision=envelope.revision + 1,
            updated_at=datetime.now(timezone.utc))))
        value = old.model_copy(update=dict(revision=old.revision + 1,
            state='SUPERSEDED' if superseded_by else 'INVALIDATED'))
        self._write(tables.fact, value, old)
        self._audit(object_id, 'OBJECT_SUPERSEDED' if superseded_by else 'STATUS_CHANGED',
                    old.model_dump(mode='json'), {'state': value.state, 'replacement': superseded_by, 'rationale': rationale})
        return value

    def assess(self, fact_id, *, contradictory=(), mitigating=()):
        fact = self.get_fact(fact_id)
        finding_type = {('REV-01', 'COMPARABLE_REVENUE_CHANGE'): 'REVENUE_MOVEMENT',
            ('GM-01', 'CONTRIBUTION_MARGIN_CHANGE'): 'MARGIN_MOVEMENT',
            ('CUS-01', 'TOP_CUSTOMER_CONCENTRATION'): 'CUSTOMER_CONCENTRATION'}.get((fact.diagnostic, fact.signal_type))
        for oid in (*contradictory, *mitigating):
            if oid == fact_id:
                raise ValueError('A Fact cannot challenge itself')
            self.foundation.get_object(oid)
        outcome, reason = 'INSUFFICIENT_EVIDENCE', 'No qualified significance policy for this measurement'
        if fact.state != 'OBSERVED':
            reason = 'Fact is superseded or invalidated'
        elif contradictory or mitigating or fact.eligibility != 'FULL' or fact.limitations:
            outcome, reason = 'HELD_LIMITED', 'Resolve declared counter-evidence, mitigation or source limitations before significance'
        elif (fact.diagnostic, fact.signal_type) == ('REV-01', 'COMPARABLE_REVENUE_CHANGE'):
            if fact.comparison.value != 0:
                # Equivalent to the frozen 5% diagnostic boundary; this is
                # revenue movement significance, not loss, cause or opportunity.
                with localcontext() as ctx:
                    ctx.prec = max(len(fact.comparison.value.as_tuple().digits), len(fact.derived.value.as_tuple().digits)) + 10
                    significant = fact.derived.value.copy_abs() >= fact.comparison.value.copy_abs() * Decimal('.05')
                finding_type = 'REVENUE_MOVEMENT'
                outcome = 'FINDING_CREATED' if significant else 'NOT_SIGNIFICANT'
                reason = 'Absolute observed revenue movement compared with 5% of prior revenue; no causality inferred'
        elif (fact.diagnostic, fact.signal_type) == ('GM-01', 'CONTRIBUTION_MARGIN_CHANGE'):
            finding_type = 'MARGIN_MOVEMENT'
            outcome = 'FINDING_CREATED' if fact.derived.value.copy_abs() >= Decimal('1') else 'NOT_SIGNIFICANT'
            reason = 'Observed contribution margin movement compared with 1 percentage point; no recoverability inferred'
        elif (fact.diagnostic, fact.signal_type) == ('CUS-01', 'TOP_CUSTOMER_CONCENTRATION'):
            finding_type = 'CUSTOMER_CONCENTRATION'
            outcome = 'FINDING_CREATED' if fact.observed.value >= Decimal('15') else 'NOT_SIGNIFICANT'
            reason = 'Largest customer revenue share compared with 15%; no loss probability inferred'
        assessment = FindingAssessment(outcome=outcome, rationale=reason)
        self._audit(fact_id, 'OBJECT_UPDATED', None, {'significance_assessment': assessment.model_dump(mode='json'),
                    'contradictory': list(contradictory), 'mitigating': list(mitigating)})
        if finding_type is None:
            return assessment
        key = json.dumps([self.client_id, finding_type, fact.diagnostic, fact.signal_type,
            fact.scope.entity_type, fact.scope.entity_id, fact.scope.period_basis, fact.mapping_version], separators=(',', ':'))
        oid = identity('finding', key)
        observation = FindingObservation(run_id=fact.run_id, fact_id=fact_id, scope=fact.scope)
        exists = self.session.scalar(select(tables.finding.c.object_id).where(tables.finding.c.object_id == oid))
        old = self.get_finding(oid) if exists else None
        if outcome != 'FINDING_CREATED' and old is None:
            return assessment
        assessment = assessment.model_copy(update={'finding_id': oid})
        repeated = old and any(o.fact_id == fact_id for o in old.observations)
        if repeated and old.assessment == assessment and old.contradictory_evidence == tuple(contradictory) and old.mitigating_evidence == tuple(mitigating):
            return old.assessment
        temporal = 'FIRST_OBSERVATION'
        if repeated:
            temporal = old.temporal_state
        elif old:
            prior = old.observations[-1]
            temporal = 'INSUFFICIENT_TEMPORAL_EVIDENCE'
            prev_run = self.session.get(EngineRun, prior.run_id)
            this_run = self.session.get(EngineRun, fact.run_id)
            a, b = prior.scope, fact.scope
            if all([a.period_from, a.period_to, b.period_from, b.period_to]):
                if a.period_from == b.period_from and a.period_to == b.period_to:
                    temporal = 'REPEATED_OBSERVATION'
                elif (a.period_to < b.period_from and
                      a.period_to - a.period_from == b.period_to - b.period_from and
                      datetime.fromisoformat(prev_run.started_at) < datetime.fromisoformat(this_run.started_at)):
                    temporal = 'PREVIOUS_COMPARABLE_PERIOD'
        finding = CanonicalFinding(object_id=oid, client_id=self.client_id, finding_type=finding_type,
            semantic_key=key, first_seen_run=old.first_seen_run if old else fact.run_id,
            latest_seen_run=fact.run_id, observations=old.observations if repeated else ((*old.observations, observation) if old else (observation,)),
            contradictory_evidence=tuple(contradictory), mitigating_evidence=tuple(mitigating),
            assessment=assessment, temporal_state=temporal, revision=old.revision + 1 if old else 1)
        if old:
            envelope = self.foundation.get_object(oid)
            self.foundation.update_object(envelope.model_copy(update=dict(revision=finding.revision,
                updated_at=datetime.now(timezone.utc))))
        else:
            self.foundation.create_object(ReasoningObject(object_id=oid, object_type='FINDING', client_id=self.client_id,
                run_id=fact.run_id, source_authority='SYSTEM_DERIVED', status='DETECTED'))
        self._write(tables.finding, finding, old)
        from profit_doctor.persistence import reasoning_schema
        relationships = [(fact_id, 'SUPPORTS', 'SUPPORTING')]
        relationships += [(eid, 'CONTRADICTS', 'CONTRADICTORY') for eid in contradictory]
        relationships += [(eid, 'MITIGATES', 'MITIGATING') for eid in mitigating]
        for source, relationship, role in relationships:
            link_id = identity(source, oid, relationship)
            if not self.session.scalar(select(reasoning_schema.evidence_link.c.link_id).where(reasoning_schema.evidence_link.c.link_id == link_id)):
                authority = self.foundation.get_object(source).source_authority
                self.foundation.link_evidence(EvidenceLink(link_id=link_id, client_id=self.client_id, run_id=fact.run_id,
                    source_id=source, target_id=oid, source_authority=authority, relationship_type=relationship, evidence_role=role))
        self._audit(oid, 'OBJECT_UPDATED', old.model_dump(mode='json') if old else None, finding.model_dump(mode='json'))
        return assessment
