from src.data.activity_sources import ACTIVITY_TAGS,enrich_activity
from experiments.prepare_user30_spotcheck_20261127 import propose


def test_sport_label_requires_actual_tag_not_name():
    item={'source_tags':{'name':'synthetic 篮球场','leisure':'pitch'},'description_clauses':[{'text':'名称：synthetic 篮球场','source_fields':['name']}]}
    enrich_activity(item)
    assert 'sport=' not in item['description']
    assert item['public_access_verified'] is False
    item['source_tags']['sport']='basketball'
    enrich_activity(item)
    assert 'sport=basketball' in item['description']


def test_retail_not_automatically_commercial_street():
    labels={(key,value):label for key,value,label in ACTIVITY_TAGS}
    assert labels['landuse','retail']=='商业区域'
    assert labels['highway','pedestrian']=='步行区域'


def test_author_undefined_soft_quantity_is_not_old_threshold():
    item={'category':'城市书房','name':'synthetic','description':'座位数：80；藏书量：20000','source_tags':{}}
    assert propose(20,'synthetic quantity preference',item)[0] is None
    assert propose(21,'synthetic opening preference',item)[0] is None


def test_ai_suggestions_need_explicit_sport_and_do_not_infer_missing_facilities():
    item={'category':'运动场','name':'synthetic','source_tags':{}}
    assert propose(23,'synthetic basketball preference',item)[0] is None
    item['source_tags']['sport']='basketball'
    assert propose(23,'synthetic basketball preference',item)[0]==2
    assert propose(29,'synthetic family activity',item)[0] is None
