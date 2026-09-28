"""Canonical v2.43 contract semantics, independent of the legacy runtime."""
from datetime import datetime, timezone
from decimal import Decimal
import json
import unittest

from pydantic import TypeAdapter, ValidationError

from profit_doctor.reasoning.domain import vocabulary as v
from profit_doctor.reasoning.domain.compatibility import LegacyObservation
from profit_doctor.reasoning.domain.contracts import (
    Actor, AuditEvent, ConfidenceProfile, EconomicEffect, EffectOverlap,
    EvidenceLink, LineageReference, MaterialityProfile, ReasoningObject,
)

T = datetime(2026, 9, 28, tzinfo=timezone.utc)


def obj(**changes):
    fields = dict(client_id='c1', run_id='r1', object_type='FACT',
                  source_authority='SYSTEM_DERIVED', created_at=T)
    fields.update(changes)
    return ReasoningObject(**fields)


class ReasoningContractsV243(unittest.TestCase):
    def test_unique_typed_versioned_identity_and_scope(self):
        first, second = obj(), obj()
        self.assertNotEqual(first.object_id, second.object_id)
        self.assertEqual(v.ObjectType.FACT, first.object_type)
        self.assertEqual(('c1', 'r1', 'RDF-2.43'), (first.client_id, first.run_id, first.schema_version))
        self.assertEqual(first, ReasoningObject.from_json(first.to_json()))
        with self.assertRaises(ValidationError):
            obj(schema_version='future')

    def test_every_enum_round_trips_and_rejects_unknown_values(self):
        enums = [value for value in vars(v).values()
                 if isinstance(value, type) and issubclass(value, v.StrEnum) and value is not v.StrEnum]
        self.assertEqual(18, len(enums))
        for enum in enums:
            for value in enum:
                with self.subTest(enum=enum.__name__, value=value):
                    adapter = TypeAdapter(enum)
                    self.assertIs(value, adapter.validate_json(adapter.dump_json(value)))
            with self.assertRaises(ValidationError):
                TypeAdapter(enum).validate_python('UNRECOGNISED')

    def test_all_object_types_are_distinct_and_no_automatic_status(self):
        self.assertEqual(13, len(v.ObjectType))
        for value in v.ObjectType:
            instance = obj(object_type=value)
            self.assertEqual(value, ReasoningObject.from_json(instance.to_json()).object_type)
            self.assertIsNone(instance.status)

    def test_statuses_are_namespaced_not_legacy_translations(self):
        for kind, status in [('FINDING', 'DETECTED'), ('HYPOTHESIS', 'SUPPORTED'),
                             ('INTERPRETATION', 'PLAUSIBLE'), ('ECONOMIC_STORY', 'INVESTIGATING'),
                             ('OPPORTUNITY_CANDIDATE', 'CANDIDATE'), ('VALIDATED_OPPORTUNITY', 'VALIDATED'),
                             ('ACTION', 'NOT_STARTED'), ('BENEFIT_RECORD', 'ATTRIBUTION_TESTING')]:
            self.assertEqual(status, obj(object_type=kind, status=status).status)
        for kind, status in [('FACT', 'VALIDATED'), ('FINDING', 'ACCEPTED'),
                             ('ECONOMIC_STORY', 'OPEN'), ('OPPORTUNITY_CANDIDATE', 'QUALIFIED'),
                             ('VALIDATED_OPPORTUNITY', 'SUPPORTED'), ('ACTION', 'OPEN'),
                             ('BENEFIT_RECORD', 'REALISED'), ('FINDING', 'IN_PROGRESS')]:
            with self.subTest(kind=kind, status=status), self.assertRaises(ValidationError):
                obj(object_type=kind, status=status)

    def test_deterministic_serialization_preserves_metadata_and_rejects_duplicates(self):
        a = ConfidenceProfile(rationale={'z': [1, 'evidence'], 'a': {'b': True}})
        b = ConfidenceProfile(rationale={'a': {'b': True}, 'z': [1, 'evidence']})
        self.assertEqual(a.to_json(), b.to_json())
        self.assertEqual(a, ConfidenceProfile.from_json(a.to_json()))
        with self.assertRaises(ValueError):
            ConfidenceProfile.from_json('{"data_confidence":"LOW","data_confidence":"HIGH"}')
        with self.assertRaises(ValidationError):
            ConfidenceProfile(score=99)

    def test_confidence_dimensions_remain_independent(self):
        profile = ConfidenceProfile(data_confidence='HIGH', attribution_confidence='LOW',
                                    interpretation_confidence=None)
        self.assertEqual(v.ConfidenceLevel.HIGH, profile.data_confidence)
        self.assertEqual(v.ConfidenceLevel.LOW, profile.attribution_confidence)
        self.assertIsNone(profile.interpretation_confidence)
        self.assertEqual(v.ConfidenceLevel.NOT_ASSESSED, profile.opportunity_confidence)
        self.assertEqual(profile, ConfidenceProfile.from_json(profile.to_json()))
        self.assertNotIn('score', ConfidenceProfile.model_fields)

    def test_materiality_precision_and_optional_vector(self):
        precise = Decimal('123456789012345678901234567890.12345678901234567890')
        p = MaterialityProfile(absolute_economic_magnitude=precise, currency='GBP',
                              cash_impact='-0.000000000000000001', percentage_of_revenue='12.3400',
                              urgency='HIGH', controllability='LOW')
        q = MaterialityProfile.from_json(p.to_json())
        self.assertEqual(precise.as_tuple(), q.absolute_economic_magnitude.as_tuple())
        self.assertEqual(Decimal('12.3400').as_tuple(), q.percentage_of_revenue.as_tuple())
        self.assertEqual(v.AssessmentLevel.HIGH, q.urgency)
        self.assertEqual(v.AssessmentLevel.LOW, q.controllability)
        self.assertIsNone(q.percentage_of_ebitda)
        self.assertEqual(v.AssessmentLevel.NOT_ASSESSED, q.persistence)
        self.assertNotIn('score', MaterialityProfile.model_fields)

    def test_materiality_refuses_float_nonfinite_and_currencyless_money(self):
        for value in [0.1, True, 'NaN', 'Infinity', '-Infinity']:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                MaterialityProfile(cash_impact=value, currency='GBP')
        with self.assertRaises(ValidationError):
            MaterialityProfile(cash_impact='1')
        with self.assertRaises(ValidationError):
            MaterialityProfile(universal_score='HIGH')

    def test_links_preserve_relationship_role_and_provenance(self):
        ref = LineageReference(kind='SOURCE_FILE', store='LEGACY_SQLITE', resource='source_file',
                               source_id='sha256-existing', client_id='c1')
        link = EvidenceLink(client_id='c1', source_id='one', target_id='two',
                            relationship_type='POTENTIALLY_DRIVES', evidence_role='DRIVER_CANDIDATE',
                            source_authority='SOURCE_DATA', lineage=(ref,), metadata={'ids': ['a', 'b']})
        self.assertEqual(link, EvidenceLink.from_json(link.to_json()))
        self.assertNotEqual(v.RelationshipType.POTENTIALLY_DRIVES, v.RelationshipType.SUPPORTED_DRIVER_OF)
        self.assertNotIn('causal', link.model_dump())

    def test_self_links_and_missing_endpoints_are_rejected(self):
        fields = dict(client_id='c1', source_id='one', relationship_type='SUPPORTS',
                      source_authority='SYSTEM_DERIVED')
        with self.assertRaises(ValidationError):
            EvidenceLink(**fields)
        for relationship in v.RelationshipType:
            with self.subTest(relationship=relationship), self.assertRaises(ValidationError):
                EvidenceLink(**(fields | {'relationship_type': relationship}), target_id='one')
        with self.assertRaises(ValidationError):
            EvidenceLink(**fields, target_id='')

    def test_management_assertion_is_not_system_evidence(self):
        management = obj(source_authority='MANAGEMENT_ASSERTION')
        system = obj()
        self.assertNotEqual(management.source_authority, system.source_authority)
        self.assertEqual(v.SourceAuthority.MANAGEMENT_ASSERTION,
                         ReasoningObject.from_json(management.to_json()).source_authority)
        self.assertEqual(ConfidenceProfile(), management.confidence)

    def test_shared_ancestry_survives_serialization(self):
        ref = LineageReference(kind='CANONICAL_RECORD', store='LEGACY_SQLITE',
                               resource='transaction_line', source_id='existing-row', client_id='c1')
        a, b = obj(lineage=(ref,)), obj(lineage=(ref,))
        self.assertEqual(ReasoningObject.from_json(a.to_json()).lineage,
                         ReasoningObject.from_json(b.to_json()).lineage)
        self.assertNotEqual(a.object_id, b.object_id)

    def test_entity_period_timestamps_and_tenant_validation(self):
        entity = LineageReference(kind='ENTITY', store='LEGACY_SQLITE', resource='entity',
                                  source_id='existing-entity', client_id='c1')
        a = obj(entity=entity, period_from='2026-01-01', period_to='2026-12-31')
        self.assertEqual(a, ReasoningObject.from_json(a.to_json()))
        for changes in [dict(period_from='2026-12-31', period_to='2026-01-01'),
                        dict(created_at='2026-09-28T00:00:00'),
                        dict(updated_at='2020-01-01T00:00:00Z'),
                        dict(lineage=(entity.model_copy(update={'client_id': 'c2'}),)),
                        dict(object_id=''), dict(revision=True)]:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                obj(**changes)

    def test_effect_identity_and_overlap_do_not_compute_amounts(self):
        effect = EconomicEffect(client_id='c1')
        self.assertEqual(effect, EconomicEffect.from_json(effect.to_json()))
        self.assertNotEqual(effect.effect_id, obj(object_type='ECONOMIC_STORY').object_id)
        for overlap in v.OverlapType:
            relationship = EffectOverlap(client_id='c1', source_effect_id='a', target_effect_id='b', overlap_type=overlap)
            self.assertEqual(overlap, EffectOverlap.from_json(relationship.to_json()).overlap_type)
        with self.assertRaises(ValidationError):
            EffectOverlap(client_id='c1', source_effect_id='a', target_effect_id='a', overlap_type='SAME_EFFECT')
        self.assertNotIn('amount', effect.model_dump())

    def test_impact_profit_cash_risk_and_realised_are_distinct(self):
        bases = [v.ImpactBasis.RECURRING_PROFIT, v.ImpactBasis.ONE_OFF_PROFIT, v.ImpactBasis.CASH_RELEASE,
                 v.ImpactBasis.BALANCE_SHEET_EXPOSURE, v.ImpactBasis.FUTURE_RISK_EXPOSURE,
                 v.ImpactBasis.REALISED_BENEFIT]
        self.assertEqual(6, len(set(bases)))
        for impact in v.ImpactType:
            a = obj(object_type='ECONOMIC_IMPACT', impact_type=impact, impact_basis='NOT_ASSESSED')
            self.assertEqual(a, ReasoningObject.from_json(a.to_json()))
        with self.assertRaises(ValidationError):
            obj(object_type='ECONOMIC_IMPACT', impact_type='REV')
        with self.assertRaises(ValidationError):
            obj(impact_type='CASH_TRAPPED')

    def test_audit_before_after_and_human_override(self):
        actor = Actor(actor_type='HUMAN', source_authority='HUMAN_FD_JUDGEMENT', actor_id='fd-1')
        audit = AuditEvent(client_id='c1', object_id='o1', event_type='HUMAN_OVERRIDE_RECORDED',
                           actor=actor, previous={'status': 'TESTING'}, new={'status': 'UNRESOLVED'},
                           rationale={'evidence_ids': ['ref-1']})
        self.assertEqual(audit, AuditEvent.from_json(audit.to_json()))
        self.assertEqual('TESTING', audit.previous['status'])
        with self.assertRaises(ValidationError):
            AuditEvent(client_id='c1', object_id='o1', event_type='MANAGEMENT_ASSERTION_RECORDED', actor=actor)
        with self.assertRaises(ValidationError):
            AuditEvent(client_id='c1', event_type='OBJECT_CREATED', actor=actor)

    def test_legacy_adapter_preserves_ambiguous_values_without_promotion(self):
        ref = LineageReference(kind='DERIVED_ANCESTOR', store='LEGACY_SQLITE', resource='finding',
                               source_id='existing-id', client_id='c1')
        for status in ['ACCEPTED', 'OPEN', 'QUALIFIED', 'SUPPORTED', 'REALISED', 'REV']:
            old = LegacyObservation(source=ref, legacy_type='legacy', legacy_status=status,
                                    legacy_confidence='HIGH', legacy_materiality='HIGH', original_fields={'value': '1.2300'})
            recovered = LegacyObservation.from_json(old.to_json())
            self.assertEqual(status, recovered.legacy_status)
            self.assertEqual('UNRESOLVED', recovered.conversion_state)
            self.assertEqual(v.SourceAuthority.LEGACY_UNCLASSIFIED, recovered.source_authority)
            self.assertNotIn('status', recovered.model_dump())
            self.assertNotIn('confidence', recovered.model_dump())
            self.assertNotIn('materiality', recovered.model_dump())


if __name__ == '__main__':
    unittest.main()
