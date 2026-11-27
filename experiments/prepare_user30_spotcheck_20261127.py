"""4530 rule suggestions + prespecified60-pair human audit; never fabricate human actions."""
import hashlib
import json
from pathlib import Path
import random
from collections import Counter
from experiments.prepare_assisted_review_20261126 import suggest,feature
from src.evaluation.assisted_review import AssistedReview

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/labels/user30_activity151_spotcheck_v1_20261127'


def propose(i,query,record):
    if i<10:
        return suggest(record,('named',query.removeprefix('我想去').strip()))
    tags=record.get('source_tags',{});category=record['category'];name=record['name']
    if i==16:
        if category in ('游戏娱乐场所','游乐场','水上乐园','保龄球馆'):
            return 2,'来源明确标为娱乐或游乐设施；不证明当前运营、收费或实际体验。'
        return None,'来源未明确记载所需娱乐设施，不能凭其他类别排除附属设施。'
    if i==18:
        if category in ('运动场','体育中心','体育场','健身场所','游泳场馆'):
            return 2,'来源明确运动/健身类别；是否对公众开放及收费仍未知。'
        return None,'来源缺少明确运动健身用途证据，未知不补0。'
    if i==22:
        return (2,'来源amenity=karaoke_box明确卡拉OK用途；当前设备状况未知。') if tags.get('amenity')=='karaoke_box' else (None,'来源未明确记载唱歌设备。')
    if i in (23,24):
        required='basketball' if i==23 else 'tennis'
        if tags.get('sport')==required:
            return 2,'来源明确记载运动项目sport='+required+'；开放权限未核实。'
        if category in ('运动场','体育中心','体育场'):
            return (1,'运动场类别有依据，但明确记载的其他运动项目不匹配该偏好。') if tags.get('sport') else (None,'运动场类别有依据，但篮球/网球项目未明确记载。')
        return None,'缺少是否含所需运动场的来源事实。'
    if i==20:
        return None,'“座位充足”“藏书丰富”没有作者给定阈值，不能擅自沿用旧40座/12000册规则。'
    if i==21:
        return None,'“藏书量比较多”阈值未定义；来源开放时段也不证明当前营业，待明确评价规则。'
    return None,'本请求包含体验或设施要求（'+query+'），现有来源未充分支持全部属性。保留资料不足；不凭名称、类别或模型排名猜测。'


def main():
    if OUT.exists():raise FileExistsError('Preserve existing audit version')
    corpus=ROOT/'data/clean/activity_review_v0_6_20261126/poi_candidates.json'
    submission=ROOT/'data/queries/prospective_human30_v1_20261126/submission.json'
    records=sorted(json.loads(corpus.read_text(encoding='utf-8')),key=lambda r:r['poi_id'])
    queries=json.loads(submission.read_text(encoding='utf-8'))['draft']['queries']
    assert len(records)==151 and len(queries)==30
    items=[];sample=[]
    for i,query in enumerate(queries):
        group=[]
        for r in records:
            grade,basis=propose(i,query,r)
            group.append({'case_id':f'U30-{i+1:02}::{r["poi_id"]}','query_id':f'U30-{i+1:02}',
                'query':query,'query_author':'user_reported_self_authored_not_independently_verified',
                'record':{k:r.get(k) for k in ('poi_id','name','category','address','description','source_url')},
                'ai_suggestion':{'grade':grade,'basis':basis,'method':'assistant_authored_conservative_rules_v1','human_confirmed':False}})
        # Sample without looking at grades, relevance or model scores.
        selected=sorted(random.Random(f'5801:user30:20261127:{i+1}').sample(range(151),2))
        items.extend(group);sample.extend(group[j] for j in selected)
    OUT.mkdir()
    (OUT/'all_ai_suggestions.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
    binding={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in (corpus,submission,Path(__file__).resolve(),OUT/'all_ai_suggestions.json')}
    packet={'purpose':'ai_assisted_development_review_NOT_independent_test','items':sample,'source_bindings':binding,
        'query_authorship':'user_reported_self_authored_with_prior_project_exposure','total_ai_suggestions':4530,
        'sampling':'two uniform without replacement per query, sorted IDs, Random(5801:user30:20261127:query_number)',
        'pair_inclusion_probability':2/151,'human_audit_sample_size':60,'all_pairs_human_reviewed':False,
        'model_scores_used_for_sampling_or_suggestions':False,'unknowns_imputed_as_zero':False,
        'unreviewed_ai_suggestions_are_not_human_labels':True,'formal_effectiveness_metrics':None}
    (OUT/'packet.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'manifest.json').write_text(json.dumps({'packet_sha256':hashlib.sha256((OUT/'packet.json').read_bytes()).hexdigest()},indent=2),encoding='utf-8')
    assert AssistedReview(OUT,ROOT).state()['handled']==0
    counts=Counter('unknown' if x['ai_suggestion']['grade'] is None else str(x['ai_suggestion']['grade']) for x in items)
    summary={'total_suggestions':len(items),'human_spotcheck_tasks':len(sample),'actual_human_decisions':0,
        'suggested_grade_counts':dict(counts),'scope':'AI-rule suggestions plus future60-pair human spotcheck; not4530 human labels',
        'new_formal_metrics':None,'old_labels_modified':False}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary))


if __name__=='__main__':main()
