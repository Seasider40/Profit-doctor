"""Separate monthly measurements and receivables absence; no temporal activation."""
from alembic import op
from sqlalchemy import (Column, ForeignKeyConstraint, Integer, String, Text,
                        UniqueConstraint, CheckConstraint)

revision = '0017_production_evidence'
down_revision = '0016_temporal_evidence'
branch_labels = None
depends_on = None


def upgrade():
    for name,key,prefix,context in (
            ('canonical_monthly_measurement','measurement_id','monthly',True),
            ('canonical_receivables_absence','assessment_id','ar_absence',False)):
        parts = [Column(key,String(64),primary_key=True),Column('series_id',String(64),nullable=False),
            Column('client_id',String(64),nullable=False),Column('run_id',String(64),nullable=False),
            Column('revision',Integer,nullable=False),Column('supersedes',String(64)),Column('document',Text,nullable=False),
            UniqueConstraint(key,'client_id',name='uq_'+prefix+'_client'),
            UniqueConstraint('client_id','series_id','revision',name='uq_'+prefix+'_revision'),
            ForeignKeyConstraint(['client_id'],['client.client_id'],ondelete='RESTRICT'),
            ForeignKeyConstraint(['run_id'],['engine_run.run_id'],ondelete='RESTRICT'),
            ForeignKeyConstraint(['supersedes','client_id'],[name+'.'+key,name+'.client_id'],ondelete='RESTRICT')]
        if context:
            parts += [Column('context_id',String(64),nullable=False),
                ForeignKeyConstraint(['context_id','client_id'],
                    ['canonical_measurement_context.context_id','canonical_measurement_context.client_id'],ondelete='RESTRICT')]
        op.create_table(name,*parts)
    op.create_table('canonical_production_evidence_audit',
        Column('event_id',String(64),primary_key=True),Column('client_id',String(64),nullable=False),
        Column('measurement_id',String(64)),Column('assessment_id',String(64)),
        Column('created_at',String(40),nullable=False),Column('document',Text,nullable=False),
        CheckConstraint('(measurement_id IS NULL) <> (assessment_id IS NULL)',name='ck_production_audit_owner'),
        ForeignKeyConstraint(['measurement_id','client_id'],['canonical_monthly_measurement.measurement_id','canonical_monthly_measurement.client_id'],ondelete='RESTRICT'),
        ForeignKeyConstraint(['assessment_id','client_id'],['canonical_receivables_absence.assessment_id','canonical_receivables_absence.client_id'],ondelete='RESTRICT'))


def downgrade():
    # Monthly contexts/bindings are owned by this extension; legacy CMC rows stay.
    op.execute("DELETE FROM canonical_measurement_audit WHERE context_id IN (SELECT context_id FROM canonical_monthly_measurement)")
    op.execute("DELETE FROM canonical_measurement_binding WHERE context_id IN (SELECT context_id FROM canonical_monthly_measurement)")
    op.drop_table('canonical_production_evidence_audit')
    # Remove values before contexts, then children-first context revisions.
    bind = op.get_bind()
    from sqlalchemy import text
    ids = list(bind.execute(text('SELECT context_id FROM canonical_monthly_measurement ORDER BY revision DESC')).scalars())
    op.drop_table('canonical_monthly_measurement')
    for context_id in ids:
        bind.execute(text('DELETE FROM canonical_measurement_context WHERE context_id=:id'),{'id':context_id})
    op.drop_table('canonical_receivables_absence')
