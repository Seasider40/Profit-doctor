"""Canonical Impact qualification/history; no legacy conversion."""
from alembic import op
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint

revision = '0011_economic_impact'
down_revision = '0010_economic_bridge'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('canonical_impact_qualification',
        Column('candidate_id', String(64), primary_key=True), Column('revision', Integer, primary_key=True),
        Column('client_id', String(64), ForeignKey('client.client_id', ondelete='RESTRICT'), nullable=False),
        Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
        Column('bridge_id', String(64)), Column('source_object_id', String(64)),
        Column('document', Text, nullable=False),
        UniqueConstraint('candidate_id', 'revision', 'client_id', name='uq_impact_qualification_client'),
        ForeignKeyConstraint(['bridge_id', 'client_id'], ['canonical_bridge_snapshot.snapshot_id', 'canonical_bridge_snapshot.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['source_object_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'))

    op.create_table('canonical_impact',
        Column('impact_id', String(64), primary_key=True), Column('client_id', String(64), nullable=False),
        Column('candidate_id', String(64), nullable=False), Column('revision', Integer, nullable=False),
        Column('effect_id', String(64), nullable=False), Column('document', Text, nullable=False),
        ForeignKeyConstraint(['impact_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['candidate_id', 'revision', 'client_id'], ['canonical_impact_qualification.candidate_id', 'canonical_impact_qualification.revision', 'canonical_impact_qualification.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['effect_id', 'client_id'], ['economic_effect_v243.effect_id', 'economic_effect_v243.client_id'], ondelete='RESTRICT'),
        UniqueConstraint('candidate_id', 'revision', name='uq_impact_qualification_result'))

    op.create_table('canonical_impact_qualification_audit',
        Column('event_id', String(64), primary_key=True), Column('candidate_id', String(64), nullable=False),
        Column('revision', Integer, nullable=False), Column('client_id', String(64), nullable=False),
        Column('created_at', String(40), nullable=False), Column('document', Text, nullable=False),
        ForeignKeyConstraint(['candidate_id', 'revision', 'client_id'], ['canonical_impact_qualification.candidate_id', 'canonical_impact_qualification.revision', 'canonical_impact_qualification.client_id'], ondelete='RESTRICT'))


def downgrade():
    op.drop_table('canonical_impact_qualification_audit')
    op.drop_table('canonical_impact')
    op.drop_table('canonical_impact_qualification')
