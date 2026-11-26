"""以下仅为合成 OSM 响应单元测试，不是实际 POI 或人工核验。"""
from copy import deepcopy
import hashlib
import json
import pytest

from src.data.osm_import import build_candidates, import_osm_pilot

@pytest.fixture
def metadata():
    return dict(license='ODbL-1.0', license_evidence_sha256='synthetic_hash',
                sha256='synthetic_hash', raw_path='synthetic.json', finished='2026-10-31T00:00:00Z',
                endpoint='https://overpass-api.de/api/interpreter')

def element(kind='node', identifier=1):
    row = dict(type=kind, id=identifier, tags={'name':'模拟测试公园','leisure':'park'})
    if kind == 'node':
        row.update(lat=28.0, lon=120.6)
    else:
        row['center'] = dict(lat=28.0, lon=120.6)
    return row

def payload(*rows):
    return dict(elements=list(rows), osm3s={'timestamp_osm_base':'2026-10-31T00:00:00Z'})

def test_explicit_tag_category_and_missing_attributes(metadata):
    records, evidence, counts = build_candidates(payload(element()), metadata)
    record = records[0]
    assert record['category'] == '公园'
    assert record['opening_hours'] is None and record['ticket_info'] is None
    assert record['operational_status'] == 'UNKNOWN'
    assert '安静' not in record['description'] and '免费' not in record['description']
    assert counts['named_candidates'] == 1
    assert any(e['source_field'] == 'tags.leisure' for e in evidence)

@pytest.mark.parametrize('kind', ['node','way','relation'])
def test_identity_and_coordinate_semantics(metadata, kind):
    records, _, _ = build_candidates(payload(element(kind)), metadata)
    record = records[0]
    assert record['poi_id'] == f'osm_{kind}_1'
    assert record['original_crs'] == 'WGS84'
    assert record['coordinate_kind'] == ('node_position' if kind == 'node' else 'overpass_bounding_box_center')
    assert record['wgs84_longitude'] is None
    assert not record['coordinate_verified'] and not record['district_verified'] and not record['map_ready']

def test_same_name_different_elements_not_merged(metadata):
    records, _, counts = build_candidates(payload(element(identifier=1), element(identifier=2)), metadata)
    assert len(records) == 2 and counts['unique_osm_elements'] == 2

def test_exact_repeat_only_is_deduplicated(metadata):
    row = element()
    records, _, counts = build_candidates(payload(row, deepcopy(row)), metadata)
    assert len(records) == 1 and counts['exact_duplicate_elements'] == 1

def test_conflicting_identity_rejected(metadata):
    row = element()
    other = deepcopy(row)
    other['tags']['name'] = '另一模拟名称'
    with pytest.raises(ValueError, match='Conflicting'):
        build_candidates(payload(row, other), metadata)

def test_no_category_inference_from_name(metadata):
    row = element()
    row['tags'] = {'name':'模拟博物馆'}
    records, _, _ = build_candidates(payload(row), metadata)
    assert records[0]['category'] == ''

def test_anomalous_coordinate_preserved(metadata):
    row = element()
    row['lat'] = 7.2
    records, _, _ = build_candidates(payload(row), metadata)
    assert records[0]['latitude'] == 7.2
    assert records[0]['coordinate_status'] == 'outside_coarse_regional_range'

def test_missing_coordinate_and_address_remain_unknown(metadata):
    row = element('way')
    row.pop('center')
    records, _, _ = build_candidates(payload(row), metadata)
    assert records[0]['longitude'] is None and records[0]['address'] == ''
    assert records[0]['coordinate_status'] == 'missing'

def test_incomplete_server_response_rejected(metadata):
    source = payload(element())
    source['remark'] = 'runtime timeout'
    with pytest.raises(ValueError, match='Incomplete'):
        build_candidates(source, metadata)

def test_license_required(metadata):
    metadata.pop('license_evidence_sha256')
    with pytest.raises(ValueError, match='license'):
        build_candidates(payload(element()), metadata)

def test_limit_enforced(metadata):
    with pytest.raises(ValueError, match='28'):
        build_candidates(payload(*(element(identifier=i) for i in range(1,30))), metadata)

def test_name_zh_and_address_use_only_actual_tags(metadata):
    row = element()
    row['tags'].update({'name:zh':'模拟中文名','addr:street':'模拟路','addr:housenumber':'1号'})
    records, evidence, _ = build_candidates(payload(row), metadata)
    assert records[0]['name'] == '模拟中文名'
    assert records[0]['address'] == '模拟路 1号'
    assert '瓯海区' not in records[0]['address']
    assert any(e['source_field'] == 'tags.name:zh' for e in evidence)

def make_source(tmp_path, metadata):
    source = tmp_path / 'response.json'
    source.write_text(json.dumps(payload(element()), ensure_ascii=False), encoding='utf-8')
    license_path = tmp_path / 'copyright.html'
    license_path.write_bytes(b'SYNTHETIC LICENSE EVIDENCE FOR UNIT TEST ONLY')
    metadata.update(status='downloaded_pending_import_and_verification',
                    sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    license_evidence_sha256=hashlib.sha256(license_path.read_bytes()).hexdigest())
    return source

def test_import_refuses_overwrite_and_preserves_source(tmp_path, metadata):
    source = make_source(tmp_path, metadata)
    original = source.read_bytes()
    output = tmp_path / 'new'
    summary = import_osm_pilot(source, metadata, output, tmp_path)
    assert summary['candidate_records'] == 1 and not summary['formal_evaluation_ready']
    assert source.read_bytes() == original
    assert summary['provenance_issues'] == []
    with pytest.raises(FileExistsError):
        import_osm_pilot(source, metadata, output, tmp_path)

def test_tampered_raw_rejected(tmp_path, metadata):
    source = make_source(tmp_path, metadata)
    source.write_bytes(source.read_bytes() + b' ')
    with pytest.raises(ValueError, match='SHA256'):
        import_osm_pilot(source, metadata, tmp_path / 'new', tmp_path)
    assert not (tmp_path / 'new').exists()

def test_existing_evidence_required(tmp_path, metadata):
    source = make_source(tmp_path, metadata)
    with pytest.raises(ValueError, match='existing field evidence'):
        import_osm_pilot(source, metadata, tmp_path / 'new', tmp_path, existing=[])
