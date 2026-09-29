"""Immutable measurement semantics and scoped value-owner bindings."""
from alembic import op
import sqlalchemy as sa

revision = '0009_measurement_context'
down_revision = '0008_economic_story'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('canonical_measurement_context',
        sa.Column('context_id', sa.String(64), primary_key=True),
        sa.Column('client_id', sa.String(64), sa.ForeignKey('client.client_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('run_id', sa.String(64), sa.ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('supersedes', sa.String(64)), sa.Column('document', sa.Text(), nullable=False),
        sa.UniqueConstraint('context_id', 'client_id', name='uq_measurement_context_client'),
        sa.ForeignKeyConstraint(['supersedes','client_id'], ['canonical_measurement_context.context_id','canonical_measurement_context.client_id'], ondelete='RESTRICT'))
    op.create_table('canonical_measurement_binding',
        sa.Column('binding_id', sa.String(64), primary_key=True),
        sa.Column('client_id', sa.String(64), nullable=False),
        sa.Column('run_id', sa.String(64), sa.ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('context_id', sa.String(64), nullable=False),
        sa.Column('parent_binding_id', sa.String(64)),
        sa.Column('owner_key', sa.String(255), nullable=False),
        sa.Column('owner_digest', sa.String(64), nullable=False),
        sa.Column('document', sa.Text(), nullable=False),
        sa.UniqueConstraint('binding_id', 'client_id', name='uq_measurement_binding_client'),
        sa.UniqueConstraint('client_id','owner_key','owner_digest', name='uq_measurement_owner_snapshot'),
        sa.ForeignKeyConstraint(['context_id','client_id'], ['canonical_measurement_context.context_id','canonical_measurement_context.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['parent_binding_id','client_id'], ['canonical_measurement_binding.binding_id','canonical_measurement_binding.client_id'], ondelete='RESTRICT'))
    op.create_table('canonical_measurement_audit',
        sa.Column('event_id', sa.String(64), primary_key=True),
        sa.Column('client_id', sa.String(64), nullable=False),
        sa.Column('context_id', sa.String(64), nullable=False),
        sa.Column('binding_id', sa.String(64)),
        sa.Column('created_at', sa.String(40), nullable=False),
        sa.Column('document', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['context_id','client_id'], ['canonical_measurement_context.context_id','canonical_measurement_context.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['binding_id','client_id'], ['canonical_measurement_binding.binding_id','canonical_measurement_binding.client_id'], ondelete='RESTRICT'))


def downgrade():
    op.drop_table('canonical_measurement_audit')
    op.drop_table('canonical_measurement_binding')
    op.drop_table('canonical_measurement_context')
