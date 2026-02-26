"""reset_screen – Reset screen package for PersonaUI.

Provides:
  - load_reset_html()        → Returns the complete HTML string
  - reset_sequence(...)      → Reset logic with selectable options and GUI output
  - collect_personas()       → Collects all available personas
  - PRESETS / PRESET_ORDER   → Reset preset definitions
"""

import os

from .utils import reset_sequence as reset_sequence
from .utils.reset import collect_personas as collect_personas, PRESETS as PRESETS, PRESET_ORDER as PRESET_ORDER

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_reset_html() -> str:
    """Reads reset.html, reset.css and reset.js and returns complete HTML string."""
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
