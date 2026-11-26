"""Live API tests with explicitly synthetic test records; no model inference."""
from http.server import ThreadingHTTPServer
import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import pytest

from src.demo.server import SearchEngine, StorageGuardError, make_handler, map_preview, validate_request


@pytest.mark.parametrize('change', [
    {'poi_id': 'osm_way_1'}, {'original_crs': 'UNKNOWN'},
    {'latitude': 7.0}, {'longitude': float('nan')}, {'latitude': True},
])
def test_map_preview_withholds_unsupported_coordinates(change):
    record = {'poi_id': 'osm_node_1', 'original_crs': 'WGS84',
              'latitude': 27.97, 'longitude': 120.61}
    assert map_preview(record)['status'] == 'unverified_osm_point'
    assert map_preview(record | change) is None

@pytest.mark.parametrize('value', [None, [], {}, {'method':'other','query':'书房'},
    {'method':'bm25','query':''}, {'method':'encoder','query':' '},
    {'method':'bm25','query':1}, {'method':'bm25','query':'书'*501}])
def test_invalid_live_request_rejected(value):
    with pytest.raises(ValueError):
        validate_request(value)

def test_request_trims_query_and_retains_method():
    assert validate_request({'method':'encoder','query':'  潘桥书房  '}) == ('encoder','潘桥书房')

@pytest.fixture
def engine(tmp_path):
    source=tmp_path/'synthetic_only_for_unit_test.json'
    source.write_text(json.dumps([
        {'poi_id':'synthetic_book','name':'模拟测试书房','category':'城市书房','address':'模拟路',
         'description':'仅单元测试模拟文本：藏书。','is_synthetic':False},
        {'poi_id':'synthetic_park','name':'模拟测试公园','category':'公园','address':'',
         'description':'仅单元测试模拟文本。','is_synthetic':False}],ensure_ascii=False),encoding='utf-8')
    run=tmp_path/'run';run.mkdir()
    obj=SearchEngine(source,run,space=lambda d:(2 if d=='C' else 50)*1024**3)
    yield obj
    obj.close()

def test_low_space_blocks_encoder_before_worker_start(engine):
    with pytest.raises(StorageGuardError,match='保护线'):
        engine.search('encoder','书房')
    assert engine.worker is None


def test_explicit_model_pause_blocks_start_even_with_space(engine,monkeypatch):
    engine.encoder_enabled=False
    monkeypatch.setattr('src.demo.server.subprocess.Popen',lambda *a,**k:pytest.fail('Paused model started'))
    with pytest.raises(RuntimeError,match='已暂停'):
        engine.search('encoder','synthetic query')
    assert engine.status()['encoder_state']=='disabled'
    assert engine.worker is None

def test_bm25_returns_live_query_metadata_and_stable_ids(engine):
    first=engine.search('bm25','书房')
    second=engine.search('bm25','书房')
    assert first['live_computation'] and first['saved_results_used'] is False
    assert first['request_id'] != second['request_id']
    assert [r['poi_id'] for r in first['results']] == [r['poi_id'] for r in second['results']]
    assert first['results'][0]['poi_id']=='synthetic_book'
    assert '书房' in first['results'][0]['matched_tokens']
    assert first['search_ms']>=0


def test_keyword_api_computes_without_a_model_even_when_models_are_paused(engine,monkeypatch):
    engine.encoder_enabled=False
    monkeypatch.setattr('src.demo.server.subprocess.Popen',lambda *a,**k:pytest.fail('Lexical method started GPU'))
    assert validate_request({'method':'keyword','query':'书房'})==('keyword','书房')
    result=engine.search('keyword','书房')
    assert result['results'][0]['poi_id']=='synthetic_book'
    assert result['results'][0]['model']=='keyword_overlap'
    assert result['live_computation'] is True and result['saved_results_used'] is False
    assert result['dense_configuration'] is None and engine.worker is None

def test_unknown_quiet_attribute_is_not_claimed(engine):
    result=engine.search('bm25','安静学习')
    assert any('不能证明' in w for w in result['warnings'])
    assert all('待独立核验' in r['verification_status'] for r in result['results'])

def test_status_never_loads_encoder(engine):
    status=engine.status()
    assert status['live_backend'] and status['saved_results_used'] is False
    assert not status['encoder_ready'] and engine.worker is None


def test_bge_validation_and_storage_guard_before_worker(engine,monkeypatch):
    assert validate_request({'method':'bge_m3','query':'合成查询'})==('bge_m3','合成查询')
    engine.allow_bge=True
    monkeypatch.setattr('src.demo.server.subprocess.Popen',lambda *a,**k:pytest.fail('Storage guard bypassed'))
    with pytest.raises(StorageGuardError):engine.search('bge_m3','合成查询')
    assert engine.worker is None


def test_unavailable_bge_does_not_kill_other_active_worker(engine):
    class FakeWorker:
        terminated=False
        def poll(self):return 0 if self.terminated else None
        def terminate(self):self.terminated=True
        def wait(self,timeout):return 0
    worker=FakeWorker();engine.worker=worker
    with pytest.raises(ValueError,match='未启用'):engine.search('bge_m3','合成查询')
    assert not worker.terminated
    assert engine.worker_error is None


def test_dense_switch_releases_previous_worker_and_keeps_common_corpus(engine,monkeypatch):
    import io
    class FakeWorker:
        def __init__(self,messages=()):self.terminated=False;self.stdin=io.StringIO();self.stdout=iter(messages)
        def poll(self):return 0 if self.terminated else None
        def terminate(self):self.terminated=True
        def wait(self,timeout):return 0
    engine.space=lambda drive:50*1024**3
    engine.allow_bge=True;engine.safe_streaming=True
    old=FakeWorker();engine.worker=old
    rows=[{'rank':i+1,'poi_id':p.poi_id,'score':1/(i+1),'model':'synthetic_bge'} for i,p in enumerate(engine.pois)]
    new=FakeWorker([json.dumps({'type':'ready','load_ms':1}),json.dumps({'type':'result','rows':rows,'search_ms':1})])
    def start(command,**kwargs):
        assert command[-1]=='bge_m3'
        assert kwargs['env']['CPS5801_BGE_LOADER']=='streamed'
        return new
    monkeypatch.setattr('src.demo.server.subprocess.Popen',start)
    result=engine.search('bge_m3','合成查询')
    assert old.terminated and engine.worker is new
    assert result['corpus_sha256']==engine.corpus_hash
    assert {r['poi_id'] for r in result['results']}=={p.poi_id for p in engine.pois}
    assert engine.status()['dense_states']['bge_m3']=='ready'
    assert engine.status()['encoder_ready'] is False


def test_dead_encoder_is_reported_stopped_and_is_not_restarted(engine, monkeypatch):
    from types import SimpleNamespace
    engine.space = lambda drive: 50 * 1024**3
    engine.worker = SimpleNamespace(poll=lambda: 1)
    monkeypatch.setattr('src.demo.server.subprocess.Popen', lambda *a, **k: pytest.fail('Failed worker was restarted'))
    assert engine.status()['encoder_state'] == 'stopped'
    with pytest.raises(RuntimeError, match='停止'):
        engine.search('encoder', 'synthetic query')
    assert not engine.status()['encoder_ready']


def test_inventory_navigation_metadata_does_not_replace_shared_address(engine):
    record = engine.places()['places'][0]
    original = engine.records[record['poi_id']]
    assert record['address'] == original['address']
    assert record['navigation']['snapshot_address'] == original['address']
    assert record['navigation']['entrance_verified'] is False


def test_inventory_exposes_same_corpus_without_starting_model(server, engine):
    with urlopen(server + '/api/places', timeout=5) as response:
        data = json.load(response)
    assert data['corpus_sha256'] == engine.corpus_hash
    assert {row['poi_id'] for row in data['places']} == {row.poi_id for row in engine.pois}
    assert all('score' not in row and 'rank' not in row for row in data['places'])
    assert engine.worker is None


def test_full_candidate_ranking_keeps_same_ids(engine):
    result=engine.search('bm25','书房',top_k=len(engine.pois))
    assert len(result['results'])==len(engine.pois)
    assert {r['poi_id'] for r in result['results']}=={p.poi_id for p in engine.pois}


@pytest.mark.parametrize('size',[0,-1,True,'49',1001])
def test_invalid_requested_ranking_size(engine,size):
    with pytest.raises(ValueError):engine.search('bm25','书房',top_k=size)

@pytest.fixture
def server(engine):
    service=ThreadingHTTPServer(('127.0.0.1',0),make_handler(engine))
    thread=threading.Thread(target=service.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{service.server_port}'
    service.shutdown();service.server_close();thread.join(timeout=5)

def send(url, value, origin=None):
    headers={'Content-Type':'application/json'}
    if origin is not None: headers['Origin']=origin
    return urlopen(Request(url+'/api/search',data=json.dumps(value).encode(),headers=headers),timeout=5)

def test_http_search_uses_requested_query(server):
    with send(server,{'method':'bm25','query':'书房'}) as response:
        data=json.load(response)
    assert data['query']=='书房' and data['saved_results_used'] is False

def test_http_storage_error_is_explicit_and_not_saved_results(server):
    with pytest.raises(HTTPError) as error:
        send(server,{'method':'encoder','query':'书房'})
    assert error.value.code==409
    assert json.load(error.value)['code']=='STORAGE_GUARD'

def test_http_foreign_origin_is_rejected(server):
    with pytest.raises(HTTPError) as error:
        send(server,{'method':'bm25','query':'书房'},'https://unrelated.invalid')
    assert error.value.code==403

def test_http_does_not_serve_project_files(server):
    with pytest.raises(HTTPError) as error:
        urlopen(server+'/../../AGENTS.md',timeout=5)
    assert error.value.code==404


@pytest.mark.parametrize('path,kind', [('/', 'text/html'), ('/map.js', 'application/javascript'),
    ('/map.css', 'text/css'), ('/vendor/leaflet-1.9.4/leaflet.js', 'application/javascript'),
    ('/vendor/leaflet-1.9.4/leaflet.css', 'text/css')])
def test_product_map_static_assets_and_referrer_policy(server, path, kind):
    with urlopen(server + path, timeout=5) as response:
        assert response.headers.get_content_type() == kind
        assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
        assert 'https://tile.openstreetmap.org' in response.headers['Content-Security-Policy']
        assert len(response.read()) > 100


def test_worker_exit_does_not_hide_recorded_storage_failure(engine):
    from types import SimpleNamespace
    engine.worker = SimpleNamespace(poll=lambda: 1)
    engine.worker_error = 'synthetic storage protection reason'
    with pytest.raises(StorageGuardError, match='synthetic storage protection reason'):
        engine._receive(timeout=.1)
