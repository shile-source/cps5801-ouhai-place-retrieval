"""New CPU baseline against immutable Pilot labels; never republishes the original study."""
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from src.data.load_candidates import load_candidates
from src.evaluation.human_pilot import Pilot, sha
from src.evaluation.metrics import score_query
from src.retrieval.keyword import KeywordRetriever
from src.retrieval.bm25 import BM25Retriever, tokenize

ROOT=Path(__file__).resolve().parents[1]


def main():
    protocol_path=ROOT/'configs/keyword_supplement_v1_20261126.json'
    protocol=json.loads(protocol_path.read_text(encoding='utf-8'))
    pilot=Pilot()
    protected={pilot.path/name:sha(pilot.path/name) for name in
               ('corpus.json','packet.json','human_actions.jsonl','evaluation_20261125_183623_491202.json')}
    for key,name in [('source_corpus_sha256','corpus.json'),('source_actions_sha256','human_actions.jsonl'),('source_packet_sha256','packet.json')]:
        if protected[pilot.path/name]!=protocol[key]:raise ValueError('Frozen source mismatch')
    if (ROOT/'results/keyword_supplement_v1_20261126.json').exists():
        raise ValueError('Supplement exists; inspect saved evidence instead of silently overwriting')
    pois=load_candidates(pilot.path/'corpus.json')
    labels=pilot.ratings()
    old=json.loads((pilot.path/'evaluation_20261125_183623_491202.json').read_text(encoding='utf-8'))
    output=ROOT/'outputs'/('keyword_supplement_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    output.mkdir()
    (output/'protocol.json').write_bytes(protocol_path.read_bytes())
    tokenize('初始化共享分词器')  # Shared tokenizer warm-up precedes both index measurements.
    engines={};index_ms={}
    for name,cls in [('keyword_overlap',KeywordRetriever),('bm25',BM25Retriever)]:
        start=perf_counter();engines[name]=cls(pois);index_ms[name]=(perf_counter()-start)*1000
    records=[];latencies=[]
    for qid,q in pilot.queries.items():
        grades={pid:labels[qid,pid]['semantic_grade'] for pid in pilot.records}
        for name,engine in engines.items():
            rows=engine.search(q['text'],len(pois))
            ranking=[r.poi_id for r in rows]
            if set(ranking)!=set(pilot.records):raise ValueError('Incomplete ranking')
            scored=score_query(ranking,grades,eligible_ids=list(pilot.records),include_recall=True)
            records.append({'query_id':qid,'method':name,'ranking':ranking,'scores':[r.score for r in rows],**scored})
            if name=='bm25' and scored['status']=='scored':
                published=next(x for x in old['raw_runs'] if x['query_id']==qid and x['method']=='bm25')['run']['results']
                if ranking!=[r['poi_id'] for r in published]:raise ValueError('BM25 differs from original ranking')
                if any(not math.isclose(r.score,p['score'],abs_tol=1e-10,rel_tol=1e-10) for r,p in zip(rows,published)):
                    raise ValueError('BM25 score mismatch')
        for engine in engines.values():
            for _ in range(protocol['latency']['warmups_per_query']):engine.search(q['text'],5)
        timings={name:[] for name in engines}
        for repeat in range(protocol['latency']['repeats_per_query']):
            order=list(engines) if repeat%2==0 else list(reversed(engines))
            for name in order:
                start=perf_counter();engines[name].search(q['text'],5)
                timings[name].append((perf_counter()-start)*1000)
        for name,values in timings.items():
            ordered=sorted(values)
            latencies.append({'query_id':qid,'method':name,'repeats':len(values),
                              'mean_ms':mean(values),'median_ms':median(values),
                              'p95_nearest_rank_ms':ordered[math.ceil(.95*len(values))-1],
                              'raw_ms':values})
    for path,h in protected.items():
        if sha(path)!=h:raise ValueError('Protected input changed')
    ids=sorted(pilot.records);mapping={pid:f'candidate_{i+1:03}' for i,pid in enumerate(ids)}
    row=next(r for r in records if r['query_id']=='P02' and r['method']=='keyword_overlap')
    artifact={'purpose':'post_publication_keyword_supplement_arithmetic','query_id':'P02',
              'protocol':protocol,'protocol_sha256':sha(protocol_path),
              'source_evaluation_sha256':protected[pilot.path/'evaluation_20261125_183623_491202.json'],
              'implementation_sha256':sha(ROOT/'src/retrieval/keyword.py'),
              'candidate_ids':[mapping[pid] for pid in ids],
              'judgments':{mapping[pid]:labels['P02',pid]['semantic_grade'] for pid in ids},
              'ranking':[mapping[pid] for pid in row['ranking']],'reported_metrics':row['metrics'],
              'excluded_query_count':7,'new_labels':0,'original_publication_modified':False,
              'latency_rows':latencies,'index_build_ms_after_shared_tokenizer_warmup':index_ms,
              'latency_scope':'same-process CPU warm searches; not GPU/model load, network or universal performance',
              'claims_independent_human_ground_truth':False,'claims_confirmatory_experiment':False}
    private={'created_at':datetime.now().astimezone().isoformat(),'protocol':protocol,
             'protected_inputs':{str(p.relative_to(ROOT)):h for p,h in protected.items()},
             'records':records,'public_artifact':artifact,'new_model_inference':False}
    (output/'report.json').write_text(json.dumps(private,ensure_ascii=False,indent=2),encoding='utf-8')
    target=ROOT/'results/keyword_supplement_v1_20261126.json'
    target.write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'outputs/latest_keyword_supplement_20261126.json').write_text(json.dumps({'report':str(output/'report.json'),
        'public_artifact':str(target),'status':'completed_post_publication_exploratory_supplement'},indent=2),encoding='utf-8')
    print(json.dumps({'output':str(output),'metrics':row['metrics'],'latency_means_ms':{
        name:mean(r['mean_ms'] for r in latencies if r['method']==name) for name in engines},
        'bm25_matches_original':True,'new_labels':0,'original_files_unchanged':True}))


if __name__=='__main__':main()
