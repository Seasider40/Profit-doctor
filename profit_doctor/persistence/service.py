"""Tenant-safe persistence commands for migrated economic objects."""
from .models import EngineRun,EconomicStory,EconomicImpact
def _scope(session,run_id,client_id,story_id=None):
 r=session.get(EngineRun,run_id)
 if not r or r.client_id!=client_id: raise ValueError('Run does not belong to client')
 if story_id:
  st=session.get(EconomicStory,story_id)
  if not st or st.client_id!=client_id: raise ValueError('Economic story does not belong to client')
def add_impact(session,impact_id,run_id,client_id,story_id,impact_type,measure,amount,currency,attribution,basis,status,created_at):
 _scope(session,run_id,client_id,story_id)
 obj=EconomicImpact(impact_id=impact_id,run_id=run_id,client_id=client_id,economic_story_id=story_id,impact_type=impact_type,primary_economic_measure=measure,amount=amount,currency=currency,attribution_state=attribution,calculation_basis=basis,status=status,created_at=created_at);session.add(obj);return obj
