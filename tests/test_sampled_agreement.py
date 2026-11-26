"""Synthetic paired opinions only; no real annotations created."""
import pytest
from src.evaluation.sampled_agreement import analyse_sample


def event(g,source='user_local_ui'):return {'semantic_grade':g,'source':source}


def test_partial_sample_never_exposes_interim_agreement():
    result=analyse_sample([('q','a'),('q','b')],{('q','a'):event(2)},{('q','a'):event(0)})
    assert result['statistics'] is None and not result['adjudication_queue']
    assert result['missing_second']==1


def test_unknown_and_assisted_pairs_are_separate_and_never_imputed():
    tasks=[('q',str(i)) for i in range(4)]
    a={tasks[0]:event(0),tasks[1]:event(2),tasks[2]:event(1,'ai_assisted_user_requested'),tasks[3]:event(None)}
    b={p:event(g) for p,g in zip(tasks,[0,2,2,0])}
    r=analyse_sample(tasks,a,b)
    assert r['statistics']['original_human_pairs_only']['n']==2
    assert r['statistics']['original_human_pairs_only']['quadratic']['kappa']==1
    assert r['statistics']['including_AI_assisted_first_rater_sensitivity']['n']==3
    assert r['exclusions']['one_or_both_unknown']==1
    assert len(r['adjudication_queue'])==2
    assert all(x['final_grade'] is None for x in r['adjudication_queue'])


def test_degenerate_agreement_is_undefined_not_perfect_kappa():
    pair=('q','a');r=analyse_sample([pair],{pair:event(0)},{pair:event(0)})
    assert r['statistics']['original_human_pairs_only']['exact_agreement']==1
    assert r['statistics']['original_human_pairs_only']['linear']['kappa'] is None


def test_extra_pairs_rejected():
    with pytest.raises(ValueError,match='outside'):
        analyse_sample([('q','a')],{},{('q','b'):event(0)})


def test_invalid_grade_rejected_and_no_missing_first_fabricated():
    pair=('q','a')
    with pytest.raises(ValueError):analyse_sample([pair],{pair:event(True)},{pair:event(0)})
    r=analyse_sample([pair],{},{pair:event(0)})
    assert r['exclusions']['first_missing']==1
    assert r['statistics']['original_human_pairs_only']['n']==0
