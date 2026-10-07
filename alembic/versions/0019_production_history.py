"""Scoped production histories and explicit raw/AR semantic contract ownership."""
from alembic import op
from sqlalchemy import Column, String, Integer, Text, ForeignKeyConstraint, UniqueConstraint, CheckConstraint

revision = '0019_production_history'
down_revision = '0018_production_qualification'
branch_labels = None
depends_on = None

OWNERS=(('canonical_ar_semantic_projection','projection_id','ar_projection'),
    ('canonical_production_unknown','unknown_id','production_unknown'),
    ('canonical_zero_ar_population','zero_id','zero_ar'),
    ('canonical_production_temporal','assessment_id','production_temporal'),
    ('canonical_evidence_readiness','readiness_id','evidence_readiness'))
TARGETS=(('monthly_id','canonical_monthly_measurement','measurement_id'),
    ('margin_id','canonical_monthly_c0_margin','margin_id'),
    ('projection_id','canonical_ar_semantic_projection','projection_id'),
    ('unknown_id','canonical_production_unknown','unknown_id'),
    ('zero_id','canonical_zero_ar_population','zero_id'))


def fk(keys, target, pks):
    return ForeignKeyConstraint(keys,[target+'.'+key for key in pks],ondelete='RESTRICT')


def upgrade():
    with op.batch_alter_table('canonical_dataset_contract') as batch:
        batch.add_column(Column('contract_role',String(32),nullable=False,server_default='RAW'))
        batch.drop_constraint('uq_dataset_contract_source_revision',type_='unique')
        batch.create_unique_constraint('uq_dataset_contract_source_revision',['client_id','source_version_id','contract_role','revision'])
        batch.create_check_constraint('ck_dataset_contract_role',"contract_role IN ('RAW', 'AR_SEMANTIC_PROJECTION')")
    for name,key,prefix in OWNERS:
        parts=[Column(key,String(64),primary_key=True),Column('series_id',String(64),nullable=False),
            Column('client_id',String(64),nullable=False),Column('run_id',String(64),nullable=False),
            Column('revision',Integer,nullable=False),Column('supersedes',String(64)),Column('document',Text,nullable=False),
            UniqueConstraint(key,'client_id',name='uq_'+prefix+'_client'),
            UniqueConstraint('client_id','series_id','revision',name='uq_'+prefix+'_revision'),
            fk(['client_id'],'client',['client_id']),fk(['run_id'],'engine_run',['run_id']),
            fk(['supersedes','client_id'],name,[key,'client_id'])]
        if key=='projection_id':
            parts += [Column('contract_id',String(64),nullable=False),Column('impact_id',String(64)),Column('absence_id',String(64)),
                fk(['contract_id','client_id'],'canonical_dataset_contract',['contract_id','client_id']),
                fk(['impact_id'],'canonical_impact',['impact_id']),
                fk(['impact_id','client_id'],'reasoning_object_v243',['object_id','client_id']),
                fk(['absence_id','client_id'],'canonical_receivables_absence',['assessment_id','client_id']),
                CheckConstraint('(impact_id IS NULL) <> (absence_id IS NULL)',name='ck_ar_projection_owner')]
        op.create_table(name,*parts)
    op.create_table('canonical_zero_ar_absence_reference',Column('absence_id',String(64),primary_key=True),
        Column('zero_id',String(64),nullable=False),Column('client_id',String(64),nullable=False),
        fk(['absence_id','client_id'],'canonical_receivables_absence',['assessment_id','client_id']),
        fk(['zero_id','client_id'],'canonical_zero_ar_population',['zero_id','client_id']))
    for name,parent,key,prefix in (
            ('canonical_production_temporal_reference','canonical_production_temporal','assessment_id','production_temporal_ref'),
            ('canonical_evidence_readiness_reference','canonical_evidence_readiness','readiness_id','evidence_readiness_ref')):
        parts=[Column(key,String(64),primary_key=True),Column('reference_id',String(64),primary_key=True),
            Column('client_id',String(64),nullable=False),fk([key,'client_id'],parent,[key,'client_id'])]
        targets=TARGETS+((('absence_id','canonical_receivables_absence','assessment_id'),
            ('temporal_id','canonical_production_temporal','assessment_id')) if key=='readiness_id' else ())
        for column,target,pk in targets:
            parts += [Column(column,String(64)),fk([column,'client_id'],target,[pk,'client_id'])]
        parts.append(CheckConstraint(' + '.join('CASE WHEN '+column+' IS NULL THEN 0 ELSE 1 END' for column,_,_ in targets)+' = 1',
            name='ck_'+prefix+'_one_owner'))
        op.create_table(name,*parts)
    parts=[Column('event_id',String(64),primary_key=True),Column('client_id',String(64),nullable=False),
        Column('created_at',String(40),nullable=False),Column('document',Text,nullable=False)]
    for name,key,_ in OWNERS:
        parts += [Column(key,String(64)),fk([key,'client_id'],name,[key,'client_id'])]
    parts.append(CheckConstraint(' + '.join('CASE WHEN '+key+' IS NULL THEN 0 ELSE 1 END' for _,key,_ in OWNERS)+' = 1',
        name='ck_production_history_audit_one_owner'))
    op.create_table('canonical_production_history_audit',*parts)


def downgrade():
    op.drop_table('canonical_production_history_audit')
    op.drop_table('canonical_evidence_readiness_reference')
    op.drop_table('canonical_production_temporal_reference')
    # Empty-population absence became possible only with this release's owned
    # positive zero proof. Retain all pre-existing nonzero-population absences.
    bind=op.get_bind()
    from sqlalchemy import text
    zero_absences=list(bind.execute(text('SELECT absence_id FROM canonical_zero_ar_absence_reference')).scalars())
    zero_descendants=set(zero_absences)
    absence_rows=list(bind.execute(text('SELECT assessment_id,supersedes,revision FROM canonical_receivables_absence')))
    changed=True
    while changed:
        changed=False
        for identifier,predecessor,_ in absence_rows:
            if predecessor in zero_descendants and identifier not in zero_descendants:
                zero_descendants.add(identifier);changed=True
    zero_absences=[identifier for identifier,_,_ in sorted(absence_rows,key=lambda row:row[2],reverse=True)
                   if identifier in zero_descendants]
    op.drop_table('canonical_zero_ar_absence_reference')
    for name,_,_ in reversed(OWNERS):
        op.drop_table(name)
    for identifier in zero_absences:
        bind.execute(text('DELETE FROM canonical_production_evidence_audit WHERE assessment_id=:id'),{'id':identifier})
        bind.execute(text('DELETE FROM canonical_receivables_absence WHERE assessment_id=:id'),{'id':identifier})
    # Remove only this release's semantic views and their existing-store audits/comparisons.
    op.execute("DELETE FROM canonical_dataset_audit WHERE contract_id IN (SELECT contract_id FROM canonical_dataset_contract WHERE contract_role='AR_SEMANTIC_PROJECTION') OR assessment_id IN (SELECT assessment_id FROM canonical_dataset_comparability WHERE left_contract_id IN (SELECT contract_id FROM canonical_dataset_contract WHERE contract_role='AR_SEMANTIC_PROJECTION') OR right_contract_id IN (SELECT contract_id FROM canonical_dataset_contract WHERE contract_role='AR_SEMANTIC_PROJECTION'))")
    op.execute("DELETE FROM canonical_dataset_comparability WHERE left_contract_id IN (SELECT contract_id FROM canonical_dataset_contract WHERE contract_role='AR_SEMANTIC_PROJECTION') OR right_contract_id IN (SELECT contract_id FROM canonical_dataset_contract WHERE contract_role='AR_SEMANTIC_PROJECTION')")
    ids=list(bind.execute(text("SELECT contract_id FROM canonical_dataset_contract WHERE contract_role='AR_SEMANTIC_PROJECTION' ORDER BY revision DESC")).scalars())
    for identifier in ids:
        bind.execute(text('DELETE FROM canonical_dataset_contract WHERE contract_id=:id'),{'id':identifier})
    with op.batch_alter_table('canonical_dataset_contract') as batch:
        batch.drop_constraint('ck_dataset_contract_role',type_='check')
        batch.drop_constraint('uq_dataset_contract_source_revision',type_='unique')
        batch.drop_column('contract_role')
        batch.create_unique_constraint('uq_dataset_contract_source_revision',['client_id','source_version_id','revision'])
