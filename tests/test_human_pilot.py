"""Explicitly synthetic fixtures; no real human labels are generated."""
import json
import pytest
from src.evaluation.human_pilot import Pilot, prepare, sha


@pytest.fixture
def pilot(tmp_path):
    corpus=tmp_path/'synthetic.json'
    corpus.write_text(json.dumps([
        {'poi_id':'synthetic_a','name':'模拟书房','category':'书房','description':'模拟数据','is_synthetic':True},
        {'poi_id':'synthetic_b','name':'模拟公园','category':'公园','description':'模拟数据','is_synthetic':True}],ensure_ascii=False),encoding='utf-8')
    qs=[{'query_id':'synthetic_q','text':'模拟查询','query_type':'named_lexical','rubric':'仅合成测试'}]
    return Pilot(prepare(tmp_path/'session',corpus,queries=qs))


def approve(p):
    p.approve('synthetic_test_rater',['synthetic_q'],True)


def fetch(p, order=None):
    def run(method,text,count):
        return {'corpus_sha256':p.packet['source_corpus_sha256'],
                'results':[{'poi_id':i} for i in (order or ['synthetic_a','synthetic_b'])]}
    return run


def test_initial_packet_is_unjudged_and_not_formal(pilot):
    s=pilot.state()
    assert s['graded']==0 and s['review'] is None and not s['formal_evaluation']
    assert not (pilot.path/'human_actions.jsonl').exists()


def test_task_payload_is_blind_and_order_stable(pilot):
    a=pilot.state();b=Pilot(pilot.path).state()
    assert a['candidate']==b['candidate']
    assert not {'model','rank','score','retrieval_score'} & a['candidate'].keys()


def test_rating_requires_real_review(pilot):
    with pytest.raises(ValueError,match='人工确认'):
        pilot.rate('synthetic_q','synthetic_a',2,evidence='模拟类别')


@pytest.mark.parametrize('grade',[True,3,-1,'2',0.5])
def test_invalid_grades_rejected(pilot,grade):
    approve(pilot)
    with pytest.raises(ValueError):pilot.rate('synthetic_q','synthetic_a',grade,evidence='模拟')


def test_unknown_needs_reason_and_is_not_zero(pilot):
    approve(pilot)
    with pytest.raises(ValueError):pilot.rate('synthetic_q','synthetic_a',None)
    pilot.rate('synthetic_q','synthetic_a',None,reason='模拟字段未知')
    assert pilot.ratings()['synthetic_q','synthetic_a']['semantic_grade'] is None
    assert pilot.state()['unknown']==1 and pilot.state()['graded']==0


def test_scored_grade_needs_evidence(pilot):
    approve(pilot)
    with pytest.raises(ValueError):pilot.rate('synthetic_q','synthetic_a',0)


def test_earlier_ratings_retained_when_corrected(pilot):
    approve(pilot)
    pilot.rate('synthetic_q','synthetic_a',1,evidence='模拟部分证据')
    pilot.rate('synthetic_q','synthetic_a',2,evidence='模拟补充证据')
    assert len([e for e in pilot.events() if e['action']=='human_rating'])==2
    assert pilot.ratings()['synthetic_q','synthetic_a']['semantic_grade']==2


def test_incomplete_labels_never_call_a_model(pilot):
    approve(pilot)
    pilot.rate('synthetic_q','synthetic_a',2,evidence='模拟')
    def forbidden(*a):raise AssertionError('No model run with incomplete labels')
    assert pilot.evaluate(forbidden)['status']=='not_ready'


def test_assisted_correction_preserves_human_history_and_requires_matching_revision(pilot):
    approve(pilot)
    pilot.rate('synthetic_q', 'synthetic_a', 1, evidence='模拟旧证据')
    original = pilot.ratings()['synthetic_q', 'synthetic_a']
    correction = {'action': 'assisted_annotation_correction', 'query_id': 'synthetic_q',
                  'poi_id': 'synthetic_a', 'semantic_grade': None,
                  'unknown_reason': '模拟资料缺失', 'source': 'ai_assisted_user_requested',
                  'supersedes_recorded_at': original['recorded_at']}
    pilot.append(correction)
    assert pilot.ratings()['synthetic_q', 'synthetic_a']['semantic_grade'] is None
    assert pilot.state()['unknown'] == 1
    assert len([e for e in pilot.events() if e['action'] == 'human_rating']) == 1
    pilot.rate('synthetic_q', 'synthetic_a', 2, evidence='模拟人工复核')
    pilot.append(correction.copy())
    assert pilot.ratings()['synthetic_q', 'synthetic_a']['semantic_grade'] == 2


def test_unknown_query_excluded_without_fabricated_metrics(pilot):
    approve(pilot)
    pilot.rate('synthetic_q','synthetic_a',2,evidence='模拟')
    pilot.rate('synthetic_q','synthetic_b',None,reason='模拟未知')
    assert pilot.evaluate(fetch(pilot))['status']=='not_ready'


def test_single_rater_real_formula_and_post_result_lock(pilot):
    approve(pilot)
    pilot.rate('synthetic_q','synthetic_a',2,evidence='模拟')
    pilot.rate('synthetic_q','synthetic_b',0,evidence='模拟')
    r=pilot.evaluate(fetch(pilot))
    assert r['annotator_count']==1 and r['kappa'] is None and not r['formal_evaluation']
    assert r['summary'][0]['ndcg_at_5']==1 and r['summary'][0]['mrr']==1
    assert r['summary'][0]['precision_at_3']==pytest.approx(1/3)
    assert r['summary'][0]['ndcg_at_5_n']==1
    with pytest.raises(ValueError,match='锁定'):
        pilot.rate('synthetic_q','synthetic_b',2,evidence='不得按结果改分')


def test_truncated_mrr_and_wrong_corpus_are_rejected(pilot):
    approve(pilot)
    for p,g in [('synthetic_a',2),('synthetic_b',0)]:pilot.rate('synthetic_q',p,g,evidence='模拟')
    with pytest.raises(ValueError,match='Full common ranking'):pilot.evaluate(fetch(pilot,['synthetic_a']))
    with pytest.raises(ValueError,match='corpus differs'):
        pilot.evaluate(lambda *a:{'corpus_sha256':'wrong','results':[]})


def test_frozen_packet_changes_stop(pilot):
    (pilot.path/'corpus.json').write_text('[]',encoding='utf-8')
    with pytest.raises(ValueError,match='changed'):pilot.state()


def test_prepare_never_overwrites_existing_human_session(pilot):
    approve(pilot)
    before=sha(pilot.path/'human_actions.jsonl')
    prepare(pilot.path,pilot.path/'corpus.json')
    assert sha(pilot.path/'human_actions.jsonl')==before


def test_failed_model_attempt_preserved_without_changing_grades(pilot):
    approve(pilot)
    for p,g in [('synthetic_a',2),('synthetic_b',0)]:pilot.rate('synthetic_q',p,g,evidence='模拟')
    before=pilot.ratings()
    def failed(*a):raise RuntimeError('synthetic model failure')
    with pytest.raises(RuntimeError):pilot.evaluate(failed)
    assert pilot.ratings()==before
    assert pilot.events()[-1]['action']=='evaluation_failed'


def test_human_result_tables_are_exported_only_after_completion(pilot):
    approve(pilot)
    for p,g in [('synthetic_a',2),('synthetic_b',0)]:pilot.rate('synthetic_q',p,g,evidence='模拟')
    pilot.evaluate(fetch(pilot))
    assert len(list(pilot.path.glob('evaluation_*.csv')))==1
    assert 'single-rater' in next(pilot.path.glob('evaluation_*.md')).read_text(encoding='utf-8')


@pytest.fixture
def service(pilot):
    from http.server import ThreadingHTTPServer
    import threading
    from src.demo.annotation_server import handler
    server=ThreadingHTTPServer(('127.0.0.1',0),handler(pilot))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown();server.server_close();thread.join(3)


def test_http_blind_initial_state(service):
    from urllib.request import urlopen
    with urlopen(service+'/api/task?index=0') as response:state=json.load(response)
    assert state['graded']==0 and state['review'] is None
    assert 'score' not in state['candidate']


def test_http_rejects_foreign_origin_and_project_paths(service):
    from urllib.request import Request,urlopen
    from urllib.error import HTTPError
    request=Request(service+'/api/review',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://foreign.invalid'})
    with pytest.raises(HTTPError) as e:urlopen(request)
    assert e.value.code==403
    with pytest.raises(HTTPError) as e:urlopen(service+'/../../PROJECT_STATUS.md')
    assert e.value.code==404
