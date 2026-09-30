"""Outstanding-balance snapshot owners; no legacy ledger conversion."""
from alembic import op
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint
revision = '0012_receivables_snapshot'
down_revision = '0011_economic_impact'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('canonical_receivables_snapshot',
        Column('snapshot_id', String(64), primary_key=True),
        Column('client_id', String(64), ForeignKey('client.client_id', ondelete='RESTRICT'), nullable=False),
        Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
        Column('series_id', String(64), nullable=False), Column('revision', Integer, nullable=False),
        Column('previous_id', String(64)), Column('document', Text, nullable=False),
        UniqueConstraint('snapshot_id', 'client_id', name='uq_ar_snapshot_client'),
        UniqueConstraint('client_id', 'series_id', 'revision', name='uq_ar_series_revision'),
        ForeignKeyConstraint(['previous_id', 'client_id'], ['canonical_receivables_snapshot.snapshot_id', 'canonical_receivables_snapshot.client_id'], ondelete='RESTRICT'))

    op.create_table('canonical_receivable_invoice',
        Column('owner_id', String(64), primary_key=True), Column('snapshot_id', String(64), nullable=False),
        Column('client_id', String(64), nullable=False), Column('document', Text, nullable=False),
        ForeignKeyConstraint(['snapshot_id', 'client_id'], ['canonical_receivables_snapshot.snapshot_id', 'canonical_receivables_snapshot.client_id'], ondelete='RESTRICT'))

    op.create_table('canonical_receivables_audit',
        Column('event_id', String(64), primary_key=True), Column('snapshot_id', String(64), nullable=False),
        Column('client_id', String(64), nullable=False), Column('created_at', String(40), nullable=False),
        Column('document', Text, nullable=False),
        ForeignKeyConstraint(['snapshot_id', 'client_id'], ['canonical_receivables_snapshot.snapshot_id', 'canonical_receivables_snapshot.client_id'], ondelete='RESTRICT'))

    op.create_table('canonical_receivables_impact_source',
        Column('candidate_id', String(64), primary_key=True), Column('revision', Integer, primary_key=True),
        Column('snapshot_id', String(64), nullable=False), Column('client_id', String(64), nullable=False),
        ForeignKeyConstraint(['snapshot_id', 'client_id'], ['canonical_receivables_snapshot.snapshot_id', 'canonical_receivables_snapshot.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['candidate_id', 'revision', 'client_id'], ['canonical_impact_qualification.candidate_id', 'canonical_impact_qualification.revision', 'canonical_impact_qualification.client_id'], ondelete='RESTRICT'))


def downgrade():
    import sqlalchemy as sa
    connection = op.get_bind()
    keys = connection.execute(sa.text('SELECT candidate_id, revision FROM canonical_receivables_impact_source')).all()
    op.drop_table('canonical_receivables_impact_source')
    for candidate, revision in keys:
        for table in ('canonical_impact', 'canonical_impact_qualification_audit', 'canonical_impact_qualification'):
            connection.execute(sa.text('DELETE FROM '+table+' WHERE candidate_id=:c AND revision=:r'), {'c':candidate,'r':revision})
    # CMC remains the context authority. Remove only contexts owned by the
    # invoice snapshot type being rolled back, never unrelated accounting CMC.
    bindings = connection.execute(sa.text('SELECT owner_key, context_id FROM canonical_measurement_binding')).all()
    context_ids = {context for owner,context in bindings if owner.startswith('CANONICAL:canonical_receivable_invoice:')}
    for context in context_ids:
        for table in ('canonical_measurement_audit','canonical_measurement_binding','canonical_measurement_context'):
            connection.execute(sa.text('DELETE FROM '+table+' WHERE context_id=:c'), {'c':context})
    op.drop_table('canonical_receivables_audit')
    op.drop_table('canonical_receivable_invoice')
    op.drop_table('canonical_receivables_snapshot')
