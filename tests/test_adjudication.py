"""Synthetic-only review saves, provenance, locks and HTTP isolation."""
import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import pytest
from src.evaluation.adjudication import create_session,Adjudication,digest
from src.demo.adjudication_server import handler


@pytest.fixture
def review(tmp_path):
    source=tmp_path/'synthetic_source.txt';source.write_text('synthetic immutable opinions',encoding='utf-8')
    item={'case_id':'synthetic:q1','query':{'text':'synthetic','rubric':'synthetic only'},
          'candidate':{'name':'synthetic fixture'},'original':{'first_grade':1,'second_grade':0}}
    return create_session(tmp_path/'review',[item],{'synthetic_source.txt':digest(source)},tmp_path)


def test_start_empty_resume_and_revisions_preserve_source(review):
    assert review.state()['handled']==0 and review.state()['existing'] is None
    before=(review.root/'synthetic_source.txt').read_bytes()
    review.decide('synthetic:q1',1,'synthetic evidence','synthetic reviewer',True)
    review.decide('synthetic:q1',None,'synthetic missing fact','synthetic reviewer',True)
    resumed=Adjudication(review.path,review.root)
    assert resumed.state()['handled']==1 and resumed.state()['unknown']==1
    assert len((review.path/'decisions.jsonl').read_text().splitlines())==2
    assert (review.root/'synthetic_source.txt').read_bytes()==before
    assert resumed.export()['cases'][0]['decision']['grade'] is None
    assert resumed.export()['independent_blind_adjudicator'] is False


@pytest.mark.parametrize('grade,reason,person,confirmed',[(True,'synthetic','synthetic',True),(3,'synthetic','synthetic',True),
    (0,'','synthetic',True),(None,'','synthetic',True),(1,'synthetic','',True),(1,'synthetic','synthetic',False)])
def test_invalid_or_unconfirmed_decisions_write_nothing(review,grade,reason,person,confirmed):
    with pytest.raises(ValueError):review.decide('synthetic:q1',grade,reason,person,confirmed)
    assert not (review.path/'decisions.jsonl').exists()


def test_finalize_requires_all_and_locks_actual_human_history(review):
    with pytest.raises(ValueError):review.finalize()
    review.decide('synthetic:q1',0,'synthetic evidence','synthetic reviewer',True)
    assert review.finalize()['complete']
    assert review.state()['locked']
    with pytest.raises(ValueError):review.decide('synthetic:q1',2,'synthetic revision','synthetic',True)
    assert review.finalize()['handled']==1
    (review.path/'completed_review.json').unlink()  # Disposable synthetic output, simulating interrupted export.
    assert review.finalize()['complete'] and (review.path/'completed_review.json').is_file()
    with (review.path/'decisions.jsonl').open('a') as file:file.write('\n')
    with pytest.raises(ValueError,match='Locked'):review.state()


def test_changed_original_evidence_blocks_review(review):
    (review.root/'synthetic_source.txt').write_text('changed synthetic source')
    with pytest.raises(ValueError,match='Original'):review.state()
    with pytest.raises(ValueError):review.decide('synthetic:q1',0,'synthetic','synthetic',True)


def test_http_requires_token_rejects_foreign_origin_and_has_no_model_route(review,tmp_path):
    page=tmp_path/'synthetic.html';page.write_text('<p>synthetic only</p>')
    server=ThreadingHTTPServer(('127.0.0.1',0),handler(review,page));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    value={'case_id':'synthetic:q1','grade':0,'reason':'synthetic evidence','reviewer':'synthetic','confirmed':True}
    def post(path,token='',origin=None):
        headers={'Content-Type':'application/json','X-Review-Token':token}
        if origin:headers['Origin']=origin
        return urlopen(Request(base+path,data=json.dumps(value).encode(),headers=headers),timeout=3)
    try:
        with urlopen(base+'/api/state') as response:state=json.load(response)
        assert state['handled']==0
        with pytest.raises(HTTPError) as caught:post('/api/decision')
        assert caught.value.code==403 and review.state()['handled']==0
        with pytest.raises(HTTPError) as caught:post('/api/decision',state['request_token'],'https://foreign.invalid')
        assert caught.value.code==403
        with pytest.raises(HTTPError) as caught:post('/api/evaluate',state['request_token'])
        assert caught.value.code==404
        with post('/api/decision',state['request_token']) as response:assert json.load(response)['saved']
        assert review.state()['handled']==1
    finally:server.shutdown();server.server_close();thread.join(timeout=3)
