"""Add governed temporal assessment and audit history.

Revision ID: 0016_temporal_evidence
Revises: 0015_dataset_comparability
"""
from alembic import op
from sqlalchemy import Column, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint

revision = '0016_temporal_evidence'
down_revision = '0015_dataset_comparability'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('canonical_temporal_assessment',
        Column('assessment_id', String(64), primary_key=True),
        Column('series_id', String(64), nullable=False),
        Column('subject_id', String(64), nullable=False),
        Column('client_id', String(64), nullable=False),
        Column('run_id', String(64), nullable=False),
        Column('revision', Integer, nullable=False),
        Column('supersedes', String(64)),
        Column('created_at', String(40), nullable=False),
        Column('document', Text, nullable=False),
        UniqueConstraint('assessment_id', 'client_id', name='uq_temporal_assessment_client'),
        UniqueConstraint('series_id', 'revision', name='uq_temporal_series_revision'),
        ForeignKeyConstraint(['run_id'], ['engine_run.run_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['subject_id', 'client_id'],
            ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['supersedes', 'client_id'],
            ['canonical_temporal_assessment.assessment_id', 'canonical_temporal_assessment.client_id'], ondelete='RESTRICT'))
    op.create_table('canonical_temporal_audit',
        Column('event_id', String(64), primary_key=True),
        Column('assessment_id', String(64), nullable=False),
        Column('client_id', String(64), nullable=False),
        Column('created_at', String(40), nullable=False),
        Column('document', Text, nullable=False),
        ForeignKeyConstraint(['assessment_id', 'client_id'],
            ['canonical_temporal_assessment.assessment_id', 'canonical_temporal_assessment.client_id'], ondelete='RESTRICT'))


def downgrade():
    op.drop_table('canonical_temporal_audit')
    op.drop_table('canonical_temporal_assessment')
