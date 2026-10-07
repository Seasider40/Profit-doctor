"""Separate monthly value/AR absence ownership, immutable snapshots and audit."""
from sqlalchemy import (Column, ForeignKey, ForeignKeyConstraint, Integer, String,
                        Table, Text, UniqueConstraint, CheckConstraint)
from .models import Base


def owner_table(name, key, prefix, context=False):
    columns = [Column(key,String(64),primary_key=True),Column('series_id',String(64),nullable=False),
        Column('client_id',String(64),ForeignKey('client.client_id',ondelete='RESTRICT'),nullable=False),
        Column('run_id',String(64),ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False),
        Column('revision',Integer,nullable=False),Column('supersedes',String(64)),
        Column('document',Text,nullable=False),
        UniqueConstraint(key,'client_id',name='uq_'+prefix+'_client'),
        UniqueConstraint('client_id','series_id','revision',name='uq_'+prefix+'_revision'),
        ForeignKeyConstraint(['supersedes','client_id'],[name+'.'+key,name+'.client_id'],ondelete='RESTRICT')]
    if context:
        columns += [Column('context_id',String(64),nullable=False),
            ForeignKeyConstraint(['context_id','client_id'],
                ['canonical_measurement_context.context_id','canonical_measurement_context.client_id'],ondelete='RESTRICT')]
    return Table(name,Base.metadata,*columns)


monthly = owner_table('canonical_monthly_measurement','measurement_id','monthly',True)
absence = owner_table('canonical_receivables_absence','assessment_id','ar_absence')
audit = Table('canonical_production_evidence_audit',Base.metadata,
    Column('event_id',String(64),primary_key=True),Column('client_id',String(64),nullable=False),
    Column('measurement_id',String(64)),Column('assessment_id',String(64)),
    Column('created_at',String(40),nullable=False),Column('document',Text,nullable=False),
    CheckConstraint('(measurement_id IS NULL) <> (assessment_id IS NULL)',name='ck_production_audit_owner'),
    ForeignKeyConstraint(['measurement_id','client_id'],['canonical_monthly_measurement.measurement_id','canonical_monthly_measurement.client_id'],ondelete='RESTRICT'),
    ForeignKeyConstraint(['assessment_id','client_id'],['canonical_receivables_absence.assessment_id','canonical_receivables_absence.client_id'],ondelete='RESTRICT'))
