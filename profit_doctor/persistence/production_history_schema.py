"""Production evidence ownership/history; Dataset Contract remains the single store."""
from sqlalchemy import Column, String, Table, Text, ForeignKeyConstraint, CheckConstraint
from .models import Base
from .production_evidence_schema import owner_table


projection = owner_table('canonical_ar_semantic_projection','projection_id','ar_projection')
projection.append_column(Column('contract_id',String(64),nullable=False))
projection.append_column(Column('impact_id',String(64)))
projection.append_column(Column('absence_id',String(64)))
projection.append_constraint(ForeignKeyConstraint(['contract_id','client_id'],
    ['canonical_dataset_contract.contract_id','canonical_dataset_contract.client_id'],ondelete='RESTRICT'))
projection.append_constraint(ForeignKeyConstraint(['impact_id'],['canonical_impact.impact_id'],ondelete='RESTRICT'))
projection.append_constraint(ForeignKeyConstraint(['impact_id','client_id'],
    ['reasoning_object_v243.object_id','reasoning_object_v243.client_id'],ondelete='RESTRICT'))
projection.append_constraint(ForeignKeyConstraint(['absence_id','client_id'],
    ['canonical_receivables_absence.assessment_id','canonical_receivables_absence.client_id'],ondelete='RESTRICT'))
projection.append_constraint(CheckConstraint('(impact_id IS NULL) <> (absence_id IS NULL)',name='ck_ar_projection_owner'))
unknown = owner_table('canonical_production_unknown','unknown_id','production_unknown')
zero = owner_table('canonical_zero_ar_population','zero_id','zero_ar')
zero_absence = Table('canonical_zero_ar_absence_reference',Base.metadata,
    Column('absence_id',String(64),primary_key=True),Column('zero_id',String(64),nullable=False),
    Column('client_id',String(64),nullable=False),
    ForeignKeyConstraint(['absence_id','client_id'],['canonical_receivables_absence.assessment_id','canonical_receivables_absence.client_id'],ondelete='RESTRICT'),
    ForeignKeyConstraint(['zero_id','client_id'],['canonical_zero_ar_population.zero_id','canonical_zero_ar_population.client_id'],ondelete='RESTRICT'))
temporal = owner_table('canonical_production_temporal','assessment_id','production_temporal')
readiness = owner_table('canonical_evidence_readiness','readiness_id','evidence_readiness')


def references(name, parent, parent_key, prefix):
    table = Table(name,Base.metadata,Column(parent_key,String(64),primary_key=True),
        Column('reference_id',String(64),primary_key=True),Column('client_id',String(64),nullable=False),
        ForeignKeyConstraint([parent_key,'client_id'],[parent+'.'+parent_key,parent+'.client_id'],ondelete='RESTRICT'))
    targets=(('monthly_id','canonical_monthly_measurement','measurement_id'),
        ('margin_id','canonical_monthly_c0_margin','margin_id'),
        ('projection_id','canonical_ar_semantic_projection','projection_id'),
        ('unknown_id','canonical_production_unknown','unknown_id'),
        ('zero_id','canonical_zero_ar_population','zero_id'))
    if parent_key=='readiness_id':
        targets += (('absence_id','canonical_receivables_absence','assessment_id'),
            ('temporal_id','canonical_production_temporal','assessment_id'))
    for key,target,pk in targets:
        table.append_column(Column(key,String(64)))
        table.append_constraint(ForeignKeyConstraint([key,'client_id'],[target+'.'+pk,target+'.client_id'],ondelete='RESTRICT'))
    table.append_constraint(CheckConstraint(' + '.join('CASE WHEN '+key+' IS NULL THEN 0 ELSE 1 END' for key,_,_ in targets)+' = 1',
        name='ck_'+prefix+'_one_owner'))
    return table


temporal_reference = references('canonical_production_temporal_reference','canonical_production_temporal','assessment_id','production_temporal_ref')
readiness_reference = references('canonical_evidence_readiness_reference','canonical_evidence_readiness','readiness_id','evidence_readiness_ref')
audit = Table('canonical_production_history_audit',Base.metadata,
    Column('event_id',String(64),primary_key=True),Column('client_id',String(64),nullable=False),
    Column('created_at',String(40),nullable=False),Column('document',Text,nullable=False))
owners=(('projection_id','canonical_ar_semantic_projection'),('unknown_id','canonical_production_unknown'),
    ('zero_id','canonical_zero_ar_population'),('assessment_id','canonical_production_temporal'),
    ('readiness_id','canonical_evidence_readiness'))
for key,target in owners:
    audit.append_column(Column(key,String(64)))
    audit.append_constraint(ForeignKeyConstraint([key,'client_id'],[target+'.'+key,target+'.client_id'],ondelete='RESTRICT'))
audit.append_constraint(CheckConstraint(' + '.join('CASE WHEN '+key+' IS NULL THEN 0 ELSE 1 END' for key,_ in owners)+' = 1',
    name='ck_production_history_audit_one_owner'))
