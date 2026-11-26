"""Synthetic encoder only: no model load, download, or human-label generation."""
import numpy as np
import pytest
from src.data.poi import POI
from src.retrieval.bge_m3 import BGEM3DenseRetriever


class FakeBGE:
    def __init__(self,dim=1024): self.dim=dim; self.calls=[]
    def encode(self,texts,**kwargs):
        self.calls.append(tuple(texts))
        out=np.zeros((len(texts),self.dim),dtype=np.float32)
        for i,t in enumerate(texts): out[i,0 if '阅读' in t else 1]=2
        return out


def records():
    return [POI('synthetic2','阅读',is_synthetic=True),POI('synthetic1','阅读',is_synthetic=True),
            POI('synthetic3','运动',is_synthetic=True)]


def test_dense_only_interface_fields_cosine_ties():
    encoder=FakeBGE(); model=BGEM3DenseRetriever(records(),encoder=encoder)
    result=model.search('阅读',10)
    assert [r.poi_id for r in result]==['synthetic1','synthetic2','synthetic3']
    assert [r.score for r in result]==pytest.approx([1,1,0])
    assert model.documents==tuple(p.search_text for p in records())
    assert all(r.model=='BAAI/bge-m3' for r in result)
    assert encoder.max_seq_length==128


def test_common_predicate_unknown_does_not_pass():
    model=BGEM3DenseRetriever(records(),encoder=FakeBGE())
    assert model.search('阅读',predicate=lambda p:None)==[]
    assert [r.poi_id for r in model.search('阅读',predicate=lambda p:p.poi_id=='synthetic1')]==['synthetic1']


def test_wrong_dimension_fails_instead_of_using_mpnet_dimension():
    with pytest.raises(ValueError,match='1024'):
        BGEM3DenseRetriever(records(),encoder=FakeBGE(768))


def test_incomplete_deployment_never_loads_or_downloads(tmp_path,monkeypatch):
    import src.retrieval.bge_m3 as module
    monkeypatch.setattr(module,'MODEL_PATH',tmp_path)
    with pytest.raises(FileNotFoundError,match='deployment missing'):
        BGEM3DenseRetriever(records())


def test_empty_corpus_does_not_load():
    assert BGEM3DenseRetriever([]).search('阅读')==[]


def test_direct_gpu_is_explicit_and_missing_helper_not_installed(monkeypatch):
    model=BGEM3DenseRetriever([],direct_gpu_load=True)
    monkeypatch.setattr('src.retrieval.bge_m3.importlib.util.find_spec',lambda _:None)
    with pytest.raises(RuntimeError,match='no automatic installation'):model._loader_kwargs('cuda')
    with pytest.raises(ValueError,match='requires CUDA'):model._loader_kwargs('cpu')


def test_direct_gpu_map_only_when_requested(monkeypatch):
    monkeypatch.setattr('src.retrieval.bge_m3.importlib.util.find_spec',lambda _:object())
    assert BGEM3DenseRetriever([])._loader_kwargs('cuda')=={}
    assert BGEM3DenseRetriever([],direct_gpu_load=True)._loader_kwargs('cuda')=={'device_map':{'':'cuda:0'}}


def test_fp16_is_explicit_and_keeps_normalized_output(monkeypatch):
    monkeypatch.setattr('src.retrieval.bge_m3.importlib.util.find_spec',lambda _:object())
    model=BGEM3DenseRetriever(records(),encoder=FakeBGE(),device='cuda',precision='float16',direct_gpu_load=True)
    assert model._loader_kwargs('cuda')=={'dtype':'float16','device_map':{'':'cuda:0'}}
    assert model.search('阅读')[0].score==pytest.approx(1)
    assert model.precision=='float16'


def test_fp16_cpu_not_silently_selected():
    with pytest.raises(ValueError,match='requires CUDA'):
        BGEM3DenseRetriever([],precision='float16')
