"""Opt-in snapshot inference; no labels, effectiveness metrics or automatic retries."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--corpus',type=Path,default=ROOT/'data/clean/open_osm_v2_20261126/poi_candidates.json')
    parser.add_argument('--method',choices=['keyword','bm25','encoder','bge_m3'],default='bm25')
    parser.add_argument('--query',required=True)
    parser.add_argument('--top-k',type=int,default=5)
    parser.add_argument('--allow-model-inference',action='store_true')
    args=parser.parse_args()
    if not args.query.strip() or len(args.query)>500 or not 1<=args.top_k<=200:
        raise ValueError('Bounded query and top-k required')
    corpus=args.corpus.resolve()
    if not corpus.is_relative_to(ROOT/'data/clean'):raise ValueError('Use a versioned project snapshot')
    if args.method not in ('keyword','bm25') and not args.allow_model_inference:
        raise ValueError('Model inference is opt-in; inspect prior failures before authorizing a new run')
    from src.data.load_candidates import load_candidates
    pois=load_candidates(corpus)
    if not 1<=len(pois)<=200:raise ValueError('This runner supports1–200 candidates')
    output=ROOT/'outputs'/('snapshot_run_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    output.mkdir(parents=True)
    report={'purpose':'snapshot_functional_retrieval_NOT_effectiveness_evaluation','method':args.method,
            'query':args.query,'candidate_count':len(pois),'new_labels':0,'formal_evaluation':False,
            'corpus_sha256':hashlib.sha256(corpus.read_bytes()).hexdigest()}
    if args.method in ('keyword','bm25'):
        from src.retrieval.bm25 import BM25Retriever
        from src.retrieval.keyword import KeywordRetriever
        retriever = KeywordRetriever if args.method=='keyword' else BM25Retriever
        rows=retriever(pois).search(args.query,args.top_k)
        report.update(status='completed',rows=[{'rank':r.rank,'poi_id':r.poi_id,'score':r.score,'model':r.model} for r in rows])
    else:
        import psutil
        system='C:/' if os.name=='nt' else '/'
        baseline=shutil.disk_usage(system).free
        def guard():
            current=shutil.disk_usage(system).free
            if current<5*1024**3 or baseline-current>1024**3 or shutil.disk_usage(ROOT).free<10*1024**3:
                raise RuntimeError('Storage protection reached; no automatic retry')
        guard();worker=None
        env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',CPS5801_DENSE_LOADER='streamed',
                 CPS5801_BGE_LOADER='streamed',CPS5801_SAFETENSORS_BACKEND='pread',
                 CPS5801_BGE_DIRECT_GPU_LOAD='1',CPS5801_EMBEDDING_PRECISION='float32')
        try:
            with (output/'worker.jsonl').open('x',encoding='utf-8') as stdout,(output/'stderr.log').open('x',encoding='utf-8') as stderr:
                worker=subprocess.Popen([sys.executable,'-u','-m','src.demo.encoder_worker',str(corpus),args.method],
                     cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,text=True,encoding='utf-8')
                worker.stdin.write(json.dumps({'query':args.query,'top_k':min(args.top_k,len(pois))})+'\n');worker.stdin.close()
                deadline=time.monotonic()+180
                while worker.poll() is None:
                    guard()
                    if time.monotonic()>deadline:raise TimeoutError('Own worker timed out; no automatic retry')
                    time.sleep(.1)
            messages=[json.loads(line) for line in (output/'worker.jsonl').read_text(encoding='utf-8').splitlines()]
            if worker.returncode!=0 or [r['type'] for r in messages]!=['ready','result']:
                raise RuntimeError('Model failed; inspect preserved worker evidence')
            report.update(status='completed',configuration=messages[0],rows=messages[1]['rows'])
        except Exception as error:
            report.update(status='stopped_NOT_retried',error=str(error));raise
        finally:
            if worker and worker.poll() is None:
                processes=psutil.Process(worker.pid).children(recursive=True)+[psutil.Process(worker.pid)]
                for process in processes:
                    try:process.terminate()
                    except psutil.NoSuchProcess:pass
                psutil.wait_procs(processes,timeout=10)
            (output/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(output),'status':report['status'],'rows':len(report['rows'])}))


if __name__=='__main__':main()
