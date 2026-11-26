"""Verify why reviewed P02 is excluded, using public anonymous saved inputs."""
import json
from pathlib import Path
from src.evaluation.metrics import score_query

ROOT=Path(__file__).resolve().parents[1]


def main():
    value=json.loads((ROOT/'results/post_review_sensitivity_v1_20261126.json').read_text(encoding='utf-8'))
    old=json.loads((ROOT/'results/pilot_metric_inputs.json').read_text(encoding='utf-8'))
    runs={r['method']:r['ranking'] for r in old['runs']}
    for method,file in [('keyword_overlap','keyword_supplement_v1_20261126.json'),('bge_m3','bge_supplement_v1_20261126.json')]:
        runs[method]=json.loads((ROOT/'results'/file).read_text(encoding='utf-8'))['ranking']
    results={}
    for method,ranking in runs.items():
        score=score_query(ranking,value['post_review_P02_judgments'],eligible_ids=old['candidate_ids'],include_recall=True)
        if score['status']!='excluded' or any(x is not None for x in score['metrics'].values()):raise ValueError('Unknown cannot yield numeric effectiveness')
        results[method]=score['status']
    assert value['eligible_after']==[] and value['after_numeric']+value['after_unknown']==392
    assert sum(r['after_unknown'] for r in value['coverage'])==value['after_unknown']
    assert value['unknown_review_decisions']+value['numeric_review_decisions']==value['reviewed_pairs']==12
    print(json.dumps({'status':'post_review_exclusion_reproduced_without_imputation','methods':results,
                      'numeric_effectiveness_metrics':None,'new_model_inference':False,'new_labels':0},indent=2))


if __name__=='__main__':main()
