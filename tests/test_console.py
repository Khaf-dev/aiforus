import sys
import types

from aiforus.hal import console


class FakeKernel32:
    def __init__(self, mode=0x01F7, console=True):
        self.mode = mode
        self.console = console
        self.history = []

    def GetStdHandle(self, which):  # noqa: N802 - Win32 API
        assert which == -10
        return 42

    def GetConsoleMode(self, handle, ref):  # noqa: N802 - Win32 API
        if not self.console:
            return 0
        ref._obj.value = self.mode
        return 1

    def SetConsoleMode(self, handle, mode):  # noqa: N802 - Win32 API
        self.mode = mode
        self.history.append(mode)
        return 1


class _UInt:
    def __init__(self):
        self.value = 0


class _Ref:
    def __init__(self, obj):
        self._obj = obj


def fake_ctypes(kernel32):
    module = types.ModuleType("ctypes")
    module.windll = types.SimpleNamespace(kernel32=kernel32)
    module.c_uint32 = _UInt
    module.byref = _Ref
    return module


def test_quick_edit_is_disabled_and_restored(monkeypatch):
    kernel32 = FakeKernel32(mode=0x01F7)  # QuickEdit (0x40) on
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "ctypes", fake_ctypes(kernel32))
    with console.quick_edit_disabled():
        assert kernel32.mode & 0x0040 == 0
        assert kernel32.mode & 0x0080
    assert kernel32.mode == 0x01F7


def test_not_a_console_is_left_alone(monkeypatch):
    kernel32 = FakeKernel32(console=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "ctypes", fake_ctypes(kernel32))
    with console.quick_edit_disabled():
        pass
    assert kernel32.history == []


def test_noop_on_other_platforms(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    with console.quick_edit_disabled():
        pass
