"""Canonical condition Story state/history; no legacy conversion."""
from alembic import op
import sqlalchemy as sa

revision = '0008_economic_story'
down_revision = '0007_hypothesis_interpretation'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('canonical_story',
        sa.Column('object_id', sa.String(64), primary_key=True),
        sa.Column('client_id', sa.String(64), nullable=False),
        sa.Column('finding_id', sa.String(64), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('document', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['object_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['finding_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'))
    op.create_table('canonical_story_revision',
        sa.Column('object_id', sa.String(64), primary_key=True),
        sa.Column('revision', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.String(64), nullable=False),
        sa.Column('document', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['object_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'))


def downgrade():
    # Foundation identities, links and audits survive; restore typed history before replay.
    op.drop_table('canonical_story_revision')
    op.drop_table('canonical_story')
