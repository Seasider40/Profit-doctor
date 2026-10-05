"""Add governed dataset contract and comparability history.

Revision ID: 0015_dataset_comparability
Revises: 0014_priority_decision
"""
from alembic import op
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint

revision = '0015_dataset_comparability'
down_revision = '0014_priority_decision'
branch_labels = None
depends_on = None


def upgrade():
    create = op.create_table
    create('canonical_dataset_contract',
        Column('contract_id', String(64), primary_key=True),
        Column('client_id', String(64), nullable=False),
        Column('run_id', String(64), nullable=False),
        Column('source_version_id', String(128), nullable=False),
        Column('revision', Integer, nullable=False),
        Column('supersedes', String(64)),
        Column('document', Text, nullable=False),
        UniqueConstraint('contract_id', 'client_id', name='uq_dataset_contract_client'),
        UniqueConstraint('client_id', 'source_version_id', 'revision', name='uq_dataset_contract_source_revision'),
        ForeignKeyConstraint(['client_id'], ['client.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['run_id'], ['engine_run.run_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['supersedes', 'client_id'],
            ['canonical_dataset_contract.contract_id', 'canonical_dataset_contract.client_id'], ondelete='RESTRICT'))
    op.create_index('ix_dataset_contract_source_version', 'canonical_dataset_contract', ['client_id', 'source_version_id'])
    create('canonical_dataset_comparability',
        Column('assessment_id', String(64), primary_key=True),
        Column('client_id', String(64), nullable=False),
        Column('run_id', String(64), nullable=False),
        Column('left_contract_id', String(64), nullable=False),
        Column('right_contract_id', String(64), nullable=False),
        Column('policy_version', String(64), nullable=False),
        Column('outcome', String(40), nullable=False),
        Column('document', Text, nullable=False),
        UniqueConstraint('assessment_id', 'client_id', name='uq_dataset_assessment_client'),
        UniqueConstraint('client_id', 'left_contract_id', 'right_contract_id', 'policy_version',
            name='uq_dataset_comparability_pair_policy'),
        ForeignKeyConstraint(['client_id'], ['client.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['run_id'], ['engine_run.run_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['left_contract_id', 'client_id'],
            ['canonical_dataset_contract.contract_id', 'canonical_dataset_contract.client_id'], ondelete='RESTRICT'),
        ForeignKeyConstraint(['right_contract_id', 'client_id'],
            ['canonical_dataset_contract.contract_id', 'canonical_dataset_contract.client_id'], ondelete='RESTRICT'))
    create('canonical_dataset_audit',
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


def downgrade():
    op.drop_table('canonical_dataset_audit')
    op.drop_table('canonical_dataset_comparability')
    op.drop_index('ix_dataset_contract_source_version', table_name='canonical_dataset_contract')
    op.drop_table('canonical_dataset_contract')
