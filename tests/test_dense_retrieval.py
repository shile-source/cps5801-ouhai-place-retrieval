"""纯模拟向量测试；不下载、不加载真实模型，不构造研究相关性标签。"""
import numpy as np
import pytest
from src.data.poi import POI
from src.retrieval import BM25Retriever, SentenceEncoderRetriever
from src.retrieval.common import SearchResult


class SyntheticEncoder:
    def __init__(self):
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append(tuple(texts))
        vectors = np.zeros((len(texts), 768), dtype=np.float32)
        for i, text in enumerate(texts):
            vectors[i, :2] = [2, 0] if '阅读' in text else [0, 3]
        return vectors


def corpus():
    return [POI('s2', '模拟乙', description='阅读', is_synthetic=True),
            POI('s1', '模拟甲', description='阅读', is_synthetic=True),
            POI('s3', '模拟丙', description='运动', is_synthetic=True)]


def build(kind, records=None):
    records = corpus() if records is None else records
    return (BM25Retriever(records) if kind == 'bm25' else
            SentenceEncoderRetriever(records, encoder=SyntheticEncoder()))


@pytest.mark.parametrize('kind', ['bm25', 'dense'])
def test_common_results_and_candidates(kind):
    r = build(kind)
    rows = r.search('阅读', 50)
    assert len(rows) == 3
    assert [x.rank for x in rows] == [1, 2, 3]
    assert {x.poi_id for x in rows} == {'s1', 's2', 's3'}
    assert all(isinstance(x, SearchResult) and x.model == r.model_name for x in rows)
    assert all(np.isfinite(x.score) for x in rows)
    assert [x.score for x in rows] == sorted([x.score for x in rows], reverse=True)
    assert r.documents == tuple(p.search_text for p in corpus())


def test_dense_cosine_and_ties():
    rows = build('dense').search('阅读')
    assert [r.poi_id for r in rows] == ['s1', 's2', 's3']
    assert [r.score for r in rows] == pytest.approx([1, 1, 0])


@pytest.mark.parametrize('kind', ['bm25', 'dense'])
def test_repeat_and_input_order_stability(kind):
    retriever = build(kind)
    a = retriever.search('阅读')
    assert retriever.search('阅读') == a
    assert build(kind, list(reversed(corpus()))).search('阅读') == a


@pytest.mark.parametrize('kind', ['bm25', 'dense'])
@pytest.mark.parametrize('query', ['', '  ', '，！？'])
def test_empty_queries(kind, query):
    assert build(kind).search(query) == []


@pytest.mark.parametrize('kind', ['bm25', 'dense'])
@pytest.mark.parametrize('k', [-1, True, 1.5])
def test_invalid_limit(kind, k):
    with pytest.raises(ValueError):
        build(kind).search('阅读', k)


@pytest.mark.parametrize('kind', ['bm25', 'dense'])
def test_invalid_query_and_zero(kind):
    r = build(kind)
    with pytest.raises(ValueError):
        r.search(None)
    assert r.search('阅读', 0) == []


@pytest.mark.parametrize('kind', ['bm25', 'dense'])
def test_unknown_constraint_is_not_satisfied(kind):
    r = build(kind)
    evidence = {'s1': True, 's2': None, 's3': False}
    assert [x.poi_id for x in r.search('阅读', predicate=lambda p: evidence[p.poi_id])] == ['s1']
    assert r.search('阅读', predicate=lambda p: None) == []


@pytest.mark.parametrize('kind', ['bm25', 'dense'])
def test_empty_corpus_and_document(kind):
    assert build(kind, []).search('阅读') == []
    assert build(kind, [POI('empty', '')]).search('阅读') == []


@pytest.mark.parametrize('kind', ['bm25', 'dense'])
def test_dataset_isolation(kind):
    original = corpus()
    first = build(kind, original)
    original.clear()
    other = build(kind, [POI('s9', '独立模拟', is_synthetic=True)])
    assert {r.poi_id for r in first.search('阅读')} == {'s1', 's2', 's3'}
    assert [r.poi_id for r in other.search('阅读')] == ['s9']


@pytest.mark.parametrize('kind', ['bm25', 'dense'])
def test_reject_mixed_and_duplicate_ids(kind):
    with pytest.raises(ValueError, match='Synthetic'):
        build(kind, [POI('real', '仅作混合输入检查'), corpus()[0]])
    with pytest.raises(ValueError, match='unique'):
        build(kind, [corpus()[0], corpus()[0]])
    with pytest.raises(ValueError, match='nonempty'):
        build(kind, [POI('', '')])


@pytest.mark.parametrize('bad', ['nan', 'zero', 'shape'])
def test_reject_invalid_encoder_output(bad):
    class Broken(SyntheticEncoder):
        def encode(self, texts, **kwargs):
            if bad == 'shape':
                return np.ones((len(texts), 2))
            return np.full((len(texts), 768), np.nan if bad == 'nan' else 0)
    with pytest.raises(ValueError):
        SentenceEncoderRetriever(corpus(), encoder=Broken())


def test_query_encoding_failure_does_not_damage_corpus():
    encoder = SyntheticEncoder()
    retriever = SentenceEncoderRetriever(corpus(), encoder=encoder)
    original = retriever._vectors.copy()
    good = encoder.encode
    encoder.encode = lambda texts, **kwargs: np.full((len(texts), 768), np.inf)
    with pytest.raises(ValueError):
        retriever.search('阅读')
    assert np.array_equal(retriever._vectors, original)
    encoder.encode = good
    assert retriever.search('阅读')[0].poi_id == 's1'


def test_documents_cached_once_and_shared_fields():
    encoder = SyntheticEncoder()
    r = SentenceEncoderRetriever(corpus(), encoder=encoder)
    r.search('阅读')
    r.search('运动')
    assert encoder.calls == [r.documents, ('阅读',), ('运动',)]
    assert not r._vectors.flags.writeable


@pytest.mark.parametrize('kwargs', [{'batch_size': 0}, {'max_length': 0}, {'batch_size': True}])
def test_invalid_encoder_config(kwargs):
    with pytest.raises(ValueError):
        SentenceEncoderRetriever(corpus(), encoder=SyntheticEncoder(), **kwargs)


def test_missing_local_checkpoint_never_downloads(tmp_path, monkeypatch):
    import src.retrieval.dense as module
    monkeypatch.setattr(module, 'MODEL_PATH', tmp_path / 'missing_checkpoint')
    with pytest.raises(FileNotFoundError, match='automatic download is forbidden'):
        SentenceEncoderRetriever(corpus())


def test_empty_corpus_does_not_load_model():
    assert SentenceEncoderRetriever([]).search('阅读') == []
