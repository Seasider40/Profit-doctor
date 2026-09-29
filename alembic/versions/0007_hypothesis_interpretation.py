"""Canonical class-scoped hypotheses and interpretation history; no legacy conversion."""
from alembic import op
import sqlalchemy as sa

revision = '0007_hypothesis_interpretation'
down_revision = '0006_evidence_graph'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('canonical_hypothesis',
        sa.Column('object_id', sa.String(64), primary_key=True),
        sa.Column('client_id', sa.String(64), nullable=False),
        sa.Column('finding_id', sa.String(64), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('document', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['object_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['finding_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'))
    op.create_table('canonical_interpretation_revision',
        sa.Column('object_id', sa.String(64), primary_key=True),
        sa.Column('revision', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.String(64), nullable=False),
        sa.Column('hypothesis_id', sa.String(64), nullable=False),
        sa.Column('document', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['object_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['hypothesis_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'))


def downgrade():
    # Foundation identities, declared links and audits survive; restore payloads before replay.
    op.drop_table('canonical_interpretation_revision')
    op.drop_table('canonical_hypothesis')
