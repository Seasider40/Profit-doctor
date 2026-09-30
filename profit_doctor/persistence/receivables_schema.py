"""Immutable invoice-snapshot value owners and audit; source registry is reused."""
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, String, Table, Text, UniqueConstraint
from .models import Base

snapshot = Table('canonical_receivables_snapshot', Base.metadata,
    Column('snapshot_id', String(64), primary_key=True),
    Column('client_id', String(64), ForeignKey('client.client_id', ondelete='RESTRICT'), nullable=False),
    Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
    Column('series_id', String(64), nullable=False), Column('revision', Integer, nullable=False),
    Column('previous_id', String(64)), Column('document', Text, nullable=False),
    UniqueConstraint('snapshot_id', 'client_id', name='uq_ar_snapshot_client'),
    UniqueConstraint('client_id', 'series_id', 'revision', name='uq_ar_series_revision'),
    ForeignKeyConstraint(['previous_id', 'client_id'], ['canonical_receivables_snapshot.snapshot_id', 'canonical_receivables_snapshot.client_id'], ondelete='RESTRICT'))

invoice = Table('canonical_receivable_invoice', Base.metadata,
    Column('owner_id', String(64), primary_key=True), Column('snapshot_id', String(64), nullable=False),
    Column('client_id', String(64), nullable=False), Column('document', Text, nullable=False),
    ForeignKeyConstraint(['snapshot_id', 'client_id'], ['canonical_receivables_snapshot.snapshot_id', 'canonical_receivables_snapshot.client_id'], ondelete='RESTRICT'))

audit = Table('canonical_receivables_audit', Base.metadata,
    Column('event_id', String(64), primary_key=True), Column('snapshot_id', String(64), nullable=False),
    Column('client_id', String(64), nullable=False), Column('created_at', String(40), nullable=False),
    Column('document', Text, nullable=False),
    ForeignKeyConstraint(['snapshot_id', 'client_id'], ['canonical_receivables_snapshot.snapshot_id', 'canonical_receivables_snapshot.client_id'], ondelete='RESTRICT'))

impact_source = Table('canonical_receivables_impact_source', Base.metadata,
    Column('candidate_id', String(64), primary_key=True), Column('revision', Integer, primary_key=True),
    Column('snapshot_id', String(64), nullable=False), Column('client_id', String(64), nullable=False),
    ForeignKeyConstraint(['snapshot_id', 'client_id'], ['canonical_receivables_snapshot.snapshot_id', 'canonical_receivables_snapshot.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['candidate_id', 'revision', 'client_id'], ['canonical_impact_qualification.candidate_id', 'canonical_impact_qualification.revision', 'canonical_impact_qualification.client_id'], ondelete='RESTRICT'))
