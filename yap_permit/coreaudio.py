"""CoreAudio ctypes lookup of the default output device name (macOS only).

Fallback for when system_profiler is unavailable. Ported from the
airpods-say skill.
"""

import ctypes
import ctypes.util

_SYSTEM_OBJECT = 1
_DEFAULT_OUTPUT = 0x644F7574   # 'dOut'
_SCOPE_GLOBAL = 0x676C6F62     # 'glob'
_ELEMENT_MAIN = 0
_PROPERTY_NAME = 0x6C6E616D    # 'lnam'
_UTF8 = 0x08000100


class _Address(ctypes.Structure):
    _fields_ = [("mSelector", ctypes.c_uint32),
                ("mScope", ctypes.c_uint32),
                ("mElement", ctypes.c_uint32)]


def _load(name: str) -> ctypes.CDLL:
    path = ctypes.util.find_library(name)
    if not path:
        raise OSError(f"{name} not found")
    return ctypes.cdll.LoadLibrary(path)


def _get_property(ca, obj, selector, out) -> None:
    addr = _Address(selector, _SCOPE_GLOBAL, _ELEMENT_MAIN)
    size = ctypes.c_uint32(ctypes.sizeof(out))
    err = ca.AudioObjectGetPropertyData(
        obj, ctypes.byref(addr), 0, None, ctypes.byref(size),
        ctypes.byref(out))
    if err != 0:
        raise OSError(f"CoreAudio error {err:#010x}")


def _cfstring_to_str(cf, ref) -> str:
    cf.CFStringGetLength.restype = ctypes.c_long
    cf.CFStringGetLength.argtypes = [ctypes.c_void_p]
    cf.CFStringGetMaximumSizeForEncoding.restype = ctypes.c_long
    cf.CFStringGetMaximumSizeForEncoding.argtypes = [
        ctypes.c_long, ctypes.c_uint32]
    cf.CFStringGetCString.restype = ctypes.c_bool
    cf.CFStringGetCString.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
    length = cf.CFStringGetLength(ref)
    size = cf.CFStringGetMaximumSizeForEncoding(length, _UTF8) + 1
    buf = ctypes.create_string_buffer(size)
    if not cf.CFStringGetCString(ref, buf, size, _UTF8):
        raise OSError("CFStringGetCString failed")
    return buf.value.decode("utf-8")


def default_output_name() -> str:
    """Return the default output device name. Raises OSError on failure."""
    ca = _load("CoreAudio")
    cf = _load("CoreFoundation")
    ca.AudioObjectGetPropertyData.restype = ctypes.c_int32
    ca.AudioObjectGetPropertyData.argtypes = [
        ctypes.c_uint32, ctypes.POINTER(_Address), ctypes.c_uint32,
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p]
    cf.CFRelease.restype = None
    cf.CFRelease.argtypes = [ctypes.c_void_p]

    device = ctypes.c_uint32(0)
    _get_property(ca, _SYSTEM_OBJECT, _DEFAULT_OUTPUT, device)
    ref = ctypes.c_void_p(0)
    _get_property(ca, device, _PROPERTY_NAME, ref)
    if not ref.value:
        raise OSError("device name is NULL")
    try:
        return _cfstring_to_str(cf, ref)
    finally:
        cf.CFRelease(ref)
