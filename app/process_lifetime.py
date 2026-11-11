"""Windows Job Objects: processos de mídia não sobrevivem ao seu controlador."""
import ctypes
from ctypes import wintypes

kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
kernel.CreateJobObjectW.restype = wintypes.HANDLE
kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
kernel.SetInformationJobObject.restype = wintypes.BOOL
kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
kernel.AssignProcessToJobObject.restype = wintypes.BOOL
kernel.GetCurrentProcess.restype = wintypes.HANDLE
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
kernel.CloseHandle.restype = wintypes.BOOL

class BasicLimits(ctypes.Structure):
    _fields_ = [('process_time',ctypes.c_longlong),('job_time',ctypes.c_longlong),('flags',wintypes.DWORD),
                ('minimum_working_set',ctypes.c_size_t),('maximum_working_set',ctypes.c_size_t),
                ('active_process_limit',wintypes.DWORD),('affinity',ctypes.c_size_t),
                ('priority_class',wintypes.DWORD),('scheduling_class',wintypes.DWORD)]

class IOCounters(ctypes.Structure):
    _fields_ = [(name,ctypes.c_ulonglong) for name in ['read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes']]

class ExtendedLimits(ctypes.Structure):
    _fields_ = [('basic',BasicLimits),('io',IOCounters),('process_memory',ctypes.c_size_t),
                ('job_memory',ctypes.c_size_t),('peak_process_memory',ctypes.c_size_t),('peak_job_memory',ctypes.c_size_t)]

class ProcessGroup:
    def __init__(self, process_handle):
        self.handle = kernel.CreateJobObjectW(None,None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimits()
        limits.basic.flags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits)):
            error=ctypes.get_last_error(); self.close(); raise ctypes.WinError(error)
        if not kernel.AssignProcessToJobObject(self.handle,process_handle):
            error=ctypes.get_last_error(); self.close(); raise ctypes.WinError(error)

    def close(self):
        if self.handle:
            kernel.CloseHandle(self.handle)
            self.handle=None

SERVER_GROUP = None

def own_server_children():
    global SERVER_GROUP
    SERVER_GROUP = ProcessGroup(kernel.GetCurrentProcess())

def own_command_children(process):
    return ProcessGroup(int(process._handle))
