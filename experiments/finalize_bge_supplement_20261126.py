"""Score one saved successful BGE run; no model calls or label changes."""
import hashlib
import json
from pathlib import Path
from src.evaluation.human_pilot import Pilot,sha
from src.evaluation.metrics import score_query

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'outputs/bge_m3_function_20261126_202906/result.json'


def main():
    pilot=Pilot();pilot.verify()
    if sha(pilot.path/'human_actions.jsonl')!='bb2a2e566e7bb56ebe89f0e6600523e0fabcfe3f8e83796cb937e20860182c09':raise ValueError('Original judgments changed')
    value=json.loads(RUN.read_text(encoding='utf-8'))
    if value['status']!='function_check_passed_NOT_effectiveness_result' or value['approval_tag']!='bounded_copy':raise ValueError('No approved successful run')
    if value['corpus_sha256']!=pilot.packet['source_corpus_sha256']:raise ValueError('Corpus mismatch')
    if not value['synthetic_equivalence']['passed'] or value['ready']['parameter_dtype']!='torch.float32':raise ValueError('Configuration mismatch')
    if len(value['queries'])!=1 or value['queries'][0]['query']!=pilot.queries['P02']['text']:raise ValueError('Query mismatch')
    ranking=[r['poi_id'] for r in value['queries'][0]['rows']]
    if set(ranking)!=set(pilot.records) or len(ranking)!=49:raise ValueError('Full ranking required')
    mapping={pid:f'candidate_{i+1:03}' for i,pid in enumerate(sorted(pilot.records))}
    grades={mapping[pid]:pilot.ratings()['P02',pid]['semantic_grade'] for pid in sorted(pilot.records)}
    anonymous=[mapping[pid] for pid in ranking]
    scored=score_query(anonymous,grades,eligible_ids=list(grades),include_recall=True)
    if scored['status']!='scored':raise ValueError('Incomplete grading')
    artifact={'purpose':'post_publication_bge_supplement_arithmetic','query_id':'P02',
              'source_corpus_sha256':value['corpus_sha256'],'source_packet_sha256':pilot.manifest['packet_sha256'],
              'source_run_sha256':sha(RUN),'candidate_ids':list(grades),'judgments':grades,
              'ranking':anonymous,'reported_metrics':scored['metrics'],
              'model_id':'BAAI/bge-m3','revision':'694b61558aea4ae2512ed8d0e189d5cf8adc2259',
              'ready_configuration':value['ready'],'synthetic_equivalence':{
                  k:v for k,v in value['synthetic_equivalence'].items() if k!='output'},
              'baseline_c_free_bytes':value['baseline_c_free_bytes'],'storage_monitor':value['storage_monitor'],
              'query_search_ms_single_observation':value['queries'][0]['search_ms'],
              'load_timing_scope':'ready.load_ms includes the synthetic equivalence precheck and model construction; not an isolated model-load benchmark',
              'precision':'float32','pooling':'published_CLS_dense_only','host_copy_budget_bytes':16*1024**2,
              'new_labels':0,'original_publication_modified':False,'excluded_query_count':7,
              'claims_independent_human_ground_truth':False,'claims_confirmatory_experiment':False,
              'interpretation':'Single exposed named query; added after original publication. No general superiority or robust latency claim.'}
    target=ROOT/'results/bge_supplement_v1_20261126.json'
    body=json.dumps(artifact,indent=2)+'\n'
    if target.exists() and target.read_text(encoding='utf-8')!=body:raise ValueError('Version existing supplement instead of overwriting')
    target.write_text(body,encoding='utf-8')
    print(json.dumps({'status':'saved_bge_ranking_scored_without_inference','metrics':scored['metrics'],'artifact':str(target),'new_labels':0}))


if __name__=='__main__':main()
