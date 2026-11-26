"""本地Sentence Encoder余弦检索。候选文本缓存于内存，不修改原始数据。"""
from pathlib import Path
from contextlib import nullcontext
from typing import Iterable
import numpy as np
from src.data.poi import POI
from .common import SearchResult, Predicate, prepare_corpus, validate_query, eligible

MODEL_ID = 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
REVISION = '4328cf26390c98c5e3c738b4460a05b95f4911f5'
MODEL_PATH = Path(__file__).resolve().parents[2] / 'models/paraphrase-multilingual-mpnet-base-v2' / REVISION
DIMENSION = 768


class SentenceEncoderRetriever:
    model_name = MODEL_ID
    embedding_dimension = DIMENSION

    def _checkpoint_path(self):
        return MODEL_PATH

    def _loader_kwargs(self, device):
        return {'dtype':'float16'} if self.precision=='float16' else {}

    def _loader_context(self):
        return nullcontext()

    def _build_encoder(self,checkpoint,device):
        if self.safe_streaming:
            from .streamed_bge import load_streamed_bge
            return load_streamed_bge(checkpoint,device,self.precision,self.max_length)
        from sentence_transformers import SentenceTransformer
        with self._loader_context():
            return SentenceTransformer(str(checkpoint), device=device, local_files_only=True,
                                       trust_remote_code=False, model_kwargs=self._loader_kwargs(device))

    def __init__(self, pois: Iterable[POI], *, encoder=None, device: str = 'cpu',
                 batch_size: int = 4, max_length: int = 128, precision: str = 'float32',safe_streaming: bool = False):
        if type(safe_streaming) is not bool:
            raise ValueError('Explicit streaming boolean required')
        self.safe_streaming=safe_streaming
        if precision not in ('float32','float16'):
            raise ValueError('Explicit float32 or float16 precision required')
        if precision=='float16' and device not in ('cuda','cuda:0'):
            raise ValueError('This float16 configuration requires CUDA')
        self.precision=precision
        self.pois = prepare_corpus(pois)
        self.documents = tuple(p.search_text for p in self.pois)
        if type(batch_size) is not int or batch_size < 1 or type(max_length) is not int or max_length < 1:
            raise ValueError('batch_size and max_length must be positive integers')
        self.batch_size = batch_size
        self.max_length = max_length
        self.encoder = encoder
        self._positions = tuple(i for i, text in enumerate(self.documents) if validate_query(text, 1))
        self._vectors = np.empty((0, self.embedding_dimension), dtype=np.float32)
        if not self._positions:
            return
        if self.encoder is None:
            checkpoint = self._checkpoint_path()
            if not (checkpoint / 'model.safetensors').is_file():
                raise FileNotFoundError('Fixed local checkpoint missing; automatic download is forbidden')
            # 延迟导入：单元测试使用明确模拟的encoder，不加载真实模型或访问网络。
            self.encoder=self._build_encoder(checkpoint,device)
        self.encoder.max_seq_length = max_length
        self._vectors = self._encode([self.documents[i] for i in self._positions])
        self._vectors.setflags(write=False)

    def _encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.asarray(self.encoder.encode(
            texts, batch_size=self.batch_size, normalize_embeddings=True,
            convert_to_numpy=True, show_progress_bar=False), dtype=np.float32)
        if vectors.shape != (len(texts), self.embedding_dimension) or not np.isfinite(vectors).all():
            raise ValueError(f'Encoder must return finite N x {self.embedding_dimension} vectors')
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if not np.isfinite(norms).all() or np.any(norms <= 0):
            raise ValueError('Encoder returned invalid/zero vector norms')
        # 再次显式归一化，使点积严格表示余弦相似度，不将得分解释成概率。
        return vectors / norms

    def search(self, query: str, top_k: int = 10,
               predicate: Predicate | None = None) -> list[SearchResult]:
        if not validate_query(query, top_k) or not self._positions:
            return []
        allowed = [j for j, i in enumerate(self._positions) if eligible(self.pois[i], predicate)]
        if not allowed:
            return []
        query_vector = self._encode([query])[0]
        scores = np.clip(self._vectors[allowed] @ query_vector, -1.0, 1.0)
        rows = [(self.pois[self._positions[j]], float(score)) for j, score in zip(allowed, scores)]
        # 同分按固定POI ID排序；不同模型的原始分数不可直接比较。
        rows.sort(key=lambda item: (-item[1], item[0].poi_id))
        return [SearchResult(rank, poi, score, self.model_name)
                for rank, (poi, score) in enumerate(rows[:top_k], 1)]
