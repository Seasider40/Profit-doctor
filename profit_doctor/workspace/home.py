"""Bounded administrative summaries; no original-file hashing or analysis."""
import json
from sqlalchemy import select, func
from profit_doctor.persistence import workspace_schema as t
from .contracts import EngagementRevision, InformationRevision
from profit_doctor.reasoning.domain.service import ScopeError


def reviews(workspace, *, offset=0, limit=50):
    if offset < 0 or not 1 <= limit <= 50:
        raise ValueError('Bounded page required')
    allowed = workspace.operator.clients
    latest = select(t.engagement_revision.c.engagement_id, func.max(t.engagement_revision.c.revision).label('rev')).where(
        t.engagement_revision.c.client_id.in_(allowed)).group_by(t.engagement_revision.c.engagement_id).subquery()
    rows = workspace.session.execute(select(t.engagement_revision, t.engagement.c.created_at).join(latest,
        (t.engagement_revision.c.engagement_id == latest.c.engagement_id) &
        (t.engagement_revision.c.revision == latest.c.rev)).join(t.engagement,
        t.engagement.c.engagement_id == t.engagement_revision.c.engagement_id).where(
        t.engagement_revision.c.client_id.in_(allowed)).order_by(t.engagement.c.created_at.desc(),
        t.engagement.c.engagement_id).offset(offset).limit(limit)).mappings().all()
    ids = [r['engagement_id'] for r in rows]
    if not ids:
        return []
    newest = select(t.request_revision.c.request_id, func.max(t.request_revision.c.revision).label('rev')).where(
        t.request_revision.c.client_id.in_(allowed), t.request_revision.c.engagement_id.in_(ids)).group_by(t.request_revision.c.request_id).subquery()
    requests = workspace.session.execute(select(t.request_revision).join(newest,
        (t.request_revision.c.request_id == newest.c.request_id) & (t.request_revision.c.revision == newest.c.rev)).where(
        t.request_revision.c.client_id.in_(allowed), t.request_revision.c.engagement_id.in_(ids))).mappings()
    outstanding = {i: 0 for i in ids}
    for row in requests:
        value = InformationRevision.from_json(row['document'])
        if (value.client_id, value.engagement_id, value.request_id, value.revision) != (
                row['client_id'], row['engagement_id'], row['request_id'], row['revision']):
            raise ScopeError('Request summary ownership differs')
        if value.status in ('OPEN', 'EVIDENCE_RECEIVED'):
            outstanding[value.engagement_id] += 1
    result = []
    for row in rows:
        value = EngagementRevision.from_json(row['document'])
        if (value.client_id, value.engagement_id, value.revision) != (row['client_id'], row['engagement_id'], row['revision']):
            raise ScopeError('Review summary ownership differs')
        result.append({'review': value.model_dump(mode='json'), 'created_at': row['created_at'],
            'outstanding_information': outstanding[value.engagement_id]})
    return result
