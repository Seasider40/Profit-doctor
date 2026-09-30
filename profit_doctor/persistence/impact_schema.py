"""Impact qualifications and typed extensions; existing effect/audit authority reused."""
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, String, Table, Text, UniqueConstraint
from .models import Base

qualification = Table('canonical_impact_qualification', Base.metadata,
    Column('candidate_id', String(64), primary_key=True), Column('revision', Integer, primary_key=True),
    Column('client_id', String(64), ForeignKey('client.client_id', ondelete='RESTRICT'), nullable=False),
    Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
    Column('bridge_id', String(64)), Column('source_object_id', String(64)),
    Column('document', Text, nullable=False),
    UniqueConstraint('candidate_id', 'revision', 'client_id', name='uq_impact_qualification_client'),
    ForeignKeyConstraint(['bridge_id', 'client_id'], ['canonical_bridge_snapshot.snapshot_id', 'canonical_bridge_snapshot.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['source_object_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'))

impact = Table('canonical_impact', Base.metadata,
    Column('impact_id', String(64), primary_key=True), Column('client_id', String(64), nullable=False),
    Column('candidate_id', String(64), nullable=False), Column('revision', Integer, nullable=False),
    Column('effect_id', String(64), nullable=False), Column('document', Text, nullable=False),
    ForeignKeyConstraint(['impact_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['candidate_id', 'revision', 'client_id'], ['canonical_impact_qualification.candidate_id', 'canonical_impact_qualification.revision', 'canonical_impact_qualification.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['effect_id', 'client_id'], ['economic_effect_v243.effect_id', 'economic_effect_v243.client_id'], ondelete='RESTRICT'),
    UniqueConstraint('candidate_id', 'revision', name='uq_impact_qualification_result'))

audit = Table('canonical_impact_qualification_audit', Base.metadata,
    Column('event_id', String(64), primary_key=True), Column('candidate_id', String(64), nullable=False),
    Column('revision', Integer, nullable=False), Column('client_id', String(64), nullable=False),
    Column('created_at', String(40), nullable=False), Column('document', Text, nullable=False),
    ForeignKeyConstraint(['candidate_id', 'revision', 'client_id'], ['canonical_impact_qualification.candidate_id', 'canonical_impact_qualification.revision', 'canonical_impact_qualification.client_id'], ondelete='RESTRICT'))
