"""Canonical dataset contracts and immutable comparability assessments."""
from sqlalchemy import (Column, ForeignKey, ForeignKeyConstraint, Index, Integer,
                        String, Table, Text, UniqueConstraint, CheckConstraint)

from .models import Base


dataset_contract = Table('canonical_dataset_contract', Base.metadata,
    Column('contract_id', String(64), primary_key=True),
    Column('client_id', String(64), ForeignKey('client.client_id', ondelete='RESTRICT'), nullable=False),
    Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
    Column('source_version_id', String(128), nullable=False),
    Column('revision', Integer, nullable=False),
    Column('supersedes', String(64)),
    Column('document', Text, nullable=False),
    Column('contract_role', String(32), nullable=False, server_default='RAW'),
    UniqueConstraint('contract_id', 'client_id', name='uq_dataset_contract_client'),
    UniqueConstraint('client_id', 'source_version_id', 'contract_role', 'revision', name='uq_dataset_contract_source_revision'),
    CheckConstraint("contract_role IN ('RAW', 'AR_SEMANTIC_PROJECTION')", name='ck_dataset_contract_role'),
    ForeignKeyConstraint(['supersedes', 'client_id'],
        ['canonical_dataset_contract.contract_id', 'canonical_dataset_contract.client_id'], ondelete='RESTRICT'))
Index('ix_dataset_contract_source_version', dataset_contract.c.client_id, dataset_contract.c.source_version_id)

dataset_comparability = Table('canonical_dataset_comparability', Base.metadata,
    Column('assessment_id', String(64), primary_key=True),
    Column('client_id', String(64), ForeignKey('client.client_id', ondelete='RESTRICT'), nullable=False),
    Column('run_id', String(64), ForeignKey('engine_run.run_id', ondelete='RESTRICT'), nullable=False),
    Column('left_contract_id', String(64), nullable=False),
    Column('right_contract_id', String(64), nullable=False),
    Column('policy_version', String(64), nullable=False),
    Column('outcome', String(40), nullable=False),
    Column('document', Text, nullable=False),
    UniqueConstraint('assessment_id', 'client_id', name='uq_dataset_assessment_client'),
    UniqueConstraint('client_id', 'left_contract_id', 'right_contract_id', 'policy_version',
        name='uq_dataset_comparability_pair_policy'),
    ForeignKeyConstraint(['left_contract_id', 'client_id'],
        ['canonical_dataset_contract.contract_id', 'canonical_dataset_contract.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['right_contract_id', 'client_id'],
        ['canonical_dataset_contract.contract_id', 'canonical_dataset_contract.client_id'], ondelete='RESTRICT'))

dataset_audit = Table('canonical_dataset_audit', Base.metadata,
    Column('event_id', String(64), primary_key=True),
    Column('client_id', String(64), nullable=False),
    Column('contract_id', String(64)),
    Column('assessment_id', String(64)),
    Column('event_type', String(40), nullable=False),
    Column('created_at', String(40), nullable=False),
    Column('document', Text, nullable=False),
    ForeignKeyConstraint(['contract_id', 'client_id'],
        ['canonical_dataset_contract.contract_id', 'canonical_dataset_contract.client_id'], ondelete='RESTRICT'),
    ForeignKeyConstraint(['assessment_id', 'client_id'],
        ['canonical_dataset_comparability.assessment_id', 'canonical_dataset_comparability.client_id'], ondelete='RESTRICT'))
