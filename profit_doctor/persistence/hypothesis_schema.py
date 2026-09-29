"""Semantic extensions of existing reasoning identities; caller owns transactions."""
from sqlalchemy import Column, ForeignKeyConstraint, Integer, String, Table, Text
from .models import Base

hypothesis = Table('canonical_hypothesis', Base.metadata,
    Column('object_id', String(64), primary_key=True),
    Column('client_id', String(64), nullable=False),
    Column('finding_id', String(64), nullable=False),
    Column('revision', Integer, nullable=False),
    Column('document', Text, nullable=False),
    ForeignKeyConstraint(['object_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['finding_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'))

interpretation = Table('canonical_interpretation_revision', Base.metadata,
    Column('object_id', String(64), primary_key=True),
    Column('revision', Integer, primary_key=True),
    Column('client_id', String(64), nullable=False),
    Column('hypothesis_id', String(64), nullable=False),
    Column('document', Text, nullable=False),
    ForeignKeyConstraint(['object_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['hypothesis_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'))
