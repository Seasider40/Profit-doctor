"""Revenue + Gross Margin diagnostic persistence"""
from alembic import op
import sqlalchemy as sa
from profit_doctor.persistence.models import Base
revision='0003_rev_gm_diagnostics'; down_revision='0002_economic_backbone'; branch_labels=None; depends_on=None

def upgrade():
    bind=op.get_bind()
    Base.metadata.tables['test_execution_v2'].create(bind,checkfirst=True)
    # signal_v2 existed in v2.9 with a deliberately narrow backbone shape.
    existing={c['name'] for c in sa.inspect(bind).get_columns('signal_v2')}
    cols=[
      sa.Column('test_execution_id',sa.String(64),nullable=True),sa.Column('entity_type',sa.String(64)),sa.Column('entity_id',sa.String(128)),
      sa.Column('period_from',sa.String(40)),sa.Column('period_to',sa.String(40)),sa.Column('comparison_value',sa.String(80)),
      sa.Column('materiality_state',sa.String(32),nullable=False,server_default='INFORMATIONAL'),sa.Column('status',sa.String(32),nullable=False,server_default='ACTIVE'),sa.Column('source_primitive_id',sa.String(64))]
    for c in cols:
      if c.name not in existing: op.add_column('signal_v2',c)
    Base.metadata.tables['diagnostic_lineage_v2'].create(bind,checkfirst=True)

def downgrade():
    op.drop_table('diagnostic_lineage_v2'); op.drop_table('test_execution_v2')
    for n in ['source_primitive_id','status','materiality_state','comparison_value','period_to','period_from','entity_id','entity_type','test_execution_id']:
      try: op.drop_column('signal_v2',n)
      except Exception: pass
