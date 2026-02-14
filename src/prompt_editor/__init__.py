"""prompt_editor – Eigenständiger Prompt-Editor für PersonaUI.

Separater PyWebView-Prozess zum komfortablen Bearbeiten von Prompts.
Arbeitet direkt mit den JSON-Dateien über die PromptEngine.

Start:
    python -m prompt_editor.editor
    oder
    bin/start_prompt_editor.bat
"""

import os

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_editor_html() -> str:
    """Liest editor.html und inline't CSS + alle JS-Dateien.

    Gleiche Technik wie splash_screen: Alles wird in einen
    einzigen HTML-String eingebettet, damit pywebview keine
    externen Ressourcen laden muss (kein file://-Problem).
    """
    template_path = os.path.join(_PACKAGE_DIR, 'templates', 'editor.html')
    css_path = os.path.join(_PACKAGE_DIR, 'static', 'css', 'editor.css')
    js_dir = os.path.join(_PACKAGE_DIR, 'static', 'js')

    # JS-Dateien in korrekter Reihenfolge (Abhängigkeiten beachten)
    js_files = [
        'utils.js',
        'prompt-list.js',
        'prompt-editor.js',
        'highlight.js',
        'placeholder-manager.js',
        'autocomplete.js',
        'preview.js',
        'compositor.js',
        'app.js',
    ]

    # Template laden
    with open(template_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # CSS einbetten
    with open(css_path, 'r', encoding='utf-8') as f:
        css = f.read()
    html = html.replace('{{EDITOR_CSS}}', css)

    # JS-Dateien zusammenführen und einbetten
    js_parts = []
    for js_file in js_files:
        js_path = os.path.join(js_dir, js_file)
        with open(js_path, 'r', encoding='utf-8') as f:
            js_parts.append(f'// ===== {js_file} =====\n{f.read()}')

    html = html.replace('{{EDITOR_JS}}', '\n\n'.join(js_parts))
    return html
