"""Export pinned artifact metadata and anonymous metric inputs, never source text/logs."""
import json
from pathlib import Path
from src.evaluation.human_pilot import Pilot,sha
from src.evaluation.metrics import score_query

ROOT=Path(__file__).resolve().parents[1]


def save_once(path,value):
    text=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    if path.exists() and path.read_text(encoding='utf-8')!=text:
        raise ValueError('Existing reproduction artifact differs; version rather than overwrite')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')


def main():
    model_specs={}
    for key,folder in [('encoder','paraphrase-multilingual-mpnet-base-v2'),('bge_m3','bge-m3')]:
        manifests=list((ROOT/'models'/folder).glob('*/deployment_manifest.json'))
        if len(manifests)!=1:raise ValueError('Explicit unique pinned model required')
        manifest=manifests[0];value=json.loads(manifest.read_text(encoding='utf-8'))
        files=[]
        for row in value.get('files',value.get('completed',[])):
            name=row.get('file') or Path(row['path']).relative_to(manifest.parent).as_posix()
            files.append({'file':name,'bytes':row['bytes'],'sha256':row['sha256']})
        model_specs[key]={'id':value['model_id'],'revision':value['revision'],
                          'directory':manifest.parent.relative_to(ROOT).as_posix(),
                          'license':'MIT' if key=='bge_m3' else 'Apache-2.0','files':files}
    save_once(ROOT/'configs/model_artifacts.json',{'models':model_specs,'weights_in_repository':False})
    pilot=Pilot();pilot.verify()
    if sha(pilot.path/'human_actions.jsonl')!='bb2a2e566e7bb56ebe89f0e6600523e0fabcfe3f8e83796cb937e20860182c09':
        raise ValueError('Published source log changed')
    value=json.loads((pilot.path/'evaluation_20261125_183623_491202.json').read_text(encoding='utf-8'))
    ids=sorted(pilot.records);mapping={pid:f'candidate_{i+1:03}' for i,pid in enumerate(ids)}
    grades={mapping[pid]:pilot.ratings()['P02',pid]['semantic_grade'] for pid in ids}
    runs=[]
    for item in value['raw_runs']:
        if item['query_id']!='P02':raise ValueError('Unexpected published eligible query')
        ranking=[mapping[row['poi_id']] for row in item['run']['results']]
        check=score_query(ranking,grades,eligible_ids=list(grades),include_recall=True)
        saved=next(row for row in value['per_query'] if row['query_id']=='P02' and row['method']==item['method'])
        if any(check['metrics'][m]!=saved[m] for m in check['metrics']):raise ValueError('Metric audit mismatch')
        runs.append({'method':item['method'],'ranking':ranking,'reported_metrics':check['metrics']})
    save_once(ROOT/'results/pilot_metric_inputs.json',{
        'purpose':'published_metric_arithmetic_reproduction_NOT_new_model_inference',
        'query_id':'P02','query_type':'named_lexical','source_corpus_sha256':pilot.packet['source_corpus_sha256'],
        'source_packet_sha256':pilot.manifest['packet_sha256'],
        'source_evaluation_sha256':sha(pilot.path/'evaluation_20261125_183623_491202.json'),
        'identifiers':'bijective anonymous tokens replacing original source record IDs',
        'contains_POI_text_coordinates_or_annotator_names':False,
        'candidate_ids':list(grades),'judgments':grades,'runs':runs,
        'excluded_query_count':7,'unknown_pair_count_in_original_packet':43,
        'full_packet_latest_assisted_judgments':23,
        'claims_independent_human_ground_truth':False})
    functional=json.loads((ROOT/'outputs/three_method_live_check_20261125_201215/summary.json').read_text(encoding='utf-8'))
    functional['purpose']='previous_function_check_NOT_effectiveness_or_performance_benchmark'
    functional.pop('labels_unchanged_sha256',None)
    functional['metadata_correction']='Encoder used streamed pread despite the original ready payload reporting mmap; original local evidence retained.'
    functional['later_service_state']='BGE stopped after a later supplemental synthetic check triggered protection; no automatic retry'
    save_once(ROOT/'results/three_method_function.json',functional)
    print(json.dumps({'model_artifact_specs':len(model_specs),'metric_methods':len(runs),'new_labels':0}))


if __name__=='__main__':main()
