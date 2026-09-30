"""Immutable economic Bridge snapshots and qualified input references."""
from alembic import op
import sqlalchemy as sa

revision='0010_economic_bridge'
down_revision='0009_measurement_context'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('canonical_bridge_snapshot',
        sa.Column('snapshot_id',sa.String(64),primary_key=True),
        sa.Column('client_id',sa.String(64),sa.ForeignKey('client.client_id',ondelete='RESTRICT'),nullable=False),
        sa.Column('run_id',sa.String(64),sa.ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False),
        sa.Column('series_id',sa.String(64),nullable=False),sa.Column('revision',sa.Integer(),nullable=False),
        sa.Column('prior_id',sa.String(64)),sa.Column('document',sa.Text(),nullable=False),
        sa.UniqueConstraint('snapshot_id','client_id',name='uq_bridge_snapshot_client'),
        sa.UniqueConstraint('client_id','series_id','revision',name='uq_bridge_series_revision'),
        sa.ForeignKeyConstraint(['prior_id','client_id'],['canonical_bridge_snapshot.snapshot_id','canonical_bridge_snapshot.client_id'],ondelete='RESTRICT'))
    op.create_table('canonical_bridge_input',
        sa.Column('snapshot_id',sa.String(64),primary_key=True),sa.Column('binding_id',sa.String(64),primary_key=True),
        sa.Column('client_id',sa.String(64),nullable=False),sa.Column('role',sa.String(32),nullable=False),
        sa.ForeignKeyConstraint(['snapshot_id','client_id'],['canonical_bridge_snapshot.snapshot_id','canonical_bridge_snapshot.client_id'],ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['binding_id','client_id'],['canonical_measurement_binding.binding_id','canonical_measurement_binding.client_id'],ondelete='RESTRICT'))
    op.create_table('canonical_bridge_audit',
        sa.Column('event_id',sa.String(64),primary_key=True),sa.Column('snapshot_id',sa.String(64),nullable=False),
        sa.Column('client_id',sa.String(64),nullable=False),sa.Column('created_at',sa.String(40),nullable=False),sa.Column('document',sa.Text(),nullable=False),
        sa.ForeignKeyConstraint(['snapshot_id','client_id'],['canonical_bridge_snapshot.snapshot_id','canonical_bridge_snapshot.client_id'],ondelete='RESTRICT'))


def downgrade():
    op.drop_table('canonical_bridge_audit')
    op.drop_table('canonical_bridge_input')
    op.drop_table('canonical_bridge_snapshot')
