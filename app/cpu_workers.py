"""Physical-core discovery and verified per-process CPU affinity on Windows."""
import ctypes
import os
import queue
from contextlib import contextmanager

def kernel():
    api=ctypes.WinDLL("kernel32",use_last_error=True)
    api.GetCurrentProcess.restype=ctypes.c_void_p
    api.GetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)]
    api.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    return api

def physical_core_cpus():
    if os.name!="nt": raise RuntimeError("Physical-core binding currently requires Windows")
    api=kernel()
    class Payload(ctypes.Union):
        _fields_=[("reserved",ctypes.c_ulonglong*2)]
    class Info(ctypes.Structure):
        _fields_=[("mask",ctypes.c_size_t),("relationship",ctypes.c_int),("data",Payload)]
    size=ctypes.c_ulong()
    api.GetLogicalProcessorInformation(None,ctypes.byref(size))
    if not size.value: raise ctypes.WinError(ctypes.get_last_error())
    buffer=ctypes.create_string_buffer(size.value)
    if not api.GetLogicalProcessorInformation(buffer,ctypes.byref(size)):raise ctypes.WinError(ctypes.get_last_error())
    allowed=ctypes.c_size_t();system=ctypes.c_size_t()
    if not api.GetProcessAffinityMask(api.GetCurrentProcess(),ctypes.byref(allowed),ctypes.byref(system)):
        raise ctypes.WinError(ctypes.get_last_error())
    cpus=[]
    for offset in range(0,size.value,ctypes.sizeof(Info)):
        record=Info.from_buffer(buffer,offset)
        mask=record.mask & allowed.value
        if record.relationship==0 and mask:
            cpus.append((mask & -mask).bit_length()-1)
    if not cpus:raise RuntimeError("No available physical cores detected")
    return cpus

def worker_count(requested,available):
    if requested=="auto":return min(4,available)
    if isinstance(requested,bool) or not str(requested).isdigit() or not 1<=int(requested)<=available:
        raise ValueError(f"Choose between 1 and {available} physical cores")
    return int(requested)

def bind_process(process,cpu):
    api=kernel();mask=1<<cpu
    if not api.SetProcessAffinityMask(int(process._handle),mask):raise ctypes.WinError(ctypes.get_last_error())
    actual=ctypes.c_size_t();system=ctypes.c_size_t()
    if not api.GetProcessAffinityMask(int(process._handle),ctypes.byref(actual),ctypes.byref(system)):
        raise ctypes.WinError(ctypes.get_last_error())
    if actual.value!=mask:raise RuntimeError("JavaFoil CPU affinity did not match the selected core")
    return actual.value

class CoreSlots:
    def __init__(self,cpus):
        self.queue=queue.Queue()
        for cpu in cpus:self.queue.put(cpu)
    @contextmanager
    def acquire(self):
        cpu=self.queue.get()
        try:yield cpu
        finally:self.queue.put(cpu)
