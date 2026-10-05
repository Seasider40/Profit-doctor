"""Opt-in Dataset Contract production-boundary and persistence tests."""
from contextlib import contextmanager
import csv
from pathlib import Path
import shutil
import unittest

from alembic import command
from sqlalchemy import select, func

from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import register_dataset_version
from profit_doctor.persistence import (Base, Client, DatabaseConfig, EngineRun, build_engine,
    dataset_schema, session_factory)
from profit_doctor.reasoning.dataset.contracts import AssessmentOutcome, DatasetCoverage
from profit_doctor.reasoning.dataset.service import DatasetContractService
from profit_doctor.reasoning.domain.contracts import Actor
from profit_doctor.reasoning.domain.service import RevisionConflict, ScopeError
from tests.test_postgresql_live_qualification_v218 import alembic_config


T = '2026-10-01T00:00:00+00:00'
HEAD = Path(__file__).resolve().parents[1]


class DatasetContractServiceV253(unittest.TestCase):
    target_url = None
    @staticmethod
    def _remove_test_root(root):
        if root.exists():
            # The source adapter intentionally stores immutable read-only copies.
            for path in root.rglob('*'):
                if path.is_file():
                    path.chmod(0o666)
            shutil.rmtree(root)

    def setUp(self):
        # Use one predictable workspace-local directory. Random temp directory
        # ACLs can prevent SQLite from opening files in managed Windows runs.
        self.root = HEAD/'tests'/'.v253_dataset_contract_tmp'
        self._remove_test_root(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(self._remove_test_root, self.root)
        self.url = self.target_url or ('sqlite+pysqlite:///' + (self.root/'canonical.db').as_posix())
        self.engine = build_engine(DatabaseConfig(self.url))
        self.addCleanup(self.engine.dispose)
        command.upgrade(alembic_config(self.url), 'head')
        if self.engine.dialect.name == 'postgresql':
            with self.engine.begin() as connection:
                for table in reversed(Base.metadata.sorted_tables):
                    connection.execute(table.delete())
        self.factory = session_factory(self.engine)
        self.legacy = connect(self.root/'legacy.db')
        self.addCleanup(self.legacy.close)
        for client, run in (('c1','r1'),('c2','r2')):
            self.legacy.execute('INSERT INTO client VALUES (?,?,?,?,?)',(client,'Client '+client,'GBP','MANUFACTURING',T))
            self.legacy.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(run,client,'ADVISORY',T,None,'RUNNING',None,None,'2.53'))
        self.legacy.commit()
        with self.factory.begin() as session:
            for client, run in (('c1','r1'),('c2','r2')):
                session.add(Client(client_id=client,client_name='Client '+client,base_currency='GBP',created_at=T))
                session.add(EngineRun(run_id=run,client_id=client,run_type='ADVISORY',started_at=T,
                    status='RUNNING',engine_version='2.53'))
        self.actor = Actor(actor_type='SYSTEM',source_authority='SYSTEM_DERIVED',actor_id='qualification-system')
        self.human = Actor(actor_type='MANAGEMENT',source_authority='MANAGEMENT_ASSERTION',actor_id='manager-1')

    def new_dataset(self, month, *, domain='D07_SALES_TRANSACTIONS', logical='northstar:transactions'):
        source = self.root/f'{month}.csv'
        rows = [{'transaction_id':f'{month}-1','month':f'2026-{month:02}-01','revenue':'10.00'},
                {'transaction_id':f'{month}-2','month':f'2026-{month:02}-02','revenue':'20.00'}]
        with source.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
            writer.writeheader(); writer.writerows(rows)
        job = f'job-{month}'
        self.legacy.execute('INSERT INTO ingestion_job VALUES (?,?,?,?,?,?,?)',
            (job,'r1','c1',T,T,'COMPLETED',None))
        version, _, _, _ = register_dataset_version(self.legacy,'c1',job,source,domain,logical,self.root/'store','month')
        self.legacy.execute('UPDATE dataset_version SET ingestion_status=? WHERE dataset_version_id=?',('COMPLETED',version))
        for idx,row in enumerate(rows,2):
            self.legacy.execute('''INSERT INTO sales_transaction(sales_transaction_id,client_id,source_transaction_key,
                transaction_date,dataset_version_id,source_row_reference) VALUES (?,?,?,?,?,?)''',
                (f'txn-{month}-{idx}','c1',row['transaction_id'],row['month'],version,idx))
        self.legacy.commit()
        return version

    @contextmanager
    def service(self, client='c1', run='r1'):
        session = self.factory()
        try:
            with session.begin():
                yield DatasetContractService(session,client,run,self.actor,self.legacy)
        finally:
            session.close()

    def test_existing_sales_route_captures_only_verified_technical_facts(self):
        version = self.new_dataset(1)
        with self.service() as service:
            value = service.capture_sales(version)
            replay = service.capture_sales(version)
            self.assertEqual(value, replay)
            self.assertEqual('SALES_TRANSACTIONS', value.family.verified_value)
            self.assertIsNone(value.population.declared_value)
            self.assertIsNone(value.population.verified_value)
            self.assertIsNone(value.coverage.declared_value)
            self.assertEqual(2, value.observed_row_count)
            self.assertEqual(version, value.source_version.source_id)
        with self.factory() as session:
            self.assertEqual(1, session.scalar(select(func.count()).select_from(dataset_schema.dataset_contract)))
            self.assertEqual(1, session.scalar(select(func.count()).select_from(dataset_schema.dataset_audit)))

    def test_non_sales_route_and_unknown_provider_fail_closed(self):
        version = self.new_dataset(1,domain='D01_PNL')
        with self.service() as service, self.assertRaisesRegex(ValueError,'Only the existing D07'):
            service.capture_sales(version)
        version = self.new_dataset(2,logical='unknown:transactions')
        with self.service() as service, self.assertRaisesRegex(ValueError,'Unregistered sales provider'):
            service.capture_sales(version)

    def test_declaration_is_audited_immutable_and_idempotent(self):
        version = self.new_dataset(1)
        with self.service() as service:
            original = service.capture_sales(version)
            declared = service.declare(original.contract_id, {'population':{'key':'all-uk-sales', 'label':'All UK sales'}}, actor=self.human)
            replay = service.declare(original.contract_id, {'population':{'key':'all-uk-sales', 'label':'All UK sales'}}, actor=self.human)
            self.assertEqual(declared, replay)
            self.assertEqual(2, declared.revision)
            self.assertEqual(original.contract_id, declared.supersedes)
            self.assertIsNone(original.population.declared_value)
            self.assertEqual('all-uk-sales', declared.population.declared_value['key'])
            self.assertIsNone(declared.population.verified_value)
            self.assertEqual('manager-1', declared.population.declared_by.actor_id)
            self.assertEqual(1, len(service.audit_events(contract_id=declared.contract_id)))
        with self.factory() as session:
            revisions = session.scalars(select(dataset_schema.dataset_contract.c.revision).order_by(
                dataset_schema.dataset_contract.c.revision)).all()
            self.assertEqual([1,2], revisions)

    def test_revision_target_is_explicit_same_client_and_source(self):
        jan, feb = self.new_dataset(1), self.new_dataset(2)
        with self.service() as service:
            first, second = service.capture_sales(jan), service.capture_sales(feb)
            updated = service.declare(second.contract_id, {'revision_relationship':'RESTATEMENT'},
                actor=self.human, revision_target_contract_id=first.contract_id)
            self.assertEqual(first.contract_id, updated.revision_target_contract_id)
            self.assertEqual(second.contract_id, updated.supersedes)
            self.assertEqual('UNKNOWN', service.get_contract(second.contract_id).revision_relationship.verified_value or 'UNKNOWN')

    def test_cross_client_source_contract_is_not_retrievable(self):
        version = self.new_dataset(1)
        with self.service() as service:
            value = service.capture_sales(version)
        with self.service('c2','r2') as foreign, self.assertRaises(ScopeError):
            foreign.get_contract(value.contract_id)

    def test_missing_population_keeps_persisted_comparison_insufficient_and_replay_safe(self):
        jan, feb = self.new_dataset(1), self.new_dataset(2)
        with self.service() as service:
            a, b = service.capture_sales(jan), service.capture_sales(feb)
            result = service.compare(a.contract_id,b.contract_id)
            replay = service.compare(b.contract_id,a.contract_id)
            self.assertEqual(result, replay)
            self.assertEqual(AssessmentOutcome.INSUFFICIENT_EVIDENCE, result.outcome)
            self.assertEqual(1, len(service.audit_events(assessment_id=result.assessment_id)))
        with self.factory() as session:
            self.assertEqual(1, session.scalar(select(func.count()).select_from(dataset_schema.dataset_comparability)))

    def test_source_change_invalidates_current_contract_without_erasing_history(self):
        version = self.new_dataset(1)
        with self.service() as service:
            value = service.capture_sales(version)
            # Same row count and period bounds, changed content must still be detected.
            self.legacy.execute('UPDATE sales_transaction SET net_revenue=? WHERE dataset_version_id=?',('999.00',version))
            self.legacy.commit()
            with self.assertRaises(RevisionConflict):
                service.get_contract(value.contract_id,current=True)
            self.assertEqual(value,service.get_contract(value.contract_id))

    def test_caller_owned_transaction_can_rollback_capture(self):
        version = self.new_dataset(1)
        session = self.factory()
        try:
            session.begin()
            service = DatasetContractService(session,'c1','r1',self.actor,self.legacy)
            value = service.capture_sales(version)
            session.rollback()
        finally:
            session.close()
        with self.factory() as session:
            self.assertIsNone(session.execute(select(dataset_schema.dataset_contract.c.contract_id).where(
                dataset_schema.dataset_contract.c.contract_id == value.contract_id)).scalar_one_or_none())

    def test_declaration_rejects_unidentified_or_machine_actor(self):
        version = self.new_dataset(1)
        with self.service() as service:
            value = service.capture_sales(version)
            with self.assertRaises(ValueError):
                service.declare(value.contract_id,{'population':'all'},actor=self.actor)


if __name__ == '__main__':
    unittest.main()
