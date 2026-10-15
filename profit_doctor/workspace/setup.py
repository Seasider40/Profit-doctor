"""Durable partial setup without weakening the strict engagement contract."""
from datetime import date
import hashlib
import json
from typing import Literal
from pydantic import Field, model_validator
from sqlalchemy import insert, select
from profit_doctor.persistence import setup_schema as t
from profit_doctor.reasoning.domain.contracts import Contract, Identifier
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from .contracts import Scope, EngagementRevision
from .service import identifier, now, document


class SetupFields(Contract):
    title: str = Field(default='', max_length=255)
    entity_id: Identifier | None = None
    ledger_id: Identifier | None = None
    period_start: date | None = None
    period_end: date | None = None

    @model_validator(mode='after')
    def dates(self):
        if self.period_start and self.period_end and self.period_start > self.period_end:
            raise ValueError('Reporting period is reversed')
        return self

    def scope(self):
        if not self.title.strip():
            raise ValueError('Review title required')
        return Scope(entity_id=self.entity_id, ledger_id=self.ledger_id,
            period_start=self.period_start, period_end=self.period_end)


class SetupDraft(Contract):
    schema_version: Literal['SETUP-DRAFT-2.57'] = 'SETUP-DRAFT-2.57'
    draft_id: Identifier
    client_id: Identifier
    revision: int = Field(strict=True, ge=1)
    fields: SetupFields = Field(default_factory=SetupFields)
    step: int = Field(strict=True, ge=1, le=3)
    lifecycle: Literal['DRAFT', 'REVIEW_CREATED', 'COMPLETE', 'CANCELLED']
    engagement_id: Identifier | None = None

    @model_validator(mode='after')
    def linkage(self):
        if self.lifecycle == 'DRAFT' and (self.engagement_id is not None or self.step != 1):
            raise ValueError('Partial setup has no formal review')
        if self.lifecycle in ('REVIEW_CREATED', 'COMPLETE') and self.engagement_id is None:
            raise ValueError('Created review identity required')
        if self.lifecycle == 'COMPLETE' and self.step != 3:
            raise ValueError('Complete setup requires final step')
        if self.engagement_id:
            self.fields.scope()
        return self


class SetupService:
    def __init__(self, workspace):
        self.workspace = workspace
        self.session = workspace.session

    def get(self, client_id, draft_id, revision=None):
        self.workspace._row(t.draft, 'draft_id', draft_id, client_id)
        query = select(t.revision).where(t.revision.c.client_id == client_id, t.revision.c.draft_id == draft_id)
        if revision is not None:
            query = query.where(t.revision.c.revision == revision)
        row = self.session.execute(query.order_by(t.revision.c.revision.desc()).limit(1)).mappings().one_or_none()
        if row is None:
            raise ScopeError('Setup revision unavailable')
        value = SetupDraft.from_json(row['document'])
        if (value.client_id, value.draft_id, value.revision) != (client_id, draft_id, row['revision']):
            raise ScopeError('Setup indexed ownership differs')
        link = self.session.execute(select(t.link).where(t.link.c.draft_id == draft_id,
            t.link.c.client_id == client_id)).mappings().one_or_none()
        if value.engagement_id and (link is None or link['engagement_id'] != value.engagement_id):
            raise ScopeError('Setup linkage differs')
        if value.engagement_id:
            owned = self.workspace.engagement(client_id, value.engagement_id)
            if owned.scope != value.fields.scope():
                raise ScopeError('Setup scope differs from fixed review')
        return value

    def list(self, client_id, *, offset=0, limit=50):
        self.workspace.client(client_id)
        if not 0 <= offset or not 1 <= limit <= 50:
            raise ValueError('Bounded page required')
        latest = select(t.revision.c.draft_id, t.revision.c.revision, t.revision.c.document).where(
            t.revision.c.client_id == client_id).subquery()
        from sqlalchemy import func
        maximum = select(t.revision.c.draft_id, func.max(t.revision.c.revision).label('rev')).where(
            t.revision.c.client_id == client_id).group_by(t.revision.c.draft_id).subquery()
        rows = self.session.execute(select(latest.c.document, latest.c.draft_id, latest.c.revision).join(maximum,
            (latest.c.draft_id == maximum.c.draft_id) & (latest.c.revision == maximum.c.rev)).order_by(
                latest.c.draft_id).offset(offset).limit(limit)).mappings()
        result = []
        for row in rows:
            value = SetupDraft.from_json(row['document'])
            if (value.client_id, value.draft_id, value.revision) != (client_id, row['draft_id'], row['revision']):
                raise ScopeError('Setup list ownership differs')
            result.append(value.model_dump(mode='json'))
        return result

    def save(self, client_id, draft_id, fields, *, expected_revision, key, action='SAVE', step=1):
        self.workspace.client(client_id)
        if type(expected_revision) is not int or expected_revision < 0 or action not in ('SAVE', 'CREATE_REVIEW', 'COMPLETE', 'CANCEL'):
            raise ValueError('Valid setup operation and revision required')
        if not isinstance(key, str) or not 1 <= len(key) <= 64:
            raise ValueError('Bounded idempotency key required')
        fields = SetupFields.model_validate(fields.model_dump(mode='json') if isinstance(fields, SetupFields) else fields)
        payload = document({'client': client_id, 'draft': draft_id, 'fields': fields.model_dump(mode='json'),
            'expected': expected_revision, 'action': action, 'step': step})
        digest = hashlib.sha256(payload.encode()).hexdigest()
        replay = self.session.execute(select(t.revision).where(t.revision.c.client_id == client_id,
            t.revision.c.request_key == key)).mappings().one_or_none()
        if replay:
            if replay['digest'] != digest or replay['actor'] != self.workspace.operator.actor:
                raise RevisionConflict('Setup operation identity reused')
            return self.get(client_id, draft_id, replay['revision'])
        old = self.get(client_id, draft_id) if expected_revision else None
        if old and (old.revision != expected_revision or old.lifecycle in ('COMPLETE', 'CANCELLED')):
            raise RevisionConflict('Setup changed or is no longer editable')
        if old and old.engagement_id and fields != old.fields:
            raise RevisionConflict('Materialised scope/details are fixed in setup; edit the review separately')
        if old is None and action != 'SAVE':
            raise ValueError('Save partial setup before creating a review')
        lifecycle = old.lifecycle if old else 'DRAFT'
        engagement_id = old.engagement_id if old else None
        if action == 'COMPLETE':
            if not engagement_id or step != 3:
                raise ValueError('Created review and final step required')
            lifecycle = 'COMPLETE'
        if action == 'CANCEL':
            lifecycle = 'CANCELLED'
        with self.workspace.atomic():
            if old is None:
                self.session.execute(insert(t.draft).values(draft_id=draft_id, client_id=client_id, created_at=now()))
            if action == 'CREATE_REVIEW':
                if engagement_id:
                    raise RevisionConflict('Review already created')
                scope = fields.scope()
                engagement_id = identifier()
                self.workspace.save_engagement(EngagementRevision(engagement_id=engagement_id, client_id=client_id,
                    revision=1, title=fields.title, scope=scope), expected_revision=0, key='setup:' + identifier())
                self.session.execute(insert(t.link).values(draft_id=draft_id, client_id=client_id,
                    engagement_id=engagement_id, created_at=now(), actor=self.workspace.operator.actor))
                lifecycle, step = 'REVIEW_CREATED', 2
            value = SetupDraft(draft_id=draft_id, client_id=client_id, revision=expected_revision + 1,
                fields=fields, step=step, lifecycle=lifecycle, engagement_id=engagement_id)
            self.session.execute(insert(t.revision).values(revision_id=identifier(), draft_id=draft_id,
                client_id=client_id, revision=value.revision, previous_revision=expected_revision or None,
                created_at=now(), actor=self.workspace.operator.actor, event_type=action,
                request_key=key, digest=digest, document=value.to_json()))
        return value

    def history(self, client_id, draft_id):
        self.get(client_id, draft_id)
        rows = self.session.execute(select(t.revision).where(t.revision.c.client_id == client_id,
            t.revision.c.draft_id == draft_id).order_by(t.revision.c.revision)).mappings()
        result = []
        for row in rows:
            value = SetupDraft.from_json(row['document'])
            if (value.client_id, value.draft_id, value.revision) != (client_id, draft_id, row['revision']):
                raise ScopeError('Setup history ownership differs')
            result.append({'revision': value.revision, 'created_at': row['created_at'],
                'actor': row['actor'], 'event': row['event_type'], 'previous_revision': row['previous_revision'],
                'value': value.model_dump(mode='json')})
        return result

    def review_history(self, client_id, engagement_id):
        self.workspace.engagement(client_id, engagement_id)
        draft_id = self.session.execute(select(t.link.c.draft_id).where(t.link.c.client_id == client_id,
            t.link.c.engagement_id == engagement_id)).scalar_one_or_none()
        return self.history(client_id, draft_id) if draft_id else []
