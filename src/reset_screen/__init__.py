"""reset_screen – Reset-Screen-Paket für PersonaUI.

Stellt bereit:
  - load_reset_html()        → Gibt den fertigen HTML-String zurück
  - reset_sequence(...)      → Komplette Reset-Logik mit GUI-Ausgabe
"""

import os

from .utils import reset_sequence

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_reset_html() -> str:
    """Liest reset.html, reset.css und reset.js und gibt fertigen HTML-String zurück."""
    template_path = os.path.join(_PACKAGE_DIR, 'templates', 'reset.html')
    css_path = os.path.join(_PACKAGE_DIR, 'static', 'reset.css')
    js_path = os.path.join(_PACKAGE_DIR, 'static', 'reset.js')

    with open(template_path, 'r', encoding='utf-8') as f:
        html = f.read()
    with open(css_path, 'r', encoding='utf-8') as f:
        css = f.read()
    with open(js_path, 'r', encoding='utf-8') as f:
        js = f.read()

    html = html.replace('{{RESET_CSS}}', css)
    html = html.replace('{{RESET_JS}}', js)
    return html
