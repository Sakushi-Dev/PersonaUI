"""
Custom Specs Routes - Verwaltung von benutzerdefinierten Persona-Spezifikationen
"""
from flask import Blueprint, request
import os
import json
import re
from utils.settings_defaults import get_autofill_model
from utils.logger import log
from utils.provider import get_api_client
from utils.api_request import RequestConfig
from routes.helpers import success_response, error_response, handle_route_error
from routes.user_profile import get_user_profile_data
custom_specs_bp = Blueprint('custom_specs', __name__)

# Pfade
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUSTOM_SPEC_DIR = os.path.join(BASE_DIR, 'instructions', 'personas', 'spec', 'custom_spec')
CUSTOM_SPEC_FILE = os.path.join(CUSTOM_SPEC_DIR, 'custom_spec.json')

# Standard-Modell für Auto-Fill (kostengünstig)
AUTOFILL_MODEL = get_autofill_model()


def _ensure_custom_spec_dir():
    """Stellt sicher, dass das custom_spec Verzeichnis existiert"""
    os.makedirs(CUSTOM_SPEC_DIR, exist_ok=True)


def _load_custom_spec():
    """Lädt die custom_spec.json"""
    _ensure_custom_spec_dir()
    try:
        if os.path.exists(CUSTOM_SPEC_FILE):
            with open(CUSTOM_SPEC_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "persona_spec": {
                "persona_type": {},
                "core_traits_details": {},
                "knowledge_areas": {},
                "expression_styles": {},
                "scenarios": {}
            }
        }
    except Exception as e:
        log.error("Fehler beim Laden der Custom Spec: %s", e)
        return {
            "persona_spec": {
                "persona_type": {},
                "core_traits_details": {},
                "knowledge_areas": {},
                "expression_styles": {},
                "scenarios": {}
            }
        }


def _save_custom_spec(data):
    """Speichert die custom_spec.json"""
    _ensure_custom_spec_dir()
    try:
        with open(CUSTOM_SPEC_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log.error("Fehler beim Speichern der Custom Spec: %s", e)
        return False


# ===== API Endpoints =====

@custom_specs_bp.route('/api/custom-specs', methods=['GET'])
@handle_route_error('get_custom_specs')
def get_custom_specs():
    """Gibt alle Custom Specs zurück"""
    specs = _load_custom_spec()
    return success_response(specs=specs)


@custom_specs_bp.route('/api/custom-specs/persona-type', methods=['POST'])
@handle_route_error('add_persona_type')
def add_persona_type():
    """Fügt einen neuen Persona-Typ hinzu"""
    data = request.get_json()
    key = data.get('key', '').strip()
    description = data.get('description', '').strip()
    
    if not key:
        return error_response('Name ist erforderlich')
    if len(description) > 120:
        return error_response('Beschreibung darf maximal 120 Zeichen lang sein')
    
    specs = _load_custom_spec()
    specs['persona_spec']['persona_type'][key] = description
    
    if _save_custom_spec(specs):
        return success_response()
    return error_response('Speichern fehlgeschlagen', 500)


@custom_specs_bp.route('/api/custom-specs/core-trait', methods=['POST'])
@handle_route_error('add_core_trait')
def add_core_trait():
    """Fügt ein neues Core Trait hinzu"""
    data = request.get_json()
    key = data.get('key', '').strip()
    description = data.get('description', '').strip()
    behaviors = data.get('behaviors', [])
    
    if not key:
        return error_response('Name ist erforderlich')
    if not behaviors or len(behaviors) > 6:
        return error_response('1-6 Verhaltensmuster erforderlich')
    
    specs = _load_custom_spec()
    specs['persona_spec']['core_traits_details'][key] = {
        "description": description,
        "behaviors": behaviors
    }
    
    if _save_custom_spec(specs):
        return success_response()
    return error_response('Speichern fehlgeschlagen', 500)


@custom_specs_bp.route('/api/custom-specs/knowledge', methods=['POST'])
@handle_route_error('add_knowledge')
def add_knowledge():
    """Fügt ein neues Wissensgebiet hinzu"""
    data = request.get_json()
    key = data.get('key', '').strip()
    description = data.get('description', '').strip()
    
    if not key:
        return error_response('Name ist erforderlich')
    
    specs = _load_custom_spec()
    specs['persona_spec']['knowledge_areas'][key] = description
    
    if _save_custom_spec(specs):
        return success_response()
    return error_response('Speichern fehlgeschlagen', 500)


@custom_specs_bp.route('/api/custom-specs/scenario', methods=['POST'])
@handle_route_error('add_scenario')
def add_scenario():
    """Fügt ein neues Szenario hinzu"""
    data = request.get_json()
    key = data.get('key', '').strip()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    setting = data.get('setting', [])
    
    if not key:
        return error_response('Key ist erforderlich')
    if not setting or len(setting) > 6:
        return error_response('1-6 Setting-Elemente erforderlich')
    
    specs = _load_custom_spec()
    specs['persona_spec']['scenarios'][key] = {
        "name": name or key,
        "description": description,
        "setting": setting
    }
    
    if _save_custom_spec(specs):
        return success_response()
    return error_response('Speichern fehlgeschlagen', 500)


@custom_specs_bp.route('/api/custom-specs/expression-style', methods=['POST'])
@handle_route_error('add_expression_style')
def add_expression_style():
    """Fügt einen neuen Schreibstil hinzu"""
    data = request.get_json()
    key = data.get('key', '').strip()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    example = data.get('example', '').strip()
    characteristics = data.get('characteristics', [])
    
    if not key:
        return error_response('Key ist erforderlich')
    
    specs = _load_custom_spec()
    specs['persona_spec']['expression_styles'][key] = {
        "name": name or key,
        "description": description,
        "example": example,
        "characteristics": characteristics
    }
    
    if _save_custom_spec(specs):
        return success_response()
    return error_response('Speichern fehlgeschlagen', 500)


@custom_specs_bp.route('/api/custom-specs/<category>/<key>', methods=['DELETE'])
@handle_route_error('delete_custom_spec')
def delete_custom_spec(category, key):
    """Löscht einen Custom Spec Eintrag"""
    category_map = {
        'persona-type': 'persona_type',
        'core-trait': 'core_traits_details',
        'knowledge': 'knowledge_areas',
        'scenario': 'scenarios',
        'expression-style': 'expression_styles'
    }
    
    spec_key = category_map.get(category)
    if not spec_key:
        return error_response('Ungültige Kategorie')
    
    specs = _load_custom_spec()
    if key in specs['persona_spec'].get(spec_key, {}):
        del specs['persona_spec'][spec_key][key]
        if _save_custom_spec(specs):
            return success_response()
        return error_response('Speichern fehlgeschlagen', 500)
    
    return error_response('Eintrag nicht gefunden', 404)


@custom_specs_bp.route('/api/custom-specs/autofill', methods=['POST'])
@handle_route_error('autofill_spec')
def autofill_spec():
    """KI-gestützte Auto-Generierung einzelner Spec-Felder (Plaintext, kein JSON).

    Request-Body:
        type:   z.B. 'core_trait', 'expression_style', ...
        field:  'description' | 'example' | 'items'
        input:  Name des Specs (Pflicht)
        hint:   Optionaler Freitext-Hinweis des Users
        item_count: Anzahl der gewünschten Items (nur für field=items)
    
    Response:
        { success: true, text: "...", tokens: {...} }
    """
    data = request.get_json()
    spec_type = data.get('type', '').strip()
    field = data.get('field', 'description').strip()
    input_text = data.get('input', '').strip()
    hint = data.get('hint', '').strip()
    item_count = data.get('item_count', 3)

    if not spec_type or not input_text:
        return error_response('Typ und Input sind erforderlich')
    
    if field not in ('description', 'example', 'items'):
        return error_response('Ungültiges Feld')

    # ── Sprache aus User-Profil ──
    profile = get_user_profile_data()
    language = profile.get('persona_language', 'english') or 'english'

    # ── Prompt bauen ──
    prompt = _build_field_prompt(spec_type, field, input_text, hint, item_count, language)
    if not prompt:
        return error_response(f'Prompt konnte nicht gebaut werden für "{spec_type}/{field}"', 400)

    # ── API-Call ──
    try:
        config = RequestConfig(
            system_prompt='',
            model=AUTOFILL_MODEL,
            max_tokens=300,
            messages=[{'role': 'user', 'content': prompt}],
            request_type='spec_autofill'
        )
        response = get_api_client().request(config)

        if not response.success:
            return error_response(f'API-Fehler: {response.error}', 500)

        result_text = response.content.strip()
        # Bereinige: Anführungszeichen am Anfang/Ende entfernen
        if result_text.startswith('"') and result_text.endswith('"'):
            result_text = result_text[1:-1]

        tokens = {
            'input': response.usage.get('input_tokens', 0) if response.usage else 0,
            'output': response.usage.get('output_tokens', 0) if response.usage else 0
        }

        # Für Items: in Liste aufteilen (Line-by-line)
        if field == 'items':
            lines = _parse_items_response(result_text, item_count)
            return success_response(items=lines, tokens=tokens)

        return success_response(text=result_text, tokens=tokens)

    except Exception as api_error:
        log.error("Claude API Fehler bei Auto-Fill: %s", api_error)
        return error_response(f'API-Fehler: {str(api_error)}', 500)


# ── Prompt-Builder für Einzelfeld-Autofill ──

# Feldnamen pro Kategorie (für besseren Kontext im Prompt)
_FIELD_LABELS = {
    'persona_type': {'description': 'a persona type'},
    'core_trait': {'description': 'a personality trait', 'items': 'behavioral patterns for this trait'},
    'knowledge': {'description': 'a field of knowledge'},
    'scenario': {'description': 'a roleplay scenario', 'items': 'setting elements for this scenario'},
    'expression_style': {'description': 'a writing/communication style', 'example': 'a writing style', 'items': 'characteristics of this style'},
}

def _build_field_prompt(spec_type: str, field: str, name: str, hint: str, item_count: int, language: str = 'english') -> str:
    """Baut einen Plaintext-Prompt für ein einzelnes Feld."""

    labels = _FIELD_LABELS.get(spec_type, {})
    context_label = labels.get(field, labels.get('description', 'a spec'))
    hint_section = f'\nThe user adds this hint: "{hint}"' if hint else ''
    lang_rule = f'- Respond in {language}'

    if field == 'description':
        return (
            f'Generate a brief description for {context_label}.\n'
            f'Name: "{name}"{hint_section}\n\n'
            f'Rules:\n'
            f'{lang_rule}\n'
            f'- Maximum 120 characters\n'
            f'- One or two sentences\n'
            f'- Be creative but clear\n'
            f'- Return ONLY the description text, nothing else'
        )

    elif field == 'example':
        return (
            f'Generate a short example sentence that demonstrates {context_label}.\n'
            f'Style name: "{name}"{hint_section}\n\n'
            f'Rules:\n'
            f'{lang_rule}\n'
            f'- A short greeting or statement in this style\n'
            f'- Maximum 150 characters\n'
            f'- Return ONLY the example text, nothing else'
        )

    elif field == 'items':
        item_label = labels.get('items', 'items')
        count = min(max(item_count, 1), 6)
        return (
            f'Generate exactly {count} {item_label}.\n'
            f'Name: "{name}"{hint_section}\n\n'
            f'Rules:\n'
            f'{lang_rule}\n'
            f'- Each item on its own line\n'
            f'- Each item: maximum 60 characters, short and concise\n'
            f'- No numbering, no bullet points, no dashes — just the text\n'
            f'- No extra explanations\n'
            f'- Return exactly {count} lines'
        )

    return ''


def _parse_items_response(text: str, expected_count: int) -> list:
    """Parst eine mehrzeilige AI-Antwort in eine Liste von Items."""
    lines = []
    for line in text.split('\n'):
        cleaned = line.strip()
        if not cleaned:
            continue
        # Nummerierung/Aufzählungszeichen entfernen
        cleaned = re.sub(r'^[\d]+[.):\-]\s*', '', cleaned)
        cleaned = re.sub(r'^[-•*]\s*', '', cleaned)
        cleaned = cleaned.strip(' "\'')
        if cleaned:
            lines.append(cleaned)
    # Auf erwartete Anzahl begrenzen
    return lines[:expected_count]
