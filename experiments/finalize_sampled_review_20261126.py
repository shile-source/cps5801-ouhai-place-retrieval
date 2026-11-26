"""Preserve completed real ratings, lock this version and export descriptive agreement."""
import argparse
import csv
from datetime import datetime
import hashlib
import html
import json
from pathlib import Path
from src.evaluation.human_pilot import Pilot,sha
from src.evaluation.second_rater import REFERENCE,SAMPLED_SESSION,SecondRaterPilot

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('report',type=Path);args=parser.parse_args()
    path=args.report.resolve()
    if not path.is_relative_to(ROOT/'outputs'):raise ValueError('Use an existing local agreement report')
    report=json.loads(path.read_text(encoding='utf-8'))
    if report['status']!='completed_supplemental_sample' or report['second_handled']!=80:
        raise ValueError('All frozen80 tasks must be handled before finalization')
    for relative,expected in report['input_sha256'].items():
        if sha(ROOT/relative)!=expected:raise ValueError('Inputs changed since agreement calculation')
    independent=json.loads((path.parent/'independent_metric_verification.json').read_text(encoding='utf-8'))
    if independent['status']!='matched':raise ValueError('Independent arithmetic verification missing')
    a,b=Pilot(REFERENCE),SecondRaterPilot(SAMPLED_SESSION)
    state=b.state()
    if state['handled']!=80:raise ValueError('Second-rater progress differs')
    output=ROOT/'outputs'/('completed_sampled_review_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    output.mkdir()
    evidence=output/'private_evidence';evidence.mkdir()
    manifest={}
    for name,pilot in [('first',a),('second',b)]:
        destination=evidence/name;destination.mkdir()
        for filename in ('packet.json','manifest.json','corpus.json','human_actions.jsonl'):
            source=pilot.path/filename;body=source.read_bytes();(destination/filename).write_bytes(body)
            if sha(destination/filename)!=hashlib.sha256(body).hexdigest():raise ValueError('Evidence copy mismatch')
            manifest[(destination/filename).relative_to(output).as_posix()]=sha(destination/filename)
    action_hash=sha(b.path/'human_actions.jsonl')
    marker={'purpose':'freeze_completed_second_rater_version_after_agreement_export',
            'actions_sha256':action_hash,'packet_sha256':b.manifest['packet_sha256'],
            'agreement_report_sha256':sha(path),'agreement_report':path.relative_to(ROOT).as_posix(),
            'locked_at':datetime.now().astimezone().isoformat(),'grades_changed':False}
    lock=b.path/'analysis_lock.json'
    if lock.exists():
        if json.loads(lock.read_text(encoding='utf-8'))['actions_sha256']!=action_hash:
            raise ValueError('Existing completed-version lock differs')
    else:lock.write_text(json.dumps(marker,ensure_ascii=False,indent=2),encoding='utf-8')
    summary={'purpose':'post_publication_sampled_agreement_NOT_full_dual_annotation',
             'sample_size':80,'queries':8,'pairs_per_query':10,'second_numeric':state['graded'],
             'second_unknown':state['unknown'],'statistics':report['statistics'],
             'pairwise_unknown_exclusions':report['exclusions']['one_or_both_unknown'],
             'numeric_disagreements':sum(r['first_grade'] is not None and r['second_grade'] is not None for r in report['adjudication_queue']),
             'review_queue_size':len(report['adjudication_queue']),'adjudications_completed':0,
             'original_ranking_metrics_changed':False,'second_packet_sha256':b.manifest['packet_sha256'],
             'first_log_sha256':sha(a.path/'human_actions.jsonl'),'second_log_sha256':action_hash,
             'identities_independently_verified':False,'limitations':report['limitations']}
    target=ROOT/'results/sampled_agreement_summary.json'
    if target.exists() and json.loads(target.read_text(encoding='utf-8'))!=summary:
        raise ValueError('Existing exported summary differs; preserve a separate version')
    target.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'summary.json').write_bytes(target.read_bytes())
    rows=[]
    for name,value in summary['statistics'].items():
        rows.append({'group':name,'n':value['n'],'exact_agreement':value['exact_agreement'],
                     'linear_weighted_kappa':value['linear']['kappa'],'quadratic_weighted_kappa':value['quadratic']['kappa']})
    with (output/'agreement.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    def esc(value):return html.escape(str(value))
    cards=[]
    for index,item in enumerate(report['adjudication_queue'],1):
        record=a.records[item['poi_id']];query=a.queries[item['query_id']]
        first='资料不足' if item['first_grade'] is None else str(item['first_grade'])
        second='资料不足' if item['second_grade'] is None else str(item['second_grade'])
        cards.append(f"<section><h2>{index}. {esc(record['name'])}</h2><p>{esc(query['text'])}</p><p class='notice'>{esc(query['rubric'])}</p><p>{esc(record.get('category',''))}；{esc(record.get('address','未知'))}</p><p>{esc(record.get('description',''))}</p><table><tr><th>第一份</th><th>第二份</th></tr><tr><td>{esc(first)}</td><td>{esc(second)}</td></tr><tr><td>{esc(item['first_evidence'])}<br>{esc(item['first_unknown_reason'])}</td><td>{esc(item['second_evidence'])}<br>{esc(item['second_unknown_reason'])}</td></tr></table><p>第一份来源：{esc(item['first_source'])}。最终裁决：尚未填写。</p></section>")
    page="<!doctype html><html lang='zh-CN'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>80对抽样复核完成</title><style>body{max-width:1000px;margin:30px auto;padding:0 20px;font:17px/1.7 system-ui;background:#f2f5f4;color:#173a36}section{background:white;border:1px solid #ccd8d2;padding:20px;margin:18px 0}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:10px;width:50%;vertical-align:top}.notice{background:#fff2ce;padding:12px}h2{font-size:21px}</style><h1>80对已全部保存</h1><p>第二份78项有分、2项资料不足。71对原人工可比较记录中67对一致（94.4%），线性加权κ=0.875，二次加权κ=0.885。</p><p class='notice'>这是后加入的抽样一致性复核，不是新的完整双人测试。原分数保持；下面6对分歧及6对资料不足供人工复核，没有自动裁决或改分。</p>"+''.join(cards)+"</html>"
    primary=summary['statistics']['original_human_pairs_only']
    count=sum(primary['confusion_matrix_0_1_2'][i][i] for i in range(3))
    text=(f"第二份{summary['second_numeric']}项有分、{summary['second_unknown']}项资料不足。"
          f"{primary['n']}对原人工可比较记录中{count}对一致（{primary['exact_agreement']:.1%}），"
          f"线性加权κ={primary['linear']['kappa']:.3f}，二次加权κ={primary['quadratic']['kappa']:.3f}。")
    page=page.replace('第二份78项有分、2项资料不足。71对原人工可比较记录中67对一致（94.4%），线性加权κ=0.875，二次加权κ=0.885。',text)
    page=page.replace('下面6对分歧及6对资料不足',f"下面{summary['numeric_disagreements']}对分歧及{summary['pairwise_unknown_exclusions']}对资料不足")
    (output/'REVIEW_ZH.html').write_text(page,encoding='utf-8')
    (output/'private_evidence_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (ROOT/'outputs/latest_completed_sampled_review_20261126.json').write_text(json.dumps({
        'directory':str(output),'review_html':str(output/'REVIEW_ZH.html'),'summary':str(output/'summary.json'),
        'raw_agreement_report':str(path),'ratings_locked':True},indent=2),encoding='utf-8')
    print(json.dumps({'output':str(output),'complete':80,'numeric':state['graded'],'unknown':state['unknown'],'review_cases':len(cards),'ratings_locked':True,'grades_changed':False}))


if __name__=='__main__':main()
