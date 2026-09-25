import tempfile, unittest
from pathlib import Path
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from alembic import command
from alembic.config import Config
from profit_doctor.persistence import *
T='2026-09-25T00:00:00Z'
class V29(unittest.TestCase):
 def make(self):
  f=tempfile.NamedTemporaryFile(suffix='.db',delete=False);f.close();p=Path(f.name);e=build_engine(DatabaseConfig(f'sqlite+pysqlite:///{p}'));Base.metadata.create_all(e);return p,e,session_factory(e)
 def seed(self,F):
  with session_scope(F) as s:
   s.add(Client(client_id='c1',client_name='A',base_currency='GBP',created_at=T))
  with session_scope(F) as s:
   s.add(EngineRun(run_id='r1',client_id='c1',run_type='BASELINE',started_at=T,status='RUNNING',engine_version='2.9'))
  with session_scope(F) as s:
   s.add(Finding(finding_id='f1',client_id='c1',finding_type='OPPORTUNITY',title='x',status='ACCEPTED',first_run_id='r1',last_run_id='r1',created_at=T,updated_at=T));s.add(EconomicStory(economic_story_id='st1',client_id='c1',story_key='K',story_type='PERFORMANCE',title='K',status='OPEN',first_run_id='r1',last_run_id='r1',created_at=T,updated_at=T))
 def test_full_economic_chain_and_decimal_equivalence(self):
  p,e,F=self.make();self.seed(F)
  rows=[
   EconomicImpact(impact_id='i1',run_id='r1',client_id='c1',economic_story_id='st1',impact_type='REV',primary_economic_measure='REVENUE',amount='100.10',currency='GBP',attribution_state='OBSERVED',calculation_basis='x',status='OPEN',created_at=T),
   OpportunityCandidate(opportunity_candidate_id='oc1',run_id='r1',client_id='c1',economic_story_id='st1',finding_id='f1',purpose='RECOVER',benefit_type='B1_RECURRING_PROFIT_IMPROVEMENT',theoretical_amount='100.10',addressable_amount='60.06',expected_amount='30.03',currency='GBP',availability_state='IMMEDIATE',candidate_status='QUALIFIED',created_at=T),
   Opportunity(opportunity_id='o1',run_id='r1',client_id='c1',economic_story_id='st1',finding_id='f1',mechanism_id='m1',purpose='RECOVER',benefit_type='B1_RECURRING_PROFIT_IMPROVEMENT',theoretical_amount='100.10',addressable_amount='60.06',expected_amount='30.03',currency='GBP',availability_state='IMMEDIATE',status='SUPPORTED',created_at=T),
   Decision(decision_id='d1',run_id='r1',client_id='c1',opportunity_id='o1',selected_course='Act',rationale='Evidence',status='MADE',decided_at=T,created_at=T),
   Action(action_id='a1',run_id='r1',client_id='c1',decision_id='d1',opportunity_id='o1',description='Do',status='COMPLETED',created_at=T,updated_at=T),
   BenefitLeg(benefit_leg_id='b1',run_id='r1',client_id='c1',opportunity_id='o1',action_id='a1',benefit_type='B1_RECURRING_PROFIT_IMPROVEMENT',gross_amount='31.03',implementation_cost='1.00',ongoing_cost='0',adverse_effect='0',net_amount='30.03',currency='GBP',attribution_state='DIRECTLY_ATTRIBUTABLE',status='REALISED',created_at=T)]
  for row in rows:
   with session_scope(F) as ss: ss.add(row)
  with F() as ss:
   x=ss.get(BenefitLeg,'b1');self.assertEqual(Decimal(x.gross_amount)-Decimal(x.implementation_cost)-Decimal(x.ongoing_cost)-Decimal(x.adverse_effect),Decimal(x.net_amount));self.assertEqual(x.net_amount,'30.03')
  e.dispose();p.unlink(missing_ok=True)
 def test_cross_client_chain_rejected(self):
  p,e,F=self.make();self.seed(F)
  with session_scope(F) as s: s.add(Client(client_id='c2',client_name='B',base_currency='GBP',created_at=T))
  with session_scope(F) as s: s.add(EngineRun(run_id='r2',client_id='c2',run_type='BASELINE',started_at=T,status='RUNNING',engine_version='2.9'))
  # FK existence alone cannot guarantee run/client pairing; application boundary must reject it. Documented by service test below.
  from profit_doctor.persistence.service import add_impact
  with self.assertRaises(ValueError):
   with session_scope(F) as s: add_impact(s,'i2','r2','c1','st1','REV','REVENUE','1','GBP','OBSERVED','x','OPEN',T)
  e.dispose();p.unlink(missing_ok=True)
 def test_alembic_head_contains_backbone(self):
  f=tempfile.NamedTemporaryFile(suffix='.db',delete=False);f.close();p=Path(f.name);cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'));cfg.set_main_option('sqlalchemy.url',f'sqlite+pysqlite:///{p}');command.upgrade(cfg,'head');e=build_engine(DatabaseConfig(f'sqlite+pysqlite:///{p}'))
  from sqlalchemy import inspect
  names=set(inspect(e).get_table_names());self.assertIn('benefit_leg_v2',names);self.assertIn('economic_story_v2',names);e.dispose();command.downgrade(cfg,'base');p.unlink(missing_ok=True)
if __name__=='__main__':unittest.main()
