"""Prepare explicit-rule suggestions only; never append a human decision."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from experiments.run_ai_query_smoke_20261126 import REQUESTS
from src.evaluation.assisted_review import AssistedReview

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / 'data/labels/assisted_ai30_76_v1_20261126'
CORPUS = ROOT / 'data/clean/research_review_v0_5_20261125/poi_candidates.json'


def feature(record, kind, value):
    name, category = record['name'], record['category']
    description = record.get('description', '') or ''
    if kind == 'category':
        if value == 'reading':
            return any(w in category for w in ('书房', '书屋', '图书馆', '阅读驿站'))
        if value == 'city_reading':
            return True if category == '城市书房' else (None if '城市书房' in name else False)
        if value == 'community_reading':
            return True if category == '百姓书屋' else (None if '百姓书屋' in name else False)
        return value in category
    if kind == 'name_contains':
        return value in name
    if kind == 'address':
        address = record.get('address')
        return None if not address else value in address
    if kind == 'fact':
        return True if value in description else None
    if kind in ('seats', 'books'):
        label = '座位数' if kind == 'seats' else '藏书量'
        match = re.search(label + r'[:：]\s*(\d+)', description)
        return None if not match else int(match.group(1)) >= value
    raise ValueError('Unknown feature')


def suggest(record, spec):
    if spec[0] == 'named':
        target = spec[1]
        if record['name'] == target:
            return 2, '来源名称与请求名称完全相同；仅支持来源文字匹配，不证明实体身份或现状。'
        if record['name'] in target or target in record['name']:
            return None, '名称部分重合，别名或实体关系未经核实，建议资料不足。'
        return 0, '来源名称与指定名称不同，未见别名或同一实体证据。'
    features = spec[1]
    values = [feature(record, *entry) for entry in features]
    if len(values) == 1:
        grade = None if values[0] is None else (2 if values[0] else 0)
    elif spec[0] == 'semantic':
        grade = 0 if any(v is False for v in values) else (None if any(v is None for v in values) else 2)
    elif all(v is True for v in values):
        grade = 2
    elif any(v is True for v in values):
        grade = 1 if all(v is not None for v in values) else None
    elif any(v is None for v in values):
        grade = None
    else:
        grade = 0
    basis = '；'.join(f'{kind}={value}：' + ('未知' if found is None else ('来源支持' if found else '不匹配'))
                     for (kind, value), found in zip(features, values))
    return grade, basis + '。这是保守规则建议，请人工核对；缺少记载不自动判0。'


def specifications(records):
    names = ['潘桥城市书房', '南白象城市书房', '数安港城市书房', '龙舟公园城市书房', '瓯海博物馆',
             '梧田老街', '紫薇主题公园', '温州中学图书馆', '南火车站广场', '青灯石刻艺术博物馆南馆']
    single = [[('category', '公园')], [('fact', '借')], [('category', '博物馆')], [('category', '景点')],
              [('category', 'community_reading')], [('category', '公园'), ('name_contains', '滨水')],
              [('fact', '儿童')], [('fact', '成人')], [('fact', '自助借还')], [('fact', '少儿绘本')]]
    pairs = [[('category', 'city_reading'), ('seats', 40)], [('category', 'community_reading'), ('books', 12000)],
             [('category', 'city_reading'), ('books', 15000)], [('seats', 50), ('books', 15000)],
             [('category', 'community_reading'), ('address', '新桥')], [('category', '公园'), ('name_contains', '滨水')],
             [('category', '博物馆'), ('name_contains', '艺术')], [('address', '仙岩'), ('category', 'reading'), ('seats', 41)],
             [('fact', '儿童'), ('fact', '成人')], [('address', '娄桥'), ('category', 'city_reading'), ('books', 12000)]]
    assert all(any(r['name'] == name for r in records) for name in names)
    return [('named', n) for n in names] + [('semantic', s) for s in single] + [('soft_preferences', s) for s in pairs]


def main():
    if SESSION.exists():
        state = AssistedReview(SESSION, ROOT).state()
        print(json.dumps({'existing': True, 'total': state['total'], 'handled': state['handled']})); return
    records = sorted(json.loads(CORPUS.read_text(encoding='utf-8')), key=lambda r: r['poi_id'])
    queries = [q for group in REQUESTS.values() for q in group]
    specs = specifications(records)
    items = []
    for index, (query, spec) in enumerate(zip(queries, specs), 1):
        for record in records:
            grade, basis = suggest(record, spec)
            items.append({'case_id': f'AI30-{index:02}::{record["poi_id"]}', 'query_id': f'AI30-{index:02}',
                          'query': query, 'query_author': 'AI_assistant',
                          'record': {key: record.get(key) for key in ('poi_id', 'name', 'category', 'address', 'description', 'source_url')},
                          'ai_suggestion': {'grade': grade, 'basis': basis, 'method': 'assistant_authored_explicit_rules_v1',
                                            'human_confirmed': False}, 'specification': spec})
    SESSION.mkdir(parents=True)
    packet = {'purpose': 'ai_assisted_development_review_NOT_independent_test', 'created_utc': datetime.now(timezone.utc).isoformat(),
              'items': items, 'source_bindings': {str(CORPUS.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(CORPUS.read_bytes()).hexdigest()},
              'rubric': 'source-text only; 2 fully supported,1 known partial match,0 known nonmatch,unknown insufficient evidence; multiple preferences remain soft; conjunctive semantic requests require all facts',
              'model_rankings_used': False, 'original_human_labels_modified': False,
              'query_authorship': 'AI_assistant', 'requires_each_human_confirmation': True}
    (SESSION / 'packet.json').write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding='utf-8')
    (SESSION / 'manifest.json').write_text(json.dumps({'packet_sha256': hashlib.sha256((SESSION / 'packet.json').read_bytes()).hexdigest()}, indent=2), encoding='utf-8')
    state = AssistedReview(SESSION, ROOT).state()
    print(json.dumps({'prepared': True, 'total': state['total'], 'handled': state['handled'], 'human_labels_created': 0}))


if __name__ == '__main__':
    main()
