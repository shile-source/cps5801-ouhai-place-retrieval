"""Synthetic query phrasing: suggestions are not human relevance annotations."""
import pytest
from src.retrieval.constraint_proposals import propose_constraints


@pytest.mark.parametrize('text', ['希望座位至少40个','优先找公园','藏书最好不少于10000册'])
def test_soft_preference_is_never_a_hard_filter(text):
    result=propose_constraints(text)
    assert not result['constraints'] and result['notices']


def test_explicit_category_and_counts_require_confirmation():
    result=propose_constraints('只找图书馆，并且座位至少50个，藏书不少于12000册')
    assert result['constraints']==[{'field':'category','operator':'eq','value':'图书馆'},
                                  {'field':'seats','operator':'gte','value':50},
                                  {'field':'holdings','operator':'gte','value':12000}]
    assert result['requires_user_confirmation'] and not result['models_called']


def test_before_unit_and_after_field_forms_match():
    assert propose_constraints('不少于50个座位')['constraints']==propose_constraints('座位不少于50个')['constraints']


def test_soft_context_across_clauses_does_not_become_mandatory():
    assert not propose_constraints('希望座位至少30个，藏书至少10000册')['constraints']
    result=propose_constraints('必须是公园，同时希望在某街道')
    assert result['constraints']==[{'field':'category','operator':'eq','value':'公园'}]


def test_unsupported_conditions_are_not_invented():
    result=propose_constraints('必须安静，今天开放，不要博物馆')
    assert not result['constraints']
    assert {r['reason'] for r in result['notices']}=={'unverified_attribute_not_filterable','negative_condition_requires_manual_review'}


def test_conflicting_counts_and_strict_greater_than_are_not_silently_resolved():
    assert not propose_constraints('座位至少40个，座位至少50个')['constraints']
    assert not propose_constraints('藏书超过一万册')['constraints']


@pytest.mark.parametrize('value',[None,'','x'*501])
def test_invalid_proposal_input_rejected(value):
    with pytest.raises(ValueError):propose_constraints(value)
