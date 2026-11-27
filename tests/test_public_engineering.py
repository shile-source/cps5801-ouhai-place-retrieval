import copy
import hashlib
import pytest
from src.data.evidence_facts import compile_facts
from src.evaluation.public_engineering import summarize


def fixture():
    methods=['keyword','bm25','bge_m3']
    protocol={'methods':methods,'repeats_per_query':2,'top_k':5}
    queries={'items':[{'query_id':'F01','group':'constructed_exact_name','expected_source_id':'a'}],
             'constraint_checks':[{'case_id':'C01'}]}
    observations=[]
    def row(method,phase,**extra):
        return dict(method=method,phase=phase,search_ms=1,elapsed_ms=2,load_ms=0,
                    results=[{'poi_id':'a','score':1}],**extra)
    cold=row('bge_m3','cold');cold['load_ms']=10;observations.append(cold)
    for method in methods:
        observations.append(row(method,'warmup'))
        for repeat in range(2):observations.append(row(method,'measurement',query_id='F01',repeat=repeat))
        observations.append(row(method,'constraint',case_id='C01',eligible_ids=['a'],unknown_count=1,unmet_count=0))
    return protocol,queries,observations


def test_descriptive_arithmetic_not_relevance():
    result=summarize(*fixture())
    assert result['measured_requests']==6 and result['new_human_labels']==0
    assert result['methods']['bm25']['source_id_recovery_at1']==1
    assert result['pairwise_overlap']['keyword__bge_m3']['mean_top5_jaccard']==1
    assert result['relevance_ndcg_mrr_recall'] is None


def test_incomplete_and_different_pools_rejected():
    protocol,queries,rows=fixture()
    with pytest.raises(ValueError,match='Incomplete'):summarize(protocol,queries,rows[:-1])
    bad=copy.deepcopy(rows);bad[-1]['eligible_ids']=[]
    with pytest.raises(ValueError,match='different source pools'):summarize(protocol,queries,bad)
    bad=copy.deepcopy(rows);bad[3]['results'][0]['poi_id']='other'
    with pytest.raises(ValueError,match='Repeated rankings'):summarize(protocol,queries,bad)


def test_explicit_activity_categories_require_hashed_source(tmp_path):
    raw=tmp_path/'raw.json';raw.write_text('{}')
    evidence=[dict(poi_id='a',source_field='tags.amenity',source_value='karaoke_box',
        raw_path='raw.json',raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),source_url='https://example.test')]
    records=[{'poi_id':'a','category':'KTV'}]
    assert compile_facts(records,evidence,tmp_path)['a']['category']['status']=='unknown'
    mapping={('tags.amenity','karaoke_box'):'KTV'}
    assert compile_facts(records,evidence,tmp_path,category_labels=mapping)['a']['category']['value']=='KTV'
    raw.write_text('changed')
    with pytest.raises(ValueError,match='hash mismatch'):compile_facts(records,evidence,tmp_path,category_labels=mapping)
    with pytest.raises(ValueError,match='redefine'):compile_facts(records,evidence,tmp_path,category_labels={('tags.leisure','park'):'KTV'})
