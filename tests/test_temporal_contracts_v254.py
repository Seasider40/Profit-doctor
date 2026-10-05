"""Adversarial temporal evidence qualification; all positives explicitly synthetic."""
from decimal import Decimal, localcontext
import unittest

from tests.temporal_evidence_v254 import basis, observation
from tests import test_dataset_contract_v253 as datasets
from profit_doctor.reasoning.dataset.contracts import DatasetAssertion, DatasetContract
from profit_doctor.reasoning.domain.contracts import ConfidenceProfile
from profit_doctor.reasoning.temporal.contracts import (
    AbsenceEvidence, ContractKey, Observation, TemporalInput, TemporalResult,
)
from profit_doctor.reasoning.temporal.engine import evaluate


AR = ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE
REV = ContractKey.REVENUE_DESCRIPTIVE_TRAJECTORY


class TemporalContractsV254(unittest.TestCase):
    def test_three_increasing_c0_observations_improve_only_qualified_definition(self):
        result = evaluate(basis())
        self.assertEqual(('QUALIFIED','INCREASING','IMPROVING'),(result.sequence,result.trajectory,result.interpretation))
        self.assertEqual('PERCENTAGE_POINT_CHANGE',result.movements[0].basis)
        self.assertEqual(Decimal('2'),result.movements[0].delta)
        self.assertNotIn('gross',result.to_json())

    def test_decreasing_c0_qualified_directionality_is_worsening(self):
        result=evaluate(basis(('32','30','28')))
        self.assertEqual(('DECREASING','WORSENING'),(result.trajectory,result.interpretation))

    def test_revenue_decrease_remains_descriptive(self):
        result=evaluate(basis(('100','90','80'),key=REV))
        self.assertEqual(('DECREASING','NOT_ASSESSED'),(result.trajectory,result.interpretation))

    def test_threshold_below_equal_above_in_both_directions_decimal_exact(self):
        for key, first, threshold in ((ContractKey.CONTRIBUTION_0_MARGIN_TRAJECTORY,Decimal('30'),Decimal('1')),
                                     (REV,Decimal('100'),Decimal('5'))):
            for sign in (-1,1):
                for offset,state in ((Decimal('-0.00000000000000000000000000001'),'WITHIN_TOLERANCE'),
                                     (Decimal('0'),'POSITIVE' if sign>0 else 'NEGATIVE'),
                                     (Decimal('0.00000000000000000000000000001'),'POSITIVE' if sign>0 else 'NEGATIVE')):
                    with self.subTest(key=key,sign=sign,offset=offset),localcontext() as ctx:
                        ctx.prec=80
                        second=first+sign*(threshold+offset)
                        result=evaluate(basis((str(first),str(second)),key=key,end=2))
                        self.assertEqual(state,result.movements[0].state)
                        self.assertEqual(second-first,result.movements[0].delta)

    def test_decimal_roundtrip_and_no_universal_score(self):
        result=evaluate(basis(('30.00000000000000000001','31.00000000000000000001','32.00000000000000000001')))
        self.assertEqual(result,TemporalResult.from_json(result.to_json()))
        self.assertEqual(ConfidenceProfile(),result.confidence)
        self.assertNotIn('score',result.to_json())

    def test_stable_checks_every_adjacent_movement(self):
        self.assertEqual('STABLE',evaluate(basis(('30','30.2','30.8'))).trajectory)

    def test_mixed_has_no_majority_voting(self):
        self.assertEqual('MIXED',evaluate(basis(('30','32','34','30'),end=4)).trajectory)

    def test_flat_interval_does_not_break_direction(self):
        self.assertEqual('INCREASING',evaluate(basis(('30','32','32','34'),end=4)).trajectory)

    def test_first_last_equal_is_not_stable(self):
        self.assertEqual('MIXED',evaluate(basis(('30','25','30'))).trajectory)

    def test_two_observations_describe_movement_without_trajectory(self):
        r=evaluate(basis(('30','32'),end=2))
        self.assertEqual(('QUALIFIED','NOT_ASSESSED','NOT_ASSESSED'),(r.sequence,r.trajectory,r.interpretation))
        self.assertEqual('POSITIVE',r.movements[0].state)

    def test_one_observation_can_sequence_without_movement(self):
        r=evaluate(basis(('30',),end=1))
        self.assertEqual('QUALIFIED',r.sequence)
        self.assertEqual((),r.movements)
        self.assertEqual('NOT_ASSESSED',r.trajectory)

    def test_explicit_windows_do_not_choose_interesting_subwindow(self):
        rows=tuple(observation(i+1,v) for i,v in enumerate(('30','32','34','30')))
        full=evaluate(basis(observations=rows,end=4))
        recent=evaluate(basis(observations=rows,start=2,end=4))
        early=evaluate(basis(observations=rows,end=3))
        self.assertEqual(('MIXED','MIXED','INCREASING'),(full.trajectory,recent.trajectory,early.trajectory))
        self.assertEqual('OUTSIDE_REQUESTED_WINDOW',early.excluded[0].reason)
        self.assertNotEqual(full.basis.window,early.basis.window)

    def test_same_dates_incomparable_population_refuses(self):
        rows=(observation(1),observation(2,dataset_changes={'population':'other'}),observation(3))
        self.assertEqual('NOT_ASSESSED',evaluate(basis(observations=rows)).trajectory)

    def test_same_totals_different_population_cannot_supply_comparability(self):
        rows=(observation(1,'30'),observation(2,'30',dataset_changes={'population':'other'}),observation(3,'30'))
        self.assertEqual('NOT_ASSESSED',evaluate(basis(observations=rows)).trajectory)

    def test_coverage_population_currency_unit_definition_scope_mismatches_refuse(self):
        for field,value in (('currency','USD'),('unit','RATIO'),('definition',{'key':'different'}),
                            ('organisational_scope',{'entity':'other'}),('population','different')):
            with self.subTest(field=field):
                rows=(observation(1),observation(2,dataset_changes={field:value}),observation(3))
                self.assertEqual('NOT_ASSESSED',evaluate(basis(observations=rows)).trajectory)
        second=observation(2)
        coverage=dict(second.dataset.coverage.verified_value,completeness='PARTIAL')
        ds=second.dataset.model_copy(update={'coverage':datasets.verified(coverage,second.dataset.source_version)})
        rows=(observation(1),second.model_copy(update={'dataset':ds}),observation(3))
        self.assertEqual('NOT_ASSESSED',evaluate(basis(observations=rows)).trajectory)

    def test_declarations_and_unknowns_do_not_promote(self):
        for claim in (DatasetAssertion(),DatasetAssertion(declared_value='all-uk-sales',
                declaration_authority='MANAGEMENT_ASSERTION',declared_by=datasets.Actor(
                    actor_type='MANAGEMENT',actor_id='manager',source_authority='MANAGEMENT_ASSERTION'),declared_at=datasets.T)):
            second=observation(2)
            ds=second.dataset.model_copy(update={'population':claim})
            r=evaluate(basis(observations=(observation(1),second.model_copy(update={'dataset':ds}),observation(3))))
            self.assertEqual('NOT_ASSESSED',r.trajectory)

    def test_contradictory_verified_declaration_fails_closed(self):
        second=observation(2)
        claim=datasets.verified('other',second.dataset.source_version).model_copy(update=dict(
            declared_value='all-uk-sales',declaration_authority='MANAGEMENT_ASSERTION',
            declared_by=datasets.Actor(actor_type='MANAGEMENT',actor_id='manager',source_authority='MANAGEMENT_ASSERTION'),declared_at=datasets.T))
        ds=second.dataset.model_copy(update={'population':claim})
        self.assertEqual('NOT_ASSESSED',evaluate(basis(observations=(observation(1),second.model_copy(update={'dataset':ds}),observation(3)))).trajectory)

    def test_missing_month_is_explicit_not_consecutive(self):
        r=evaluate(basis(observations=(observation(1),observation(3))))
        self.assertEqual(('2026-02',),r.gaps)
        self.assertFalse(r.consecutive)
        self.assertEqual('INDETERMINATE',r.trajectory)

    def test_duplicate_periods_do_not_manufacture_persistence(self):
        r=evaluate(basis(observations=(observation(1),observation(2),observation(2,name='duplicate'),observation(3))))
        self.assertEqual('INDETERMINATE',r.sequence)
        self.assertNotEqual('INCREASING',r.trajectory)

    def test_verified_restatement_selects_one_period_and_preserves_revisions(self):
        feb=observation(2,'80')
        corrected=observation(2,'32',name='corrected-feb')
        ds=corrected.dataset.model_copy(update=dict(revision_relationship=datasets.verified('RESTATEMENT',corrected.dataset.source_version),
            revision_target_contract_id=feb.dataset.contract_id))
        corrected=corrected.model_copy(update={'dataset':ds})
        r=evaluate(basis(observations=(observation(1),feb,corrected,observation(3,'34'))))
        self.assertEqual(('QUALIFIED','INCREASING'),(r.sequence,r.trajectory))
        self.assertEqual(3,len(r.included))
        self.assertEqual('synthetic-2',r.revisions[0].observation_id)
        self.assertEqual(4,len(r.basis.observations))

    def test_competing_restatement_tips_fail_closed(self):
        feb=observation(2)
        rows=[observation(1),feb]
        for name in ('tip-a','tip-b'):
            o=observation(2,name=name)
            ds=o.dataset.model_copy(update=dict(revision_relationship=datasets.verified('RESTATEMENT',o.dataset.source_version),
                revision_target_contract_id=feb.dataset.contract_id))
            rows.append(o.model_copy(update={'dataset':ds}))
        rows.append(observation(3))
        self.assertEqual('INDETERMINATE',evaluate(basis(observations=tuple(rows))).sequence)

    def test_production_cannot_relabel_synthetic_positive_claim(self):
        r=evaluate(basis(origin='CANONICAL'))
        self.assertEqual(('NOT_ASSESSED','NOT_ASSESSED','NOT_ASSESSED'),(r.sequence,r.trajectory,r.interpretation))
        rows=(observation(1,key=AR,presence='ABSENT_VERIFIED',value=None),)
        with self.assertRaises(ValueError):basis(observations=rows,key=AR,end=1,origin='CANONICAL')

    def test_invalid_vocabulary_float_and_duplicate_identity_are_rejected(self):
        row=observation(1)
        for changes in ({'presence':'MAYBE'},{'value':30.0},{'unit':'PERCENTAGE_POINTS'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                Observation.model_validate(dict(row.model_dump(),**changes))
        with self.assertRaises(ValueError):basis(observations=(row,row))

    def test_nonpositive_revenue_base_has_no_relative_movement(self):
        r=evaluate(basis(('0','100','200'),key=REV))
        self.assertEqual('INDETERMINATE',r.trajectory)
        self.assertEqual('INCOMPARABLE',r.movements[0].state)


class TemporalLifecycleV254(unittest.TestCase):
    def result(self,states,values=None,months=None):
        rows=tuple(observation(month,(values or ['200']*len(states))[i],key=AR,presence=state)
            for i,(month,state) in enumerate(zip(months or range(1,len(states)+1),states)))
        return evaluate(basis(observations=rows,key=AR,end=max(months or range(1,len(states)+1))))

    def test_first_present_is_new_only_in_requested_history(self):
        self.assertEqual('NEW',self.result(['PRESENT']).lifecycle)

    def test_two_consecutive_present_are_persistent(self):
        self.assertEqual('PERSISTENT',self.result(['PRESENT','PRESENT']).lifecycle)

    def test_three_present_are_persistent_not_recurrent(self):
        self.assertEqual('PERSISTENT',self.result(['PRESENT']*3).lifecycle)

    def test_explicit_verified_absence_resolves(self):
        self.assertEqual('RESOLVED',self.result(['PRESENT','ABSENT_VERIFIED'],['200',None]).lifecycle)

    def test_present_absent_present_is_recurrent(self):
        self.assertEqual('RECURRENT',self.result(['PRESENT','ABSENT_VERIFIED','PRESENT'],['200',None,'100']).lifecycle)

    def test_unknown_gap_is_not_recurrence(self):
        self.assertEqual('INDETERMINATE',self.result(['PRESENT','UNKNOWN','PRESENT']).lifecycle)

    def test_missing_month_is_not_recurrence(self):
        self.assertEqual('INDETERMINATE',self.result(['PRESENT','PRESENT'],months=[1,3]).lifecycle)

    def test_missing_impact_zero_and_not_applicable_are_not_absence(self):
        for value in (None,'0'):
            r=self.result(['PRESENT','UNKNOWN'],['200',value])
            self.assertEqual('INDETERMINATE',r.lifecycle)
        row=observation(2,'0',key=AR)
        with self.assertRaises(ValueError):Observation.model_validate(dict(row.model_dump(),presence='ABSENT_VERIFIED'))

    def test_persistence_does_not_require_worsening_magnitude(self):
        r=self.result(['PRESENT']*3,['200','100','50'])
        self.assertEqual('PERSISTENT',r.lifecycle)
        self.assertEqual('NOT_ASSESSED',r.trajectory)
        self.assertEqual('NOT_ASSESSED',r.interpretation)
        # Independent fields can represent future separately qualified magnitude
        # interpretation without forcing persistence into a trend enum.
        represented=r.model_copy(update={'trajectory':'DECREASING','interpretation':'IMPROVING'})
        self.assertEqual(('PERSISTENT','DECREASING','IMPROVING'),(
            represented.lifecycle,represented.trajectory,represented.interpretation))
        self.assertEqual(r,evaluate(r.basis))

    def test_absence_requires_every_explicit_proof_and_exact_scope(self):
        proof=observation(2,None,key=AR,presence='ABSENT_VERIFIED').absence
        for field in ('complete_population_verified','control_reconciled','contractual_and_status_review_complete',
                      'no_unresolved_classifications','condition_absence_verified'):
            with self.subTest(field=field),self.assertRaises(ValueError):
                AbsenceEvidence.from_json(proof.model_copy(update={field:False}).to_json())
        row=observation(2,None,key=AR,presence='ABSENT_VERIFIED')
        with self.assertRaises(ValueError):Observation.from_json(row.model_copy(update={'scope_key':'other'}).to_json())
