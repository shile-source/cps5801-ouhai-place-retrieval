"""Recompute saved published metrics from anonymous symbolic inputs; no inference."""
import argparse
import json
import math
from pathlib import Path
from src.evaluation.metrics import score_query

ROOT=Path(__file__).resolve().parents[1]


def reproduce(path):
    value=json.loads(Path(path).read_text(encoding='utf-8'))
    if value.get('purpose')!='published_metric_arithmetic_reproduction_NOT_new_model_inference':
        raise ValueError('Unexpected reproduction artifact')
    rows=[]
    for row in value['runs']:
        result=score_query(row['ranking'],value['judgments'],eligible_ids=value['candidate_ids'],include_recall=True)
        for metric,expected in row['reported_metrics'].items():
            actual=result['metrics'][metric]
            if actual is None or not math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-12):
                raise ValueError('Published metric differs from saved inputs: '+metric)
        rows.append({'query_id':value['query_id'],'method':row['method'],**result['metrics']})
    return {'status':'published_metric_arithmetic_reproduced','new_inference':False,'rows':rows,
            'eligible_queries':1,'excluded_queries':7,
            'limitation':'Symbolic inputs reproduce the arithmetic, not acquisition or original model inference.'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=ROOT/'results/pilot_metric_inputs.json')
    args=parser.parse_args()
    print(json.dumps(reproduce(args.input),indent=2))


if __name__=='__main__':main()
