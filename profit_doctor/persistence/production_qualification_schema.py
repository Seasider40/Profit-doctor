"""Owned component bindings and exact margin qualification histories."""
from sqlalchemy import Column, String, Text, ForeignKeyConstraint, CheckConstraint, Table
from .models import Base
from .production_evidence_schema import owner_table


binding = owner_table('canonical_c0_component_binding', 'binding_id', 'c0_component')
margin = owner_table('canonical_monthly_c0_margin', 'margin_id', 'c0_margin')
for table in (binding, margin):
    for key in ('revenue_owner_id', 'contribution_owner_id'):
        table.append_column(Column(key, String(64), nullable=False))
        table.append_constraint(ForeignKeyConstraint([key, 'client_id'],
            ['canonical_monthly_measurement.measurement_id', 'canonical_monthly_measurement.client_id'], ondelete='RESTRICT'))
margin.append_column(Column('binding_id', String(64), nullable=False))
margin.append_constraint(ForeignKeyConstraint(['binding_id', 'client_id'],
    ['canonical_c0_component_binding.binding_id', 'canonical_c0_component_binding.client_id'], ondelete='RESTRICT'))
margin.append_column(Column('context_id', String(64)))
margin.append_constraint(ForeignKeyConstraint(['context_id', 'client_id'],
    ['canonical_measurement_context.context_id', 'canonical_measurement_context.client_id'], ondelete='RESTRICT'))
audit = Table('canonical_production_qualification_audit', Base.metadata,
    Column('event_id', String(64), primary_key=True), Column('client_id', String(64), nullable=False),
    Column('binding_id', String(64)), Column('margin_id', String(64)),
    Column('created_at', String(40), nullable=False), Column('document', Text, nullable=False),
    CheckConstraint('(binding_id IS NULL) <> (margin_id IS NULL)', name='ck_production_qualification_audit_owner'),
    ForeignKeyConstraint(['binding_id', 'client_id'], ['canonical_c0_component_binding.binding_id', 'canonical_c0_component_binding.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['margin_id', 'client_id'], ['canonical_monthly_c0_margin.margin_id', 'canonical_monthly_c0_margin.client_id'], ondelete='RESTRICT'))
