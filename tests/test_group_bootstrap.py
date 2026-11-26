"""Synthetic metric differences only; no real experiment uncertainty is fabricated."""
import pytest
from src.evaluation.group_bootstrap import paired_group_bootstrap


def test_single_group_does_not_create_a_misleading_zero_width_interval():
    r=paired_group_bootstrap({'a':1},{'a':.5},{'a':'one_intent'})
    assert r['status']=='not_estimable' and r['interval'] is None


def test_group_means_prevent_paraphrases_from_counting_as_independent_queries():
    a={'a':1,'b':1,'c':0};b={'a':0,'b':0,'c':0};g={'a':'same','b':'same','c':'different'}
    r=paired_group_bootstrap(a,b,g,samples=100)
    assert r['mean']==.5 and r['n_groups']==2 and r['n_queries']==3
    assert r==paired_group_bootstrap(a,b,g,samples=100)


def test_methods_must_use_identical_queries_and_valid_metrics():
    with pytest.raises(ValueError):paired_group_bootstrap({'a':1},{'b':1},{'a':'g'})
    with pytest.raises(ValueError):paired_group_bootstrap({'a':True},{'a':1},{'a':'g'})
