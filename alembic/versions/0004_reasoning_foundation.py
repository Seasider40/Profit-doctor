"""Add canonical reasoning foundation without converting legacy data."""
from alembic import op
import sqlalchemy as sa

revision = '0004_reasoning_foundation'
down_revision = '0003_rev_gm_diagnostics'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('economic_effect_v243',
        sa.Column('effect_id', sa.String(length=64), nullable=False, primary_key=True),
        sa.Column('client_id', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('run_id', sa.String(length=64), nullable=True, primary_key=False),
        sa.Column('schema_version', sa.String(length=32), nullable=False, primary_key=False),
        sa.Column('created_at', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('document', sa.Text(), nullable=False, primary_key=False),
        sa.ForeignKeyConstraint(['client_id'], ['client.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['run_id'], ['engine_run.run_id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('effect_id', 'client_id', name='uq_rd_effect_client'),
    )
    op.create_table('reasoning_object_v243',
        sa.Column('object_id', sa.String(length=64), nullable=False, primary_key=True),
        sa.Column('client_id', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('run_id', sa.String(length=64), nullable=True, primary_key=False),
        sa.Column('schema_version', sa.String(length=32), nullable=False, primary_key=False),
        sa.Column('created_at', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('document', sa.Text(), nullable=False, primary_key=False),
        sa.Column('object_type', sa.String(length=32), nullable=False, primary_key=False),
        sa.Column('source_authority', sa.String(length=32), nullable=False, primary_key=False),
        sa.Column('revision', sa.Integer(), nullable=False, primary_key=False),
        sa.ForeignKeyConstraint(['client_id'], ['client.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['run_id'], ['engine_run.run_id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('object_id', 'client_id', name='uq_rd_object_client'),
    )
    op.create_table('effect_overlap_v243',
        sa.Column('overlap_id', sa.String(length=64), nullable=False, primary_key=True),
        sa.Column('client_id', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('run_id', sa.String(length=64), nullable=True, primary_key=False),
        sa.Column('schema_version', sa.String(length=32), nullable=False, primary_key=False),
        sa.Column('created_at', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('document', sa.Text(), nullable=False, primary_key=False),
        sa.Column('source_effect_id', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('target_effect_id', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('overlap_type', sa.String(length=32), nullable=False, primary_key=False),
        sa.Column('pair_key', sa.String(length=140), nullable=False, primary_key=False),
        sa.ForeignKeyConstraint(['client_id'], ['client.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['run_id'], ['engine_run.run_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['source_effect_id', 'client_id'], ['economic_effect_v243.effect_id', 'economic_effect_v243.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['target_effect_id', 'client_id'], ['economic_effect_v243.effect_id', 'economic_effect_v243.client_id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('client_id', 'pair_key', name='uq_rd_effect_overlap_pair'),
    )
    op.create_table('effect_reference_v243',
        sa.Column('reference_id', sa.String(length=64), nullable=False, primary_key=True),
        sa.Column('client_id', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('run_id', sa.String(length=64), nullable=True, primary_key=False),
        sa.Column('schema_version', sa.String(length=32), nullable=False, primary_key=False),
        sa.Column('created_at', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('document', sa.Text(), nullable=False, primary_key=False),
        sa.Column('object_id', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('effect_id', sa.String(length=64), nullable=False, primary_key=False),
        sa.ForeignKeyConstraint(['client_id'], ['client.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['effect_id', 'client_id'], ['economic_effect_v243.effect_id', 'economic_effect_v243.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['object_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['run_id'], ['engine_run.run_id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('object_id', 'effect_id', name='uq_rd_object_effect'),
    )
    op.create_table('evidence_link_v243',
        sa.Column('link_id', sa.String(length=64), nullable=False, primary_key=True),
        sa.Column('client_id', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('run_id', sa.String(length=64), nullable=True, primary_key=False),
        sa.Column('schema_version', sa.String(length=32), nullable=False, primary_key=False),
        sa.Column('created_at', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('document', sa.Text(), nullable=False, primary_key=False),
        sa.Column('source_id', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('target_id', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('relationship_type', sa.String(length=32), nullable=False, primary_key=False),
        sa.ForeignKeyConstraint(['client_id'], ['client.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['run_id'], ['engine_run.run_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['source_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['target_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
    )
    op.create_table('reasoning_audit_event_v243',
        sa.Column('event_id', sa.String(length=64), nullable=False, primary_key=True),
        sa.Column('client_id', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('run_id', sa.String(length=64), nullable=True, primary_key=False),
        sa.Column('schema_version', sa.String(length=32), nullable=False, primary_key=False),
        sa.Column('created_at', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('document', sa.Text(), nullable=False, primary_key=False),
        sa.Column('object_id', sa.String(length=64), nullable=True, primary_key=False),
        sa.Column('effect_id', sa.String(length=64), nullable=True, primary_key=False),
        sa.Column('event_type', sa.String(length=40), nullable=False, primary_key=False),
        sa.ForeignKeyConstraint(['client_id'], ['client.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['effect_id', 'client_id'], ['economic_effect_v243.effect_id', 'economic_effect_v243.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['object_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['run_id'], ['engine_run.run_id'], ondelete='RESTRICT'),
    )


def downgrade():
    op.drop_table('reasoning_audit_event_v243')
    op.drop_table('evidence_link_v243')
    op.drop_table('effect_reference_v243')
    op.drop_table('effect_overlap_v243')
    op.drop_table('reasoning_object_v243')
    op.drop_table('economic_effect_v243')
