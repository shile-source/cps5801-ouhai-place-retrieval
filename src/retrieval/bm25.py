import re
from typing import Iterable
import jieba
from rank_bm25 import BM25Okapi
from src.data.poi import POI
from .common import SearchResult, Predicate, prepare_corpus, validate_query, eligible

def tokenize(text: str) -> list[str]:
    # Jieba 将中文切分为词；保留含文字或数字的词，去掉空白和标点。
    return [word.lower().strip() for word in jieba.lcut(text)
            if re.search(r'[\w]', word, flags=re.UNICODE)]

class BM25Retriever:
    model_name = 'bm25'

    def __init__(self, pois: Iterable[POI]):
        self.pois = prepare_corpus(pois)
        self.documents = tuple(p.search_text for p in self.pois)
        self.tokens = [tokenize(p.search_text) for p in self.pois]
        self.index = BM25Okapi(self.tokens) if any(self.tokens) else None

    def search(self, query: str, top_k: int = 10,
               predicate: Predicate | None = None) -> list[SearchResult]:
        if not validate_query(query, top_k):
            return []
        query_tokens = tokenize(query)
        if not query_tokens or top_k == 0 or self.index is None:
            return []
        # BM25 综合词频、逆文档频率和文档长度，不是相关性概率。
        scores = self.index.get_scores(query_tokens)
        candidates = [(p, float(score)) for p, score, terms in
                      zip(self.pois, scores, self.tokens)
                      if terms and eligible(p, predicate)]
        # 分数降序；同分使用固定 ID 排序，保证重复运行一致。
        candidates.sort(key=lambda item: (-item[1], item[0].poi_id))
        return [SearchResult(rank, poi, score, self.model_name) for rank, (poi, score)
                in enumerate(candidates[:top_k], 1)]
