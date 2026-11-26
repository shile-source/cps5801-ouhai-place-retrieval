"""Arithmetic check of the separately identified post-publication lexical baseline."""
import json
import math
from pathlib import Path
from src.evaluation.metrics import score_query

ROOT=Path(__file__).resolve().parents[1]


def main():
    value=json.loads((ROOT/'results/keyword_supplement_v1_20261126.json').read_text(encoding='utf-8'))
    if value['purpose']!='post_publication_keyword_supplement_arithmetic':raise ValueError('Unexpected artifact')
    result=score_query(value['ranking'],value['judgments'],eligible_ids=value['candidate_ids'],include_recall=True)
    if result['status']!='scored':raise ValueError('Supplement cannot be scored')
    for name,expected in value['reported_metrics'].items():
        if not math.isclose(result['metrics'][name],expected,rel_tol=1e-12,abs_tol=1e-12):
            raise ValueError('Supplement metric mismatch')
    print(json.dumps({'status':'post_publication_keyword_arithmetic_reproduced','metrics':result['metrics'],
                      'new_inference':False,'new_labels':0,'original_publication_modified':False},indent=2))


if __name__=='__main__':main()
