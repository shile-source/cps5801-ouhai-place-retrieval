"""Synthetic I/O hooks: no model or external package mutation persists."""
from types import SimpleNamespace
import pytest
from src.retrieval.safetensor_io import transformers_safetensors_backend


def test_pread_scoped_and_restored_on_error(monkeypatch):
    calls=[]
    def original(*args,**kwargs):calls.append((args,kwargs));return 'synthetic'
    fake=SimpleNamespace(safe_open=original)
    monkeypatch.setattr('src.retrieval.safetensor_io.importlib.import_module',lambda _:fake)
    with pytest.raises(RuntimeError,match='synthetic failure'):
        with transformers_safetensors_backend('pread'):
            assert fake.safe_open('synthetic_file',framework='pt')=='synthetic'
            raise RuntimeError('synthetic failure')
    assert fake.safe_open is original
    assert calls==[(('synthetic_file',),{'framework':'pt','backend':'pread'})]


def test_default_does_not_import_or_patch(monkeypatch):
    monkeypatch.setattr('src.retrieval.safetensor_io.importlib.import_module',lambda _:pytest.fail('unexpected import'))
    with transformers_safetensors_backend('mmap'):pass


def test_unknown_backend_rejected():
    with pytest.raises(ValueError):
        with transformers_safetensors_backend('unknown'):pass
