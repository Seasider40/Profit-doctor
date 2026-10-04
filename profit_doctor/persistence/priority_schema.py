"""Additive canonical assessment and adviser history."""
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint
from sqlalchemy import Table
from .models import Base

def _register():
    def create(name, *columns): return Table(name, Base.metadata, *columns)
    create('canonical_priority_subject',
        Column('subject_id', String(64), primary_key=True), Column('client_id', String(64), nullable=False),
        Column('source_id', String(64), nullable=False), Column('source_kind', String(32), nullable=False),
        UniqueConstraint('subject_id','client_id', name='uq_priority_subject_client'),
        UniqueConstraint('source_id','client_id','source_kind', name='uq_priority_source'),
        ForeignKeyConstraint(['source_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'))
    create('canonical_priority_assessment',
        Column('subject_id', String(64), primary_key=True), Column('revision', Integer, primary_key=True),
        Column('client_id', String(64), nullable=False), Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
        Column('created_at', String(40), nullable=False), Column('document', Text, nullable=False),
        UniqueConstraint('subject_id','revision','client_id', name='uq_priority_assessment_client'),
        ForeignKeyConstraint(['subject_id','client_id'], ['canonical_priority_subject.subject_id','canonical_priority_subject.client_id'], ondelete='RESTRICT'))
    create('canonical_adviser_decision',
        Column('subject_id', String(64), primary_key=True), Column('revision', Integer, primary_key=True),
        Column('client_id', String(64), nullable=False), Column('assessment_revision', Integer, nullable=False),
        Column('request_id', String(64), nullable=False), Column('choice', String(24), nullable=False),
        Column('created_at', String(40), nullable=False), Column('document', Text, nullable=False),
        UniqueConstraint('client_id','request_id', name='uq_adviser_request'),
        ForeignKeyConstraint(['subject_id','assessment_revision','client_id'], ['canonical_priority_assessment.subject_id','canonical_priority_assessment.revision','canonical_priority_assessment.client_id'], ondelete='RESTRICT'))
    create('canonical_priority_audit',
        Column('event_id', String(64), primary_key=True), Column('subject_id', String(64), nullable=False),
        Column('client_id', String(64), nullable=False), Column('created_at', String(40), nullable=False),
        Column('document', Text, nullable=False),
        ForeignKeyConstraint(['subject_id','client_id'], ['canonical_priority_subject.subject_id','canonical_priority_subject.client_id'], ondelete='RESTRICT'))

_register()
subject = Base.metadata.tables['canonical_priority_subject']
assessment = Base.metadata.tables['canonical_priority_assessment']
decision = Base.metadata.tables['canonical_adviser_decision']
audit = Base.metadata.tables['canonical_priority_audit']
