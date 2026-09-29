"""Canonical Story extension of foundation identity; append-only semantic history."""
from sqlalchemy import Column, ForeignKeyConstraint, Integer, String, Table, Text
from .models import Base

story = Table('canonical_story', Base.metadata,
    Column('object_id', String(64), primary_key=True),
    Column('client_id', String(64), nullable=False),
    Column('finding_id', String(64), nullable=False),
    Column('revision', Integer, nullable=False),
    Column('document', Text, nullable=False),
    ForeignKeyConstraint(['object_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['finding_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'))

story_revision = Table('canonical_story_revision', Base.metadata,
    Column('object_id', String(64), primary_key=True),
    Column('revision', Integer, primary_key=True),
    Column('client_id', String(64), nullable=False),
    Column('document', Text, nullable=False),
    ForeignKeyConstraint(['object_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'))
