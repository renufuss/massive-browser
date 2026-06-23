"""Best-effort OS window control, matched by the unique window title we set.

Playwright has no API to minimise/raise the OS window, so this drops to the
native layer. Each browser's window title contains its instance name
(``document.title = instance.name``), which is unique per run, so we match on it.

ponytail: Windows-only via stdlib ctypes (the target platform); no-op elsewhere.
        Matches by title -- a site that rewrites its <title> faster than the
        caller re-asserts it can dodge the match. Upgrade path: pygetwindow/
        wmctrl, or CDP `Browser.setWindowBounds` for the Chromium share.
"""

from __future__ import annotations

import os
import sys

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32
    _HWND = wintypes.HWND
    _OWN_PID = os.getpid()

    _SW_MINIMIZE = 6
    _SW_RESTORE = 9
    _HWND_TOPMOST = _HWND(-1)
    _HWND_NOTOPMOST = _HWND(-2)
    _SWP = 0x0001 | 0x0002 | 0x0040  # NOSIZE | NOMOVE | SHOWWINDOW

    # Pin handle-taking signatures so 64-bit HWNDs aren't truncated to 32-bit.
    _user32.IsWindowVisible.argtypes = [_HWND]
    _user32.GetWindowTextLengthW.argtypes = [_HWND]
    _user32.GetWindowTextW.argtypes = [_HWND, wintypes.LPWSTR, ctypes.c_int]
    _user32.ShowWindow.argtypes = [_HWND, ctypes.c_int]
    _user32.SetWindowPos.argtypes = [
        _HWND, _HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint
    ]
    _user32.SetForegroundWindow.argtypes = [_HWND]
    _user32.BringWindowToTop.argtypes = [_HWND]
    _user32.GetForegroundWindow.restype = _HWND
    _user32.GetWindowThreadProcessId.argtypes = [_HWND, wintypes.LPDWORD]
    _user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    _user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]

    _EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, _HWND, wintypes.LPARAM)

    def _find(title_fragment: str) -> int | None:
        found: dict[str, int] = {}

        def _cb(hwnd, _lparam):
            if _user32.IsWindowVisible(hwnd):
                # Skip our own windows (e.g. the preview dialog "Name - preview"),
                # whose title also contains the instance name -- only real browser
                # windows live in a different process.
                pid = wintypes.DWORD(0)
                _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value != _OWN_PID:
                    length = _user32.GetWindowTextLengthW(hwnd)
                    if length:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        _user32.GetWindowTextW(hwnd, buf, length + 1)
                        if title_fragment in buf.value:
                            found["hwnd"] = hwnd
                            return False  # stop enumerating
            return True

        _user32.EnumWindows(_EnumProc(_cb), 0)
        return found.get("hwnd")

    def _raise_window(hwnd: int) -> None:
        _user32.ShowWindow(hwnd, _SW_RESTORE)
        # Topmost toggle lifts the window to the top of the Z-order even from a
        # background process, where SetForegroundWindow alone just flashes the
        # taskbar (Windows foreground lock).
        _user32.SetWindowPos(hwnd, _HWND_TOPMOST, 0, 0, 0, 0, _SWP)
        _user32.SetWindowPos(hwnd, _HWND_NOTOPMOST, 0, 0, 0, 0, _SWP)
        # Best-effort focus: borrow the current foreground thread's input queue so
        # the focus hand-off is permitted.
        fg = _user32.GetForegroundWindow()
        cur = _kernel32.GetCurrentThreadId()
        fg_thread = _user32.GetWindowThreadProcessId(fg, None) if fg else 0
        if fg_thread and fg_thread != cur:
            _user32.AttachThreadInput(cur, fg_thread, True)
            _user32.SetForegroundWindow(hwnd)
            _user32.BringWindowToTop(hwnd)
            _user32.AttachThreadInput(cur, fg_thread, False)
        else:
            _user32.SetForegroundWindow(hwnd)

    def restore(title_fragment: str) -> bool:
        """Un-minimise the matching window and raise it to the front."""
        hwnd = _find(title_fragment)
        if hwnd is None:
            return False
        _raise_window(hwnd)
        return True

    def minimize(title_fragment: str) -> bool:
        """Minimise the matching window."""
        hwnd = _find(title_fragment)
        if hwnd is None:
            return False
        _user32.ShowWindow(hwnd, _SW_MINIMIZE)
        return True

else:  # ponytail: no-op off Windows until a cross-platform backend is needed

    def restore(title_fragment: str) -> bool:
        return False

    def minimize(title_fragment: str) -> bool:
        return False


if __name__ == "__main__":
    # ponytail: smoke check -- a title that cannot exist returns False, no raise.
    assert minimize("∅ no such window ∅") is False
    assert restore("∅ no such window ∅") is False
    print("window_control self-check OK")
