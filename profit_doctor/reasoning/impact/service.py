"""Explicit assessments, immutable history and fail-closed totals.

No legacy caller is switched. The caller owns Session/transaction/resources.
Synthetic evidence providers are qualification-only trusted fixture owners, not
production authority adapters. There is intentionally no production positive path.
"""
import json
from decimal import Decimal, localcontext

from sqlalchemy import insert, select
from profit_doctor.persistence import impact_schema as tables, reasoning_schema as foundation_tables
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.domain.contracts import (
    EconomicEffect, EffectReference, ReasoningObject, LineageReference,
    MaterialityProfile, ConfidenceProfile, now,
)
from profit_doctor.reasoning.domain.service import FoundationService, ScopeError, RevisionConflict
from profit_doctor.reasoning.domain.vocabulary import ImpactType, OverlapType
from .contracts import (Source, SyntheticBasis, Qualification, QualifiedImpact, ImpactAmount,
                        Outcome, Dimension, DIMENSIONS, Aggregation, precision)
from .registry import REGISTRY


class ImpactService:
    def __init__(self, foundation: FoundationService, run_id, *, bridges=None, synthetic_resolver=None,
                 synthetic_overlap_resolver=None, receivables=None):
        self.foundation = foundation
        self.session = foundation.session
        self.client_id = foundation.client_id
        self.run_id = run_id
        self.bridges = bridges
        self.synthetic_resolver = synthetic_resolver
        self.synthetic_overlap_resolver = synthetic_overlap_resolver
        self.receivables = receivables
        if receivables is not None:
            from profit_doctor.reasoning.receivables.service import ReceivablesService
            if not isinstance(receivables, ReceivablesService) or (receivables.session is not self.session or
                    (receivables.client_id, receivables.run_id) != (self.client_id, self.run_id)):
                raise ScopeError('Receivables owner must share caller transaction and scope')
        foundation._run(run_id)
        if bridges is not None and (bridges.session is not self.session or
                bridges.contexts.client_id != self.client_id or bridges.contexts.run_id != run_id):
            raise ScopeError('Bridge owner must share the caller transaction and scope')

    def _resolve(self, source):
        if source.kind == 'RECEIVABLES':
            if self.receivables is None: raise ScopeError('Governed receivables provider required')
            value = self.receivables.latest(source.source_id)
            for invoice in value.invoices:
                from profit_doctor.reasoning.measurement.contracts import MeasurementSlot
                owner = MeasurementSlot(store='CANONICAL',resource='canonical_receivable_invoice',
                    source_id=self.receivables.owner_id(value,invoice),slot='amount')
                binding = self.receivables.contexts.lookup(owner)
                self.receivables.contexts.resolve_binding(binding.binding_id)
            return value.to_json(), None
        if source.kind == 'SYNTHETIC':
            if self.synthetic_resolver is None:
                raise ScopeError('Explicit synthetic fixture resolver required')
            value = self.synthetic_resolver(source.source_id)
            value = SyntheticBasis.from_json(value.to_json())
            if (value.fixture_key, value.client_id, value.run_id) != (source.source_id, self.client_id, self.run_id):
                raise ScopeError('Synthetic fixture identity/scope mismatch')
            return value.to_json(), None
        if source.kind == 'BRIDGE':
            if self.bridges is None:
                raise ScopeError('Authoritative Bridge service required')
            value = self.bridges.get(source.source_id)
            if value.run_id != self.run_id:
                raise ScopeError('Source run differs from assessment run')
            try:
                self.bridges.get(source.source_id, current=True)
            except RevisionConflict:
                return value.to_json(), 'SOURCE_STALE_REASSESSMENT_REQUIRED'
            return value.to_json(), None
        value = self.foundation.get_object(source.source_id)
        if value.run_id != self.run_id:
            raise ScopeError('Source run differs from assessment run')
        if value.confidence.rationale.get('evidence_domain') == 'SYNTHETIC' or value.materiality.rationale.get('evidence_domain') == 'SYNTHETIC':
            raise ScopeError('Synthetic foundation evidence cannot be relabelled as a production candidate')
        # An identity/envelope is not a proof of analytical classification.
        return value.to_json(), ('SOURCE_AUTHORITY_NOT_VERIFIED' if value.source_authority != 'SYSTEM_DERIVED' else None)

    def _latest(self, candidate_id):
        return self.session.execute(select(tables.qualification).where(
            tables.qualification.c.candidate_id == candidate_id,
            tables.qualification.c.client_id == self.client_id)
            .order_by(tables.qualification.c.revision.desc()).limit(1)).mappings().one_or_none()

    def _assessment(self, source, category, candidate_id, revision):
        document, held = self._resolve(source)
        contract = REGISTRY[category]
        domain = 'SYNTHETIC' if source.kind == 'SYNTHETIC' else 'PRODUCTION'
        result = dict(candidate_id=candidate_id, revision=revision, client_id=self.client_id,
            run_id=self.run_id, source=source, source_document=document, domain=domain,
            category=category, outcome=Outcome.HELD if held else Outcome.INSUFFICIENT_EVIDENCE,
            available=('Resolved source identity and retained source snapshot',),
            missing=(contract.required_evidence,), required_counterfactual=contract.counterfactual,
            blockers=(held or 'NO_QUALIFIED_PRODUCTION_IMPACT_CONTRACT',))
        if source.kind == 'REASONING':
            refs = self.session.execute(select(foundation_tables.effect_reference.c.effect_id).where(
                foundation_tables.effect_reference.c.object_id == source.source_id,
                foundation_tables.effect_reference.c.client_id == self.client_id)).scalars().all()
            result['effect_ids'] = tuple(sorted(set(refs)))
            for key in result['effect_ids']:
                self.foundation.get_effect(key)
        if source.kind == 'RECEIVABLES' and category == ImpactType.CASH_TRAPPED:
            from .receivables import qualify
            result.update(qualify(document, candidate_id, revision))
        if source.kind == 'SYNTHETIC' and category == ImpactType.CASH_TRAPPED:
            basis = SyntheticBasis.from_json(document)
            with localcontext() as ctx:
                ctx.prec = precision((basis.observed, basis.counterfactual.required))
                amount = basis.observed - basis.counterfactual.required
            if amount <= 0:
                result.update(outcome=Outcome.NOT_APPLICABLE, missing=(), blockers=('NO_POSITIVE_EXCESS',))
            else:
                # The identity is the economic scope, never the describing fixture/diagnostic.
                effect_id = identity('impact-effect', domain, self.client_id, basis.consequence_key,
                    basis.metric, basis.scope, basis.as_of.isoformat(), basis.currency)
                impact_id = identity('qualified-impact', candidate_id, revision, document)
                impact = QualifiedImpact(impact_id=impact_id, candidate_id=candidate_id, revision=revision,
                    client_id=self.client_id, run_id=self.run_id, effect_id=effect_id,
                    amount=ImpactAmount(value=amount, observed=basis.observed, counterfactual=basis.counterfactual,
                        as_of=basis.as_of, scope=basis.scope, coverage=basis.coverage),
                    confidence=ConfidenceProfile(quantification_confidence='HIGH',
                        rationale={'evidence_domain': 'SYNTHETIC', 'quantification_confidence': 'Exact synthetic fixture arithmetic only; no production attribution assessed'}),
                    materiality=MaterialityProfile(absolute_economic_magnitude=amount, cash_impact=amount, currency='GBP',
                        rationale={'evidence_domain': 'SYNTHETIC'}),
                    limitations=basis.limitations + ('No recoverability, addressability or Opportunity value established.',))
                result.update(outcome=Outcome.QUALIFIED_IMPACT, missing=(), blockers=(),
                              effect_ids=(effect_id,), impact=impact)
        return Qualification(**result)

    def assess(self, source: Source, category, *, expected_revision=None):
        source = Source.from_json(source.to_json())
        category = ImpactType(category)  # Unknown vocabulary has no fallback.
        candidate_id = identity('impact-candidate', self.client_id, self.run_id, source.kind,
                                source.source_id, category.value, 'IC-2.49.1')
        old = self._latest(candidate_id)
        revision = old['revision'] if old else 1
        proposed = self._assessment(source, category, candidate_id, revision)
        if old:
            previous = self.get(candidate_id)
            if previous == proposed:
                return previous
            if expected_revision != revision:
                raise RevisionConflict('Changed evidence requires explicit current assessment revision')
            proposed = self._assessment(source, category, candidate_id, revision + 1)
        elif expected_revision is not None:
            raise RevisionConflict('New candidate has no previous revision')
        # Semantic checks precede writes; a savepoint prevents partial new state
        # on an integrity failure while the outer transaction stays caller-owned.
        connection = self.session.connection()
        if connection.dialect.name == 'sqlite' and not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql('BEGIN')
        with self.session.begin_nested():
            self.session.execute(insert(tables.qualification).values(candidate_id=candidate_id,
                revision=proposed.revision, client_id=self.client_id, run_id=self.run_id,
                bridge_id=source.source_id if source.kind == 'BRIDGE' else None,
                source_object_id=source.source_id if source.kind == 'REASONING' else None,
                document=proposed.to_json()))
            if source.kind == 'RECEIVABLES':
                from profit_doctor.persistence.receivables_schema import impact_source
                self.session.execute(insert(impact_source).values(candidate_id=candidate_id,revision=proposed.revision,
                    client_id=self.client_id,snapshot_id=self.receivables.latest(source.source_id).snapshot_id))
            if proposed.impact:
                i = proposed.impact
                t = foundation_tables.economic_effect
                existing = self.session.scalar(select(t.c.effect_id).where(t.c.effect_id == i.effect_id))
                if existing:
                    self.foundation.get_effect(existing)
                else:
                    self.foundation.create_effect(EconomicEffect(effect_id=i.effect_id, client_id=self.client_id,
                        period_from=i.amount.as_of, period_to=i.amount.as_of))
                lineage = (LineageReference(kind='ANALYTICAL_RUN', store='SQLALCHEMY', resource='engine_run',
                    source_id=self.run_id, client_id=self.client_id, run_id=self.run_id),)
                self.foundation.create_object(ReasoningObject(object_id=i.impact_id, object_type='ECONOMIC_IMPACT',
                    source_authority='SYSTEM_DERIVED', client_id=self.client_id, run_id=self.run_id,
                    period_from=i.amount.as_of, period_to=i.amount.as_of, lineage=lineage,
                    impact_type=i.category, impact_basis='BALANCE_SHEET_EXPOSURE', confidence=i.confidence, materiality=i.materiality))
                self.foundation.reference_effect(EffectReference(client_id=self.client_id, run_id=self.run_id,
                    object_id=i.impact_id, effect_id=i.effect_id))
                self.session.execute(insert(tables.impact).values(impact_id=i.impact_id, client_id=self.client_id,
                    candidate_id=candidate_id, revision=i.revision, effect_id=i.effect_id, document=i.to_json()))
                if source.kind == 'RECEIVABLES':
                    from .receivables import link_aggregate
                    link_aggregate(self.foundation, i)
            self.session.execute(insert(tables.audit).values(event_id=identity('impact-qualification-audit', candidate_id, proposed.revision),
                candidate_id=candidate_id, revision=proposed.revision, client_id=self.client_id, created_at=now().isoformat(),
                document=json.dumps({'event_type': 'OBJECT_UPDATED' if old else 'OBJECT_CREATED',
                    'actor': self.foundation.actor.model_dump(mode='json'), 'previous': old['document'] if old else None,
                    'new': proposed.to_json(), 'reason': 'Explicit versioned Impact qualification; prior assessment remains historical'}, sort_keys=True)))
        return proposed

    def get(self, candidate_id, revision=None, *, current=False):
        if revision is None:
            row = self._latest(candidate_id)
        else:
            row = self.session.execute(select(tables.qualification).where(
                tables.qualification.c.candidate_id == candidate_id, tables.qualification.c.revision == revision,
                tables.qualification.c.client_id == self.client_id)).mappings().one_or_none()
        if row is None:
            raise ScopeError('Candidate missing or foreign')
        q = Qualification.from_json(row['document'])
        if (q.candidate_id, q.revision, q.client_id, q.run_id) != (row['candidate_id'], row['revision'], row['client_id'], row['run_id']):
            raise ScopeError('Qualification envelope mismatch')
        if (row['bridge_id'], row['source_object_id']) != (
            q.source.source_id if q.source.kind == 'BRIDGE' else None,
            q.source.source_id if q.source.kind == 'REASONING' else None):
            raise ScopeError('Qualification source FK mismatch')
        from profit_doctor.reasoning.receivables.contracts import Snapshot
        expected_ar = Snapshot.from_json(q.source_document).snapshot_id if q.source.kind == 'RECEIVABLES' else None
        from profit_doctor.persistence.receivables_schema import impact_source
        actual_ar = self.session.scalar(select(impact_source.c.snapshot_id).where(
            impact_source.c.candidate_id == q.candidate_id, impact_source.c.revision == q.revision,
            impact_source.c.client_id == self.client_id))
        if actual_ar != expected_ar: raise ScopeError('Receivables source FK mismatch')
        if q.impact:
            i = q.impact
            stored = self.session.execute(select(tables.impact).where(tables.impact.c.impact_id == i.impact_id,
                tables.impact.c.client_id == self.client_id)).mappings().one_or_none()
            if stored is None or (stored['candidate_id'], stored['revision'], stored['effect_id'], stored['document']) != (
                q.candidate_id, q.revision, i.effect_id, i.to_json()):
                raise ScopeError('Qualified Impact extension missing or inconsistent')
            obj = self.foundation.get_object(i.impact_id)
            if obj.object_type != 'ECONOMIC_IMPACT' or obj.impact_type != i.category or obj.run_id != q.run_id:
                raise ScopeError('Impact foundation identity mismatch')
            self.foundation.get_effect(i.effect_id)
            ref = self.session.scalar(select(foundation_tables.effect_reference.c.reference_id).where(
                foundation_tables.effect_reference.c.object_id == i.impact_id,
                foundation_tables.effect_reference.c.effect_id == i.effect_id))
            if ref is None:
                raise ScopeError('Missing Impact/effect reference')
            self.foundation.get_effect_reference(ref)
        if current:
            latest = self._latest(candidate_id)
            if latest['revision'] != q.revision or q.run_id != self.run_id:
                raise RevisionConflict('Historical assessment cannot enter current totals')
            if self._assessment(q.source, q.category, q.candidate_id, q.revision) != q:
                raise RevisionConflict('Evidence changed; explicit reassessment required')
        return q

    def lifecycle(self, candidate_id, revision=None):
        """Historical supersession is explicit; no automatic benefit transition."""
        q = self.get(candidate_id, revision)
        latest = self.get(candidate_id)
        if q.revision != latest.revision:
            return 'INVALIDATED' if q.impact and not latest.impact else 'SUPERSEDED'
        return 'QUANTIFIED' if q.impact else 'CANDIDATE'

    def aggregate(self, candidate_ids, *, domain, dimension, category, qualification_origin='REAL_SOURCE'):
        dimension, category = Dimension(dimension), ImpactType(category)
        if DIMENSIONS[category] != dimension:
            raise ValueError('Incompatible economic dimension/category')
        included, excluded, blockers, impacts = [], [], [], []
        for key in sorted(set(candidate_ids)):
            q = self.get(key, current=True)
            if (q.domain, q.category) != (domain, category):
                blockers.append('INCOMPATIBLE_DOMAIN_OR_CATEGORY:' + key)
            elif q.impact is None:
                excluded.append(key)
            else:
                if hasattr(q.impact.amount, 'qualification_origin') and q.impact.amount.qualification_origin != qualification_origin:
                    blockers.append('QUALIFICATION_ORIGIN_NOT_SELECTED:' + key)
                impacts.append(q.impact)
        if impacts:
            origins = {getattr(i.amount, 'qualification_origin', i.domain) for i in impacts}
            if len(origins) != 1: blockers.append('INCOMPATIBLE_QUALIFICATION_ORIGIN')
            signatures = {(i.amount.as_of, i.amount.scope, i.amount.currency, i.amount.basis, i.amount.coverage) for i in impacts}
            if len(signatures) != 1:
                blockers.append('INCOMPATIBLE_PERIOD_SCOPE_BASIS_OR_COVERAGE')
        # Deduplicate only exact valuations of the same effect; never choose a
        # favourable valuation or silently add conflicting views.
        unique = {}
        for i in impacts:
            if i.effect_id in unique and unique[i.effect_id].amount != i.amount:
                blockers.append('CONFLICTING_SAME_EFFECT_VALUATION')
            else:
                unique.setdefault(i.effect_id, i)
        items = sorted(unique.values(), key=lambda i: i.effect_id)
        same_pairs = set()
        relations = {}
        for index, a in enumerate(items):
            for b in items[index + 1:]:
                pair = '|'.join(sorted((a.effect_id, b.effect_id)))
                t = foundation_tables.effect_overlap
                key = self.session.scalar(select(t.c.overlap_id).where(t.c.client_id == self.client_id, t.c.pair_key == pair))
                relation = OverlapType.UNKNOWN_OVERLAP
                if key:
                    declared = self.foundation.get_effect_overlap(key)
                    # Foundation relationships are declarations, not independent
                    # proof. Only the explicit fixture owner can qualify this
                    # synthetic relation; production support remains unavailable.
                    proof = self.synthetic_overlap_resolver(key) if domain == 'SYNTHETIC' and self.synthetic_overlap_resolver else None
                    if proof is not None and proof.to_json() == declared.to_json():
                        relation = declared.overlap_type
                relations[(a.effect_id, b.effect_id)] = relation
                if relation == OverlapType.SAME_EFFECT:
                    if a.amount != b.amount:
                        blockers.append('CONFLICTING_SAME_EFFECT_VALUATION')
                    same_pairs.add((a.effect_id, b.effect_id))
                elif relation != OverlapType.INDEPENDENT:
                    blockers.append(relation.value + ':' + pair)
        # SAME_EFFECT equivalence must be fully declared pairwise; unknown or
        # contradictory third-party relations above block the entire total.
        representatives = {i.effect_id: i.effect_id for i in items}
        def root(key):
            while representatives[key] != key:
                key = representatives[key]
            return key
        for a, b in sorted(same_pairs):
            representatives[root(b)] = root(a)
        for i in items:
            representative = root(i.effect_id)
            representatives[i.effect_id] = representative
            if representative == i.effect_id:
                included.append(i.impact_id)
        for (a, b), relation in relations.items():
            if representatives[a] == representatives[b] and relation == OverlapType.INDEPENDENT:
                blockers.append('CONTRADICTORY_EFFECT_EQUIVALENCE')
        if blockers:
            return Aggregation(domain=domain, dimension=dimension, category=category,
                status='NOT_SAFELY_AGGREGATABLE', excluded=tuple(excluded), blockers=tuple(sorted(set(blockers))),
                qualification_origin=qualification_origin if any(hasattr(i.amount,'qualification_origin') for i in impacts) else None)
        with localcontext() as ctx:
            ctx.prec = precision([i.amount.value for i in items] or [Decimal(0)])
            total = sum((i.amount.value for i in items if i.impact_id in included), Decimal(0))
        return Aggregation(domain=domain, dimension=dimension, category=category,
            status='TOTAL' if included else 'EMPTY', total=total if included else None,
            included=tuple(included), excluded=tuple(excluded),
            qualification_origin=qualification_origin if any(hasattr(i.amount,'qualification_origin') for i in impacts) else None)
