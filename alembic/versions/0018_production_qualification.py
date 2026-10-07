"""Authenticated Revenue component binding and exact monthly C0 margin ownership."""
from alembic import op
from sqlalchemy import Column, String, Integer, Text, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, text

revision = '0018_production_qualification'
down_revision = '0017_production_evidence'
branch_labels = None
depends_on = None


def upgrade():
    for name, key, prefix in (('canonical_c0_component_binding', 'binding_id', 'c0_component'),
                              ('canonical_monthly_c0_margin', 'margin_id', 'c0_margin')):
        parts = [Column(key, String(64), primary_key=True), Column('series_id', String(64), nullable=False),
            Column('client_id', String(64), nullable=False), Column('run_id', String(64), nullable=False),
            Column('revision', Integer, nullable=False), Column('supersedes', String(64)), Column('document', Text, nullable=False),
            UniqueConstraint(key, 'client_id', name='uq_'+prefix+'_client'),
            UniqueConstraint('client_id', 'series_id', 'revision', name='uq_'+prefix+'_revision'),
            ForeignKeyConstraint(['client_id'], ['client.client_id'], ondelete='RESTRICT'),
            ForeignKeyConstraint(['run_id'], ['engine_run.run_id'], ondelete='RESTRICT'),
            ForeignKeyConstraint(['supersedes', 'client_id'], [name+'.'+key, name+'.client_id'], ondelete='RESTRICT')]
        for component in ('revenue_owner_id', 'contribution_owner_id'):
            parts += [Column(component, String(64), nullable=False), ForeignKeyConstraint([component, 'client_id'],
                ['canonical_monthly_measurement.measurement_id', 'canonical_monthly_measurement.client_id'], ondelete='RESTRICT')]
        if key == 'margin_id':
            parts += [Column('binding_id', String(64), nullable=False), Column('context_id', String(64)),
                ForeignKeyConstraint(['binding_id', 'client_id'], ['canonical_c0_component_binding.binding_id', 'canonical_c0_component_binding.client_id'], ondelete='RESTRICT'),
                ForeignKeyConstraint(['context_id', 'client_id'], ['canonical_measurement_context.context_id', 'canonical_measurement_context.client_id'], ondelete='RESTRICT')]
        op.create_table(name, *parts)
    op.create_table('canonical_production_qualification_audit',
        Column('event_id', String(64), primary_key=True), Column('client_id', String(64), nullable=False),
        Column('binding_id', String(64)), Column('margin_id', String(64)),
        Column('created_at', String(40), nullable=False), Column('document', Text, nullable=False),
        CheckConstraint('(binding_id IS NULL) <> (margin_id IS NULL)', name='ck_production_qualification_audit_owner'),
        ForeignKeyConstraint(['binding_id', 'client_id'], ['canonical_c0_component_binding.binding_id', 'canonical_c0_component_binding.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['margin_id', 'client_id'], ['canonical_monthly_c0_margin.margin_id', 'canonical_monthly_c0_margin.client_id'], ondelete='RESTRICT'))


def downgrade():
    bind = op.get_bind()
    ids = list(bind.execute(text('SELECT context_id FROM canonical_monthly_c0_margin WHERE context_id IS NOT NULL ORDER BY revision DESC')).scalars())
    op.execute('DELETE FROM canonical_measurement_audit WHERE context_id IN (SELECT context_id FROM canonical_monthly_c0_margin)')
    op.execute('DELETE FROM canonical_measurement_binding WHERE context_id IN (SELECT context_id FROM canonical_monthly_c0_margin)')
    op.drop_table('canonical_production_qualification_audit')
    op.drop_table('canonical_monthly_c0_margin')
    for context_id in ids:
        bind.execute(text('DELETE FROM canonical_measurement_context WHERE context_id=:id'), {'id': context_id})
    op.drop_table('canonical_c0_component_binding')
