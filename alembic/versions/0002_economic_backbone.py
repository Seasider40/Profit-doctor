"""economic backbone persistence"""
from alembic import op
from profit_doctor.persistence.models import Base
revision='0002_economic_backbone'; down_revision='0001_persistence_foundation'; branch_labels=None; depends_on=None
TABLES=['primitive_result_v2','signal_v2','finding_v2','economic_story_v2','economic_impact_v2','economic_exposure_v2','opportunity_candidate_v2','opportunity_v2','decision_v2','action_v2','benefit_leg_v2']
def upgrade():
    bind=op.get_bind()
    for name in TABLES: Base.metadata.tables[name].create(bind,checkfirst=True)
def downgrade():
    for name in reversed(TABLES): op.drop_table(name)
