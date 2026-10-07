"""Opt-in durable ownership. Caller owns both stores and all transactions."""
from sqlalchemy import insert, select

from profit_doctor.persistence import production_evidence_schema as tables, measurement_schema
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import Actor, AuditEvent
from profit_doctor.reasoning.domain.service import FoundationService, ScopeError, RevisionConflict
from profit_doctor.reasoning.measurement.service import MeasurementContextService
from .monthly import MonthlyMeasurement, MonthlyMeasurementService
from .absence import AbsenceAssessment, ReceivablesAbsenceService


def equivalent(left, right):
    a,b = left.model_dump(mode='json'),right.model_dump(mode='json')
    # Capture timestamp is history, not a source-semantic change.
    for value in (a,b):
        if 'semantic' in value:
            value['semantic']['contract'].pop('created_at',None)
    return a == b


class ProductionEvidenceService:
    """Production entry points accept registered IDs, never asserted values/proofs.

    Prior documents are loaded from immutable owned history, not supplied by a
    caller. Authority resolver is a trusted deployment dependency, default unknown.
    """
    def __init__(self, session, connection, client_id, run_id, actor, authority_resolver=None):
        self.session,self.connection,self.client_id,self.run_id = session,connection,client_id,run_id
        self.actor = Actor.from_json(actor.to_json())
        FoundationService(session,client_id,self.actor)._run(run_id)
        self.authority_resolver = authority_resolver
        self.monthly = MonthlyMeasurementService(connection,client_id,run_id,authority_resolver)
        self.absence = ReceivablesAbsenceService(connection,client_id,run_id,authority_resolver)
        self.contexts = MeasurementContextService(session,client_id,run_id,self.actor,connection)
        self.contexts.monthly = self

    def _get(self, table, key, identifier, model):
        row = self.session.execute(select(table).where(table.c[key]==identifier,
            table.c.client_id==self.client_id)).mappings().one_or_none()
        if row is None:
            raise ScopeError('Production owner missing or foreign')
        value = model.from_json(row['document'])
        if model is MonthlyMeasurement and value.context.context_id != row['context_id']:
            raise ScopeError('Monthly context disagrees with indexed ownership')
        if (getattr(value,key),value.client_id,value.run_id,value.series_id,value.revision,value.supersedes) != (
                row[key],row['client_id'],row['run_id'],row['series_id'],row['revision'],row['supersedes']):
            raise ScopeError('Production owner document disagrees with indexed envelope')
        FoundationService(self.session,self.client_id,self.actor)._run(value.run_id)
        return value

    def get_monthly(self, measurement_id, *, current=False):
        value = self._get(tables.monthly,'measurement_id',measurement_id,MonthlyMeasurement)
        if current:
            self._require_latest(tables.monthly,value)
            previous = self.get_monthly(value.supersedes) if value.supersedes else None
            versions = value.semantic.source_versions
            result = MonthlyMeasurementService(self.connection,self.client_id,value.run_id,self.authority_resolver).qualify(
                versions[0],versions[1],versions[2],mapping_version=versions[3],family=value.family,previous=previous)
            if result.outcome != 'QUALIFIED' or not equivalent(result.value,value):
                raise RevisionConflict('Monthly owner no longer matches qualified retained evidence')
        return value

    def get_absence(self, assessment_id, *, current=False):
        value = self._get(tables.absence,'assessment_id',assessment_id,AbsenceAssessment)
        if value.zero_population_id:
            from profit_doctor.persistence import production_history_schema
            from .zero import ZeroARPopulationService
            zero=ZeroARPopulationService(self).get(value.zero_population_id,current=current)
            linked=self.session.scalar(select(production_history_schema.zero_absence.c.zero_id).where(
                production_history_schema.zero_absence.c.absence_id==assessment_id,
                production_history_schema.zero_absence.c.client_id==self.client_id))
            if linked!=zero.zero_id or zero.source_version_id!=value.zero_source_version_id or zero.scope!=value.scope:
                raise ScopeError('Zero AR/absence ownership relationship differs')
        if current:
            self._require_latest(tables.absence,value)
            previous = self.get_absence(value.supersedes) if value.supersedes else None
            reproduced = ReceivablesAbsenceService(self.connection,self.client_id,value.run_id,
                self.authority_resolver).assess(*value.source_versions,previous=previous,zero_version=value.zero_source_version_id)
            if not equivalent(reproduced,value):
                raise RevisionConflict('AR absence no longer matches qualified retained evidence')
        return value

    def _require_latest(self, table, value):
        latest = self.session.scalar(select(table.c.revision).where(table.c.client_id==self.client_id,
            table.c.series_id==value.series_id).order_by(table.c.revision.desc()).limit(1))
        if latest != value.revision:
            raise RevisionConflict('Superseded evidence is historical, not current')

    def _latest(self, table, key, series):
        return self.session.scalar(select(table.c[key]).where(table.c.client_id==self.client_id,
            table.c.series_id==series).order_by(table.c.revision.desc()).limit(1))

    def qualify_monthly(self, record_version, control_version, manifest_version, *, mapping_version, family):
        manifest,_,_ = self.monthly.semantic.sources.document(manifest_version,'manifest')
        series = identity('monthly-owner-2.55.1',self.client_id,family,manifest.scope.to_json())
        previous_id = self._latest(tables.monthly,'measurement_id',series)
        previous = self.get_monthly(previous_id) if previous_id else None
        result = self.monthly.qualify(record_version,control_version,manifest_version,mapping_version=mapping_version,
            family=family,previous=previous)
        if result.outcome != 'QUALIFIED':
            return result
        value = result.value
        existing = self.session.scalar(select(tables.monthly.c.measurement_id).where(tables.monthly.c.measurement_id==value.measurement_id))
        if existing:
            self.get_monthly(existing,current=True)
            return result
        context = value.context
        self.session.execute(insert(measurement_schema.measurement_context).values(context_id=context.context_id,
            client_id=self.client_id,run_id=self.run_id,supersedes=context.supersedes,document=context.to_json()))
        self.contexts._audit(context)
        self.session.execute(insert(tables.monthly).values(measurement_id=value.measurement_id,series_id=value.series_id,
            client_id=value.client_id,run_id=value.run_id,revision=value.revision,supersedes=value.supersedes,
            context_id=context.context_id,document=value.to_json()))
        self.contexts._bind(context,context.origin)
        self._audit(value,'measurement_id')
        return result

    def assess_absence(self, export_version, manifest_version, control_version, *, zero_version=None):
        export,_,_ = self.absence._document(export_version,'ar-export')
        series = identity('ar-absence-owner-2.55.1',export.scope.to_json())
        previous_id = self._latest(tables.absence,'assessment_id',series)
        previous = self.get_absence(previous_id) if previous_id else None
        if zero_version is not None:
            from .zero import ZeroARPopulationService
            ZeroARPopulationService(self).capture(zero_version)
        value = self.absence.assess(export_version,manifest_version,control_version,previous=previous,zero_version=zero_version)
        existing = self.session.scalar(select(tables.absence.c.assessment_id).where(tables.absence.c.assessment_id==value.assessment_id))
        if existing:
            self.get_absence(existing,current=True)
            return value
        self.session.execute(insert(tables.absence).values(assessment_id=value.assessment_id,series_id=value.series_id,
            client_id=value.client_id,run_id=value.run_id,revision=value.revision,supersedes=value.supersedes,
            document=value.to_json()))
        self._audit(value,'assessment_id')
        if value.zero_population_id:
            from profit_doctor.persistence import production_history_schema
            self.session.execute(insert(production_history_schema.zero_absence).values(absence_id=value.assessment_id,
                zero_id=value.zero_population_id,client_id=self.client_id))
        return value

    def _audit(self, value, key):
        owner = getattr(value,key)
        event = AuditEvent(event_id=identity('production-evidence-audit',owner),object_id=owner,
            client_id=self.client_id,run_id=self.run_id,event_type='OBJECT_CREATED',actor=self.actor,
            previous={'supersedes':value.supersedes} if value.supersedes else None,
            new={'owner':owner,'revision':value.revision},lineage=value.lineage,
            rationale={'qualification_contract':value.qualification_contract,'boundary':'owned source evidence; no temporal uplift'})
        self.session.execute(insert(tables.audit).values(event_id=event.event_id,client_id=self.client_id,
            **{key:owner},created_at=event.created_at.isoformat(),document=event.to_json()))

    def owner(self, measurement_id):
        value = self.get_monthly(measurement_id,current=True)
        # Context binding uses the complete owned snapshot, never diagnostic data.
        return value.model_dump(mode='json'),value.measurement.value,value.measurement.unit.value

    def context(self, measurement_id):
        return self.get_monthly(measurement_id,current=True).context
