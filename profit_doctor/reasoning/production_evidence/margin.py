"""Separate exact percentage owner; registered component evidence is mandatory."""
import hashlib
from typing import Literal

from pydantic import Field, model_validator
from sqlalchemy import select, insert

from profit_doctor.persistence import production_qualification_schema as tables, measurement_schema, production_evidence_schema
from profit_doctor.reasoning.bridge.qualification import Period
from profit_doctor.reasoning.canonical.contracts import Measurement
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import Contract, Identifier, LineageReference, AuditEvent
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.measurement.contracts import MeasurementSlot, MeasurementContext
from .component import ComponentSource, ComponentBinding, binding_reasons
from .precision import exact_percentage, NON_TERMINATING


class MarginOwner(Contract):
    schema_version: Literal['MONTHLY-C0-MARGIN-2.55.1'] = 'MONTHLY-C0-MARGIN-2.55.1'
    qualification_contract: Literal['MONTHLY_CONTRIBUTION_0_MARGIN_1'] = 'MONTHLY_CONTRIBUTION_0_MARGIN_1'
    margin_id: Identifier
    series_id: Identifier
    client_id: Identifier
    run_id: Identifier
    revenue_owner_id: Identifier
    contribution_owner_id: Identifier
    binding_id: Identifier
    status: Literal['QUALIFIED', 'REFUSED']
    measurement: Measurement | None = None
    context: MeasurementContext | None = None
    reasons: tuple[str, ...] = ()
    lineage: tuple[LineageReference, ...] = Field(min_length=1)
    revision: int = Field(strict=True, ge=1)
    supersedes: Identifier | None = None
    limitations: tuple[str, ...] = ('Contribution 0 margin, not gross margin or GM-01. No rounding policy is authorised.',)

    @model_validator(mode='after')
    def owned_percentage(self):
        if (self.revision == 1) != (self.supersedes is None):
            raise ValueError('Margin revision requires its explicit predecessor')
        if any(r.client_id != self.client_id for r in self.lineage):
            raise ScopeError('Foreign margin lineage')
        for resource, identifier in (('canonical_monthly_measurement', self.revenue_owner_id),
                ('canonical_monthly_measurement', self.contribution_owner_id), ('canonical_c0_component_binding', self.binding_id)):
            if not any(r.kind == 'DERIVED_ANCESTOR' and r.store == 'CANONICAL' and r.resource == resource and
                       r.source_id == identifier for r in self.lineage):
                raise ValueError('Margin must retain both exact component owners and its binding')
        if self.status == 'REFUSED':
            if self.measurement is not None or self.context is not None or not self.reasons:
                raise ValueError('Refused margin must retain reasons without an approximate value/context')
        else:
            if self.reasons or self.measurement is None or self.context is None:
                raise ValueError('Qualified margin requires its exact measurement/context')
            m, c = self.measurement, self.context
            if c.origin_digest != hashlib.sha256(m.to_json().encode()).hexdigest():
                raise ValueError('Margin measurement disagrees with its context digest')
            if (m.metric, m.unit, m.currency, m.basis) != ('contribution_0_margin', 'PERCENTAGE', None, 'CALENDAR_MONTH'):
                raise ValueError('Margin requires percentage semantics')
            if c.origin != MeasurementSlot(store='CANONICAL', resource='canonical_monthly_c0_margin', source_id=self.margin_id, slot='derived'):
                raise ValueError('Margin context requires its distinct owner')
            if (c.client_id, c.run_id, c.unit, c.currency, c.period.basis, c.period.nature) != (
                    self.client_id, self.run_id, 'PERCENTAGE', None, 'MONTHLY', 'RATE') or c.lineage != self.lineage:
                raise ValueError('Margin context disagrees with owned semantics/lineage')
        return self


class MarginQualificationService:
    """Opt-in service. Registered-ID-only API; caller owns both transactions."""
    def __init__(self, production):
        from .service import ProductionEvidenceService
        if not isinstance(production, ProductionEvidenceService):
            raise ScopeError('Registered production evidence owner required')
        self.production = production
        self.session = production.session
        self.client_id, self.run_id = production.client_id, production.run_id
        self.sources = ComponentSource(production.connection, self.client_id, production.authority_resolver)
        self.contexts = production.contexts
        self.contexts.margins = self

    def _get(self, table, key, identifier, model):
        value = self.production._get(table, key, identifier, model)
        row = self.session.execute(select(table).where(table.c[key] == identifier)).mappings().one()
        if (value.revenue_owner_id, value.contribution_owner_id) != (row['revenue_owner_id'], row['contribution_owner_id']):
            raise ScopeError('Component identities disagree with indexed ownership')
        if model is MarginOwner and value.binding_id != row['binding_id']:
            raise ScopeError('Margin binding disagrees with indexed ownership')
        if model is MarginOwner and value.context is not None:
            if row['context_id'] != value.context.context_id:
                raise ScopeError('Margin context disagrees with indexed ownership')
        elif model is MarginOwner and row['context_id'] is not None:
            raise ScopeError('Refused margin cannot have an indexed context')
        return value

    @staticmethod
    def _revision_reasons(proof, previous):
        if previous:
            if (proof.predecessor_version_id != previous.proof_version_id or proof.revision != previous.proof.revision + 1 or
                    proof.change_kind not in ('RESTATEMENT', 'CORRECTION') or
                    proof.economic_observation_reference != previous.proof.economic_observation_reference or
                    proof.source_system_id != previous.proof.source_system_id):
                return ('COMPONENT_REVISION_AUTHORITY_REQUIRED',)
        elif proof.predecessor_version_id is not None or proof.change_kind != 'ORIGINAL':
            return ('COMPONENT_PREDECESSOR_REQUIRED',)
        return ()

    def _root_reasons(self, proof, revenue, contribution):
        roots = set()
        versions = self.production.connection.execute('''SELECT v.dataset_version_id FROM dataset_version v
            JOIN dataset d ON d.dataset_id=v.dataset_id WHERE d.client_id=? AND d.logical_dataset_key=?
            AND v.ingestion_status='COMPLETED' ''', (self.client_id, 'production-evidence:c0-component-manifest-1')).fetchall()
        for (version,) in versions:
            candidate, _, _ = self.sources.proof(version)
            if candidate.scope != proof.scope or candidate.source_system_id != proof.source_system_id or candidate.predecessor_version_id is not None:
                continue
            owners = dict(self.session.execute(select(production_evidence_schema.monthly.c.measurement_id,
                production_evidence_schema.monthly.c.series_id).where(production_evidence_schema.monthly.c.client_id == self.client_id,
                production_evidence_schema.monthly.c.measurement_id.in_((candidate.revenue_owner_id, candidate.contribution_owner_id)))).all())
            if (owners.get(candidate.revenue_owner_id), owners.get(candidate.contribution_owner_id)) == (revenue.series_id, contribution.series_id):
                roots.add(version)
        return () if len(roots) == 1 else ('COMPONENT_SOURCE_ROOT_AMBIGUOUS',)

    def get_binding(self, identifier, *, current=False):
        value = self._get(tables.binding, 'binding_id', identifier, ComponentBinding)
        if current:
            self.production._require_latest(tables.binding, value)
            revenue = self.production.get_monthly(value.revenue_owner_id, current=True)
            contribution = self.production.get_monthly(value.contribution_owner_id, current=True)
            proof, row, authority = self.sources.proof(value.proof_version_id)
            previous = self.get_binding(value.supersedes) if value.supersedes else None
            reasons = tuple(sorted(set((*binding_reasons(proof, authority, revenue, contribution, self.production.connection),
                *self._revision_reasons(proof, previous), *self._root_reasons(proof, revenue, contribution)))))
            if proof != value.proof or row['file_hash'] != value.proof_digest or reasons != value.reasons or (authority or 'UNKNOWN') != value.source_authority:
                raise RevisionConflict('Component binding no longer matches qualified retained source evidence')
        return value

    def _audit(self, value, key):
        owner = getattr(value, key)
        event = AuditEvent(event_id=identity('production-qualification-audit', owner), object_id=owner,
            client_id=self.client_id, run_id=self.run_id, event_type='OBJECT_CREATED', actor=self.production.actor,
            previous={'supersedes': value.supersedes} if value.supersedes else None,
            new={'owner': owner, 'revision': value.revision, 'status': value.status}, lineage=value.lineage,
            rationale={'qualification_contract': value.qualification_contract, 'reasons': list(value.reasons)})
        self.session.execute(insert(tables.audit).values(event_id=event.event_id, client_id=self.client_id,
            **{key: owner}, created_at=event.created_at.isoformat(), document=event.to_json()))

    def bind(self, proof_version_id):
        proof, row, authority = self.sources.proof(proof_version_id)
        revenue = self.production.get_monthly(proof.revenue_owner_id, current=True)
        contribution = self.production.get_monthly(proof.contribution_owner_id, current=True)
        reasons = list(binding_reasons(proof, authority, revenue, contribution, self.production.connection))
        reasons.extend(self._root_reasons(proof, revenue, contribution))
        series = identity('c0-component-series', revenue.series_id, contribution.series_id)
        old_id = self.production._latest(tables.binding, 'binding_id', series)
        old = self.get_binding(old_id) if old_id else None
        lineage = tuple(dict.fromkeys((*revenue.lineage, *contribution.lineage, *self.sources.refs(proof_version_id, row))))
        if old and old.proof_version_id == proof_version_id and old.proof == proof and old.source_authority == (authority or 'UNKNOWN'):
            self.get_binding(old.binding_id, current=True)
            return old
        reasons.extend(self._revision_reasons(proof, old))
        reasons = tuple(sorted(set(reasons)))
        revision = old.revision + 1 if old else 1
        value = ComponentBinding(binding_id=identity('c0-component-binding', series, proof_version_id, row['file_hash'], revision, reasons),
            series_id=series, client_id=self.client_id, run_id=self.run_id, revenue_owner_id=revenue.measurement_id,
            contribution_owner_id=contribution.measurement_id, proof_version_id=proof_version_id, proof_digest=row['file_hash'], proof=proof,
            source_authority=authority or 'UNKNOWN', status='REFUSED' if reasons else 'QUALIFIED', reasons=reasons,
            lineage=lineage, revision=revision, supersedes=old.binding_id if old else None)
        self.session.execute(insert(tables.binding).values(binding_id=value.binding_id, series_id=series, client_id=self.client_id,
            run_id=self.run_id, revenue_owner_id=value.revenue_owner_id, contribution_owner_id=value.contribution_owner_id,
            revision=revision, supersedes=value.supersedes, document=value.to_json()))
        self._audit(value, 'binding_id')
        return value

    def qualify(self, binding_id):
        binding = self.get_binding(binding_id, current=True)
        revenue = self.production.get_monthly(binding.revenue_owner_id, current=True)
        contribution = self.production.get_monthly(binding.contribution_owner_id, current=True)
        reasons = list(binding.reasons)
        percentage = None
        # Semantic eligibility precedes arithmetic. No asserted margin input.
        if not reasons:
            try:
                percentage = exact_percentage(contribution.measurement.value, revenue.measurement.value)
            except ValueError as error:
                if str(error) not in (NON_TERMINATING, 'POSITIVE_REVENUE_REQUIRED'):
                    raise
                reasons.append(str(error))
        series = identity('monthly-c0-margin-series', revenue.series_id, contribution.series_id)
        old_id = self.production._latest(tables.margin, 'margin_id', series)
        old = self.get_margin(old_id) if old_id else None
        if old and old.binding_id == binding_id:
            self.get_margin(old.margin_id, current=True)
            return old
        revision = old.revision + 1 if old else 1
        mid = identity('monthly-c0-margin', series, binding.binding_id, revision)
        refs = tuple(dict.fromkeys((*binding.lineage,
            LineageReference(kind='DERIVED_ANCESTOR', store='CANONICAL', resource='canonical_monthly_measurement', source_id=revenue.measurement_id, client_id=self.client_id, run_id=revenue.run_id),
            LineageReference(kind='DERIVED_ANCESTOR', store='CANONICAL', resource='canonical_monthly_measurement', source_id=contribution.measurement_id, client_id=self.client_id, run_id=contribution.run_id),
            LineageReference(kind='DERIVED_ANCESTOR', store='CANONICAL', resource='canonical_c0_component_binding', source_id=binding_id, client_id=self.client_id, run_id=binding.run_id))))
        measurement = context = None
        if percentage is not None:
            measurement = Measurement(metric='contribution_0_margin', value=percentage, unit='PERCENTAGE', basis='CALENDAR_MONTH')
            period = revenue.context.period
            context = MeasurementContext(client_id=self.client_id, run_id=self.run_id,
                origin=MeasurementSlot(store='CANONICAL', resource='canonical_monthly_c0_margin', source_id=mid, slot='derived'),
                origin_digest=hashlib.sha256(measurement.to_json().encode()).hexdigest(), metric='contribution_0_margin',
                unit='PERCENTAGE', economic_basis='CONTRIBUTION_0_DIVIDED_BY_BOUND_NET_REVENUE',
                entity_type=revenue.context.entity_type, entity_id=revenue.context.entity_id, segment_scope=revenue.context.segment_scope,
                period=Period(start=period.start, end=period.end, basis='MONTHLY', nature='RATE'), coverage='COMPLETE',
                coverage_basis='SOURCE_SUPPORTED_EXACT_COMPONENT_EQUIVALENCE', source_version=revenue.context.source_version,
                lineage=refs, source_locator=binding.proof.relationship_reference, capture_method='QUALIFIED_C0_MARGIN_V255',
                supersedes=old.context.context_id if old and old.context else None,
                limitations=('Own monthly C0 percentage owner; never gross margin or rolling GM-01.',))
        value = MarginOwner(margin_id=mid, series_id=series, client_id=self.client_id, run_id=self.run_id,
            revenue_owner_id=revenue.measurement_id, contribution_owner_id=contribution.measurement_id, binding_id=binding_id,
            status='REFUSED' if reasons else 'QUALIFIED', reasons=tuple(reasons), measurement=measurement, context=context,
            lineage=refs, revision=revision, supersedes=old.margin_id if old else None)
        if context:
            self.session.execute(insert(measurement_schema.measurement_context).values(context_id=context.context_id, client_id=self.client_id,
                run_id=self.run_id, supersedes=context.supersedes, document=context.to_json()))
            self.contexts._audit(context)
        self.session.execute(insert(tables.margin).values(margin_id=mid, series_id=series, client_id=self.client_id,
            run_id=self.run_id, revenue_owner_id=value.revenue_owner_id, contribution_owner_id=value.contribution_owner_id,
            binding_id=binding_id, context_id=context.context_id if context else None, revision=revision,
            supersedes=value.supersedes, document=value.to_json()))
        if context:
            self.contexts._bind(context, context.origin)
        self._audit(value, 'margin_id')
        return value

    def get_margin(self, identifier, *, current=False):
        value = self._get(tables.margin, 'margin_id', identifier, MarginOwner)
        if current:
            self.production._require_latest(tables.margin, value)
            binding = self.get_binding(value.binding_id, current=True)
            revenue = self.production.get_monthly(binding.revenue_owner_id, current=True)
            contribution = self.production.get_monthly(binding.contribution_owner_id, current=True)
            expected = None
            reasons = list(binding.reasons)
            if not reasons:
                try:
                    expected = exact_percentage(contribution.measurement.value, revenue.measurement.value)
                except ValueError as error:
                    if str(error) not in (NON_TERMINATING, 'POSITIVE_REVENUE_REQUIRED'):
                        raise
                    reasons.append(str(error))
            if tuple(reasons) != value.reasons or (value.measurement.value if value.measurement else None) != expected:
                raise RevisionConflict('Margin no longer matches current source-qualified components')
        return value

    def owner(self, identifier):
        value = self.get_margin(identifier, current=True)
        if value.status != 'QUALIFIED':
            raise ScopeError('Refused margin has no qualified measurement context')
        return value.model_dump(mode='json'), value.measurement.value, value.measurement.unit.value
