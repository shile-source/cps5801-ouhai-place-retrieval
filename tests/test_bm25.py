import pytest
from src.data.poi import POI
from src.retrieval.bm25 import BM25Retriever, tokenize

@pytest.fixture
def pois():
    # 仅单元测试模拟文本，不代表真实地点。
    return [POI('s1', '模拟图书馆', description='安静 阅读 学习', is_synthetic=True),
            POI('s2', '模拟公园', description='散步 运动', is_synthetic=True),
            POI('s3', '模拟餐厅', description='餐饮 聚餐', is_synthetic=True),
            POI('s4', '模拟商店', description='购物', is_synthetic=True)]

def test_chinese_tokenization():
    assert tokenize('阅读，学习！') == ['阅读', '学习']

def test_normal_query(pois):
    assert BM25Retriever(pois).search('安静 阅读')[0].poi.poi_id == 's1'

def test_top_k_order(pois):
    results = BM25Retriever(pois).search('阅读', 3)
    assert len(results) == 3
    assert [r.rank for r in results] == [1, 2, 3]
    assert [r.score for r in results] == sorted([r.score for r in results], reverse=True)

@pytest.mark.parametrize('query', ['', '   ', '，！？'])
def test_empty_query(pois, query):
    assert BM25Retriever(pois).search(query) == []

def test_empty_dataset():
    assert BM25Retriever([]).search('阅读') == []

def test_empty_documents():
    assert BM25Retriever([POI('empty', '')]).search('阅读') == []

def test_repeated_query(pois):
    retriever = BM25Retriever(pois)
    assert retriever.search('阅读') == retriever.search('阅读')

def test_reproducibility(pois):
    assert BM25Retriever(pois).search('阅读') == BM25Retriever(pois).search('阅读')

def test_tie_order(pois):
    assert [r.poi.poi_id for r in BM25Retriever(reversed(pois)).search('不存在词')] == ['s1','s2','s3','s4']

def test_filter(pois):
    assert all(r.poi.poi_id != 's1' for r in BM25Retriever(pois).search('阅读', predicate=lambda p: p.poi_id != 's1'))

@pytest.mark.parametrize('value', [-1, 1.5, True])
def test_invalid_top_k(pois, value):
    with pytest.raises(ValueError):
        BM25Retriever(pois).search('阅读', value)

def test_zero_top_k(pois):
    assert BM25Retriever(pois).search('阅读', 0) == []

def test_duplicate_id():
    with pytest.raises(ValueError):
        BM25Retriever([POI('same','甲'),POI('same','乙')])

def test_shared_text():
    assert POI('a',' 名称 ','类别','','说明').search_text == '名称\n类别\n说明'

def test_utf8_roundtrip(tmp_path):
    path = tmp_path / 'roundtrip.txt'
    path.write_text('瓯海区中文读写测试', encoding='utf-8')
    assert path.read_text(encoding='utf-8') == '瓯海区中文读写测试'
