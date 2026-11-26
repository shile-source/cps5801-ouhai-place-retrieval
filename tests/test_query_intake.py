"""Synthetic intake only; no genuine human queries, labels or approvals."""
from copy import deepcopy
import pytest
from src.evaluation.query_intake import validate_intake,KINDS


@pytest.fixture
def intake():
    return {'schema':'independent_query_intake_v1','author_alias':'synthetic_fixture',
            'formal_eligible':False,'is_draft':False,'original_authorship_declared':True,
            'prior_ranking_exposure':False,'source_catalog_sha256':'synthetic_sha',
            'queries':[{'query_id':f'{k}{i}','query_type':k,'text':f'合成测试语句{k}{i}'} for k in sorted(KINDS) for i in range(3)]}


def test_valid_intake_stays_draft_and_not_verified_independent(intake):
    result=validate_intake(intake,'synthetic_sha')
    assert result['formal_eligible'] is False and result['independence_verified'] is False


def test_earlier_form_binding_gap_not_silently_fixed(intake):
    intake.pop('source_catalog_sha256')
    assert validate_intake(intake,'synthetic_sha')['catalog_binding'].startswith('missing')


def test_different_catalog_rejected(intake):
    with pytest.raises(ValueError,match='catalog differs'): validate_intake(intake,'other')


def test_model_score_or_label_field_rejected(intake):
    intake['queries'][0]['grade']=2
    with pytest.raises(ValueError,match='not grades'):validate_intake(intake,'synthetic_sha')


def test_duplicate_text_rejected(intake):
    intake['queries'][1]['text']=intake['queries'][0]['text']
    with pytest.raises(ValueError,match='Duplicate query text'):validate_intake(intake,'synthetic_sha')


@pytest.mark.parametrize('key,value',[('formal_eligible',True),('is_draft',True),('prior_ranking_exposure',None),('original_authorship_declared',False)])
def test_missing_declaration_or_self_promotion_rejected(intake,key,value):
    intake[key]=value
    with pytest.raises(ValueError):validate_intake(intake,'synthetic_sha')
