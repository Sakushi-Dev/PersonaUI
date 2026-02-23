"""splash_screen – Splash screen package for PersonaUI.

Provides:
  - load_splash_html()        → Returns the complete HTML string
  - hide_console_window()     → Hide the Windows console
  - show_console_window()     → Show the Windows console
  - startup_sequence(...)     → Complete startup logic in splash
"""

import os

# Re-exports from utils
from .utils import (
    hide_console_window,
    show_console_window,
    startup_sequence,
)

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_splash_html() -> str:
    """Read splash.html, splash.css, and splash.js and return the complete HTML string."""
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
