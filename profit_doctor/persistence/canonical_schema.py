"""Typed semantic extensions to v2.43 identities, not a second identity authority."""
from sqlalchemy import Column, ForeignKeyConstraint, Integer, String, Table, Text, UniqueConstraint
from .models import Base


def extension(name):
    return Table(name, Base.metadata,
        Column('object_id', String(64), primary_key=True),
        Column('client_id', String(64), nullable=False),
        Column('revision', Integer, nullable=False),
        Column('document', Text, nullable=False),
        ForeignKeyConstraint(['object_id', 'client_id'],
            ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'))


fact = extension('canonical_fact_v244')
finding = extension('canonical_finding_v244')
history = Table('canonical_semantic_revision_v244', Base.metadata,
    Column('revision_id', String(64), primary_key=True),
    Column('object_id', String(64), nullable=False),
    Column('client_id', String(64), nullable=False),
    Column('revision', Integer, nullable=False),
    Column('document', Text, nullable=False),
    ForeignKeyConstraint(['object_id', 'client_id'],
        ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
    UniqueConstraint('object_id', 'revision', name='uq_canonical_semantic_revision'))
