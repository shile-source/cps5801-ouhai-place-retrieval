"""模型无关的严格评价；未标注不是0，候选池必须完整判断。"""
from collections import Counter
import math
import random
from statistics import mean
from typing import Mapping, Sequence

METRICS = ('ndcg_at_5', 'precision_at_3', 'mrr', 'recall_at_5')


def _ids(values):
    items = tuple(values)
    if any(not isinstance(x, str) or not x.strip() for x in items) or len(set(items)) != len(items):
        raise ValueError('IDs must be nonempty strings without duplicates')
    return items


def score_query(ranking: Sequence[str], judgments: Mapping[str, int | None], *,
                eligible_ids: Sequence[str], relevance_threshold: int = 2,
                include_recall: bool = False) -> dict:
    """给定同一已核实过滤池；nDCG理想列表也必须基于该完整池。"""
    ranking, candidates = _ids(ranking), _ids(eligible_ids)
    if type(relevance_threshold) is not int or relevance_threshold not in (1, 2):
        raise ValueError('Binary relevance threshold must be 1 or 2')
    if not set(ranking) <= set(candidates):
        raise ValueError('Run contains a POI outside the shared eligible pool')
    grades = {p: judgments.get(p) for p in candidates}
    if any(v is not None and (type(v) is not int or v not in (0, 1, 2)) for v in grades.values()):
        raise ValueError('Grades must be integers 0/1/2 or None for unjudged')
    result = {'status': 'excluded', 'metrics': {m: None for m in METRICS},
        'eligible_count': len(candidates), 'judged_count': sum(v is not None for v in grades.values()),
        'returned_count': len(ranking), 'relevance_threshold': relevance_threshold, 'reasons': []}
    if not candidates:
        result['reasons'] = ['empty_eligible_pool']
        return result
    if any(v is None for v in grades.values()):
        result['reasons'] = ['incomplete_candidate_judgments']
        return result
    result['status'] = 'scored'
    # 固定指数gain：0/1/2对应0/1/3；不得与线性gain结果混用。
    dcg = lambda seq: sum((2**g - 1) / math.log2(i + 2) for i, g in enumerate(seq[:5]))
    ideal = dcg(sorted(grades.values(), reverse=True))
    if ideal:
        result['metrics']['ndcg_at_5'] = dcg([grades[p] for p in ranking]) / ideal
    else:
        result['reasons'].append('ndcg_undefined_no_positive_gain')
    relevant = {p for p, g in grades.items() if g >= relevance_threshold}
    # 返回不足3条时仍除以3，缺失返回位置不是未标注文档。
    result['metrics']['precision_at_3'] = sum(p in relevant for p in ranking[:3]) / 3
    # 当前检索接口可能只输出Top-5；完整MRR严格要求全候选排列，不伪装成MRR@5。
    if set(ranking) == set(candidates):
        result['metrics']['mrr'] = next((1 / i for i, p in enumerate(ranking, 1) if p in relevant), 0.0)
    else:
        result['reasons'].append('mrr_requires_full_candidate_ranking')
    if include_recall:
        if relevant:
            result['metrics']['recall_at_5'] = sum(p in relevant for p in ranking[:5]) / len(relevant)
        else:
            result['reasons'].append('recall_undefined_no_relevant_candidates')
    return result


def evaluate_runs(runs: Mapping[str, Mapping[str, Sequence[str]]], queries: Mapping[str, dict],
                  judgments: Mapping[str, Mapping[str, int | None]],
                  eligible_by_query: Mapping[str, Sequence[str]], *, purpose='formal',
                  relevance_threshold=2, include_recall=False) -> dict:
    """共用查询/候选池/标签；每个指标只汇总所有方法均可计分的同一查询交集。"""
    if purpose not in ('formal', 'synthetic_test') or not runs:
        raise ValueError('Explicit purpose and at least one model are required')
    if purpose == 'synthetic_test' and any(q.get('is_synthetic') is not True for q in queries.values()):
        raise ValueError('Synthetic test mode cannot score real/draft research queries')
    if any(set(run) - set(queries) for run in runs.values()):
        raise ValueError('Run contains unknown query IDs')
    rows = []
    for qid, query in queries.items():
        if not query.get('query_type'):
            raise ValueError('Each query needs query_type')
        reason = None
        if purpose == 'formal' and (query.get('formal_eligible') is not True or
                                    query.get('human_review_status') != 'approved'):
            reason = 'draft_or_unapproved_query'
        elif purpose == 'formal' and (query.get('split') != 'held_out_test' or not query.get('freeze_id') or
                                       query.get('labels_status') != 'adjudicated'):
            reason = 'query_not_frozen_test_or_labels_not_adjudicated'
        elif (query.get('has_hard_constraints') or query['query_type'] == 'hard_constraint') and query.get('eligibility_verified') is not True:
            reason = 'hard_constraint_pool_not_verified'
        elif any(qid not in run for run in runs.values()):
            reason = 'missing_run_for_at_least_one_model'
        elif qid not in eligible_by_query:
            reason = 'shared_candidate_pool_missing'
        for model, run in runs.items():
            score = ({'status': 'excluded', 'metrics': {m: None for m in METRICS}, 'reasons': [reason]}
                     if reason else score_query(run[qid], judgments.get(qid, {}),
                         eligible_ids=eligible_by_query[qid], relevance_threshold=relevance_threshold,
                         include_recall=include_recall))
            rows.append({'query_id': qid, 'query_type': query['query_type'], 'model': model, **score})
    summaries = {}
    for group in ['overall'] + sorted({q['query_type'] for q in queries.values()}):
        group_ids = {qid for qid, q in queries.items() if group == 'overall' or q['query_type'] == group}
        summaries[group] = {}
        for metric in METRICS:
            # 禁止不同模型在不同的可评分查询上单独平均，避免选择性漏标改变比较。
            shared = sorted(qid for qid in group_ids if all(
                next(r for r in rows if r['query_id'] == qid and r['model'] == model)['metrics'][metric] is not None
                for model in runs))
            summaries[group][metric] = {'query_ids': shared, 'n': len(shared), 'means': {
                model: mean(next(r for r in rows if r['query_id'] == qid and r['model'] == model)['metrics'][metric]
                            for qid in shared) if shared else None for model in runs}}
    return {'purpose': purpose, 'status': 'scored' if any(r['status'] == 'scored' for r in rows) else 'not_evaluated',
        'protocol': {'gain': '2^grade-1', 'relevance_threshold': relevance_threshold,
            'unjudged_policy': 'exclude query unless all shared eligible candidates have valid judgments',
            'mrr_policy': 'full shared eligible candidate ranking required',
            'aggregation': 'macro mean on identical per-metric query intersection across all models'},
        'per_query': rows, 'summary': summaries}


def weighted_kappa(first: Sequence[int], second: Sequence[int], *, weights='linear') -> dict:
    """仅用于两名独立标注者原始分数，不能对协商后分数计算一致性。"""
    if len(first) != len(second) or weights not in ('linear', 'quadratic'):
        raise ValueError('Paired ratings and valid weights required')
    if any(type(x) is not int or x not in (0, 1, 2) for x in (*first, *second)):
        raise ValueError('Kappa needs complete original 0/1/2 ratings; blanks are not 0')
    if not first:
        return {'n': 0, 'kappa': None, 'reason': 'no_paired_ratings', 'weights': weights}
    n, power = len(first), 1 if weights == 'linear' else 2
    distance = lambda a, b: (abs(a - b) / 2) ** power
    observed = sum(distance(a, b) for a, b in zip(first, second)) / n
    a, b = Counter(first), Counter(second)
    expected = sum(a[i] * b[j] * distance(i, j) for i in range(3) for j in range(3)) / n**2
    return {'n': n, 'kappa': 1 - observed / expected if expected else None,
        'reason': None if expected else 'undefined_degenerate_marginals', 'weights': weights}


def query_bootstrap(values: Mapping[str, float], *, samples=2000, seed=5801, confidence=0.95) -> dict:
    """成对差异可传每查询差值。仅计算区间，不推断当前项目有研究结果。"""
    if not values or type(samples) is not int or samples < 1 or not 0 < confidence < 1:
        raise ValueError('Nonempty query values, positive samples and valid confidence required')
    if any(isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x) for x in values.values()):
        raise ValueError('All query values must be finite numbers')
    data, rng = [values[k] for k in sorted(values)], random.Random(seed)
    replicates = sorted(mean(rng.choices(data, k=len(data))) for _ in range(samples))
    def percentile(p):
        pos = p * (samples - 1)
        lo, hi = math.floor(pos), math.ceil(pos)
        return replicates[lo] + (replicates[hi] - replicates[lo]) * (pos - lo)
    tail = (1 - confidence) / 2
    return {'mean': mean(data), 'lower': percentile(tail), 'upper': percentile(1 - tail),
        'n_queries': len(data), 'samples': samples, 'seed': seed, 'confidence': confidence,
        'unit': 'query; assumes independent queries, paraphrase clusters require group handling'}
