"""One project GPU process at a time, using a kernel lock released on process exit."""
from datetime import datetime
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


class GPULease:
    def __init__(self,path=None):
        self.path=Path(path) if path is not None else ROOT/'.cache/locks/gpu_worker.lock'
        self.handle=None

    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.handle=self.path.open('a+b')
        if self.path.stat().st_size==0:
            self.handle.write(b'0');self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:
            self.handle.close();self.handle=None
            raise RuntimeError('另一项项目GPU任务正在运行；本次未导入或加载模型，请等待它结束') from exc
        # The metadata is diagnostic only; exclusion is enforced by the kernel lock.
        self.handle.seek(1);self.handle.truncate()
        self.handle.write(json.dumps({'pid':os.getpid(),'acquired_at':datetime.now().astimezone().isoformat()}).encode())
        self.handle.flush()
        return self

    def __exit__(self,*exc):
        if self.handle is not None:
            self.handle.seek(0)
            try:
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(self.handle.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    import fcntl
                    fcntl.flock(self.handle.fileno(),fcntl.LOCK_UN)
            finally:
                self.handle.close();self.handle=None
