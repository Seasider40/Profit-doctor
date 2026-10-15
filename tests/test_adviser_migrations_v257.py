"""Frozen 0020 upgrade, additive schema integrity and preserved data."""
import unittest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import select, inspect
from sqlalchemy.engine import create_mock_engine
from tests.test_workspace_v256 import WorkspaceFixture
from tests.test_postgresql_live_qualification_v218 import alembic_config
from profit_doctor.persistence import Base, setup_schema as t
from profit_doctor.workspace.setup import SetupService


class AdviserMigrationsV257(WorkspaceFixture, unittest.TestCase):
    def snapshot(self):
        with self.engine.connect() as c:
            return {name:sorted([dict(r) for r in c.execute(select(table)).mappings()],key=repr)
                for name,table in Base.metadata.tables.items() if not name.startswith('workspace_setup_')}

    def test_clean_head_exact_metadata(self):
        with self.engine.connect() as c:
            ctx=MigrationContext.configure(c,opts={'compare_type':True,'compare_server_default':True})
            self.assertEqual(ctx.get_current_heads(),('0021_adviser_setup',))
            self.assertEqual(compare_metadata(ctx,Base.metadata),[])

    def test_frozen_0020_upgrade_preserves_every_legacy_row(self):
        self.receive(); self.request(); self.session.commit(); self.session.close()
        command.downgrade(alembic_config(self.url),'0020_engagement_workspace')
        self.assertEqual(set(inspect(self.engine).get_table_names())-{'alembic_version'},
            set(Base.metadata.tables)-{x.name for x in t.TABLES})
        before=self.snapshot()
        command.upgrade(alembic_config(self.url),'head')
        self.assertEqual(self.snapshot(),before)

    def test_downgrade_reupgrade_removes_only_drafts(self):
        SetupService(self.service).save('c1','draft-1',{},expected_revision=0,key='draft')
        self.receive(); self.session.commit(); self.session.close(); before=self.snapshot()
        command.downgrade(alembic_config(self.url),'0020_engagement_workspace')
        self.assertEqual(self.snapshot(),before)
        self.assertTrue(all(x.name not in inspect(self.engine).get_table_names() for x in t.TABLES))
        command.upgrade(alembic_config(self.url),'head')
        self.assertEqual(self.snapshot(),before)
        with self.engine.connect() as c:
            self.assertEqual(list(c.execute(select(t.revision))),[])

    def test_postgresql_ddl_preserves_all_constraints(self):
        statements=[]
        engine=create_mock_engine('postgresql+psycopg://',lambda sql,*a,**kw:statements.append(str(sql.compile(dialect=engine.dialect))))
        Base.metadata.create_all(engine)
        for table in t.TABLES:
            own=[s for s in statements if 'CREATE TABLE '+table.name+' ' in s or 'ALTER TABLE '+table.name+' ' in s]
            self.assertEqual(sum(s.count('FOREIGN KEY') for s in own),len(table.foreign_key_constraints))
            self.assertEqual(sum(s.count('CHECK (') for s in own),len([c for c in table.constraints if c.__class__.__name__=='CheckConstraint']))

    def test_revision_width_and_predecessor(self):
        scripts=ScriptDirectory.from_config(alembic_config(self.url))
        self.assertEqual(scripts.get_current_head(),'0021_adviser_setup')
        self.assertEqual(scripts.get_revision('0021_adviser_setup').down_revision,'0020_engagement_workspace')
        self.assertTrue(all(len(r.revision)<=32 for r in scripts.walk_revisions()))
