"""Window Settings - Speichert und lädt Fensterposition/größe für PyWebView."""

import os
import json
from typing import Dict, Optional, Tuple

from utils.settings_manager import load_section, save_section, get_section_defaults

DEFAULT_SETTINGS = get_section_defaults('window')

# Minimale Fenstergröße
MIN_WIDTH = 400
MIN_HEIGHT = 300


def _get_virtual_screen_bounds() -> Tuple[int, int, int, int]:
    """Ermittelt die Grenzen des gesamten virtuellen Bildschirms (alle Monitore).
    
    Returns:
        (left, top, right, bottom) - Grenzen des virtuellen Desktops.
        Fallback auf konservative Standardwerte wenn nicht ermittelbar.
    """
    import sys
    
    if sys.platform == 'win32':
        try:
            import ctypes
            user32 = ctypes.windll.user32
            left = user32.GetSystemMetrics(76)
            top = user32.GetSystemMetrics(77)
            width = user32.GetSystemMetrics(78)
            height = user32.GetSystemMetrics(79)
            if width > 0 and height > 0:
                return (left, top, left + width, top + height)
        except Exception:
            pass
    else:
        # Linux/macOS: Try to get screen bounds via xrandr or fallback
        try:
            import subprocess
            result = subprocess.run(
                ['xrandr', '--query'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                import re
                max_right, max_bottom = 0, 0
                for match in re.finditer(r'(\d+)x(\d+)\+(\d+)\+(\d+)', result.stdout):
                    w, h, x, y = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
                    max_right = max(max_right, x + w)
                    max_bottom = max(max_bottom, y + h)
                if max_right > 0 and max_bottom > 0:
                    return (0, 0, max_right, max_bottom)
        except Exception:
            pass
    
    # Fallback: konservative Standardwerte
    return (-200, -200, 8000, 4500)


def _sanitize_position(x: Optional[int], y: Optional[int],
                        win_width: int, win_height: int) -> Tuple[Optional[int], Optional[int]]:
    """Prüft ob die Fensterposition sichtbar ist und korrigiert sie bei Bedarf.
    
    Windows setzt minimierte Fenster auf (-32000, -32000). Solche und andere
    Off-Screen-Positionen werden hier abgefangen und auf None (= zentriert) zurückgesetzt.
    
    Returns:
        (x, y) - Bereinigte Koordinaten, oder (None, None) zum Zentrieren.
    """
    if x is None or y is None:
        return (None, None)
    
    # Sofort-Check: Windows-Minimiert-Koordinaten abfangen (-32000)
    if x <= -30000 or y <= -30000:
        return (None, None)
    
    # Bildschirmgrenzen ermitteln
    left, top, right, bottom = _get_virtual_screen_bounds()
    
    # Mindestens 80px des Fensters müssen auf einem Bildschirm sichtbar sein,
    # damit man die Titelleiste noch greifen und verschieben kann.
    visible_margin = 80
    
    x_visible = x + win_width > left + visible_margin and x < right - visible_margin
    y_visible = y > top - 50 and y < bottom - visible_margin  # -50 für Titelleiste oben
    
    if not x_visible or not y_visible:
        return (None, None)
    
    return (x, y)


def _sanitize_size(width: int, height: int) -> Tuple[int, int]:
    """Stellt sicher, dass die Fenstergröße sinnvoll ist."""
    width = max(MIN_WIDTH, width) if isinstance(width, (int, float)) else DEFAULT_SETTINGS['width']
    height = max(MIN_HEIGHT, height) if isinstance(height, (int, float)) else DEFAULT_SETTINGS['height']
    return (int(width), int(height))


def load_window_settings() -> Dict:
    """Lädt gespeicherte Fenstereinstellungen mit Positionsvalidierung."""
    settings = load_section('window')
    if not settings:
        return DEFAULT_SETTINGS.copy()

    # Standardwerte für fehlende Keys
    for key, value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = value

    # Größe validieren
    settings['width'], settings['height'] = _sanitize_size(
        settings['width'], settings['height']
    )

    # Position validieren - Off-Screen-Schutz
    settings['x'], settings['y'] = _sanitize_position(
        settings.get('x'), settings.get('y'),
        settings['width'], settings['height']
    )

    return settings


def save_window_settings(width: int, height: int, x: Optional[int] = None, y: Optional[int] = None):
    """Speichert aktuelle Fenstereinstellungen mit Positionsvalidierung."""
    # Größe validieren
    width, height = _sanitize_size(width, height)
    
    # Position validieren - verhindert Speichern von Off-Screen-Koordinaten
    x, y = _sanitize_position(x, y, width, height)
    
    settings = {
        'width': width,
        'height': height,
        'x': x,
        'y': y,
    }
    
    save_section('window', settings)
