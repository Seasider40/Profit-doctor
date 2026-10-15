"""Append-only administrative setup; preserve all frozen owners."""
from alembic import op
from sqlalchemy import Column, String, Integer, Text, ForeignKeyConstraint, UniqueConstraint, CheckConstraint

revision = '0021_adviser_setup'
down_revision = '0020_engagement_workspace'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('workspace_setup_draft',
        Column('draft_id', String(64), primary_key=True), Column('client_id', String(64), nullable=False),
        Column('created_at', String(40), nullable=False),
        UniqueConstraint('draft_id', 'client_id', name='uq_setup_draft_scope'),
        ForeignKeyConstraint(['client_id'], ['client.client_id'], ondelete='RESTRICT'))
    op.create_table('workspace_setup_revision',
        Column('revision_id', String(64), primary_key=True), Column('draft_id', String(64), nullable=False),
        Column('client_id', String(64), nullable=False), Column('revision', Integer, nullable=False),
        Column('previous_revision', Integer), Column('created_at', String(40), nullable=False),
        Column('actor', String(255), nullable=False), Column('event_type', String(32), nullable=False),
        Column('request_key', String(64), nullable=False), Column('digest', String(64), nullable=False),
        Column('document', Text, nullable=False),
        UniqueConstraint('draft_id', 'client_id', 'revision', name='uq_setup_revision_scope'),
        UniqueConstraint('client_id', 'request_key', name='uq_setup_revision_replay'),
        CheckConstraint('revision > 0', name='ck_setup_revision_positive'),
        CheckConstraint('(revision = 1 AND previous_revision IS NULL) OR (revision > 1 AND previous_revision IS NOT NULL AND previous_revision = revision - 1)', name='ck_setup_revision_previous'),
        ForeignKeyConstraint(['draft_id', 'client_id'], ['workspace_setup_draft.draft_id', 'workspace_setup_draft.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['draft_id', 'client_id', 'previous_revision'],
            ['workspace_setup_revision.draft_id', 'workspace_setup_revision.client_id', 'workspace_setup_revision.revision'], ondelete='RESTRICT'))
    op.create_table('workspace_setup_review_link',
        Column('draft_id', String(64), primary_key=True), Column('client_id', String(64), nullable=False),
        Column('engagement_id', String(64), nullable=False), Column('created_at', String(40), nullable=False),
        Column('actor', String(255), nullable=False),
        UniqueConstraint('engagement_id', name='uq_setup_link_review'),
        ForeignKeyConstraint(['draft_id', 'client_id'], ['workspace_setup_draft.draft_id', 'workspace_setup_draft.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['engagement_id', 'client_id'], ['workspace_engagement.engagement_id', 'workspace_engagement.client_id'], ondelete='RESTRICT'))


def downgrade():
    for table in ('workspace_setup_review_link', 'workspace_setup_revision', 'workspace_setup_draft'):
        op.drop_table(table)
