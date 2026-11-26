"""Unweighted distinct-token overlap baseline; no learned weights or implicit filters."""
from typing import Iterable
from src.data.poi import POI
from .bm25 import tokenize
from .common import SearchResult, Predicate, prepare_corpus, validate_query, eligible


class KeywordRetriever:
    model_name = 'keyword_overlap'

    def __init__(self, pois: Iterable[POI]):
        self.pois = prepare_corpus(pois)
        self.documents = tuple(p.search_text for p in self.pois)
        self.tokens = tuple(frozenset(tokenize(text)) for text in self.documents)

    def search(self, query: str, top_k: int = 10,
               predicate: Predicate | None = None) -> list[SearchResult]:
        if not validate_query(query, top_k):
            return []
        terms = frozenset(tokenize(query))
        if not terms:
            return []
        rows = [(poi, float(len(terms & tokens))) for poi, tokens in zip(self.pois, self.tokens)
                if tokens and eligible(poi, predicate)]
        rows.sort(key=lambda item: (-item[1], item[0].poi_id))
        return [SearchResult(rank, poi, score, self.model_name)
                for rank, (poi, score) in enumerate(rows[:top_k], 1)]
