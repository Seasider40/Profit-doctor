"""Priority and adviser history; no legacy conversion."""
from alembic import op
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint

revision = '0014_priority_decision'
down_revision = '0013_opportunity'
branch_labels = None
depends_on = None

def upgrade():
    create = op.create_table
    create('canonical_priority_subject',
        Column('subject_id', String(64), primary_key=True), Column('client_id', String(64), nullable=False),
        Column('source_id', String(64), nullable=False), Column('source_kind', String(32), nullable=False),
        UniqueConstraint('subject_id','client_id', name='uq_priority_subject_client'),
        UniqueConstraint('source_id','client_id','source_kind', name='uq_priority_source'),
        ForeignKeyConstraint(['source_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'))
    create('canonical_priority_assessment',
        Column('subject_id', String(64), primary_key=True), Column('revision', Integer, primary_key=True),
        Column('client_id', String(64), nullable=False), Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
        Column('created_at', String(40), nullable=False), Column('document', Text, nullable=False),
        UniqueConstraint('subject_id','revision','client_id', name='uq_priority_assessment_client'),
        ForeignKeyConstraint(['subject_id','client_id'], ['canonical_priority_subject.subject_id','canonical_priority_subject.client_id'], ondelete='RESTRICT'))
    create('canonical_adviser_decision',
        Column('subject_id', String(64), primary_key=True), Column('revision', Integer, primary_key=True),
        Column('client_id', String(64), nullable=False), Column('assessment_revision', Integer, nullable=False),
        Column('request_id', String(64), nullable=False), Column('choice', String(24), nullable=False),
        Column('created_at', String(40), nullable=False), Column('document', Text, nullable=False),
        UniqueConstraint('client_id','request_id', name='uq_adviser_request'),
        ForeignKeyConstraint(['subject_id','assessment_revision','client_id'], ['canonical_priority_assessment.subject_id','canonical_priority_assessment.revision','canonical_priority_assessment.client_id'], ondelete='RESTRICT'))
    create('canonical_priority_audit',
        Column('event_id', String(64), primary_key=True), Column('subject_id', String(64), nullable=False),
        Column('client_id', String(64), nullable=False), Column('created_at', String(40), nullable=False),
        Column('document', Text, nullable=False),
        ForeignKeyConstraint(['subject_id','client_id'], ['canonical_priority_subject.subject_id','canonical_priority_subject.client_id'], ondelete='RESTRICT'))

def downgrade():
    for name in ('canonical_priority_audit','canonical_adviser_decision','canonical_priority_assessment','canonical_priority_subject'):
        op.drop_table(name)
