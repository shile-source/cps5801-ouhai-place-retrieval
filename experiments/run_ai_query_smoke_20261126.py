"""Disclosed AI-authored development requests; no human judgments or effectiveness."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from src.data.load_candidates import load_candidates
from src.retrieval.bm25 import BM25Retriever
from src.retrieval.keyword import KeywordRetriever

ROOT = Path(__file__).resolve().parents[1]

# Authored by the assistant at the user's request. Not independent human queries.
REQUESTS = {
    'named': [
        '查找潘桥城市书房的来源记录。', '我想找南白象城市书房。',
        '请查一下数安港城市书房。', '查找龙舟公园城市书房。',
        '我想了解瓯海博物馆这条记录。', '找一下梧田老街。',
        '请找紫薇主题公园。', '查找温州中学图书馆。',
        '我想找南火车站广场。', '查找青灯石刻艺术博物馆南馆。'],
    'paraphrase': [
        '想找一处资料明确归为公园的地方。', '我想找可以借阅图书的公共文化设施记录。',
        '想看看有文物或艺术展陈类别的场所。', '帮我找来源归类为旅游景点的记录。',
        '我想找社区里的百姓书屋。', '想找名称里提到滨水的公园记录。',
        '希望找资料提到儿童阅读区域的设施。', '想了解设置成人阅读区域的地方。',
        '有没有资料提到自助借还设备的阅读设施？', '找一找资料提到少儿绘本的书房。'],
    'preferences': [
        '优先看城市书房，也希望座位至少40个。',
        '优先看百姓书屋，希望藏书不少于12000册。',
        '希望找城市书房，优先考虑藏书至少15000册的记录。',
        '优先看座位不少于50个的阅读设施，也希望藏书至少15000册。',
        '希望找百姓书屋，也优先考虑来源地址在新桥的记录。',
        '优先看看公园，也希望名称提到滨水。',
        '希望找博物馆，优先看看名称提到艺术的记录。',
        '优先看来源地址提到仙岩的阅读设施，也希望有40个以上座位。',
        '希望找有儿童区的阅读设施，也优先考虑有成人区的地方。',
        '优先看来源地址提到娄桥的城市书房，也希望藏书不少于12000册。']}


def main():
    corpus = ROOT / 'data/clean/research_review_v0_5_20261125/poi_candidates.json'
    pois = load_candidates(corpus)
    queries = [{'id': f'AI30-{i + 1:02}', 'type': group, 'text': query,
                'author': 'OpenAI Codex assistant', 'human_authored': False,
                'purpose': 'development_functional_smoke_only'}
               for i, (group, query) in enumerate((g, q) for g, rows in REQUESTS.items() for q in rows)]
    assert len(queries) == len({q['text'] for q in queries}) == 30
    models = {'bm25': BM25Retriever(pois), 'keyword': KeywordRetriever(pois)}
    runs = []
    for query in queries:
        for name, model in models.items():
            rows = model.search(query['text'], 5)
            repeated = model.search(query['text'], 5)
            assert len(rows) == 5 and len({r.poi_id for r in rows}) == 5
            assert [(r.poi_id, r.score) for r in rows] == [(r.poi_id, r.score) for r in repeated]
            runs.append({'query_id': query['id'], 'method': name,
                         'rows': [{'poi_id': r.poi_id, 'score': r.score, 'rank': r.rank} for r in rows]})
    output = ROOT / 'outputs' / ('ai_development_smoke_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    output.mkdir(parents=True)
    record = {'created_utc': datetime.now(timezone.utc).isoformat(), 'queries': queries,
              'corpus_sha256': hashlib.sha256(corpus.read_bytes()).hexdigest(),
              'runs': runs, 'human_judgments_created': 0, 'effectiveness_metrics': None,
              'hard_filters_applied': False, 'preferences_are_not_mandatory_filters': True,
              'independent_held_out_test': False}
    (output / 'private_runs.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = {'status': 'completed_functional_checks_only', 'queries': 30,
               'query_author': 'AI_assistant', 'human_authored': False,
               'methods_checked': list(models), 'searches_checked': len(runs),
               'repeat_checks': len(runs), 'top_k': 5, 'candidate_count': len(pois),
               'corpus_sha256': record['corpus_sha256'],
               'all_returned_five_unique_records': True, 'repeat_order_and_scores_identical': True,
               'human_judgments_created': 0, 'numeric_effectiveness_metrics': None,
               'new_dense_inference': False, 'independent_test': False,
               'correctness_of_relevance_not_established': True}
    (ROOT / 'results/ai_development_smoke_v1_20261126.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'outputs/latest_ai_development_smoke_20261126.json').write_text(json.dumps({'directory': str(output), **summary}, indent=2), encoding='utf-8')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
