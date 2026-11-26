"""Audit actual locked author review and export a separate sensitivity version, no models."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
from src.evaluation.adjudication import Adjudication,digest
from src.evaluation.human_pilot import Pilot
from src.evaluation.review_sensitivity import analyse_review

ROOT=Path(__file__).resolve().parents[1]
SESSION=ROOT/'data/labels/adjudication_first_rater_12_v1_20261126'


def main():
    review=Adjudication(SESSION,ROOT);state=review.state()
    if not state['locked'] or state['handled']!=state['total']:raise ValueError('User must complete and lock the review first')
    exported=review.export()
    saved=json.loads((SESSION/'completed_review.json').read_text(encoding='utf-8'))
    if saved!=exported:raise ValueError('Locked export does not match saved history')
    pilot=Pilot();pilot.verify()
    if digest(pilot.path/'human_actions.jsonl')!='bb2a2e566e7bb56ebe89f0e6600523e0fabcfe3f8e83796cb937e20860182c09':raise ValueError('Original action log changed')
    original={pair:row['semantic_grade'] for pair,row in pilot.ratings().items()}
    decisions={}
    for item in exported['cases']:
        decision=item['decision'];case=item['original'];qid,pid=case['query_id'],case['poi_id']
        if decision['source']!='user_adjudication_ui' or decision['role']!='first_rater_post_publication_reviewer':raise ValueError('Unexpected decision provenance')
        if original[qid,pid]!=case['first_grade']:raise ValueError('Original opinion differs from frozen case')
        decisions[qid,pid]=decision['grade']
    anonymous={pid:f'candidate_{i+1:03}' for i,pid in enumerate(sorted(pilot.records))}
    original_metric=json.loads((ROOT/'results/pilot_metric_inputs.json').read_text(encoding='utf-8'))
    runs={r['method']:r['ranking'] for r in original_metric['runs']}
    for method,file in [('keyword_overlap','keyword_supplement_v1_20261126.json'),('bge_m3','bge_supplement_v1_20261126.json')]:
        value=json.loads((ROOT/'results'/file).read_text(encoding='utf-8'))
        if set(value['candidate_ids'])!=set(original_metric['candidate_ids']):raise ValueError('Saved run candidate mismatch')
        runs[method]=value['ranking']
    reverse={v:k for k,v in anonymous.items()}
    raw_runs={'P02':{m:[reverse[pid] for pid in ids] for m,ids in runs.items()}}
    summary,revised=analyse_review(pilot.queries,pilot.records,original,decisions,raw_runs)
    out=ROOT/'outputs'/('adjudication_completed_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    private=out/'private_evidence';private.mkdir(parents=True)
    manifest={}
    for source in [*SESSION.iterdir(),pilot.path/'human_actions.jsonl',
                   ROOT/'data/labels/supplemental_rater_b_sample80_v1_20261125/human_actions.jsonl']:
        if not source.is_file():continue
        name=source.name if source.parent==SESSION else source.parent.name+'_'+source.name
        body=source.read_bytes();(private/name).write_bytes(body)
        if digest(private/name)!=hashlib.sha256(body).hexdigest():raise ValueError('Backup mismatch')
        manifest[name]=digest(private/name)
    (out/'private_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (out/'analysis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    public={k:v for k,v in summary.items() if k!='evaluations'}
    public.update(review_completed=True,review_locked=True,review_decisions_sha256=digest(SESSION/'decisions.jsonl'),
                  review_packet_sha256=digest(SESSION/'packet.json'),
                  original_log_sha256=digest(pilot.path/'human_actions.jsonl'),
                  post_review_P02_judgments={anonymous[pid]:revised['P02',pid] for pid in sorted(pilot.records)},
                  metrics_version='post_review_sensitivity_v1_20261126',
                  numeric_effectiveness_metrics_reported_after_review=False,
                  complete_query_rule_unchanged=True,
                  claims_independent_blind_adjudicator=False,
                  limitation='The original first rater reviewed after publication and could see both original opinions. Historical metrics retain their original labels; the revised version has no fully judged query. No final model-effectiveness comparison is inferred.')
    target=ROOT/'results/post_review_sensitivity_v1_20261126.json'
    if target.exists() and json.loads(target.read_text(encoding='utf-8'))!=public:raise ValueError('Preserve existing sensitivity version')
    target.write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    (out/'summary.json').write_bytes(target.read_bytes())
    (ROOT/'outputs/latest_adjudication_completed_20261126.json').write_text(json.dumps({'directory':str(out),'public_summary':str(target),
        'handled':state['handled'],'unknown':state['unknown'],'eligible_after':summary['eligible_after']},indent=2),encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ['reviewed_pairs','numeric_review_decisions','unknown_review_decisions','changed_from_original','before_numeric','before_unknown','after_numeric','after_unknown','eligible_before','eligible_after']}))


if __name__=='__main__':main()
