"""production persistence foundation"""
from alembic import op
import sqlalchemy as sa
revision="0001_persistence_foundation"; down_revision=None; branch_labels=None; depends_on=None

def upgrade():
    op.create_table("client",sa.Column("client_id",sa.String(64),primary_key=True),sa.Column("client_name",sa.String(255),nullable=False),sa.Column("base_currency",sa.String(3),nullable=False),sa.Column("business_model",sa.String(64)),sa.Column("created_at",sa.String(40),nullable=False))
    op.create_table("engine_run",sa.Column("run_id",sa.String(64),primary_key=True),sa.Column("client_id",sa.String(64),sa.ForeignKey("client.client_id",ondelete="RESTRICT"),nullable=False),sa.Column("run_type",sa.String(32),nullable=False),sa.Column("started_at",sa.String(40),nullable=False),sa.Column("completed_at",sa.String(40)),sa.Column("status",sa.String(32),nullable=False),sa.Column("previous_run_id",sa.String(64)),sa.Column("baseline_run_id",sa.String(64)),sa.Column("engine_version",sa.String(32),nullable=False)); op.create_index("ix_engine_run_client_id","engine_run",["client_id"])
    op.create_table("opportunity_relationship_v2",sa.Column("relationship_id",sa.String(64),primary_key=True),sa.Column("client_id",sa.String(64),sa.ForeignKey("client.client_id",ondelete="RESTRICT"),nullable=False),sa.Column("run_id",sa.String(64),sa.ForeignKey("engine_run.run_id",ondelete="RESTRICT"),nullable=False),sa.Column("from_opportunity_id",sa.String(64),nullable=False),sa.Column("to_opportunity_id",sa.String(64),nullable=False),sa.Column("pair_key",sa.String(140),nullable=False),sa.Column("relationship_type",sa.String(32),nullable=False),sa.Column("overlap_amount",sa.String(80)),sa.Column("evidence_basis",sa.Text(),nullable=False),sa.UniqueConstraint("client_id","run_id","pair_key","relationship_type",name="uq_opportunity_relationship_pair")); op.create_index("ix_opportunity_relationship_v2_client_id","opportunity_relationship_v2",["client_id"]); op.create_index("ix_opportunity_relationship_v2_run_id","opportunity_relationship_v2",["run_id"])
def downgrade():
    op.drop_table("opportunity_relationship_v2"); op.drop_table("engine_run"); op.drop_table("client")
