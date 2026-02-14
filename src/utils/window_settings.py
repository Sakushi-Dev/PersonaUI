"""Window Settings - Speichert und lädt Fensterposition/größe für PyWebView."""

import os
import json
from typing import Dict, Optional, Tuple


SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'settings',
    'window_settings.json'
)

DEFAULT_SETTINGS = {
    'width': 1280,
    'height': 860,
    'x': None,  # None = zentriert
    'y': None,
}

# Minimale Fenstergröße
MIN_WIDTH = 400
MIN_HEIGHT = 300


def _get_virtual_screen_bounds() -> Tuple[int, int, int, int]:
    """Ermittelt die Grenzen des gesamten virtuellen Bildschirms (alle Monitore).
    
    Returns:
        (left, top, right, bottom) - Grenzen des virtuellen Desktops.
        Fallback auf konservative Standardwerte wenn nicht ermittelbar.
    """
    try:
        import ctypes
        # SM_XVIRTUALSCREEN (76) = linke Kante aller Monitore
        # SM_YVIRTUALSCREEN (77) = obere Kante aller Monitore
        # SM_CXVIRTUALSCREEN (78) = Gesamtbreite aller Monitore
        # SM_CYVIRTUALSCREEN (79) = Gesamthöhe aller Monitore
        user32 = ctypes.windll.user32
        left = user32.GetSystemMetrics(76)
        top = user32.GetSystemMetrics(77)
        width = user32.GetSystemMetrics(78)
        height = user32.GetSystemMetrics(79)
        if width > 0 and height > 0:
            return (left, top, left + width, top + height)
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
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS.copy()
    
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
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
    except Exception:
        return DEFAULT_SETTINGS.copy()


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
    
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
    except Exception as e:
        pass  # Fehler beim Speichern ignorieren
