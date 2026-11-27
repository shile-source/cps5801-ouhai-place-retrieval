"""Small, read-only resource samples. Never imports Torch or changes Windows settings."""
from datetime import datetime
import ctypes
import os


def resource_snapshot(pid=None):
    import psutil
    result={'sampled_at':datetime.now().astimezone().isoformat(),
            'available_ram_bytes':psutil.virtual_memory().available,
            'pagefile_total_bytes':psutil.swap_memory().total}
    if pid:
        try:
            memory=psutil.Process(pid).memory_info()
            result.update(worker_pid=pid,worker_rss_bytes=memory.rss,
                          worker_private_commit_bytes=getattr(memory,'private',None))
        except (psutil.NoSuchProcess,psutil.AccessDenied):result['worker_sample_unavailable']=True
    if os.name=='nt':
        class PerformanceInfo(ctypes.Structure):
            _fields_=[('cb',ctypes.c_ulong)]+[(key,ctypes.c_size_t) for key in (
                'CommitTotal','CommitLimit','CommitPeak','PhysicalTotal','PhysicalAvailable',
                'SystemCache','KernelTotal','KernelPaged','KernelNonpaged','PageSize')]+[
                ('HandleCount',ctypes.c_ulong),('ProcessCount',ctypes.c_ulong),('ThreadCount',ctypes.c_ulong)]
        info=PerformanceInfo();info.cb=ctypes.sizeof(info)
        if ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(info),info.cb):
            result.update(system_commit_bytes=info.CommitTotal*info.PageSize,
                          system_commit_limit_bytes=info.CommitLimit*info.PageSize)
    return result
