"""Canonical prospective Opportunities; no legacy conversion."""
from alembic import op
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint

revision = '0013_opportunity'
down_revision = '0012_receivables_snapshot'
branch_labels = None
depends_on = None


def upgrade():
    create = op.create_table
    create('canonical_collection_evidence',
        Column('evidence_id', String(64), primary_key=True), Column('client_id', String(64), nullable=False),
        Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
        Column('impact_id', String(64), ForeignKey('canonical_impact.impact_id', ondelete='RESTRICT'), nullable=False),
        Column('document', Text, nullable=False),
        UniqueConstraint('evidence_id', 'client_id', name='uq_collection_evidence_client'),
        ForeignKeyConstraint(['impact_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'))
    create('canonical_opportunity_candidate',
        Column('candidate_id', String(64), primary_key=True), Column('client_id', String(64), nullable=False),
        Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
        Column('impact_id', String(64), ForeignKey('canonical_impact.impact_id', ondelete='RESTRICT'), nullable=False),
        Column('effect_id', String(64), nullable=False), Column('document', Text, nullable=False),
        UniqueConstraint('candidate_id','client_id', name='uq_opportunity_candidate_client'),
        ForeignKeyConstraint(['candidate_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['impact_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['effect_id','client_id'], ['economic_effect_v243.effect_id','economic_effect_v243.client_id'], ondelete='RESTRICT'))
    create('canonical_opportunity_assessment',
        Column('candidate_id', String(64), primary_key=True), Column('revision', Integer, primary_key=True),
        Column('client_id', String(64), nullable=False), Column('evidence_id', String(64)), Column('document', Text, nullable=False),
        UniqueConstraint('candidate_id','revision','client_id', name='uq_opportunity_assessment_client'),
        ForeignKeyConstraint(['candidate_id','client_id'], ['canonical_opportunity_candidate.candidate_id','canonical_opportunity_candidate.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['evidence_id','client_id'], ['canonical_collection_evidence.evidence_id','canonical_collection_evidence.client_id'], ondelete='RESTRICT'))
    create('canonical_opportunity',
        Column('opportunity_id', String(64), primary_key=True), Column('client_id', String(64), nullable=False),
        Column('candidate_id', String(64), nullable=False), Column('revision', Integer, nullable=False),
        Column('document', Text, nullable=False),
        UniqueConstraint('candidate_id','revision', name='uq_opportunity_assessment_result'),
        ForeignKeyConstraint(['opportunity_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['candidate_id','revision','client_id'], ['canonical_opportunity_assessment.candidate_id','canonical_opportunity_assessment.revision','canonical_opportunity_assessment.client_id'], ondelete='RESTRICT'))
    create('canonical_opportunity_audit',
        Column('event_id', String(64), primary_key=True), Column('candidate_id', String(64), nullable=False),
        Column('client_id', String(64), nullable=False), Column('created_at', String(40), nullable=False),
        Column('document', Text, nullable=False),
        ForeignKeyConstraint(['candidate_id','client_id'], ['canonical_opportunity_candidate.candidate_id','canonical_opportunity_candidate.client_id'], ondelete='RESTRICT'))


def downgrade():
    for name in ('canonical_opportunity_audit','canonical_opportunity','canonical_opportunity_assessment','canonical_opportunity_candidate','canonical_collection_evidence'):
        op.drop_table(name)
