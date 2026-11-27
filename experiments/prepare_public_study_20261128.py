"""Freeze a fully public engineering study; no new source collection or human labels."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from src.data.activity_sources import ACTIVITY_TAGS
from src.data.evidence_facts import compile_facts
from src.data.fact_store import load_bound_facts

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,value):
    body=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=body:raise ValueError('Frozen study changed; create another version')
    path.write_bytes(body)


def main():
    data=ROOT/'data/clean/open_activity_v1_20261127'
    corpus=data/'poi_candidates.json';records=json.loads(corpus.read_text(encoding='utf-8'))
    evidence=data/'field_evidence.json'
    labels={('tags.'+key,value):label for key,value,label in ACTIVITY_TAGS}
    facts=compile_facts(records,json.loads(evidence.read_text(encoding='utf-8')),ROOT,category_labels=labels)
    out=ROOT/'data/clean/open_activity_study_v1_20261128'
    save(out/'source_facts.json',facts)
    source_manifest=json.loads((data/'source_manifest.json').read_text(encoding='utf-8'))
    binding={'scope':'source_snapshot_only','corpus_sha256':sha(corpus),
        'facts_path':str((out/'source_facts.json').relative_to(ROOT)).replace('\\','/'),
        'facts_sha256':sha(out/'source_facts.json'),
        'evidence_sha256':{x['raw_path']:x['sha256'] for x in source_manifest['sources']},
        'formal_relevance_benchmark':False}
    save(ROOT/'configs/open_activity_study_binding_20261128.json',binding)
    load_bound_facts(ROOT/'configs/open_activity_study_binding_20261128.json',corpus,ROOT)
    name_counts=Counter(r['name'] for r in records)
    categories=['公园','博物馆','图书馆','KTV','电影院','健身场所','运动场','体育中心','购物中心','餐饮店']
    items=[]
    for category in categories:
        row=next(r for r in sorted(records,key=lambda x:x['poi_id']) if r['category']==category and name_counts[r['name']]==1)
        items.append({'group':'constructed_exact_name','text':row['name'],
                      'expected_source_id':row['poi_id'],
                      'reference_scope':'source_record_lookup_only_NOT_human_relevance_or_real_world_identity'})
    paraphrases=['想找看电影的地方','想和朋友唱歌','想找可以进行篮球运动的场地','想找打网球的场地',
                '想找健身锻炼的场所','想去博物馆了解文化','想找公园绿地走走','想找可以购物的商场',
                '想找吃饭的餐馆','想找喝咖啡的地方']
    preferences=['优先看看公园，同时希望有休闲步道','希望找到购物中心，也想看看餐饮店',
        '优先选择KTV，同时希望有其他娱乐设施','希望有体育中心，优先考虑篮球项目',
        '优先找运动场，同时希望能打网球','希望看看博物馆，也想了解文化类景点',
        '优先找图书馆，同时希望有阅读空间','希望看看公园，优先选择能看水景的地方',
        '优先看看咖啡饮品店，也希望可以用餐','希望找到健身场所，优先考虑游泳项目']
    items.extend({'group':'AI_authored_paraphrase','text':q} for q in paraphrases)
    items.extend({'group':'AI_authored_multiple_preferences','text':q} for q in preferences)
    for i,item in enumerate(items,1):item['query_id']=f'F{i:02}'
    constraints=[{'case_id':f'C{i+1:02}','query':q,'constraints':conditions} for i,(q,conditions) in enumerate([
        ('想找唱歌的地方',[{'field':'category','operator':'eq','value':'KTV'}]),
        ('想运动',[{'field':'category','operator':'eq','value':'运动场'}]),
        ('想看看绿地',[{'field':'category','operator':'eq','value':'公园'}]),
        ('想购物',[{'field':'category','operator':'eq','value':'购物中心'}]),
        ('想找阅读空间',[{'field':'seats','operator':'gte','value':40}]),
        ('想借书',[{'field':'holdings','operator':'gte','value':12000}])])]
    queries={'authorship':'assistant_authored_source_constructed_development_only',
        'independent_held_out':False,'human_relevance_labels':0,'items':items,'constraint_checks':constraints}
    save(ROOT/'configs/public_functional_queries_20261128.json',queries)
    protocol={'purpose':'public_source_engineering_comparison_NOT_independent_relevance_effectiveness',
        'corpus_path':str(corpus.relative_to(ROOT)).replace('\\','/'),'corpus_sha256':sha(corpus),
        'facts_binding':'configs/open_activity_study_binding_20261128.json',
        'query_path':'configs/public_functional_queries_20261128.json',
        'query_sha256':sha(ROOT/'configs/public_functional_queries_20261128.json'),
        'common_text_fields':['name','category','address','description'],
        'methods':['keyword','bm25','bge_m3'],'dense_precision':'float16','batch_size':4,'max_length':128,
        'dense_idle_seconds':60,'maximum_model_loads':1,'automatic_retries':0,
        'warmups_per_method':1,'repeats_per_query':5,'top_k':5,'order_seed':5801,
        'latency_summary':'backend search_ms and complete server elapsed_ms reported separately; repeated observations are not independent queries',
        'lookup_metric':'exact frozen source_id recovery at1/5 on10 constructed unique-name queries; not human relevance',
        'comparison_metric':'pairwise top5 Jaccard across30 requests; disagreement is not quality',
        'source_filter_checks':'same eligible IDs for each method; unknown never passes',
        'relevance_ndcg_mrr_recall':None,'bootstrapped_relevance_CI':None,
        'raw_responses_public':True,'formal_human_labels_created':False}
    save(ROOT/'configs/public_functional_study_20261128.json',protocol)
    coverage={f:dict(Counter(v[f]['status'] for v in facts.values())) for f in ['name','category','address','seats','holdings']}
    save(out/'coverage.json',{'source_records':len(records),'field_status_counts':coverage,
         'purpose':'source_snapshot_coverage_NOT_current_facility_census','new_human_labels':0})
    print(json.dumps({'records':len(records),'queries':len(items),'constraint_cases':len(constraints),'coverage':coverage},ensure_ascii=True))


if __name__=='__main__':main()
