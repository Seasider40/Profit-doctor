"""Governance extension of an existing EvidenceLink; no duplicate graph identity."""
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, String, Table, Text
from .models import Base

graph_record = Table('evidence_graph_record', Base.metadata,
    Column('link_id', String(64), ForeignKey('evidence_link_v243.link_id', ondelete='RESTRICT'), primary_key=True),
    Column('revision', Integer, primary_key=True),
    Column('client_id', String(64), nullable=False),
    Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
    Column('source_id', String(64), nullable=False),
    Column('target_id', String(64), nullable=False),
    Column('document', Text, nullable=False),
    ForeignKeyConstraint(['source_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['target_id', 'client_id'], ['reasoning_object_v243.object_id', 'reasoning_object_v243.client_id'], ondelete='RESTRICT'))
