"""Descriptive engineering diagnostics, deliberately without human relevance metrics."""
from itertools import combinations
import math
import statistics


def percentile(values, q):
    values=sorted(values)
    position=(len(values)-1)*q
    lower=int(position);upper=math.ceil(position)
    return values[lower]+(values[upper]-values[lower])*(position-lower)


def summarize(protocol, queries, observations):
    methods=protocol['methods'];repeats=protocol['repeats_per_query'];k=protocol['top_k']
    query_map={q['query_id']:q for q in queries['items']}
    if len(query_map)!=len(queries['items']):raise ValueError('Duplicate query ID')
    measured={};filters={};warmups={};cold=[]
    for row in observations:
        if row['method'] not in methods:raise ValueError('Unexpected method')
        for field in ('search_ms','elapsed_ms','load_ms'):
            if type(row[field]) not in (int,float) or not math.isfinite(row[field]) or row[field]<0:
                raise ValueError('Invalid timing')
        ids=[r['poi_id'] for r in row['results']]
        if len(ids)!=len(set(ids)) or len(ids)>k:raise ValueError('Invalid returned IDs')
        phase=row['phase']
        if phase=='measurement':
            key=(row['query_id'],row['method'],row['repeat'])
            if key in measured or row['query_id'] not in query_map or not 0<=row['repeat']<repeats:
                raise ValueError('Duplicate or unexpected observation')
            if row['load_ms']!=0:raise ValueError('Warm timing includes a model reload')
            measured[key]=row
        elif phase=='constraint':
            key=(row['case_id'],row['method'])
            if key in filters:raise ValueError('Duplicate filter case')
            filters[key]=row
        elif phase=='warmup':
            if row['method'] in warmups:raise ValueError('Duplicate warmup')
            warmups[row['method']]=row
        elif phase=='cold':cold.append(row)
        else:raise ValueError('Unexpected phase')
    expected={(qid,m,r) for qid in query_map for m in methods for r in range(repeats)}
    if set(measured)!=expected or set(warmups)!=set(methods):raise ValueError('Incomplete measurements')
    if len(cold)!=1 or cold[0]['method']!='bge_m3' or cold[0]['load_ms']<=0:
        raise ValueError('One real cold load required')
    stable={}
    for qid in query_map:
        for method in methods:
            runs=[measured[qid,method,r] for r in range(repeats)]
            signatures=[[(x['poi_id'],x['score']) for x in row['results']] for row in runs]
            if any(x!=signatures[0] for x in signatures[1:]):raise ValueError('Repeated rankings or scores differ')
            stable[qid,method]=[r['poi_id'] for r in runs[0]['results']]
    cases={c['case_id'] for c in queries['constraint_checks']}
    if set(filters)!={(c,m) for c in cases for m in methods}:raise ValueError('Incomplete constraint checks')
    filter_rows=[]
    for case in sorted(cases):
        runs=[filters[case,m] for m in methods]
        eligible=runs[0]['eligible_ids']
        if any(x['eligible_ids']!=eligible for x in runs):raise ValueError('Methods used different source pools')
        if any(any(r['poi_id'] not in eligible for r in x['results']) for x in runs):
            raise ValueError('Result outside supported source pool')
        filter_rows.append({'case_id':case,'eligible_count':len(eligible),
            'unknown_count':runs[0]['unknown_count'],'unmet_count':runs[0]['unmet_count'],
            'methods_checked':len(methods),'all_returned_ids_eligible':True})
    lookup=[q for q in query_map.values() if q['group']=='constructed_exact_name']
    metrics={}
    for method in methods:
        rows=[r for r in measured.values() if r['method']==method]
        metrics[method]={'observations':len(rows),'distinct_queries':len(query_map),
            'search_ms':{'median':statistics.median([r['search_ms'] for r in rows]),
                         'p95':percentile([r['search_ms'] for r in rows],.95)},
            'server_elapsed_ms':{'median':statistics.median([r['elapsed_ms'] for r in rows]),
                         'p95':percentile([r['elapsed_ms'] for r in rows],.95)},
            'constructed_lookup_queries':len(lookup),
            'source_id_recovery_at1':sum(stable[q['query_id'],method][:1]==[q['expected_source_id']] for q in lookup)/len(lookup),
            'source_id_recovery_at5':sum(q['expected_source_id'] in stable[q['query_id'],method] for q in lookup)/len(lookup)}
    overlaps={}
    for a,b in combinations(methods,2):
        values=[]
        for qid in query_map:
            left,right=set(stable[qid,a]),set(stable[qid,b])
            values.append(len(left&right)/len(left|right) if left|right else 1)
        overlaps[a+'__'+b]={'mean_top5_jaccard':statistics.mean(values),'queries':len(values)}
    return {'scope':'source_constructed_public_engineering_NOT_human_relevance',
        'query_count':len(query_map),'measured_requests':len(measured),'repeats_per_query':repeats,
        'methods':metrics,'cold_load':{key:cold[0][key] for key in ('method','load_ms','search_ms','elapsed_ms')},
        'pairwise_overlap':overlaps,'constraint_checks':filter_rows,
        'identical_repeated_rankings_and_scores':True,'new_human_labels':0,
        'independent_test_set':False,'relevance_ndcg_mrr_recall':None,
        'general_recommendation_quality_claim':False}
