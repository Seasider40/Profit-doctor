"""Explicit canonical writes; caller owns Session, transaction and engine.

No legacy writer imports this service. Raw SQL can bypass application enums and
revision rules; callers must use this boundary. Database FKs still protect tenant
and endpoint existence. Lineage across stores is fail-closed without a resolver.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from .contracts import (Actor, AuditEvent, EconomicEffect, EffectOverlap,
                        EffectReference, EvidenceLink, LineageReference,
                        ReasoningObject)
from .vocabulary import AuditEventType, LineageKind, ObjectType
from profit_doctor.persistence import Base, Client, EngineRun
from profit_doctor.persistence import reasoning_schema as tables


class ScopeError(ValueError):
    pass


class RevisionConflict(ValueError):
    pass


@dataclass(frozen=True)
class ResolvedScope:
    """Actual ownership returned by a trusted cross-store resolver, not a claim."""
    client_id: str
    run_id: str | None = None


# Existing SQLAlchemy identities; no competing source-file or dataset tables.
SQL_LINEAGE = {
    LineageKind.PRIMITIVE_RESULT: ('primitive_result_v2', 'primitive_result_id'),
    LineageKind.DIAGNOSTIC: ('test_execution_v2', 'test_execution_id'),
    LineageKind.ANALYTICAL_RUN: ('engine_run', 'run_id'),
}


class FoundationService:
    def __init__(self, session: Session, client_id: str, actor: Actor,
                 legacy_resolver: Callable[[LineageReference], ResolvedScope] | None = None):
        self.session = session
        self.client_id = client_id
        self.actor = Actor.from_json(actor.to_json())
        self.legacy_resolver = legacy_resolver

    def _run(self, run_id):
        if run_id is not None:
            row = self.session.get(EngineRun, run_id)
            if row is None or row.client_id != self.client_id:
                raise ScopeError('Run is missing or belongs to another client')

    def _lineage(self, ref):
        if ref.client_id != self.client_id:
            raise ScopeError('Cross-client lineage is prohibited')
        self._run(ref.run_id)
        if ref.store == 'CANONICAL':
            if ref.kind != LineageKind.DERIVED_ANCESTOR or ref.resource != 'reasoning_object_v243':
                raise ScopeError('Unsupported canonical lineage identity')
            obj = self.get_object(ref.source_id)
            actual = ResolvedScope(obj.client_id, obj.run_id)
        elif ref.store == 'SQLALCHEMY':
            expected = SQL_LINEAGE.get(ref.kind)
            if expected is None or ref.resource != expected[0]:
                raise ScopeError('Unsupported SQLAlchemy lineage identity')
            table = Base.metadata.tables[expected[0]]
            row = self.session.execute(select(table).where(table.c[expected[1]] == ref.source_id)).mappings().one_or_none()
            if row is None:
                raise ScopeError('Missing lineage endpoint')
            actual = ResolvedScope(row['client_id'], row['run_id'])
        else:
            if self.legacy_resolver is None:
                raise ScopeError('Legacy lineage requires a trusted owning-store resolver')
            actual = self.legacy_resolver(ref)
        if not isinstance(actual, ResolvedScope) or actual != ResolvedScope(ref.client_id, ref.run_id):
            raise ScopeError('Lineage ownership does not match its existing source')

    def _validate(self, value):
        # Revalidate even model_construct/model_copy and mutated nested metadata.
        value = type(value).from_json(value.to_json())
        if value.client_id != self.client_id or self.session.get(Client, self.client_id) is None:
            raise ScopeError('Client is missing or outside the service scope')
        self._run(value.run_id)
        for ref in value.lineage:
            self._lineage(ref)
        if value.entity:
            self._lineage(value.entity)
        return value

    def _row(self, value, **extra):
        return dict(client_id=value.client_id, run_id=value.run_id,
                    schema_version=value.schema_version,
                    created_at=value.created_at.isoformat(), document=value.to_json(), **extra)

    def _get(self, table, key, identity, contract):
        row = self.session.execute(select(table).where(
            table.c[key] == identity, table.c.client_id == self.client_id)).mappings().one_or_none()
        if row is None:
            raise ScopeError('Endpoint is missing or outside the service scope')
        value = contract.from_json(row['document'])
        self._consistent(row, value)
        return value

    @staticmethod
    def _consistent(row, value):
        # Fail closed if an out-of-band writer corrupts the indexed envelope.
        for key, stored in row.items():
            if key in ('document', 'pair_key'):
                continue
            actual = getattr(value, key)
            if key == 'created_at':
                actual = actual.isoformat()
            if actual != stored:
                raise ScopeError('Stored contract disagrees with its indexed identity or scope')

    def get_object(self, object_id):
        return self._get(tables.reasoning_object, 'object_id', object_id, ReasoningObject)

    def get_effect(self, effect_id):
        return self._get(tables.economic_effect, 'effect_id', effect_id, EconomicEffect)

    def get_link(self, link_id):
        return self._get(tables.evidence_link, 'link_id', link_id, EvidenceLink)

    def get_effect_reference(self, reference_id):
        return self._get(tables.effect_reference, 'reference_id', reference_id, EffectReference)

    def get_effect_overlap(self, overlap_id):
        return self._get(tables.effect_overlap, 'overlap_id', overlap_id, EffectOverlap)

    def audit_events(self, *, object_id=None, effect_id=None):
        if (object_id is None) == (effect_id is None):
            raise ValueError('Select exactly one audit subject')
        self.get_object(object_id) if object_id else self.get_effect(effect_id)
        t = tables.audit_event
        condition = t.c.object_id == object_id if object_id else t.c.effect_id == effect_id
        events = []
        for row in self.session.execute(select(t).where(condition, t.c.client_id == self.client_id)
                                        .order_by(t.c.created_at, t.c.event_id)).mappings():
            value = AuditEvent.from_json(row['document'])
            self._consistent(row, value)
            events.append(value)
        return tuple(events)

    def append_audit(self, event: AuditEvent):
        event = self._validate(event)
        self.get_object(event.object_id) if event.object_id else self.get_effect(event.effect_id)
        self.session.execute(insert(tables.audit_event).values(**self._row(
            event, event_id=event.event_id, object_id=event.object_id,
            effect_id=event.effect_id, event_type=event.event_type.value)))
        return event

    def _audit(self, value, event_type, *, object_id=None, effect_id=None, previous=None, new=None):
        return self.append_audit(AuditEvent(
            client_id=value.client_id, run_id=value.run_id, object_id=object_id,
            effect_id=effect_id, event_type=event_type, actor=self.actor,
            lineage=value.lineage, previous=previous, new=new))

    def create_object(self, value: ReasoningObject):
        value = self._validate(value)
        if value.revision != 1 or value.updated_at is not None:
            raise ValueError('New identities start at revision 1 without an update timestamp')
        self.session.execute(insert(tables.reasoning_object).values(**self._row(
            value, object_id=value.object_id, object_type=value.object_type.value,
            source_authority=value.source_authority.value, revision=value.revision)))
        self._audit(value, AuditEventType.OBJECT_CREATED, object_id=value.object_id,
                    new=value.model_dump(mode='json'))
        return value

    def update_object(self, value: ReasoningObject):
        value = self._validate(value)
        old = self.get_object(value.object_id)
        # Identity, scope, origin and ancestry cannot be silently rewritten.
        immutable = ('object_type', 'schema_version', 'client_id', 'run_id', 'entity',
                     'period_from', 'period_to', 'created_at', 'source_authority', 'lineage')
        if any(getattr(old, k) != getattr(value, k) for k in immutable):
            raise ValueError('Identity, source authority, scope and ancestry are immutable')
        if value.revision != old.revision + 1 or value.updated_at is None:
            raise RevisionConflict('Update requires the next revision and an update timestamp')
        if value.updated_at < (old.updated_at or old.created_at):
            raise RevisionConflict('Update timestamp moves backwards')
        t = tables.reasoning_object
        result = self.session.execute(update(t).where(
            t.c.object_id == value.object_id, t.c.client_id == self.client_id,
            t.c.revision == old.revision).values(document=value.to_json(), revision=value.revision))
        if result.rowcount != 1:
            raise RevisionConflict('Concurrent update; reload the current revision')
        self._audit(value, AuditEventType.OBJECT_UPDATED, object_id=value.object_id,
                    previous=old.model_dump(mode='json'), new=value.model_dump(mode='json'))
        for name, event_type in [('status', AuditEventType.STATUS_CHANGED),
                                  ('confidence', AuditEventType.CONFIDENCE_CHANGED),
                                  ('materiality', AuditEventType.MATERIALITY_CHANGED)]:
            if getattr(old, name) != getattr(value, name):
                self._audit(value, event_type, object_id=value.object_id,
                            previous=old.model_dump(mode='json')[name], new=value.model_dump(mode='json')[name])
        return value

    def create_effect(self, value: EconomicEffect):
        value = self._validate(value)
        self.session.execute(insert(tables.economic_effect).values(**self._row(value, effect_id=value.effect_id)))
        self._audit(value, AuditEventType.OBJECT_CREATED, effect_id=value.effect_id,
                    new=value.model_dump(mode='json'))
        return value

    def link_evidence(self, value: EvidenceLink):
        value = self._validate(value)
        source, target = self.get_object(value.source_id), self.get_object(value.target_id)
        if value.source_authority != source.source_authority:
            raise ValueError('Evidence link must retain source authority')
        # Cross-run links within a client are intentional (e.g. temporal ancestry).
        self.session.execute(insert(tables.evidence_link).values(**self._row(
            value, link_id=value.link_id, source_id=source.object_id, target_id=target.object_id,
            relationship_type=value.relationship_type.value)))
        self._audit(value, AuditEventType.EVIDENCE_LINKED, object_id=target.object_id,
                    new=value.model_dump(mode='json'))
        return value

    def reference_effect(self, value: EffectReference):
        value = self._validate(value)
        obj = self.get_object(value.object_id)
        self.get_effect(value.effect_id)
        if obj.object_type not in (ObjectType.ECONOMIC_STORY, ObjectType.ECONOMIC_IMPACT,
                                   ObjectType.OPPORTUNITY_CANDIDATE, ObjectType.VALIDATED_OPPORTUNITY):
            raise ValueError('Effect references belong to stories, impacts and opportunities')
        self.session.execute(insert(tables.effect_reference).values(**self._row(
            value, reference_id=value.reference_id, object_id=value.object_id, effect_id=value.effect_id)))
        self._audit(value, AuditEventType.EVIDENCE_LINKED, object_id=value.object_id,
                    new=value.model_dump(mode='json'))
        return value

    def relate_effects(self, value: EffectOverlap):
        value = self._validate(value)
        self.get_effect(value.source_effect_id)
        self.get_effect(value.target_effect_id)
        # One current declared relationship per pair. Direction remains in the
        # document for PARENT_CHILD; contradictory pair declarations are refused.
        pair = '|'.join(sorted((value.source_effect_id, value.target_effect_id)))
        self.session.execute(insert(tables.effect_overlap).values(**self._row(
            value, overlap_id=value.overlap_id, source_effect_id=value.source_effect_id,
            target_effect_id=value.target_effect_id, overlap_type=value.overlap_type.value, pair_key=pair)))
        self._audit(value, AuditEventType.EVIDENCE_LINKED, effect_id=value.source_effect_id,
                    new=value.model_dump(mode='json'))
        return value
