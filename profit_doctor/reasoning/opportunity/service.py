"""Retained owning evidence, current Impact gate, caller-owned canonical writes."""
import csv
import json
from pathlib import Path
from decimal import Decimal, localcontext
from sqlalchemy import select, insert
from profit_doctor.persistence import opportunity_schema as tables, impact_schema, reasoning_schema
from profit_doctor.ingestion.northstar import register_dataset_version, id4, now as legacy_now, sha256
from profit_doctor.reasoning.domain.contracts import ReasoningObject, LineageReference, EffectReference, now
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.impact.contracts import ReceivablesImpact, precision
from profit_doctor.reasoning.impact.service import ImpactService
from .contracts import Candidate, CollectionEvidence, Assessment
from .engine import assess


class OpportunityService:
    def __init__(self, impacts):
        if not isinstance(impacts, ImpactService) or impacts.receivables is None:
            raise ScopeError('Canonical production receivables Impact owner required')
        self.impacts = impacts
        self.session = impacts.session
        self.foundation = impacts.foundation
        self.client_id, self.run_id = impacts.client_id, impacts.run_id
        self.contexts = impacts.receivables.contexts

    def _impact(self, impact_id, *, current=True):
        row = self.session.execute(select(impact_schema.impact).where(
            impact_schema.impact.c.impact_id == impact_id, impact_schema.impact.c.client_id == self.client_id)).mappings().one_or_none()
        if row is None: raise ScopeError('Qualified Impact identity required; candidates and other layers cannot enter')
        q = self.impacts.get(row['candidate_id'],row['revision'],current=current)
        if not isinstance(q.impact, ReceivablesImpact) or q.domain != 'PRODUCTION' or q.run_id != self.run_id:
            raise ScopeError('Only the qualified production receivables contract is eligible')
        return q

    @staticmethod
    def read_evidence(path):
        with Path(path).open(encoding='utf-8-sig',newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ['collection']: raise ValueError('Expected versioned collection document CSV')
            rows = list(reader)
        if len(rows) != 1: raise ValueError('Exactly one collection document required')
        return CollectionEvidence.from_json(rows[0]['collection'])

    def ingest_evidence(self, path, storage_root):
        value = self.read_evidence(path)
        q = self._impact(value.impact_id)
        if (value.client_id,value.run_id,value.origin) != (self.client_id,self.run_id,q.impact.amount.qualification_origin):
            raise ScopeError('Collection evidence scope/origin differs from qualified Impact')
        if value.assessed_on != q.impact.amount.as_of:
            raise ValueError('Initial contract requires a current snapshot at assessment date')
        con = self.contexts.source.connection
        job = id4('job')
        # Existing ingestion owns this legacy-store transaction. Canonical writes
        # below never commit the caller Session, as in the receivables provider.
        with con:
            con.execute('INSERT INTO ingestion_job VALUES (?,?,?,?,?,?,?)',
                (job,self.run_id,self.client_id,legacy_now(),None,'RUNNING',None))
            dvid,_,_,_ = register_dataset_version(con,self.client_id,job,path,'COLLECTION_EVIDENCE',
                'collection:'+value.impact_id,storage_root)
            con.execute("UPDATE dataset_version SET ingestion_status='COMPLETED' WHERE dataset_version_id=?",(dvid,))
            con.execute("UPDATE ingestion_job SET status='COMPLETED',completed_at=? WHERE ingestion_job_id=?",(legacy_now(),job))
        value = CollectionEvidence.model_validate({**value.model_dump(),'dataset_version_id':dvid})
        if self.session.scalar(select(tables.evidence.c.evidence_id).where(tables.evidence.c.evidence_id == value.evidence_id)):
            return self.get_evidence(value.evidence_id)
        self.session.execute(insert(tables.evidence).values(evidence_id=value.evidence_id,client_id=self.client_id,
            run_id=self.run_id,impact_id=value.impact_id,document=value.to_json()))
        return value

    def get_evidence(self, evidence_id):
        row = self.session.execute(select(tables.evidence).where(tables.evidence.c.evidence_id == evidence_id,
            tables.evidence.c.client_id == self.client_id)).mappings().one_or_none()
        if row is None: raise ScopeError('Missing or foreign collection evidence')
        value = CollectionEvidence.from_json(row['document'])
        if (value.evidence_id,value.client_id,value.run_id,value.impact_id) != (evidence_id,row['client_id'],row['run_id'],row['impact_id']) or value.run_id != self.run_id:
            raise ScopeError('Collection evidence envelope mismatch')
        ds = self.contexts.source.dataset(value.dataset_version_id)
        path = Path(ds['storage_location'])
        if not ds['immutable_flag'] or ds['ingestion_status'] != 'COMPLETED' or not path.is_file() or sha256(path) != ds['file_hash']:
            raise RevisionConflict('Collection source changed or unavailable')
        source = self.read_evidence(path)
        if CollectionEvidence.model_validate({**source.model_dump(),'dataset_version_id':value.dataset_version_id}) != value:
            raise RevisionConflict('Collection document differs from immutable source')
        return value

    def _savepoint(self):
        connection = self.session.connection()
        if connection.dialect.name == 'sqlite' and not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql('BEGIN')
        return self.session.begin_nested()

    def _object(self, object_id, kind, candidate):
        lineage = (LineageReference(kind='DERIVED_ANCESTOR',store='CANONICAL',resource='reasoning_object_v243',
            source_id=candidate.impact_id,client_id=self.client_id,run_id=self.run_id),)
        self.foundation.create_object(ReasoningObject(object_id=object_id,object_type=kind,client_id=self.client_id,
            run_id=self.run_id,source_authority='SYSTEM_DERIVED',period_from=candidate.assessed_on,
            period_to=candidate.horizon_end,lineage=lineage,
            confidence={'rationale':{'origin':candidate.origin,'contract':candidate.contract}}))
        self.foundation.reference_effect(EffectReference(client_id=self.client_id,run_id=self.run_id,
            object_id=object_id,effect_id=candidate.effect_id))

    def _audit(self, candidate_id, old, new):
        document=json.dumps({'previous':old,'new':new,'actor':self.foundation.actor.model_dump(mode='json')},sort_keys=True)
        self.session.execute(insert(tables.audit).values(event_id=identity('opportunity-audit',candidate_id,document),
            candidate_id=candidate_id,client_id=self.client_id,created_at=now().isoformat(),document=document))

    def create_candidate(self, impact_id, assessed_on, horizon_days):
        q = self._impact(impact_id)
        candidate = Candidate(candidate_id=identity('opportunity-candidate',impact_id,str(assessed_on),horizon_days,'MATCHED_COLLECTION_OUTCOMES_1'),
            client_id=self.client_id,run_id=self.run_id,impact_id=impact_id,effect_id=q.impact.effect_id,
            source_candidate_id=q.candidate_id,source_revision=q.revision,assessed_on=assessed_on,horizon_days=horizon_days,
            origin=q.impact.amount.qualification_origin,scope=q.impact.amount.scope,source_amount=q.impact.amount.value,source_document=q.to_json())
        if candidate.assessed_on != q.impact.amount.as_of: raise ValueError('Assessment requires same-date current Impact snapshot')
        exists = self.session.scalar(select(tables.candidate.c.candidate_id).where(tables.candidate.c.candidate_id == candidate.candidate_id))
        if exists: return self.get_candidate(exists)
        with self._savepoint():
            self._object(candidate.candidate_id,'OPPORTUNITY_CANDIDATE',candidate)
            self.session.execute(insert(tables.candidate).values(candidate_id=candidate.candidate_id,client_id=self.client_id,
                run_id=self.run_id,impact_id=impact_id,effect_id=candidate.effect_id,document=candidate.to_json()))
            self._audit(candidate.candidate_id,None,candidate.to_json())
        return candidate

    def get_candidate(self, candidate_id, *, current=False):
        row = self.session.execute(select(tables.candidate).where(tables.candidate.c.candidate_id == candidate_id,
            tables.candidate.c.client_id == self.client_id)).mappings().one_or_none()
        if row is None: raise ScopeError('Candidate missing or foreign')
        c = Candidate.from_json(row['document'])
        if (c.candidate_id,c.client_id,c.run_id,c.impact_id,c.effect_id) != (candidate_id,row['client_id'],row['run_id'],row['impact_id'],row['effect_id']) or c.run_id != self.run_id:
            raise ScopeError('Candidate envelope mismatch')
        q=self._impact(c.impact_id,current=current)
        if q.to_json() != c.source_document: raise RevisionConflict('Candidate Impact evidence differs')
        if (c.source_candidate_id,c.source_revision,c.effect_id,c.source_amount,c.origin,c.scope,c.assessed_on) != (
                q.candidate_id,q.revision,q.impact.effect_id,q.impact.amount.value,q.impact.amount.qualification_origin,q.impact.amount.scope,q.impact.amount.as_of):
            raise ScopeError('Candidate economics differs from source Impact')
        obj=self.foundation.get_object(candidate_id)
        if obj.object_type != 'OPPORTUNITY_CANDIDATE': raise ScopeError('Candidate type mismatch')
        self._effect_reference(candidate_id,c.effect_id)
        return c

    def _effect_reference(self,object_id,effect_id):
        key=self.session.scalar(select(reasoning_schema.effect_reference.c.reference_id).where(
            reasoning_schema.effect_reference.c.object_id==object_id,reasoning_schema.effect_reference.c.effect_id==effect_id,
            reasoning_schema.effect_reference.c.client_id==self.client_id))
        if key is None:raise ScopeError('Missing canonical Opportunity effect reference')
        self.foundation.get_effect_reference(key)

    def qualify(self, candidate_id, evidence_id=None, *, expected_revision=None):
        c=self.get_candidate(candidate_id,current=True)
        evidence=self.get_evidence(evidence_id) if evidence_id else None
        if evidence and (evidence.impact_id,evidence.assessed_on,evidence.horizon_days,evidence.origin) != (c.impact_id,c.assessed_on,c.horizon_days,c.origin):
            raise ScopeError('Evidence Impact, date, horizon or origin differs')
        old=self.session.execute(select(tables.assessment).where(tables.assessment.c.candidate_id == candidate_id)
            .order_by(tables.assessment.c.revision.desc()).limit(1)).mappings().one_or_none()
        revision=old['revision'] if old else 1
        proposed=assess(c,evidence,revision)
        if old:
            if self.get(candidate_id).to_json()==proposed.to_json(): return proposed
            if expected_revision != revision: raise RevisionConflict('Changed assessment requires explicit predecessor revision')
            proposed=assess(c,evidence,revision+1)
        elif expected_revision is not None: raise RevisionConflict('No predecessor revision')
        with self._savepoint():
            self.session.execute(insert(tables.assessment).values(candidate_id=candidate_id,revision=proposed.revision,
                client_id=self.client_id,evidence_id=evidence_id,document=proposed.to_json()))
            if proposed.opportunity_id:
                self._object(proposed.opportunity_id,'VALIDATED_OPPORTUNITY',c)
                self.session.execute(insert(tables.opportunity).values(opportunity_id=proposed.opportunity_id,
                    candidate_id=candidate_id,revision=proposed.revision,client_id=self.client_id,document=proposed.to_json()))
            self._audit(candidate_id,old['document'] if old else None,proposed.to_json())
        return proposed

    def get(self,candidate_id,revision=None,*,current=False):
        stmt=select(tables.assessment).where(tables.assessment.c.candidate_id == candidate_id,tables.assessment.c.client_id == self.client_id)
        if revision is not None: stmt=stmt.where(tables.assessment.c.revision == revision)
        row=self.session.execute(stmt.order_by(tables.assessment.c.revision.desc()).limit(1)).mappings().one_or_none()
        if row is None: raise ScopeError('Assessment missing or foreign')
        q=Assessment.from_json(row['document']);c=self.get_candidate(candidate_id,current=current)
        if q.candidate != c or (q.revision,q.evidence_id)!=(row['revision'],row['evidence_id']): raise ScopeError('Assessment envelope mismatch')
        if q.opportunity_id:
            stored=self.session.execute(select(tables.opportunity).where(tables.opportunity.c.opportunity_id==q.opportunity_id)).mappings().one_or_none()
            if stored is None or (stored['document'],stored['candidate_id'],stored['revision'],stored['client_id'])!=(q.to_json(),candidate_id,q.revision,self.client_id):
                raise ScopeError('Qualified Opportunity extension mismatch')
            if self.foundation.get_object(q.opportunity_id).object_type!='VALIDATED_OPPORTUNITY':raise ScopeError('Opportunity type mismatch')
            self._effect_reference(q.opportunity_id,c.effect_id)
        if current:
            latest=self.session.scalar(select(tables.assessment.c.revision).where(tables.assessment.c.candidate_id==candidate_id).order_by(tables.assessment.c.revision.desc()).limit(1))
            if latest!=q.revision:raise RevisionConflict('Historical Opportunity cannot enter totals')
            if assess(c,self.get_evidence(q.evidence_id) if q.evidence_id else None,q.revision)!=q:
                raise RevisionConflict('Assessment differs from retained evidence')
        return q

    def lifecycle(self,candidate_id,revision=None):
        value=self.get(candidate_id,revision);latest=self.get(candidate_id)
        if value.revision!=latest.revision:
            return 'INVALIDATED' if value.opportunity_id and not latest.opportunity_id else 'SUPERSEDED'
        return value.outcome

    def aggregate(self,candidate_ids,*,origin='REAL_SOURCE',dimension='CASH'):
        if origin not in ('REAL_SOURCE','BLIND_QUALIFICATION') or dimension!='CASH':raise ValueError('Unsupported origin or dimension')
        qs=[self.get(key,current=True) for key in sorted(set(candidate_ids))]
        qs=[q for q in qs if q.opportunity_id]
        if not qs:return {'status':'EMPTY','low':None,'high':None,'central':None,'dimension':dimension,'origin':origin}
        signatures={(q.candidate.assessed_on,q.candidate.horizon_days,q.candidate.scope,q.currency,q.candidate.origin,
                     self._impact(q.candidate.impact_id).impact.amount.coverage) for q in qs}
        blockers=[]
        if len(signatures)!=1 or any(q.candidate.origin!=origin for q in qs):blockers.append('INCOMPATIBLE_SCOPE_HORIZON_OR_ORIGIN')
        effects={}
        for q in qs:
            key=q.candidate.effect_id
            if key in effects and (q.low,q.high,q.central)!=(effects[key].low,effects[key].high,effects[key].central):blockers.append('CONFLICTING_SAME_EFFECT_VALUATION')
            effects[key]=q
        if len(effects)>1:
            # Foundation declarations alone are not proof of independent value.
            blockers.append('OVERLAP_NOT_QUALIFIED: distinct effects require a future governed independence provider')
        if blockers:return {'status':'NOT_SAFELY_AGGREGATABLE','low':None,'high':None,'blockers':tuple(sorted(set(blockers))),'origin':origin,'dimension':dimension}
        with localcontext() as ctx:
            ctx.prec=precision([v for q in effects.values() for v in (q.low,q.high,q.central) if v is not None])
            return {'status':'TOTAL','low':sum((q.low for q in effects.values()),Decimal(0)),
                'high':sum((q.high for q in effects.values()),Decimal(0)),
                'central':sum((q.central for q in effects.values()),Decimal(0)) if all(q.central is not None for q in effects.values()) else None,'origin':origin,
                'dimension':dimension,'horizon_days':qs[0].candidate.horizon_days}
