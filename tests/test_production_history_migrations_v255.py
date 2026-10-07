"""0019 ownership, raw-contract coexistence and forward/downgrade DDL integrity."""
import unittest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import select, inspect
from sqlalchemy.engine import create_mock_engine
from tests import test_production_history_v255 as fixture
from tests import test_zero_ar_v255 as zero_fixture
from tests.test_postgresql_live_qualification_v218 import alembic_config
from profit_doctor.persistence import Base, dataset_schema, production_evidence_schema as legacy, production_history_schema as tables
from profit_doctor.reasoning.production_evidence.history import ARProjectionService


class ProductionHistoryMigrationsV255(unittest.TestCase):
    setUp=fixture.ProductionHistoryV255.setUp
    capture=fixture.ProductionHistoryV255.capture
    source=zero_fixture.ZeroARV255.source

    def url(self):
        return (getattr(self,'target_url',None) or ('sqlite+pysqlite:///'+(self.ar.fx.fx.root/'ar-canonical.db').as_posix())).replace('%','%%')

    def test_head_matches_metadata_and_complete_scope_constraints(self):
        with self.session.get_bind().connect() as connection:
            ctx=MigrationContext.configure(connection,opts={'compare_type':True,'compare_server_default':True})
            self.assertEqual(ctx.get_current_heads(),('0019_production_history',))
            self.assertEqual(compare_metadata(ctx,Base.metadata),[])

    def test_downgrade_removes_ar_projection_but_preserves_original_absence(self):
        value=self.capture();self.session.commit()
        engine=self.session.get_bind()
        with engine.connect() as c:expected=[dict(r) for r in c.execute(select(legacy.absence)).mappings()]
        self.session.close()
        command.downgrade(alembic_config(self.url()),'0018_production_qualification')
        self.assertNotIn(tables.projection.name,inspect(engine).get_table_names())
        with engine.connect() as c:
            self.assertEqual([dict(r) for r in c.execute(select(legacy.absence)).mappings()],expected)
            self.assertEqual(c.scalar(select(dataset_schema.dataset_contract.c.contract_id).where(
                dataset_schema.dataset_contract.c.contract_id==value.projection_id)),None)
        command.upgrade(alembic_config(self.url()),'head')
        with engine.connect() as c:
            self.assertEqual([dict(r) for r in c.execute(select(legacy.absence)).mappings()],expected)

    def test_zero_based_absence_removed_but_legacy_absence_preserved(self):
        version,proof=self.source()
        zero_absence=self.service.assess_absence(proof.export_version_id,proof.manifest_version_id,
            proof.control_version_id,zero_version=version)
        self.session.commit();self.session.close()
        command.downgrade(alembic_config(self.url()),'0018_production_qualification')
        with self.session.get_bind().connect() as c:
            self.assertEqual(list(c.execute(select(legacy.absence.c.assessment_id)).scalars()),[self.owner.assessment_id])
        command.upgrade(alembic_config(self.url()),'head')
        self.assertNotEqual(zero_absence.assessment_id,self.owner.assessment_id)

    def test_postgresql_ddl_retains_every_new_fk_and_exclusive_owner_constraint(self):
        statements=[]
        engine=create_mock_engine('postgresql+psycopg://',lambda sql,*a,**kw:statements.append(str(sql.compile(dialect=engine.dialect))))
        Base.metadata.create_all(engine)
        for table in (tables.projection,tables.unknown,tables.zero,tables.temporal,tables.readiness,
                tables.zero_absence,tables.temporal_reference,tables.readiness_reference,tables.audit):
            ddl=next(s for s in statements if 'CREATE TABLE '+table.name+' ' in s)
            self.assertEqual(ddl.count('FOREIGN KEY'),len(table.foreign_key_constraints),table.name)
        self.assertIn('ck_ar_projection_owner','\n'.join(statements))
        self.assertIn('ck_evidence_readiness_ref_one_owner','\n'.join(statements))
