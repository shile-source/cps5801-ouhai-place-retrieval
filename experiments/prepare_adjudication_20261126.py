"""Freeze the existing12-case queue for the user's explicitly requested review."""
import json
from pathlib import Path
from src.evaluation.human_pilot import Pilot,sha
from src.evaluation.adjudication import create_session

ROOT=Path(__file__).resolve().parents[1]
SESSION=ROOT/'data/labels/adjudication_first_rater_12_v1_20261126'


def main():
    report=ROOT/'outputs/sampled_agreement_20261126_192650_845083/report.json'
    value=json.loads(report.read_text(encoding='utf-8'))
    pilot=Pilot();pilot.verify()
    items=[]
    for case in value['adjudication_queue']:
        qid,pid=case['query_id'],case['poi_id']
        candidate={k:pilot.records[pid].get(k) or '' for k in ['poi_id','name','category','address','description','source_url']}
        items.append({'case_id':qid+':'+pid,'query':pilot.queries[qid],'candidate':candidate,'original':case})
    if len(items)!=12:raise ValueError('Expected the exact frozen12-case review queue')
    inputs=[report,pilot.path/'corpus.json',pilot.path/'packet.json',pilot.path/'human_actions.jsonl',
            ROOT/'data/labels/supplemental_rater_b_sample80_v1_20261125/human_actions.jsonl',
            ROOT/'data/labels/supplemental_rater_b_sample80_v1_20261125/analysis_lock.json']
    bindings={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    review=create_session(SESSION,items,bindings,ROOT)
    state=review.state()
    print(json.dumps({'session':str(SESSION),'total':state['total'],'handled':state['handled'],
                      'prefilled_decisions':False,'original_labels_modified':False,'url':'http://127.0.0.1:8775/'}))


if __name__=='__main__':main()
