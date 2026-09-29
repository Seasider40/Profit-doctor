"""Context contains semantics only; bindings reference existing value owners."""
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, String, Table, Text, UniqueConstraint
from .models import Base

measurement_context = Table('canonical_measurement_context', Base.metadata,
    Column('context_id', String(64), primary_key=True),
    Column('client_id', String(64), ForeignKey('client.client_id', ondelete='RESTRICT'), nullable=False),
    Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
    Column('supersedes', String(64)),
    Column('document', Text, nullable=False),
    UniqueConstraint('context_id', 'client_id', name='uq_measurement_context_client'),
    ForeignKeyConstraint(['supersedes', 'client_id'], ['canonical_measurement_context.context_id', 'canonical_measurement_context.client_id'], ondelete='RESTRICT'))

measurement_binding = Table('canonical_measurement_binding', Base.metadata,
    Column('binding_id', String(64), primary_key=True),
    Column('client_id', String(64), nullable=False),
    Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
    Column('context_id', String(64), nullable=False),
    Column('parent_binding_id', String(64)),
    Column('owner_key', String(255), nullable=False),
    Column('owner_digest', String(64), nullable=False),
    Column('document', Text, nullable=False),
    UniqueConstraint('binding_id', 'client_id', name='uq_measurement_binding_client'),
    UniqueConstraint('client_id', 'owner_key', 'owner_digest', name='uq_measurement_owner_snapshot'),
    ForeignKeyConstraint(['context_id', 'client_id'], ['canonical_measurement_context.context_id', 'canonical_measurement_context.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['parent_binding_id', 'client_id'], ['canonical_measurement_binding.binding_id', 'canonical_measurement_binding.client_id'], ondelete='RESTRICT'))

# Reuses foundation Actor and AuditEventType serialization. A context is not a
# reasoning object; do not manufacture a FACT identity just to give it an audit.
measurement_audit = Table('canonical_measurement_audit', Base.metadata,
    Column('event_id', String(64), primary_key=True),
    Column('client_id', String(64), nullable=False),
    Column('context_id', String(64), nullable=False),
    Column('binding_id', String(64)),
    Column('created_at', String(40), nullable=False),
    Column('document', Text, nullable=False),
    ForeignKeyConstraint(['context_id', 'client_id'], ['canonical_measurement_context.context_id', 'canonical_measurement_context.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['binding_id', 'client_id'], ['canonical_measurement_binding.binding_id', 'canonical_measurement_binding.client_id'], ondelete='RESTRICT'))
