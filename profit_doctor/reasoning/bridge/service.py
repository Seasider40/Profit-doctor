"""Caller-owned append-only persistence; never accepts caller-calculated Bridges."""
import json
from sqlalchemy import insert, select
from profit_doctor.persistence import bridge_schema as tables
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import now
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from .contracts import EconomicBridge
from .engine import BridgeEngine


def input_roles(bridge):
    result={key:'OPENING' for key in bridge.opening_bindings}
    result.update({key:'CLOSING' for key in bridge.closing_bindings})
    for component in bridge.components:
        for key in component.input_bindings:
            # WC components use the same endpoint records, not duplicated evidence.
            result.setdefault(key,'COMPONENT')
    return result


class BridgeService:
    def __init__(self,contexts):
        self.contexts=contexts
        self.session=contexts.session
        self.engine=BridgeEngine(contexts)

    def create(self,family,opening_year,closing_year,opening_ids,closing_ids,detail_ids=(),*,expected_previous=None):
        result=self.engine.assess(family,opening_year,closing_year,opening_ids,closing_ids,detail_ids)
        if result.bridge is None:
            return result
        b=result.bridge
        existing=self.session.scalar(select(tables.bridge_snapshot.c.snapshot_id).where(tables.bridge_snapshot.c.snapshot_id==b.snapshot_id))
        if existing:
            self.get(existing,current=True)
            return result
        previous=self.session.execute(select(tables.bridge_snapshot).where(
            tables.bridge_snapshot.c.client_id==b.client_id,tables.bridge_snapshot.c.series_id==b.series_id)
            .order_by(tables.bridge_snapshot.c.revision.desc()).limit(1)).mappings().one_or_none()
        previous_id=previous['snapshot_id'] if previous else None
        if expected_previous!=previous_id:
            raise RevisionConflict('Bridge history changed; explicit predecessor required')
        self.session.execute(insert(tables.bridge_snapshot).values(snapshot_id=b.snapshot_id,client_id=b.client_id,run_id=b.run_id,
            series_id=b.series_id,revision=previous['revision']+1 if previous else 1,prior_id=previous_id,document=b.to_json()))
        for key,role in input_roles(b).items():
            self.session.execute(insert(tables.bridge_input).values(snapshot_id=b.snapshot_id,binding_id=key,client_id=b.client_id,role=role))
        event={'event_type':'OBJECT_SUPERSEDED' if previous else 'OBJECT_CREATED','actor':self.contexts.actor.model_dump(mode='json'),
            'prior_snapshot_id':previous_id,'new_snapshot_id':b.snapshot_id,'reason':'Qualified immutable Bridge evidence snapshot'}
        self.session.execute(insert(tables.bridge_audit).values(event_id=identity('bridge-audit',b.snapshot_id),snapshot_id=b.snapshot_id,
            client_id=b.client_id,created_at=now().isoformat(),document=json.dumps(event,sort_keys=True,separators=(',',':'))))
        return result

    def get(self,snapshot_id,*,current=False):
        row=self.session.execute(select(tables.bridge_snapshot).where(tables.bridge_snapshot.c.snapshot_id==snapshot_id,
            tables.bridge_snapshot.c.client_id==self.contexts.client_id)).mappings().one_or_none()
        if row is None:raise ScopeError('Bridge missing or foreign')
        bridge=EconomicBridge.from_json(row['document'])
        if (bridge.snapshot_id,bridge.series_id,bridge.run_id,bridge.client_id)!=(row['snapshot_id'],row['series_id'],row['run_id'],row['client_id']):
            raise ScopeError('Bridge indexed envelope disagrees with document')
        actual=dict(self.session.execute(select(tables.bridge_input.c.binding_id,tables.bridge_input.c.role).where(
            tables.bridge_input.c.snapshot_id==snapshot_id,tables.bridge_input.c.client_id==self.contexts.client_id)).all())
        if actual!=input_roles(bridge):raise ScopeError('Bridge input references changed')
        if current:
            if bridge.run_id!=self.contexts.run_id:raise ScopeError('Current read requires originating run context')
            assessment=self.engine.assess(bridge.family,bridge.opening_year,bridge.closing_year,bridge.opening_bindings,
                bridge.closing_bindings,tuple(k for k,v in actual.items() if v=='COMPONENT'))
            if assessment.bridge!=bridge:raise RevisionConflict('Bridge source evidence is stale or changed')
        return bridge
