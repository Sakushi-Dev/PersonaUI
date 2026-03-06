"""Helper functions to hide/show the console window (cross-platform)."""

import sys


def hide_console_window():
    """Versteckt das Konsolenfenster (nur unter Windows relevant)."""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
    except Exception:
        pass


def show_console_window():
    """Zeigt das Konsolenfenster wieder an (nur unter Windows relevant)."""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW = 5
    except Exception:
        pass
