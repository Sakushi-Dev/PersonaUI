"""
Character Routes - Charaktereinstellungen verwalten
"""
from flask import Blueprint, request

from utils.logger import log
from utils.config import (
    load_character,
    load_char_profile, load_char_config, save_char_config, get_available_char_options,
    list_created_personas, save_created_persona, delete_created_persona, update_created_persona,
    load_persona_by_id, activate_persona, restore_default_persona,
    get_active_persona_id, set_active_persona_id
)
from utils.settings_defaults import get_autofill_model
from utils.provider import get_api_client
from utils.api_request import RequestConfig
from routes.helpers import success_response, error_response, handle_route_error

character_bp = Blueprint('character', __name__)


# ===== Persona Config System =====

@character_bp.route('/get_char_config', methods=['GET'])
@handle_route_error('get_char_config')
def get_char_config():
    """Gibt die aktuelle Charakterkonfiguration zurück"""
    config = load_char_config()
    return success_response(config=config)


@character_bp.route('/get_available_options', methods=['GET'])
@handle_route_error('get_available_options')
def get_available_options():
    """Gibt alle verfügbaren Optionen aus dem Persona-Profil zurück"""
    options = get_available_char_options()
    profile = load_char_profile()
    
    # Hole auch die vollen Details für Vorschau
    persona_profile = profile.get('persona_spec', {})
    persona_types_full = persona_profile.get('persona_type', {})
    core_traits_full = persona_profile.get('core_traits_details', {})
    knowledge_full = persona_profile.get('knowledge_areas', {})
    expression_full = persona_profile.get('expression_styles', {})
    scenarios_full = persona_profile.get('scenarios', {})
    
    # Lade Custom Spec Keys für Highlighting
    custom_keys = {}
    try:
        import os, json
        custom_spec_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                        'instructions', 'personas', 'spec', 'custom_spec', 'custom_spec.json')
        if os.path.exists(custom_spec_path):
            with open(custom_spec_path, 'r', encoding='utf-8') as f:
                custom_data = json.load(f)
            cs = custom_data.get('persona_spec', {})
            custom_keys = {
                'persona_types': list(cs.get('persona_type', {}).keys()),
                'core_traits': list(cs.get('core_traits_details', {}).keys()),
                'knowledge': list(cs.get('knowledge_areas', {}).keys()),
                'expression_styles': list(cs.get('expression_styles', {}).keys()),
                'scenarios': list(cs.get('scenarios', {}).keys())
            }
    except Exception as e:
        log.warning("Custom Keys konnten nicht geladen werden: %s", e)
    
    return success_response(
        options=options,
        details={
            'persona_types': persona_types_full,
            'core_traits': core_traits_full,
            'knowledge': knowledge_full,
            'expression_styles': expression_full,
            'scenarios': scenarios_full
        },
        custom_keys=custom_keys
    )


@character_bp.route('/save_char_config', methods=['POST'])
@handle_route_error('save_char_config')
def save_char_config_route():
    """Speichert die Persona-Konfiguration (name, age, gender, persona, core_traits, knowledge, expression)"""
    data = request.get_json()
    
    # Validiere dass die erforderlichen Felder vorhanden sind
    if not all(k in data for k in ['name', 'age', 'gender', 'persona', 'core_traits', 'knowledge', 'expression']):
        return error_response('Fehlende erforderliche Felder')
    
    success = save_char_config(data)
    
    if success:
        return success_response()
    else:
        return error_response('Fehler beim Speichern', 500)


# ===== Created Personas CRUD =====

@character_bp.route('/api/personas', methods=['GET'])
@handle_route_error('get_personas')
def get_personas():
    """Listet alle erstellten Personas + Standard"""
    personas = list_created_personas()
    return success_response(personas=personas)


@character_bp.route('/api/personas', methods=['POST'])
@handle_route_error('create_persona')
def create_persona():
    """Erstellt eine neue Persona und speichert sie"""
    data = request.get_json()
    
    if not all(k in data for k in ['name', 'age', 'gender', 'persona', 'core_traits', 'knowledge', 'expression']):
        return error_response('Fehlende erforderliche Felder')
    
    persona_id = save_created_persona(data)
    
    if persona_id:
        return success_response(id=persona_id)
    else:
        return error_response('Fehler beim Speichern der Persona', 500)


@character_bp.route('/api/personas/<persona_id>', methods=['DELETE'])
@handle_route_error('remove_persona')
def remove_persona(persona_id):
    """Löscht eine erstellte Persona"""
    if persona_id == 'default':
        return error_response('Standard-Persona kann nicht gelöscht werden')
    
    success = delete_created_persona(persona_id)
    
    if success:
        return success_response()
    else:
        return error_response('Persona nicht gefunden', 404)


@character_bp.route('/api/personas/<persona_id>', methods=['PUT'])
@handle_route_error('update_persona')
def update_persona(persona_id):
    """Aktualisiert eine bestehende Persona (Name bleibt unveränderlich)"""
    if persona_id == 'default':
        return error_response('Standard-Persona kann nicht bearbeitet werden')
    
    data = request.get_json()
    if not data:
        return error_response('Keine Daten zum Aktualisieren')
    
    success = update_created_persona(persona_id, data)
    
    if success:
        return success_response()
    else:
        return error_response('Persona nicht gefunden oder Fehler beim Aktualisieren', 404)


@character_bp.route('/api/personas/<persona_id>/activate', methods=['POST'])
@handle_route_error('activate_persona')
def activate_persona_route(persona_id):
    """Aktiviert eine Persona als aktuelle Config"""
    success = activate_persona(persona_id)
    
    if success:
        return success_response(persona_id=persona_id)
    else:
        return error_response('Persona nicht gefunden oder Fehler beim Aktivieren', 404)


@character_bp.route('/api/personas/active', methods=['GET'])
@handle_route_error('get_active_persona')
def get_active_persona():
    """Gibt die ID der aktuell aktiven Persona zurück"""
    persona_id = get_active_persona_id()
    return success_response(persona_id=persona_id)


@character_bp.route('/api/personas/restore_default', methods=['POST'])
@handle_route_error('restore_default')
def restore_default_route():
    """Stellt die Standard-Persona wieder her"""
    success = restore_default_persona()
    
    if success:
        return success_response()
    else:
        return error_response('Fehler beim Wiederherstellen', 500)


@character_bp.route('/api/personas/background-autofill', methods=['POST'])
@handle_route_error('background_autofill')
def background_autofill():
    """KI-gestützte Auto-Generierung der Hintergrundgeschichte basierend auf Persona-Einstellungen"""
    data = request.get_json()
    if not data or not data.get('name'):
        return error_response('Persona-Name ist erforderlich')
    
    # Persona-Daten für Referenz zusammenbauen
    char_name = data.get('name', 'Assistant')
    char_age = data.get('age', 18)
    char_gender = data.get('gender', 'divers')
    persona_type = data.get('persona', 'KI')
    core_traits = data.get('core_traits', [])
    knowledge = data.get('knowledge', [])
    expression = data.get('expression', 'normal')
    scenarios = data.get('scenarios', [])
    user_hint = data.get('background_hint', '').strip()
    
    # Kompakte Referenz aus Persona-Daten (für Prompt-Kontext)
    parts = [f"Name: {char_name}", f"Alter: {char_age}", f"Geschlecht: {char_gender}", f"Persona: {persona_type}"]
    if core_traits:
        parts.append(f"Traits: {', '.join(core_traits)}")
    if knowledge:
        parts.append(f"Wissen: {', '.join(knowledge)}")
    if expression:
        parts.append(f"Stil: {expression}")
    if scenarios:
        parts.append(f"Szenarien: {', '.join(scenarios)}")
    
    reference_text = '\n'.join(parts)
    
    # Prompt bauen – über PromptEngine wenn verfügbar, sonst Fallback
    user_hint_section = f'Der Nutzer stellt sich folgendes vor: {user_hint}' if user_hint else ''
    prompt = None
    try:
        from utils.provider import get_prompt_engine
        engine = get_prompt_engine()
        if engine:
            prompt = engine.resolve_prompt(
                'background_autofill', variant='default',
                runtime_vars={'reference_text': reference_text, 'user_hint_section': user_hint_section}
            )
    except Exception:
        pass

    if not prompt:
        prompt = f"""Erstelle eine kurze, stimmige Hintergrundgeschichte für folgende Persona:

{reference_text}

{user_hint_section}

Schreibe eine kompakte Hintergrundgeschichte (max 800 Zeichen) in der dritten Person die zur Persona passt. 
Nur den Hintergrund-Text zurückgeben, keine Erklärungen oder Formatierung."""
    
    try:
        config = RequestConfig(
            system_prompt='',
            model=get_autofill_model(),
            max_tokens=400,
            messages=[{'role': 'user', 'content': prompt}],
            request_type='background_autofill'
        )
        response = get_api_client().request(config)
        
        if not response.success:
            return error_response(f'API-Fehler: {response.error}', 500)
        
        result_text = response.content.strip()
        tokens = {
            'input': response.usage.get('input_tokens', 0) if response.usage else 0,
            'output': response.usage.get('output_tokens', 0) if response.usage else 0
        }
        
        return success_response(background=result_text, tokens=tokens)
        
    except Exception as api_error:
        log.error("Claude API Fehler bei Background-Autofill: %s", api_error)
        return error_response(f'API-Fehler: {str(api_error)}', 500)
