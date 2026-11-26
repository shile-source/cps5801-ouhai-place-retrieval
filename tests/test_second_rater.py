"""Synthetic rater separation and route isolation; no real human labels."""
import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import pytest
from src.evaluation.human_pilot import Pilot,prepare,sha
from src.evaluation.second_rater import prepare_second_rater,SecondRaterPilot,make_page
from src.demo.annotation_server import handler


@pytest.fixture
def separated(tmp_path):
    corpus=tmp_path/'synthetic.json'
    corpus.write_text(json.dumps([{'poi_id':'synthetic_place','name':'synthetic fixture','category':'synthetic','is_synthetic':True}]),encoding='utf-8')
    qs=[{'query_id':'synthetic_query','query_type':'named_lexical','text':'synthetic','rubric':'synthetic only'}]
    a=Pilot(prepare(tmp_path/'a',corpus,queries=qs))
    a.approve('synthetic_A',['synthetic_query'],True)
    a.rate('synthetic_query','synthetic_place',2,evidence='synthetic evidence')
    before=sha(a.path/'human_actions.jsonl')
    b=SecondRaterPilot(prepare_second_rater(a.path,tmp_path/'b'))
    return a,b,before


def test_new_slot_shares_queries_and_corpus_but_has_no_ratings(separated):
    a,b,before=separated
    assert a.packet['queries']==b.packet['queries']
    assert a.manifest['corpus_sha256']==b.manifest['corpus_sha256']
    assert b.state()['graded']==0 and b.state()['existing'] is None
    assert b.review() is None and not b.ratings()
    assert 'reference_action_log_sha256' not in b.state()
    assert not b.packet['independent_authorship']


def test_b_rating_preserves_a_and_resume_preserves_b(separated):
    a,b,before=separated
    b.approve('synthetic_B',['synthetic_query'],True)
    b.rate('synthetic_query','synthetic_place',0,evidence='synthetic independent opinion')
    assert sha(a.path/'human_actions.jsonl')==before
    assert a.ratings()['synthetic_query','synthetic_place']['semantic_grade']==2
    assert Pilot(prepare_second_rater(a.path,b.path)).ratings()['synthetic_query','synthetic_place']['semantic_grade']==0


def test_collection_cannot_evaluate(separated):
    _,b,_=separated
    with pytest.raises(ValueError,match='never calls'):b.evaluate(lambda *a:pytest.fail('Model called'))


def test_page_explains_second_slot_and_hides_calculate():
    page=make_page()
    assert '第二位评分者' in page and 'id="evaluate" hidden disabled' in page
    assert '第三步：评分完成后计算' not in page
    assert 'function rememberPosition' in page


def test_http_evaluate_is_forbidden_without_calling_pilot(separated,tmp_path):
    _,b,_=separated
    page=tmp_path/'page.html';page.write_text(make_page(),encoding='utf-8')
    server=ThreadingHTTPServer(('127.0.0.1',0),handler(b,page_path=page,allow_evaluation=False))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        with urlopen(base+'/api/task') as response:assert json.load(response)['graded']==0
        request=Request(base+'/api/evaluate',data=b'{}',headers={'Content-Type':'application/json'})
        with pytest.raises(HTTPError) as caught:urlopen(request)
        assert caught.value.code==403
        assert not b.events()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=3)


@pytest.fixture
def sampled(tmp_path):
    corpus=tmp_path/'synthetic_sample.json'
    corpus.write_text(json.dumps([{'poi_id':f'synthetic_{i}','name':f'synthetic {i}','is_synthetic':True} for i in range(15)]),encoding='utf-8')
    queries=[{'query_id':f'synthetic_q{i}','query_type':'named_lexical','text':f'synthetic {i}','rubric':'synthetic only'} for i in range(8)]
    a=prepare(tmp_path/'a_sample',corpus,queries=queries)
    b=prepare_second_rater(a,tmp_path/'b_sample',sample_per_query=10)
    return a,SecondRaterPilot(b)


def test_sample_is_80_unique_pairs_and_starts_match_query_navigation(sampled):
    _,b=sampled
    assert len(b.tasks)==len(set(b.tasks))==80
    for index,qid in enumerate(b.queries):
        assert sum(q==qid for q,p in b.tasks)==10
        assert b.state()['query_task_starts'][qid]==10*index
    assert b.state(79)['index']==79
    assert b.state()['total']==80 and b.state()['handled']==0


def test_sample_reproducible_after_resume_without_grades(sampled,tmp_path):
    a,b=sampled
    repeated=SecondRaterPilot(prepare_second_rater(a,b.path,sample_per_query=10))
    independent=SecondRaterPilot(prepare_second_rater(a,tmp_path/'another_b',sample_per_query=10))
    assert b.tasks==repeated.tasks==independent.tasks
    assert not b.events()
    assert b.packet['selection_uses_model_rankings_or_grades'] is False


def test_sample_cannot_accept_outside_pairs_or_silently_change_plan(sampled):
    a,b=sampled
    outside=next((q,p) for q in b.queries for p in b.records if (q,p) not in b.tasks)
    with pytest.raises(ValueError,match='outside'):b.rate(*outside,2,evidence='synthetic')
    with pytest.raises(ValueError,match='different sampling plan'):prepare_second_rater(a,b.path,sample_per_query=5)


def test_sample_page_explains_reduced_count_and_uses_task_offsets():
    page=make_page(total=80,sampled=True)
    assert '共80对' in page and '不用做392对' in page
    assert "current.query_task_starts[$('querySelect').value]" in page


def test_analysis_lock_prevents_further_rating_and_preserves_original_log(separated):
    _,b,_=separated
    b.approve('synthetic_B',['synthetic_query'],True)
    b.rate('synthetic_query','synthetic_place',1,evidence='synthetic evidence')
    before=sha(b.path/'human_actions.jsonl')
    (b.path/'analysis_lock.json').write_text(json.dumps({'actions_sha256':before}),encoding='utf-8')
    assert b.state()['ratings_locked']
    with pytest.raises(ValueError,match='已锁定'):b.rate('synthetic_query','synthetic_place',2,evidence='synthetic changed opinion')
    assert sha(b.path/'human_actions.jsonl')==before


def test_analysis_lock_detects_changed_log(separated):
    _,b,_=separated
    (b.path/'analysis_lock.json').write_text(json.dumps({'actions_sha256':'incorrect'}),encoding='utf-8')
    (b.path/'human_actions.jsonl').write_text('',encoding='utf-8')
    with pytest.raises(ValueError,match='action log changed'):b.state()
