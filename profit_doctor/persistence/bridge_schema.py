"""Immutable Bridge snapshots, existing binding references and audit trail."""
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, String, Table, Text, UniqueConstraint
from .models import Base

bridge_snapshot = Table('canonical_bridge_snapshot', Base.metadata,
    Column('snapshot_id',String(64),primary_key=True),
    Column('client_id',String(64),ForeignKey('client.client_id',ondelete='RESTRICT'),nullable=False),
    Column('run_id',String(64),ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False),
    Column('series_id',String(64),nullable=False),Column('revision',Integer,nullable=False),
    Column('prior_id',String(64)),Column('document',Text,nullable=False),
    UniqueConstraint('snapshot_id','client_id',name='uq_bridge_snapshot_client'),
    UniqueConstraint('client_id','series_id','revision',name='uq_bridge_series_revision'),
    ForeignKeyConstraint(['prior_id','client_id'],['canonical_bridge_snapshot.snapshot_id','canonical_bridge_snapshot.client_id'],ondelete='RESTRICT'))

bridge_input = Table('canonical_bridge_input',Base.metadata,
    Column('snapshot_id',String(64),primary_key=True),Column('binding_id',String(64),primary_key=True),
    Column('client_id',String(64),nullable=False),Column('role',String(32),nullable=False),
    ForeignKeyConstraint(['snapshot_id','client_id'],['canonical_bridge_snapshot.snapshot_id','canonical_bridge_snapshot.client_id'],ondelete='RESTRICT'),
    ForeignKeyConstraint(['binding_id','client_id'],['canonical_measurement_binding.binding_id','canonical_measurement_binding.client_id'],ondelete='RESTRICT'))

bridge_audit = Table('canonical_bridge_audit',Base.metadata,
    Column('event_id',String(64),primary_key=True),Column('snapshot_id',String(64),nullable=False),
    Column('client_id',String(64),nullable=False),Column('created_at',String(40),nullable=False),Column('document',Text,nullable=False),
    ForeignKeyConstraint(['snapshot_id','client_id'],['canonical_bridge_snapshot.snapshot_id','canonical_bridge_snapshot.client_id'],ondelete='RESTRICT'))
