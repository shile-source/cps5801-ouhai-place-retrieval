"""共享返回结构、输入检查与证据过滤扩展；不解析或猜测自然语言硬约束。"""
import re
from dataclasses import dataclass
from typing import Callable, Iterable, Protocol
from src.data.poi import POI

Predicate = Callable[[POI], bool | None]


@dataclass(frozen=True)
class SearchResult:
    rank: int
    poi: POI
    score: float
    model: str = 'bm25'

    @property
    def poi_id(self) -> str:
        return self.poi.poi_id


class Retriever(Protocol):
    model_name: str

    def search(self, query: str, top_k: int = 10,
               predicate: Predicate | None = None) -> list[SearchResult]: ...


def prepare_corpus(pois: Iterable[POI]) -> tuple[POI, ...]:
    records = tuple(pois)
    if any(not isinstance(p, POI) or not isinstance(p.poi_id, str) or not p.poi_id.strip()
           for p in records):
        raise ValueError('Every candidate needs a nonempty POI ID')
    if len({p.poi_id for p in records}) != len(records):
        raise ValueError('poi_id must be unique')
    if len({p.is_synthetic for p in records}) > 1:
        raise ValueError('Synthetic and real candidates must remain in separate datasets')
    return records


def validate_query(query: str, top_k: int) -> bool:
    if not isinstance(query, str):
        raise ValueError('query must be a string')
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 0:
        raise ValueError('top_k must be a nonnegative integer')
    return top_k > 0 and bool(re.search(r'\w', query, flags=re.UNICODE))


def eligible(poi: POI, predicate: Predicate | None) -> bool:
    # 只有明确的True可通过；None等未知状态不能当作满足硬约束。
    return predicate is None or predicate(poi) is True
