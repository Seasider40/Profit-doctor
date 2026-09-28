"""Additive SQLAlchemy tables for typed canonical contracts.

Only foundation services write these tables. Legacy writers remain unchanged.
The document is a validated, versioned contract, never arbitrary business state.
No CHECK constraints or changes to legacy model definitions are introduced.
"""
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, String, Table, Text, UniqueConstraint
from .models import Base


def scope_columns():
    return [
        Column('client_id', String(64), ForeignKey('client.client_id', ondelete='RESTRICT'), nullable=False),
        Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT')),
        Column('schema_version', String(32), nullable=False),
        Column('created_at', String(40), nullable=False),
        Column('document', Text, nullable=False),
    ]


reasoning_object = Table(
    'reasoning_object_v243', Base.metadata,
    Column('object_id', String(64), primary_key=True),
    *scope_columns(),
    Column('object_type', String(32), nullable=False),
    Column('source_authority', String(32), nullable=False),
    Column('revision', Integer, nullable=False),
    UniqueConstraint('object_id', 'client_id', name='uq_rd_object_client'),
)
economic_effect = Table(
    'economic_effect_v243', Base.metadata,
    Column('effect_id', String(64), primary_key=True),
    *scope_columns(),
    UniqueConstraint('effect_id', 'client_id', name='uq_rd_effect_client'),
)
evidence_link = Table(
    'evidence_link_v243', Base.metadata,
    Column('link_id', String(64), primary_key=True),
    *scope_columns(),
    Column('source_id', String(64), nullable=False),
    Column('target_id', String(64), nullable=False),
    Column('relationship_type', String(32), nullable=False),
    ForeignKeyConstraint(['source_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['target_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
)
effect_reference = Table(
    'effect_reference_v243', Base.metadata,
    Column('reference_id', String(64), primary_key=True),
    *scope_columns(),
    Column('object_id', String(64), nullable=False),
    Column('effect_id', String(64), nullable=False),
    ForeignKeyConstraint(['object_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['effect_id', 'client_id'], ['economic_effect_v243.effect_id', 'economic_effect_v243.client_id'], ondelete='RESTRICT'),
    UniqueConstraint('object_id', 'effect_id', name='uq_rd_object_effect'),
)
effect_overlap = Table(
    'effect_overlap_v243', Base.metadata,
    Column('overlap_id', String(64), primary_key=True),
    *scope_columns(),
    Column('source_effect_id', String(64), nullable=False),
    Column('target_effect_id', String(64), nullable=False),
    Column('overlap_type', String(32), nullable=False),
    Column('pair_key', String(140), nullable=False),
    ForeignKeyConstraint(['source_effect_id', 'client_id'], ['economic_effect_v243.effect_id', 'economic_effect_v243.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['target_effect_id', 'client_id'], ['economic_effect_v243.effect_id', 'economic_effect_v243.client_id'], ondelete='RESTRICT'),
    UniqueConstraint('client_id', 'pair_key', name='uq_rd_effect_overlap_pair'),
)
audit_event = Table(
    'reasoning_audit_event_v243', Base.metadata,
    Column('event_id', String(64), primary_key=True),
    *scope_columns(),
    Column('object_id', String(64)),
    Column('effect_id', String(64)),
    ForeignKeyConstraint(['effect_id', 'client_id'], ['economic_effect_v243.effect_id', 'economic_effect_v243.client_id'], ondelete='RESTRICT'),
    Column('event_type', String(40), nullable=False),
    ForeignKeyConstraint(['object_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
)
