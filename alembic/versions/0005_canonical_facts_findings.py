"""Typed canonical Fact/Finding extensions; no legacy conversion."""
from alembic import op
import sqlalchemy as sa

revision = '0005_canonical_facts_findings'
down_revision = '0004_reasoning_foundation'
branch_labels = None
depends_on = None


def upgrade():
    for name in ('canonical_fact_v244', 'canonical_finding_v244'):
        op.create_table(name,
            sa.Column('object_id', sa.String(64), primary_key=True),
            sa.Column('client_id', sa.String(64), nullable=False),
            sa.Column('revision', sa.Integer(), nullable=False),
            sa.Column('document', sa.Text(), nullable=False),
            sa.ForeignKeyConstraint(['object_id', 'client_id'],
                ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'))
    op.create_table('canonical_semantic_revision_v244',
        sa.Column('revision_id', sa.String(64), primary_key=True),
        sa.Column('object_id', sa.String(64), nullable=False),
        sa.Column('client_id', sa.String(64), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('document', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['object_id', 'client_id'],
            ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('object_id', 'revision', name='uq_canonical_semantic_revision'))


def downgrade():
    # Identity/evidence/audit history belongs to v2.43 and is retained. A downgrade
    # removes semantic payloads, so restore their backup before resuming the writer.
    op.drop_table('canonical_semantic_revision_v244')
    op.drop_table('canonical_finding_v244')
    op.drop_table('canonical_fact_v244')
