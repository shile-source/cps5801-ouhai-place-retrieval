"""Synthetic-only checks: a reviewed unknown removes eligibility, never becomes zero."""
import pytest
from src.evaluation.review_sensitivity import analyse_review


def test_reviewed_unknown_removes_eligibility_without_mutating_original():
    original={('q','a'):2,('q','b'):1}
    result,revised=analyse_review(['q'],['a','b'],original,{('q','b'):None},{'q':{'synthetic':['a','b']}})
    assert original[('q','b')]==1 and revised[('q','b')] is None
    assert result['eligible_before']==['q'] and result['eligible_after']==[]
    assert result['after_numeric']==1 and result['after_unknown']==1
    assert result['evaluations'][0]['status']=='excluded' and result['evaluations'][0]['metrics'] is None


def test_explicit_numeric_review_can_complete_a_query_but_absent_run_is_not_invented():
    original={('q','a'):2,('q','b'):None}
    result,_=analyse_review(['q'],['a','b'],original,{('q','b'):0},{})
    assert result['eligible_after']==['q'] and result['after_unknown']==0
    assert result['evaluations'][0]['status']=='not_evaluated'
    scored,_=analyse_review(['q'],['a','b'],original,{('q','b'):0},{'q':{'synthetic':['a','b']}})
    assert scored['evaluations'][0]['metrics']['mrr']==1


@pytest.mark.parametrize('decisions',[{('q','a'):True},{('q','a'):3},{('q','other'):0}])
def test_invalid_or_unrelated_decisions_are_rejected(decisions):
    with pytest.raises(ValueError):analyse_review(['q'],['a'],{('q','a'):1},decisions,{})


def test_missing_original_judgment_is_not_silently_treated_as_unknown_or_zero():
    with pytest.raises(ValueError):analyse_review(['q'],['a','b'],{('q','a'):1},{},{})
