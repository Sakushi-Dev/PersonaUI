"""splash_screen – Splash-Screen-Paket für PersonaUI.

Stellt bereit:
  - load_splash_html()        → Gibt den fertigen HTML-String zurück
  - hide_console_window()     → Windows-Konsole verstecken
  - show_console_window()     → Windows-Konsole anzeigen
  - startup_sequence(...)     → Komplette Startup-Logik im Splash
"""

import os

# Re-Exports aus utils
from .utils import (
    hide_console_window,
    show_console_window,
    startup_sequence,
)

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_splash_html() -> str:
    """Liest splash.html, splash.css und splash.js und gibt fertigen HTML-String zurück."""
    template_path = os.path.join(_PACKAGE_DIR, 'templates', 'splash.html')
    css_path = os.path.join(_PACKAGE_DIR, 'static', 'splash.css')
    js_path = os.path.join(_PACKAGE_DIR, 'static', 'splash.js')

    with open(template_path, 'r', encoding='utf-8') as f:
        html = f.read()
    with open(css_path, 'r', encoding='utf-8') as f:
        css = f.read()
    with open(js_path, 'r', encoding='utf-8') as f:
        js = f.read()

    html = html.replace('{{SPLASH_CSS}}', css)
    html = html.replace('{{SPLASH_JS}}', js)
    return html
