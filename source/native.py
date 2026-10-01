"""Win32 hit testing and preferences for a single Qt Quick alpha window.

The material, smooth edge and shadow share one renderer and one contour.
"""
import ctypes as C
from ctypes import wintypes as W
import sys

IS_WINDOWS = sys.platform == "win32"
user = None
if IS_WINDOWS:
    user = C.WinDLL("user32", use_last_error=True)
    dwm = C.WinDLL("dwmapi", use_last_error=True)
    user.GetWindowRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
    user.GetCursorPos.argtypes = [C.POINTER(W.POINT)]
    user.GetDpiForWindow.argtypes = [W.HWND]
    user.GetDpiForWindow.restype = W.UINT
    user.SetWindowPos.argtypes = [W.HWND, W.HWND, C.c_int, C.c_int, C.c_int, C.c_int, W.UINT]
    user.GetAsyncKeyState.argtypes = [C.c_int]
    user.GetAsyncKeyState.restype = C.c_short
    user.GetCapture.restype = W.HWND
    dwm.DwmSetWindowAttribute.argtypes = [W.HWND, W.DWORD, C.c_void_p, W.DWORD]


def cursor_pixels():
    """Continuous desktop pixels; Qt global coordinates have mixed-DPI gaps."""
    if IS_WINDOWS:
        point = W.POINT()
        if user.GetCursorPos(C.byref(point)):
            return point.x, point.y
    return None


def left_button_down():
    """Hardware state, independent of a stale Qt/QML pointer grab."""
    if IS_WINDOWS:
        return bool(user.GetAsyncKeyState(0x01) & 0x8000)
    return None


def release_window_capture(hwnd):
    # Never release a capture owned by a menu, or by another application.
    if IS_WINDOWS and hwnd and user.GetCapture() == hwnd:
        user.ReleaseCapture()


def window_metrics(hwnd):
    if not IS_WINDOWS or not hwnd:
        return {}
    rect = W.RECT()
    if not user.GetWindowRect(hwnd, C.byref(rect)):
        return {}
    return {"nativeRect": [rect.left, rect.top, rect.right-rect.left, rect.bottom-rect.top],
            "nativeDpi": user.GetDpiForWindow(hwnd)}


def animations_allowed():
    if not IS_WINDOWS:
        return True
    value = W.BOOL(1)
    user.SystemParametersInfoW(0x1042, 0, C.byref(value), 0)
    return bool(value.value)


def prepare_alpha_window(hwnd):
    if not IS_WINDOWS:
        return
    # Disable Windows' rectangular system material, border and non-client
    # shadow. QML supplies the complete antialiased contour and soft shadow.
    for attribute, value in ((38, 1), (2, 1), (33, 1)):
        flag = C.c_int(value)
        dwm.DwmSetWindowAttribute(hwnd, attribute, C.byref(flag), C.sizeof(flag))
