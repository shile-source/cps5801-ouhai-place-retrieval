import json
import pytest
from src.data.load_candidates import load_candidates


def test_loader_preserves_missing_fields(tmp_path):
    # 人工构造的格式测试文件，不代表真实POI或正式数据。
    path = tmp_path / 'format_only.json'
    path.write_text(json.dumps([{'poi_id': 'format-test', 'name': '仅格式测试', 'is_synthetic': False}]), encoding='utf-8')
    poi = load_candidates(path)[0]
    assert poi.category == poi.address == poi.description == ''
    assert poi.search_text == '仅格式测试'


@pytest.mark.parametrize('value', [True, None])
def test_loader_rejects_synthetic_or_unspecified_status(tmp_path, value):
    path = tmp_path / 'format_only.json'
    path.write_text(json.dumps([{'poi_id': 's', 'name': '模拟', 'is_synthetic': value}]), encoding='utf-8')
    with pytest.raises(ValueError):
        load_candidates(path)


@pytest.mark.parametrize('rows', [{'poi_id': 'x'}, [{'poi_id': 'x', 'is_synthetic': False, 'description': None}]])
def test_loader_rejects_invalid_schema(tmp_path, rows):
    path = tmp_path / 'invalid.json'
    path.write_text(json.dumps(rows), encoding='utf-8')
    with pytest.raises(ValueError):
        load_candidates(path)
