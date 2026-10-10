"""Administrative workspace only; all analytical owners remain untouched."""
from alembic import op
from sqlalchemy import Column, String, Integer, Text, ForeignKeyConstraint, UniqueConstraint, CheckConstraint

revision = '0020_engagement_workspace'
down_revision = '0019_production_history'
branch_labels = None
depends_on = None


def table(name, key, *parts):
    op.create_table(name, Column(key, String(64), primary_key=True), Column('client_id', String(64), nullable=False),
        ForeignKeyConstraint(['client_id'], ['client.client_id'], ondelete='RESTRICT'),
        UniqueConstraint(key, 'client_id', name='uq_' + name + '_scope'), *parts)


def scoped(name, key, *parts):
    table(name, key, Column('engagement_id', String(64), nullable=False),
        ForeignKeyConstraint(['engagement_id', 'client_id'],
            ['workspace_engagement.engagement_id', 'workspace_engagement.client_id'], ondelete='RESTRICT'), *parts)


def revision_parts(name, owner):
    return (Column(owner, String(64), nullable=False), Column('revision', Integer, nullable=False),
        Column('document', Text, nullable=False), UniqueConstraint(owner, 'revision', name='uq_' + name + '_revision'),
        CheckConstraint('revision > 0', name='ck_' + name + '_revision'))


def upgrade():
    table('workspace_engagement', 'engagement_id', Column('created_at', String(40), nullable=False))
    table('workspace_engagement_revision', 'revision_id',
        *revision_parts('workspace_engagement_revision', 'engagement_id'),
        ForeignKeyConstraint(['engagement_id', 'client_id'],
            ['workspace_engagement.engagement_id', 'workspace_engagement.client_id'], ondelete='RESTRICT'))
    scoped('workspace_receipt', 'receipt_id', Column('document', Text, nullable=False), Column('predecessor_id', String(64)),
        UniqueConstraint('receipt_id', 'engagement_id', 'client_id', name='uq_workspace_receipt_engagement'),
        ForeignKeyConstraint(['predecessor_id', 'engagement_id', 'client_id'],
            ['workspace_receipt.receipt_id', 'workspace_receipt.engagement_id', 'workspace_receipt.client_id'], ondelete='RESTRICT'))
    scoped('workspace_registration_reference', 'reference_id', Column('receipt_id', String(64), nullable=False),
        Column('document', Text, nullable=False),
        ForeignKeyConstraint(['receipt_id', 'engagement_id', 'client_id'],
            ['workspace_receipt.receipt_id', 'workspace_receipt.engagement_id', 'workspace_receipt.client_id'], ondelete='RESTRICT'))
    scoped('workspace_information_request', 'request_id', Column('created_at', String(40), nullable=False),
        UniqueConstraint('request_id', 'engagement_id', 'client_id', name='uq_workspace_request_engagement'))
    scoped('workspace_information_request_revision', 'revision_id',
        *revision_parts('workspace_information_request_revision', 'request_id'),
        ForeignKeyConstraint(['request_id', 'engagement_id', 'client_id'],
            ['workspace_information_request.request_id', 'workspace_information_request.engagement_id',
             'workspace_information_request.client_id'], ondelete='RESTRICT'))
    scoped('workspace_audit', 'event_id', Column('created_at', String(40), nullable=False),
        Column('request_key', String(64), nullable=False), Column('document', Text, nullable=False),
        UniqueConstraint('client_id', 'request_key', name='uq_workspace_audit_replay'))


def downgrade():
    for name in ('workspace_audit', 'workspace_information_request_revision', 'workspace_information_request',
            'workspace_registration_reference', 'workspace_receipt', 'workspace_engagement_revision', 'workspace_engagement'):
        op.drop_table(name)
