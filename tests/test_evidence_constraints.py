"""Synthetic evidence fixtures only; not real POI annotations."""
import hashlib
import pytest
from src.data.evidence_facts import compile_facts
from src.retrieval.constraints import Constraint, assess, shared_pool


@pytest.fixture
def source(tmp_path):
    (tmp_path/'raw.txt').write_bytes(b'synthetic source fixture')
    def row(field,value,pid='synthetic1'):
        return {'poi_id':pid,'source_field':field,'source_value':value,'raw_path':'raw.txt',
                'raw_sha256':hashlib.sha256((tmp_path/'raw.txt').read_bytes()).hexdigest(),
                'source_url':'https://example.test/fixture','downloaded_at':'2026-01-01'}
    return tmp_path,row


def test_source_evidence_and_missing_are_distinct(source):
    root,row=source
    facts=compile_facts([{'poi_id':'synthetic1'}],[row('座位数','40'),row('类型','城市书房')],root)['synthetic1']
    assert facts['seats']['value']==40
    assert facts['holdings']['status']=='unknown'
    assert assess(facts,[Constraint('seats','gte',40)])['status']=='met'
    assert assess(facts,[Constraint('seats','gte',41)])['status']=='unmet'
    assert assess(facts,[Constraint('holdings','gte',12000)])['status']=='unknown'


def test_conflicting_facts_do_not_silently_choose(source):
    root,row=source
    facts=compile_facts([{'poi_id':'synthetic1'}],[row('座位数','30'),row('座位数','50')],root)['synthetic1']
    assert facts['seats']['status']=='conflicting'
    assert assess(facts,[Constraint('seats','gte',40)])['status']=='unknown'


def test_original_hash_is_required(source):
    root,row=source; e=row('座位数','40')
    (root/'raw.txt').write_bytes(b'changed fixture')
    with pytest.raises(ValueError,match='hash mismatch'):
        compile_facts([{'poi_id':'synthetic1'}],[e],root)


def test_invalid_number_is_unknown(source):
    root,row=source
    facts=compile_facts([{'poi_id':'synthetic1'}],[row('座位数','约四十')],root)['synthetic1']
    assert facts['seats']['value'] is None


def test_same_source_value_repeated_is_supported(source):
    root,row=source; e=row('座位数','40')
    facts=compile_facts([{'poi_id':'synthetic1'}],[e,e],root)
    assert facts['synthetic1']['seats']['status']=='supported'


@pytest.mark.parametrize('field',['quiet','district','opening_now','fee'])
def test_unsupported_real_world_conditions_rejected(field):
    with pytest.raises(ValueError,match='Unsupported'):
        Constraint(field,'eq','yes')


@pytest.mark.parametrize('value',[True,'40',-1,40.5])
def test_invalid_numeric_filter_rejected(value):
    with pytest.raises(ValueError): Constraint('seats','gte',value)


def test_unsupported_scope_rejected():
    with pytest.raises(ValueError,match='current'):
        Constraint('seats','gte',40,scope='current')


def test_common_pool_does_not_label_unknown_as_negative(source):
    root,row=source
    facts=compile_facts([{'poi_id':f'synthetic{i}'} for i in (1,2,3)],
                        [row('座位数','40'),row('座位数','20','synthetic2')],root)
    pool=shared_pool(facts,[Constraint('seats','gte',40)])
    assert pool['eligible_ids']==['synthetic1']
    assert pool['unmet_ids']==['synthetic2']
    assert pool['unknown_ids']==['synthetic3']
    assert pool['creates_relevance_grades'] is False
