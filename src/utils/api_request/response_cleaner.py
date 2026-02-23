"""
Bereinigung von API-Antworten: Code-Block-Extraktion, Formatierung.
Wird als Post-Processing nach jedem API-Response aufgerufen.

Moved from utils/helpers.py – logically belongs to API layer.
"""

import re
import html


def clean_api_response(response):
    """
    Entfernt unerwünschte Muster aus API-Antworten und formatiert Code-Blöcke.
    
    - Extrahiert Python-Code-Blöcke und bewahrt deren Formatierung
    - Entfernt alle \\n und \\n\\n aus normalem Text
    - Entfernt "---" am Anfang nach der Filterung
    - Erstellt HTML-Frames für Code-Blöcke mit Syntax-Highlighting
    
    Args:
        response: Die ungefilterte API-Antwort
        
    Returns:
        Die bereinigte und formatierte Antwort
    """
    if not response:
        return response
    
    # Extract code blocks and replace with placeholders
    cleaned, code_blocks = _extract_code_blocks(response)
    
    
    # \n im Text belassen – das Frontend konvertiert sie zu <br>
    # cleaned = re.sub(r'\n+', ' ', cleaned)
    
    # Entferne "---" am Anfang (nach Whitespace-Bereinigung)
    cleaned = re.sub(r'^\s*---\s*', '', cleaned)
  
    # Füge Code-Blöcke als formatierte HTML-Frames wieder ein
    cleaned = _insert_code_blocks_html(cleaned, code_blocks)
   
    return cleaned.strip()


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
        # Preserve line breaks! Only remove leading/trailing empty lines
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
