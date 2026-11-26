"""Kernel lock tests only; never import torch, construct a CUDA context or load weights."""
import pytest
from src.retrieval.gpu_lease import GPULease


def test_second_handle_is_rejected_until_first_releases(tmp_path):
    path=tmp_path/'synthetic_gpu.lock'
    with GPULease(path):
        with pytest.raises(RuntimeError,match='另一项'):GPULease(path).__enter__()
    with GPULease(path):pass


def test_exception_releases_lock_and_stale_metadata_does_not_block(tmp_path):
    path=tmp_path/'synthetic_gpu.lock'
    with pytest.raises(ValueError):
        with GPULease(path):raise ValueError('synthetic worker failure')
    with GPULease(path):pass


def test_lock_blocks_a_separate_process(tmp_path):
    import subprocess
    import sys
    code='''import sys
from src.retrieval.gpu_lease import GPULease
lease=GPULease(sys.argv[1])
try:lease.__enter__()
except RuntimeError:print('blocked');raise SystemExit(0)
lease.__exit__();raise SystemExit(1)
'''
    path=tmp_path/'synthetic_gpu.lock'
    with GPULease(path):
        result=subprocess.run([sys.executable,'-c',code,str(path)],capture_output=True,text=True,timeout=15)
    assert result.returncode==0 and result.stdout.strip()=='blocked'
