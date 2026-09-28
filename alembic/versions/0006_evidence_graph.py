"""Governed evidence-link assessment snapshots; no legacy conversion."""
from alembic import op
import sqlalchemy as sa

revision = '0006_evidence_graph'
down_revision = '0005_canonical_facts_findings'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('evidence_graph_record',
        sa.Column('link_id', sa.String(64), sa.ForeignKey('evidence_link_v243.link_id', ondelete='RESTRICT'), primary_key=True),
        sa.Column('revision', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.String(64), nullable=False),
        sa.Column('run_id', sa.String(64), sa.ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('source_id', sa.String(64), nullable=False),
        sa.Column('target_id', sa.String(64), nullable=False),
        sa.Column('document', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['source_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['target_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'))


def downgrade():
    # Foundation links/audits survive; restore governance records before replay.
    op.drop_table('evidence_graph_record')
