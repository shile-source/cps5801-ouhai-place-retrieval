"""Read only actual completed/locked decisions; produce a separate private audit."""
import argparse
from datetime import datetime
import json
from pathlib import Path
from src.evaluation.assisted_review import AssistedReview
from src.evaluation.spotcheck_summary import summarize

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--session',type=Path,default=ROOT/'data/labels/user30_activity151_spotcheck_v1_20261127')
    args=parser.parse_args();session=args.session.resolve()
    if not session.is_relative_to(ROOT/'data/labels'):raise ValueError('Use a project label session')
    result=summarize(AssistedReview(session,ROOT))
    out=ROOT/'outputs'/('spotcheck_summary_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    out.mkdir(exist_ok=False)
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(out),'human_decisions':result['human_decision_count'],
                      'scope':result['purpose'],'unreviewed_promoted':0}))


if __name__=='__main__':main()
