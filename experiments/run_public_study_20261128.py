"""One bounded live public-source comparison, with one cold model load and no retry."""
from datetime import datetime
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import random
import shutil
import time
from urllib.request import urlopen
import psutil
from src.demo.server import SearchEngine
from src.evaluation.public_engineering import summarize

ROOT=Path(__file__).resolve().parents[1]
JOB=ROOT/'outputs/public_study_20261128'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--fresh-workstation',action='store_true',help='Explicit one-load check on a fresh public checkout, without claiming author-workstation repair validation')
    args=parser.parse_args()
    spec_path=ROOT/'configs/public_functional_study_20261128.json'
    spec=json.loads(spec_path.read_text(encoding='utf-8'))
    queries=json.loads((ROOT/spec['query_path']).read_text(encoding='utf-8'))
    if digest(ROOT/spec['corpus_path'])!=spec['corpus_sha256'] or digest(ROOT/spec['query_path'])!=spec['query_sha256']:
        raise ValueError('Frozen inputs changed')
    from src.demo.runtime_policy import validated
    if (ROOT/'data/clean/activity_review_v0_6_20261126/poi_candidates.json').exists():
        if not validated():raise ValueError('Existing changed lifecycle receipt is no longer valid; no retry')
        preflight='author_workstation_validated_lifecycle'
    else:
        if not args.fresh_workstation:raise ValueError('Public checkout requires explicit --fresh-workstation bounded GPU check')
        if (ROOT/'outputs/residency_repair_20261127/runtime_stop.json').exists():
            raise ValueError('Existing failure cannot be bypassed by fresh-workstation mode')
        preflight='fresh_workstation_one_load_no_prior_author_receipt_claim'
    # Never displace a live user search or another model worker.
    try:
        with urlopen('http://127.0.0.1:8770/api/status',timeout=5) as response:live=json.load(response)
        if live['active_dense_backend'] is not None:raise ValueError('Wait for healthy live service idle release')
    except OSError as exc:
        from urllib.error import URLError
        reason=exc.reason if isinstance(exc,URLError) else exc
        if not isinstance(reason,ConnectionRefusedError):raise
    active=[]
    for process in psutil.process_iter(['cmdline']):
        args=process.info['cmdline'] or []
        if 'src.demo.encoder_worker' in args:active.append(process.pid)
    if active:raise ValueError('Another project model worker is active')
    if shutil.disk_usage('C:/').free<5*1024**3 or shutil.disk_usage('D:/').free<10*1024**3:
        raise ValueError('Storage preflight did not pass')
    JOB.mkdir(exist_ok=True)
    with (JOB/'single_run_claim.json').open('x',encoding='utf-8') as file:
        json.dump({'authorization':'user requested completion of all remaining non-human project steps',
            'protocol_sha256':digest(spec_path),'maximum_model_loads':1,'automatic_retries':0,
            'claimed_at':datetime.now().astimezone().isoformat(),'preflight':preflight},file)
    engine=SearchEngine(ROOT/spec['corpus_path'],JOB,min_c_gib=5,encoder_enabled=True,
        allow_bge=True,safe_streaming=True,facts_binding=ROOT/spec['facts_binding'],
        dense_precision='float16',dense_idle_seconds=60,stop_checkpoint=JOB/'runtime_stop.json')
    raw=JOB/'observations.jsonl';observations=[];worker_pids=[]
    state={'status':'running','started_at':datetime.now().astimezone().isoformat(),
        'protocol_sha256':digest(spec_path),'corpus_sha256':spec['corpus_sha256'],
        'query_sha256':spec['query_sha256'],'new_human_labels':0,'model_loads':0}
    def call(method,query,phase,**metadata):
        response=engine.search(method,query,top_k=spec['top_k'],constraints=metadata.pop('constraints',None))
        if response['load_ms']>0:
            state['model_loads']+=1
            if state['model_loads']>1:raise ValueError('Unexpected second model load; stop')
        if phase!='cold' and state['model_loads'] and response['load_ms']>0:raise ValueError('Unexpected reload')
        if response['corpus_sha256']!=spec['corpus_sha256']:raise ValueError('Wrong corpus')
        row={key:response[key] for key in ('method','query','executed_at','load_ms','search_ms','elapsed_ms','corpus_sha256')}
        row.update(phase=phase,**metadata,
            results=[{k:r[k] for k in ('poi_id','rank','score')} for r in response['results']])
        if phase=='constraint':
            pool=response['hard_filter'];row.update(eligible_ids=pool['eligible_ids'],
                unknown_count=len(pool['unknown_ids']),unmet_count=len(pool['unmet_ids']))
        if phase=='cold':
            row['dense_configuration']=response['dense_configuration']
            worker_pids.extend([engine.worker.pid,*[p.pid for p in psutil.Process(engine.worker.pid).children(recursive=True)]])
        observations.append(row)
        with raw.open('a',encoding='utf-8') as file:file.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
        return row
    try:
        print('Frozen public inputs verified; starting one cold BGE load.',flush=True)
        call('bge_m3',queries['items'][0]['text'],'cold')
        for method in spec['methods']:call(method,queries['items'][0]['text'],'warmup')
        rng=random.Random(spec['order_seed'])
        for repeat in range(spec['repeats_per_query']):
            items=list(queries['items']);rng.shuffle(items)
            for query in items:
                methods=list(spec['methods']);rng.shuffle(methods)
                for method in methods:call(method,query['text'],'measurement',query_id=query['query_id'],repeat=repeat)
            print(f'Measured repeat {repeat+1}/{spec["repeats_per_query"]}: {len(items)*len(spec["methods"])} requests.',flush=True)
        for case in queries['constraint_checks']:
            for method in spec['methods']:
                call(method,case['query'],'constraint',case_id=case['case_id'],constraints=case['constraints'])
        report=summarize(spec,queries,observations)
        report.update(corpus_sha256=spec['corpus_sha256'],query_sha256=spec['query_sha256'],
            protocol_sha256=digest(spec_path),raw_observations_sha256=digest(raw),
            hardware={'platform':platform.platform(),'cpu':platform.processor(),'ram_bytes':psutil.virtual_memory().total},
            packages={name:importlib.metadata.version(name) for name in ('torch','transformers','sentence-transformers','accelerate','psutil')},
            dense_configuration=observations[0]['dense_configuration'])
        public_raw=ROOT/'results/public_engineering_observations_20261128.jsonl'
        public_result=ROOT/'results/public_engineering_20261128.json'
        # A fresh public reproduction preserves shipped measurements. Its own results
        # stay beside its single-run claim rather than replacing the paper's inputs.
        target=JOB/'reproduced_summary.json' if public_raw.exists() or public_result.exists() else public_result
        if target==public_result:public_raw.write_bytes(raw.read_bytes())
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        state.update(status='completed_one_load_no_retry',observations=len(observations),report=str(target.relative_to(ROOT)),preflight=preflight)
    except Exception as error:
        state.update(status='stopped_no_retry',error=str(error));raise
    finally:
        engine.close()
        deadline=time.monotonic()+8
        while any(psutil.pid_exists(pid) for pid in worker_pids) and time.monotonic()<deadline:time.sleep(.2)
        state.update(finished_at=datetime.now().astimezone().isoformat(),worker_pids=worker_pids,
            model_processes_exited=all(not psutil.pid_exists(pid) for pid in worker_pids),
            c_free_bytes=shutil.disk_usage('C:/').free,d_free_bytes=shutil.disk_usage('D:/').free)
        (JOB/'status.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    if not state['model_processes_exited']:raise RuntimeError('Model process exit not confirmed')
    print(json.dumps(state),flush=True)


if __name__=='__main__':main()
