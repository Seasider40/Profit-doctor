"""Typed collection evidence and canonical Opportunity extensions."""
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint
from sqlalchemy import Table
from .models import Base


def _register():
    def create(name, *columns): return Table(name, Base.metadata, *columns)
    create('canonical_collection_evidence',
        Column('evidence_id', String(64), primary_key=True), Column('client_id', String(64), nullable=False),
        Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
        Column('impact_id', String(64), ForeignKey('canonical_impact.impact_id', ondelete='RESTRICT'), nullable=False),
        Column('document', Text, nullable=False),
        UniqueConstraint('evidence_id', 'client_id', name='uq_collection_evidence_client'),
        ForeignKeyConstraint(['impact_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'))
    create('canonical_opportunity_candidate',
        Column('candidate_id', String(64), primary_key=True), Column('client_id', String(64), nullable=False),
        Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
        Column('impact_id', String(64), ForeignKey('canonical_impact.impact_id', ondelete='RESTRICT'), nullable=False),
        Column('effect_id', String(64), nullable=False), Column('document', Text, nullable=False),
        UniqueConstraint('candidate_id','client_id', name='uq_opportunity_candidate_client'),
        ForeignKeyConstraint(['candidate_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['impact_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['effect_id','client_id'], ['economic_effect_v243.effect_id','economic_effect_v243.client_id'], ondelete='RESTRICT'))
    create('canonical_opportunity_assessment',
        Column('candidate_id', String(64), primary_key=True), Column('revision', Integer, primary_key=True),
        Column('client_id', String(64), nullable=False), Column('evidence_id', String(64)), Column('document', Text, nullable=False),
        UniqueConstraint('candidate_id','revision','client_id', name='uq_opportunity_assessment_client'),
        ForeignKeyConstraint(['candidate_id','client_id'], ['canonical_opportunity_candidate.candidate_id','canonical_opportunity_candidate.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['evidence_id','client_id'], ['canonical_collection_evidence.evidence_id','canonical_collection_evidence.client_id'], ondelete='RESTRICT'))
    create('canonical_opportunity',
        Column('opportunity_id', String(64), primary_key=True), Column('client_id', String(64), nullable=False),
        Column('candidate_id', String(64), nullable=False), Column('revision', Integer, nullable=False),
        Column('document', Text, nullable=False),
        UniqueConstraint('candidate_id','revision', name='uq_opportunity_assessment_result'),
        ForeignKeyConstraint(['opportunity_id','client_id'], ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['candidate_id','revision','client_id'], ['canonical_opportunity_assessment.candidate_id','canonical_opportunity_assessment.revision','canonical_opportunity_assessment.client_id'], ondelete='RESTRICT'))
    create('canonical_opportunity_audit',
        Column('event_id', String(64), primary_key=True), Column('candidate_id', String(64), nullable=False),
        Column('client_id', String(64), nullable=False), Column('created_at', String(40), nullable=False),
        Column('document', Text, nullable=False),
        ForeignKeyConstraint(['candidate_id','client_id'], ['canonical_opportunity_candidate.candidate_id','canonical_opportunity_candidate.client_id'], ondelete='RESTRICT'))

_register()
evidence = Base.metadata.tables['canonical_collection_evidence']
candidate = Base.metadata.tables['canonical_opportunity_candidate']
assessment = Base.metadata.tables['canonical_opportunity_assessment']
opportunity = Base.metadata.tables['canonical_opportunity']
audit = Base.metadata.tables['canonical_opportunity_audit']
