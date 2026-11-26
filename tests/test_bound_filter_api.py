"""Synthetic evidence pools and workers only; no model loading or human grades."""
import hashlib
import io
import json
import pytest
from src.data.fact_store import load_bound_facts
from src.demo.server import SearchEngine
from src.retrieval.constraints import parse_explicit_constraints


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def test_binding_checks_corpus_facts_and_original_evidence(tmp_path):
    corpus=tmp_path/'corpus.json';corpus.write_text('[{"poi_id":"synthetic"}]')
    raw=tmp_path/'raw.txt';raw.write_text('synthetic original evidence')
    facts=tmp_path/'facts.json';facts.write_text('{"synthetic":{}}')
    spec={'scope':'source_snapshot_only','corpus_sha256':sha(corpus),'facts_path':'facts.json',
          'facts_sha256':sha(facts),'evidence_sha256':{'raw.txt':sha(raw)}}
    binding=tmp_path/'binding.json';binding.write_text(json.dumps(spec))
    assert set(load_bound_facts(binding,corpus,tmp_path))=={'synthetic'}
    raw.write_text('changed')
    with pytest.raises(ValueError,match='evidence changed'):load_bound_facts(binding,corpus,tmp_path)


@pytest.mark.parametrize('value',[{},[{'field':'quiet','operator':'eq','value':'yes'}],
                                [{'field':'seats','operator':'gte','value':True}],
                                [{'field':'seats','operator':'gte','value':40,'unexpected':True}]])
def test_explicit_parser_rejects_inference_and_malformed_values(value):
    with pytest.raises(ValueError):parse_explicit_constraints(value)


@pytest.fixture
def filtered(tmp_path,monkeypatch):
    corpus=tmp_path/'synthetic.json'
    corpus.write_text(json.dumps([{'poi_id':x,'name':'synthetic '+x,'is_synthetic':True} for x in ('a','b','c')]))
    from src.data.poi import POI
    monkeypatch.setattr('src.data.load_candidates.load_candidates',lambda path:tuple(POI(poi_id=x,name='synthetic '+x,is_synthetic=True) for x in ('a','b','c')))
    run=tmp_path/'run';run.mkdir()
    engine=SearchEngine(corpus,run,space=lambda d:100*1024**3,allow_bge=True)
    engine.source_facts={x:{'seats':{'value':v,'status':'supported' if v is not None else 'unknown','evidence':['synthetic'] if v is not None else []}} for x,v in [('a',50),('b',20),('c',None)]}
    yield engine
    engine.worker=None;engine.close()


def test_same_pool_is_sent_to_both_dense_methods_and_bm25(filtered,monkeypatch):
    constraints=[{'field':'seats','operator':'gte','value':40}]
    class FakeWorker:
        def __init__(self):self.stdin=io.StringIO()
    payloads=[]
    def load(backend):
        filtered.worker=FakeWorker();filtered.worker_info={'type':'ready','backend':backend};return 0
    def receive():
        request=json.loads(filtered.worker.stdin.getvalue());payloads.append(request)
        return {'type':'result','search_ms':0,'rows':[{'poi_id':p,'rank':i+1,'score':1.0,'model':'synthetic'} for i,p in enumerate(request['eligible_ids'])]}
    monkeypatch.setattr(filtered,'_load_encoder',load);monkeypatch.setattr(filtered,'_receive',receive)
    results=[filtered.search(method,'synthetic',constraints=constraints) for method in ('bm25','encoder','bge_m3')]
    assert all([r['poi_id'] for r in result['results']]==['a'] for result in results)
    assert all(result['hard_filter']['unknown_ids']==['c'] for result in results)
    assert all(result['hard_filter']['unmet_ids']==['b'] for result in results)
    assert [r['eligible_ids'] for r in payloads]==[['a'],['a']]


def test_empty_shared_pool_starts_no_worker_and_unknown_does_not_pass(filtered,monkeypatch):
    monkeypatch.setattr(filtered,'_load_encoder',lambda *a:pytest.fail('Empty pool loaded a model'))
    for method in ('bm25','encoder','bge_m3'):
        value=filtered.search(method,'synthetic',constraints=[{'field':'seats','operator':'gte','value':999}])
        assert not value['results'] and value['eligible_candidate_count']==0
        assert value['hard_filter']['unknown_ids']==['c']


def test_unbound_snapshot_refuses_filter_without_guessing(filtered):
    filtered.source_facts=None
    with pytest.raises(ValueError,match='尚未绑定'):filtered.search('bm25','synthetic',constraints=[{'field':'seats','operator':'gte','value':40}])


def test_proposal_http_route_never_starts_retrieval(filtered,monkeypatch):
    import threading
    from http.server import ThreadingHTTPServer
    from urllib.request import Request,urlopen
    from src.demo.server import make_handler
    monkeypatch.setattr(filtered,'search',lambda *a,**k:pytest.fail('Proposal executed retrieval'))
    server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(filtered))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        body=json.dumps({'query':'座位至少50个'},ensure_ascii=False).encode()
        request=Request(f'http://127.0.0.1:{server.server_port}/api/constraints/propose',data=body,headers={'Content-Type':'application/json'})
        with urlopen(request) as response:result=json.load(response)
        assert result['constraints']==[{'field':'seats','operator':'gte','value':50}]
        assert result['requires_user_confirmation'] and not result['models_called']
    finally:
        server.shutdown();server.server_close();thread.join(timeout=3)
