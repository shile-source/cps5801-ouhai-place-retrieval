"""Opt-in local construction context for the installed safetensors pread backend."""
from contextlib import contextmanager
import importlib
import threading

_LOCK=threading.RLock()


@contextmanager
def transformers_safetensors_backend(backend):
    """Scope Transformers' I/O alias to one loader; restore even when loading fails.

    This uses the public safetensors backend argument without editing either
    installed package or checkpoint. It is intended for an isolated worker,
    not concurrent independent model construction in the same interpreter.
    """
    if backend not in ('mmap','pread'):
        raise ValueError('Unsupported safetensors backend')
    if backend=='mmap':
        yield
        return
    with _LOCK:
        module=importlib.import_module('transformers.modeling_utils')
        original=module.safe_open
        def with_backend(*args,**kwargs):
            kwargs['backend']=backend
            return original(*args,**kwargs)
        module.safe_open=with_backend
        try:
            yield
        finally:
            module.safe_open=original
