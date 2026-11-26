"""Check supplemental BGE metric arithmetic from public symbolic inputs only."""
import json
import math
from pathlib import Path
from src.evaluation.metrics import score_query

ROOT=Path(__file__).resolve().parents[1]


def main():
    value=json.loads((ROOT/'results/bge_supplement_v1_20261126.json').read_text(encoding='utf-8'))
    if value['purpose']!='post_publication_bge_supplement_arithmetic':raise ValueError('Unexpected artifact')
    scored=score_query(value['ranking'],value['judgments'],eligible_ids=value['candidate_ids'],include_recall=True)
    for name,expected in value['reported_metrics'].items():
        if scored['metrics'][name] is None or not math.isclose(scored['metrics'][name],expected,abs_tol=1e-12,rel_tol=1e-12):
            raise ValueError('BGE supplement metric mismatch')
    print(json.dumps({'status':'post_publication_bge_arithmetic_reproduced','metrics':scored['metrics'],
                      'new_model_inference':False,'new_labels':0,'original_publication_modified':False},indent=2))


if __name__=='__main__':main()
