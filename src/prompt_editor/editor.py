"""Prompt Editor – PyWebView App-Start.

Startet den Prompt-Editor als eigenständiges PyWebView-Fenster.
Der Editor arbeitet direkt mit den JSON-Dateien über die PromptEngine.

Usage:
    python -m prompt_editor.editor
"""

import os
import sys

# Add src/ directory to Python path
_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# Change to src/ directory (for relative paths of PromptEngine)
os.chdir(_SRC_DIR)


def start_editor():
    """Startet den Prompt-Editor als eigenständiges Fenster."""
    import webview
    from prompt_editor import load_editor_html
    from prompt_editor.api import EditorApi

    api = EditorApi()
    html = load_editor_html()

    window = webview.create_window(
        title='PersonaUI \u2013 Prompt Editor',
        html=html,
        js_api=api,
        width=1300,
        height=850,
        resizable=True,
        min_size=(900, 600),
        text_select=True,
    )

    webview.start(debug=False)


if __name__ == '__main__':
    start_editor()
