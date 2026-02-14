"""
Helper-Funktionen für die Chat-Anwendung
"""
import os
import secrets
import re
import html
from .logger import log


def ensure_env_file():
    """Stellt sicher, dass eine .env Datei existiert"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    
    if not os.path.exists(env_path):
        # Erstelle .env Datei mit leerem API-Key aber gültigem SECRET_KEY
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write('# Umgebungsvariablen - Automatisch generiert\n')
            f.write('ANTHROPIC_API_KEY=\n')  # Leer - muss vom Benutzer gesetzt werden
            f.write(f'SECRET_KEY={secrets.token_hex(32)}\n')

        log.info(".env Datei wurde erstellt. Bitte API-Key in den Einstellungen konfigurieren.")


def format_message(message):
    """
    Formatiert eine Nachricht - markiert nonverbalen Text zwischen Sternchen
    und verarbeitet Code-Blöcke (für bereits gespeicherte Nachrichten aus der DB)
    
    Diese Funktion verwendet die gleiche Logik wie clean_api_response,
    damit bereits gespeicherte Nachrichten beim Neuladen gleich aussehen.
    """
    if not message:
        return message
    
    # Prüfe ob die Nachricht bereits HTML-Code-Blöcke enthält (schon verarbeitet)
    if '<div class="code-block">' in message:
        # Bereits verarbeitet, nur non-verbalen Text formatieren
        formatted = re.sub(r'\*(.*?)\*', r'<span class="non_verbal">\1</span>', message)
        return formatted
    
    # Extrahiere Code-Blöcke und ersetze mit Platzhaltern
    formatted, code_blocks = _extract_code_blocks(message)
    
    # Formatiere nonverbalen Text (zwischen Sternchen)
    formatted = re.sub(r'\*(.*?)\*', r'<span class="non_verbal">\1</span>', formatted)
    
    # Ersetze Zeilenumbrüche durch <br> Tags
    if code_blocks:
        # Mit Code-Blöcken: Entferne nur übermäßige \n, kein <br> Ersatz
        formatted = formatted.strip()
    else:
        # Keine Code-Blöcke: Standard-Formatierung mit <br>
        formatted = formatted.replace('\n', '<br>')
    
    # Füge Code-Blöcke als formatierte HTML-Frames wieder ein
    formatted = _insert_code_blocks_html(formatted, code_blocks)
    
    return formatted


# ===== Interne Hilfsfunktionen für Code-Block-Verarbeitung =====

def _extract_code_blocks(text: str) -> tuple:
    """
    Extrahiert Code-Blöcke (``` ... ```) aus Text und ersetzt sie mit Platzhaltern.
    
    Args:
        text: Der Eingabetext mit möglichen Code-Blöcken
        
    Returns:
        Tuple aus (Text mit Platzhaltern, Liste der Code-Block-Inhalte)
    """
    code_blocks = []
    placeholder_pattern = "###CODE_BLOCK_{}###"
    
    def _replace_match(match):
        code_content = match.group(1)
        index = len(code_blocks)
        # Bewahre die Zeilenumbrüche! Nur führende/nachfolgende Leerzeilen entfernen
        code_content = code_content.strip('\n')
        code_blocks.append(code_content)
        return placeholder_pattern.format(index)
    
    result = re.sub(r'```(?:python)?\s*(.*?)```', _replace_match, text, flags=re.DOTALL)
    return result, code_blocks


def _insert_code_blocks_html(text: str, code_blocks: list) -> str:
    """
    Ersetzt Code-Block-Platzhalter durch formatierte HTML-Frames.
    
    Args:
        text: Text mit ###CODE_BLOCK_N### Platzhaltern
        code_blocks: Liste der Code-Block-Inhalte
        
    Returns:
        Text mit HTML-formatierten Code-Blöcken
    """
    placeholder_pattern = "###CODE_BLOCK_{}###"
    for index, code_content in enumerate(code_blocks):
        placeholder = placeholder_pattern.format(index)
        # Escape HTML um XSS zu verhindern und Code korrekt anzuzeigen
        escaped_code = html.escape(code_content)
        code_html = f'<div class="code-block"><pre><code class="language-python">{escaped_code}</code></pre></div>'
        text = text.replace(placeholder, code_html)
    return text
