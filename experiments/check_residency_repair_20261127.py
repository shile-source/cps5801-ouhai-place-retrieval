"""One newly authorized changed-lifecycle check: two loads, two clean idle releases."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import Request,urlopen
import psutil
from src.demo.runtime_policy import identity,JOB,STOP

ROOT=Path(__file__).resolve().parents[1]
CORPUS='data/clean/activity_review_v0_6_20261126/poi_candidates.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def get(path):
    with urlopen('http://127.0.0.1:8770'+path,timeout=5) as response:return json.load(response)


def query(text):
    request=Request('http://127.0.0.1:8770/api/search',
        data=json.dumps({'method':'bge_m3','query':text,'top_k':10,'constraints':[]}).encode(),
        headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8770'},method='POST')
    with urlopen(request,timeout=150) as response:value=json.load(response)
    if value['live_computation'] is not True or value['saved_results_used'] is not False:
        raise ValueError('Live computation required')
    if len(value['results'])!=10 or value['corpus_sha256']!=identity()['corpus_sha256']:
        raise ValueError('Wrong result count or snapshot')
    return value


def wait_idle(count):
    end=time.monotonic()+80
    while time.monotonic()<end:
        s=get('/api/status')
        if s['dense_states']['bge_m3']=='stopped' or STOP.exists():
            raise RuntimeError('Protection reached; stop without retry')
        if s['idle_release_count']==count and s['active_dense_backend'] is None:
            if s['dense_states']['bge_m3']!='not_loaded':raise ValueError('Incorrect clean-release state')
            return s
        time.sleep(1)
    raise TimeoutError('Healthy model did not release within the bounded idle interval')


def main():
    JOB.mkdir(exist_ok=True)
    approval=json.loads((JOB/'approval.json').read_text(encoding='utf-8'))
    if approval['identity']!=identity() or approval['maximum_model_loads']!=2:
        raise ValueError('Approval does not bind this changed configuration')
    if STOP.exists():raise ValueError('New strategy already stopped; no retry')
    with (JOB/'single_check_claim.json').open('x',encoding='utf-8') as file:
        json.dump({'claimed_at':datetime.now().astimezone().isoformat(),'automatic_retries':0},file)
    original_stop=ROOT/'outputs/model_stop_checkpoint_20261127.json'
    original_labels=ROOT/'data/labels/pilot_human_v0_1_20261102/human_actions.jsonl'
    report={'identity':identity(),'started':datetime.now().astimezone().isoformat(),
            'old_failure_sha256':sha(original_stop),'labels_sha256':sha(original_labels),
            'new_human_actions':0,'system_settings_changed':False,'automatic_retries':0,'status':'running'}
    old=get('/api/status')
    if old['active_dense_backend'] is not None or old['dense_states']['bge_m3']!='stopped':
        raise ValueError('Expected the already failed project search service, without an active model')
    listeners=[c for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port==8770]
    if len(listeners)!=1:raise ValueError('Unexpected listeners')
    owned=psutil.Process(listeners[0].pid);cmd=owned.cmdline()
    if owned.cwd().lower()!=str(ROOT).lower() or 'src.demo.server' not in cmd or not Path(cmd[0]).resolve().is_relative_to(ROOT):
        raise ValueError('Listener is not the expected project server')
    report['old_server_pid']=owned.pid
    # This replaces a failed service with a materially changed, explicitly authorized strategy.
    owned.terminate();owned.wait(timeout=10)
    with (JOB/'server_stdout.log').open('x',encoding='utf-8') as stdout,(JOB/'server_stderr.log').open('x',encoding='utf-8') as stderr:
        subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Start-Project.ps1'),
            '-u','-m','src.demo.server','--port','8770','--corpus',CORPUS,'--enable-bge','--safe-streaming',
            '--dense-precision','float16','--dense-idle-seconds','60','--stop-checkpoint',str(STOP),
            '--facts-binding','configs/activity_v0_6_facts_binding.json'],cwd=ROOT,
            stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        for _ in range(40):
            try:s=get('/api/status');break
            except OSError:time.sleep(.25)
        else:raise TimeoutError('Changed service did not start; no restart')
        if s['dense_idle_seconds']!=60 or s['candidate_count']!=151:raise ValueError('Wrong configuration')
        print('Changed service ready; starting first bounded live model load.',flush=True)
        first=query('想找有篮球运动项目的运动场')
        warm=query('想找KTV，和朋友唱歌')
        assert warm['load_ms']==0
        report.update(first=first,warm=warm)
        print('First load and warm query passed; verifying healthy automatic idle release.',flush=True)
        idle1=wait_idle(1);report['first_idle_state']=idle1
        print('First model process released; starting the second explicitly bounded load.',flush=True)
        second=query(first['query'])
        assert second['load_ms']>0
        assert [r['poi_id'] for r in first['results']]==[r['poi_id'] for r in second['results']]
        difference=max(abs(a['score']-b['score']) for a,b in zip(first['results'],second['results']))
        if difference>1e-5:raise ValueError('Unexpected numeric difference across clean reload')
        report.update(second=second,maximum_repeat_score_difference=difference)
        print('Second load passed; verifying the second idle release.',flush=True)
        report['second_idle_state']=wait_idle(2)
        report.update(status='passed_two_loads_and_two_healthy_idle_releases',maximum_model_loads=2)
    except Exception as error:
        report.update(status='check_stopped_no_automatic_retry',error=str(error))
        # Avoid leaving a model resident after an invalid or incomplete check.
        for process in psutil.process_iter(['cmdline']):
            args=process.info['cmdline'] or []
            if 'src.demo.encoder_worker' in args and Path(args[0]).resolve().is_relative_to(ROOT):
                process.terminate()
        raise
    finally:
        report.update(finished=datetime.now().astimezone().isoformat(),
            original_failure_retained=sha(original_stop)==report['old_failure_sha256'],
            original_labels_unchanged=sha(original_labels)==report['labels_sha256'])
        (JOB/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if not report['original_failure_retained'] or not report['original_labels_unchanged']:
        raise ValueError('Protected evidence changed')
    print(json.dumps({'status':report['status'],'first_load_ms':first['load_ms'],
        'warm_search_ms':warm['search_ms'],'second_load_ms':second['load_ms'],
        'idle_releases':2,'repeat_max_score_difference':difference,'new_human_actions':0}),flush=True)


if __name__=='__main__':main()
