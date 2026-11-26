"""Synthetic checks of an unweighted lexical baseline, without model inference."""
import pytest
from src.data.poi import POI
from src.retrieval.keyword import KeywordRetriever


def test_distinct_overlap_is_not_term_frequency_or_query_repetition():
    rows = [POI('b','阅读 阅读 阅读',is_synthetic=True),
            POI('a','阅读 公园',is_synthetic=True)]
    result = KeywordRetriever(rows).search('阅读 阅读 公园',2)
    assert [(r.poi_id,r.score) for r in result] == [('a',2),('b',1)]


def test_full_order_preserves_zero_overlap_and_deterministic_ties():
    rows = [POI('b','花园',is_synthetic=True),POI('a','公园',is_synthetic=True)]
    assert [r.poi_id for r in KeywordRetriever(rows).search('图书馆',2)] == ['a','b']


def test_identical_text_fields_and_unknown_constraint_does_not_pass():
    rows=[POI('a','地点',category='阅读',description='公园',is_synthetic=True),
          POI('b','另一地点',is_synthetic=True)]
    engine=KeywordRetriever(rows)
    assert engine.documents == tuple(p.search_text for p in rows)
    assert engine.search('公园',predicate=lambda p: None) == []
    assert engine.search('公园',predicate=lambda p:p.poi_id=='a')[0].poi_id=='a'


@pytest.mark.parametrize('query',['','  ','，！？'])
def test_no_terms_returns_no_ranking(query):
    assert KeywordRetriever([POI('a','阅读')]).search(query)==[]


def test_empty_corpus_and_zero_limit():
    assert KeywordRetriever([]).search('公园')==[]
    assert KeywordRetriever([POI('a','阅读')]).search('阅读',0)==[]


@pytest.mark.parametrize('limit',[-1,True,1.5])
def test_invalid_limit(limit):
    with pytest.raises(ValueError):KeywordRetriever([]).search('阅读',limit)
