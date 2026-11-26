"""证据优先的数据质量检查；合理范围不等于坐标已验证。"""
from collections import Counter
from itertools import combinations
import hashlib
import math
from pathlib import Path
from .import_reading_pilot import normalize

def missing(value):
    return value is None or (isinstance(value, str) and not value.strip()) or value == []

def coordinate_status(lon, lat):
    if missing(lon) or missing(lat):
        return 'missing'
    try:
        lon, lat = float(lon), float(lat)
    except (ValueError, TypeError):
        return 'not_numeric'
    if not math.isfinite(lon) or not math.isfinite(lat):
        return 'not_finite'
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return 'outside_global_range'
    if not (119 <= lon <= 122 and 26 <= lat <= 30):
        return 'outside_coarse_regional_range'
    return 'plausible_unverified'

def map_eligible(record):
    return bool(record.get('coordinate_verified') is True
                and record.get('district_verified') is True
                and record.get('coordinate_verification_evidence')
                and record.get('district_verification_evidence')
                and record.get('original_crs') in ('WGS84', 'GCJ-02', 'BD-09')
                and record.get('crs_evidence')
                and coordinate_status(record.get('wgs84_longitude'), record.get('wgs84_latitude')) == 'plausible_unverified'
                and record.get('coordinate_conversion_method'))

def duplicate_review(records):
    """只生成待审查对，不用同名或共用电话自动合并实体。"""
    pairs = []
    for a, b in combinations(records, 2):
        reasons = []
        for field in ('name', 'address'):
            if a.get(field) and normalize(a[field]) == normalize(b.get(field) or ''):
                reasons.append('same_' + field)
        def stem(r):
            return (r.get('name') or '').replace('百姓书屋', '').replace('城市书房', '')
        if stem(a) and stem(a) == stem(b):
            reasons.append('same_name_stem')
        if reasons:
            pairs.append({'a': a['poi_id'], 'b': b['poi_id'], 'reasons': reasons,
                          'action': 'manual_review_no_automatic_merge'})
    return pairs

def factual_description(record, evidence):
    """每一小句追溯原始字段；不推断安静、学习体验、面积单位或当前运营。"""
    selected = [e for e in evidence if e['poi_id'] == record['poi_id']]
    clauses, refs = [], []
    labels = {'名称': '名称', '类型': '类型', '地址': '地址', '座位数': '座位数',
              '藏书量': '藏书量', '开放时间': '开放时间'}
    for field, label in labels.items():
        values = {normalize(e['source_value']) for e in selected if e['source_field'] == field and not missing(e['source_value'])}
        if len(values) != 1:
            continue  # 冲突或缺失不能选择性编造事实。
        value = next(iter(values))
        clauses.append(f'{label}：{value}')
        refs.append({'clause_index': len(clauses)-1, 'source_field': field,
                     'source_value': value, 'evidence': [e for e in selected if e['source_field'] == field]})
    return ('来源记录记载：' + '；'.join(clauses) + '。' if clauses else None), refs

def report(records, evidence, root):
    """按维度统计，不把有来源、可检索、可上图三种状态混淆。"""
    issues, hashes = [], {}
    required = ('source_id', 'source_record_id', 'source_url', 'downloaded_at', 'raw_path', 'raw_sha256', 'source_field')
    for e in evidence:
        problems = [key for key in required if missing(e.get(key))]
        path = Path(e.get('raw_path') or '')
        if not path.is_absolute():
            path = Path(root) / path
        if path not in hashes:
            hashes[path] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if hashes[path] != e.get('raw_sha256'):
            problems.append('raw_hash_mismatch_or_missing')
        if problems:
            issues.append({'poi_id': e.get('poi_id'), 'field': e.get('source_field'), 'issues': problems})
    supported = {e['poi_id'] for e in evidence}
    bad = {e['poi_id'] for e in issues}
    for r in records:
        if r['poi_id'] not in supported:
            issues.append({'poi_id':r['poi_id'], 'issues':['no_field_evidence']})
            bad.add(r['poi_id'])
    fields = ('name', 'category', 'address', 'opening_hours', 'description', 'description_zh',
              'ticket_info', 'longitude', 'latitude', 'wgs84_longitude', 'wgs84_latitude')
    statuses = Counter(coordinate_status(r.get('longitude'), r.get('latitude')) for r in records)
    return {'candidate_records': len(records), 'provenance_issues': issues,
            'source_backed_records': sum(r['poi_id'] not in bad for r in records),
            'verified_places': sum(r.get('district_verified') is True and r.get('coordinate_verified') is True and map_eligible(r) for r in records),
            'map_ready_records': sum(map_eligible(r) for r in records),
            'retrieval_text_ready_records': sum(not missing(r.get('name')) and r['poi_id'] not in bad for r in records),
            'coordinate_status_counts': dict(statuses),
            'coordinate_anomalies': [{'poi_id':r['poi_id'],'name':r['name'],'original_longitude':r.get('longitude'),'original_latitude':r.get('latitude'),'status':coordinate_status(r.get('longitude'),r.get('latitude'))} for r in records if coordinate_status(r.get('longitude'),r.get('latitude')) not in ('missing','plausible_unverified')],
            'missing_counts': {f: sum(missing(r.get(f)) for r in records) for f in fields},
            'category_counts': dict(Counter(r.get('category') or 'UNKNOWN' for r in records)),
            'crs_counts': dict(Counter(r.get('original_crs') or 'UNKNOWN' for r in records)),
            'duplicate_review': duplicate_review(records),
            'note': 'Text-ready means software smoke-test eligibility, not a frozen or geographically verified evaluation corpus.'}
