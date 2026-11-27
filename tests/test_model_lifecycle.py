import json
from types import SimpleNamespace
import pytest
from src.demo.server import SearchEngine


class Worker:
    terminated=False
    def poll(self):return 0 if self.terminated else None
    def terminate(self):self.terminated=True
    def wait(self,timeout):return 0


def engine(tmp_path,checkpoint=True):
    source=tmp_path/'synthetic.json'
    source.write_text(json.dumps([{'poi_id':'synthetic','name':'Synthetic only','category':'fixture',
                                  'address':'','description':'Unit test only','is_synthetic':False}]))
    run=tmp_path/'run';run.mkdir(exist_ok=True)
    obj=SearchEngine(source,run,space=lambda d:50*1024**3,allow_bge=True,
        safe_streaming=True,dense_precision='float16',dense_idle_seconds=60,
        stop_checkpoint=tmp_path/'stopped.json' if checkpoint else None)
    obj.stop_monitor.set()  # Drive the lifecycle deterministically; do not sleep in unit tests.
    return obj


def activate(obj):
    worker=Worker();obj.worker=worker;obj.worker_backend='bge_m3'
    obj.worker_info={'load_ms':1};obj.model_baseline=50*1024**3;obj.last_dense_activity=100
    return worker


def test_healthy_idle_release_is_not_a_failure_or_model_retry(tmp_path):
    obj=engine(tmp_path);worker=activate(obj)
    obj._monitor_once(now=159);assert not worker.terminated
    obj._monitor_once(now=160)
    assert worker.terminated and obj.worker is None and obj.model_baseline is None
    assert obj.status()['dense_states']['bge_m3']=='not_loaded'
    assert obj.idle_release_count==1 and not obj.backend_failures
    assert not obj.stop_checkpoint.exists()
    obj.close()


def test_idle_timeout_does_not_interrupt_an_active_request_or_load(tmp_path):
    obj=engine(tmp_path);worker=activate(obj)
    obj.lock.acquire()
    try:obj._monitor_once(now=1000);assert not worker.terminated
    finally:obj.lock.release()
    obj.last_dense_activity=None;obj._monitor_once(now=1000)
    assert not worker.terminated
    obj.close()


def test_storage_guard_wins_over_idle_release_and_persists_across_restart(tmp_path,monkeypatch):
    obj=engine(tmp_path);worker=activate(obj)
    obj.space=lambda d:(48 if d=='C' else 50)*1024**3
    obj._monitor_once(now=1000)
    assert worker.terminated and obj.idle_release_count==0
    assert 'bge_m3' in obj.backend_failures and obj.stop_checkpoint.exists()
    saved=json.loads(obj.stop_checkpoint.read_text(encoding='utf-8'))
    assert saved['resource_sample']['baseline_c_bytes']==50*1024**3
    obj.close()
    restored=engine(tmp_path)
    monkeypatch.setattr('src.demo.server.subprocess.Popen',lambda *a,**k:pytest.fail('Recorded failure retried'))
    with pytest.raises(RuntimeError,match='停止'):restored._load_encoder('bge_m3')
    restored.close()


def test_unexpected_worker_death_is_not_reclassified_as_healthy_idle(tmp_path):
    obj=engine(tmp_path);worker=activate(obj);worker.terminated=True
    obj._monitor_once(now=1000)
    assert obj.idle_release_count==0 and obj.stop_checkpoint.exists()
    assert obj.status()['dense_states']['bge_m3']=='stopped'
    obj.close()


def test_future_request_can_load_only_after_clean_release(tmp_path,monkeypatch):
    import io
    obj=engine(tmp_path);activate(obj);obj._monitor_once(now=160)
    calls=[]
    class NewWorker(Worker):
        def __init__(self):self.stdin=io.StringIO();self.stdout=iter([json.dumps({'type':'ready','load_ms':2})]);self.terminated=False
    monkeypatch.setattr('src.demo.server.subprocess.Popen',lambda *a,**k:(calls.append(a),NewWorker())[1])
    assert obj._load_encoder('bge_m3')==2
    assert len(calls)==1 and not obj.backend_failures
    obj.close()
