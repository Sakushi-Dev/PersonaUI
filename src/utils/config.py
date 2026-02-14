"""
Hilfsfunktionen zum Laden von Konfigurationsdateien
"""

import json
import os
import uuid
import shutil
from typing import Dict, Any, List, Optional
from utils.database import create_persona_db, delete_persona_db
from utils.logger import log

# Base directory für Config-Dateien (src/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_config_path(relative_path: str) -> str:
    """Konvertiert relativen Pfad zu absolutem Pfad basierend auf src/ Verzeichnis"""
    return os.path.join(BASE_DIR, relative_path)


def load_character() -> Dict[str, Any]:
    """
    Lädt Charakterdaten aus persona_config.json und persona_spec.json
        
    Returns:
        Dictionary mit Charakterinformationen (dynamisch aus JSON gebaut)
    """
    try:
        return build_character_description()
    except Exception as e:
        log.error("Fehler beim Laden der Charakterdaten: %s", e)
        return {
            'char_name': 'Assistant',
            'desc': 'Eine freundliche Assistentin die gerne hilft.',
            'greeting': None,
            'start_msg_enabled': False,
            'background': ''
        }




def load_avatar() -> Dict[str, Any]:
    """
    Lädt Avatar-Daten aus der aktiven persona_config.json.
    
    Returns:
        Dictionary mit Avatar-Informationen (avatar, avatar_type)
    """
    try:
        config = load_char_config()
        return {
            'avatar': config.get('avatar', None),
            'avatar_type': config.get('avatar_type', None)
        }
    except Exception as e:
        log.error("Fehler beim Laden der Avatar-Daten: %s", e)
        return {
            'avatar': None,
            'avatar_type': None
        }


def save_avatar_config(avatar_data: Dict[str, Any]) -> bool:
    """
    Speichert Avatar-Daten in die aktive persona_config.json.
    Aktualisiert nur die Avatar-Felder, ohne andere Config-Daten zu überschreiben.
    
    Args:
        avatar_data: Dictionary mit Avatar-Informationen (avatar, avatar_type)
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        # Aktuelle Config laden
        config = load_char_config()
        
        # Avatar-Felder aktualisieren
        if 'avatar' in avatar_data:
            config['avatar'] = avatar_data['avatar']
        if 'avatar_type' in avatar_data:
            config['avatar_type'] = avatar_data['avatar_type']
        
        # avatar_crop entfernen falls vorhanden (nicht mehr benötigt)
        config.pop('avatar_crop', None)
        
        return save_char_config(config)
    except Exception as e:
        log.error("Fehler beim Speichern der Avatar-Daten: %s", e)
        return False


# ===== Persona Config & Profile System =====

def load_char_profile(profile_file: str = 'instructions/personas/spec/persona_spec.json') -> Dict[str, Any]:
    """
    Lädt das vollständige Persona-Profil (alle verfügbaren Optionen)
    Merged automatisch Custom Specs aus custom_spec/custom_spec.json
    
    Args:
        profile_file: Pfad zur persona_spec.json
        
    Returns:
        Dictionary mit allen verfügbaren Core Traits, Knowledge Areas und Expression Styles
    """
    try:
        full_path = get_config_path(profile_file)
        with open(full_path, 'r', encoding='utf-8') as file:
            base_profile = json.load(file)
        
        # Custom Specs laden und mergen
        custom_spec_path = get_config_path('instructions/personas/spec/custom_spec/custom_spec.json')
        if os.path.exists(custom_spec_path):
            try:
                with open(custom_spec_path, 'r', encoding='utf-8') as f:
                    custom_profile = json.load(f)
                
                # Merge custom specs in base profile
                base_spec = base_profile.get('persona_spec', {})
                custom_spec = custom_profile.get('persona_spec', {})
                
                for category in ['persona_type', 'core_traits_details', 'knowledge_areas', 'expression_styles', 'scenarios']:
                    custom_items = custom_spec.get(category, {})
                    if custom_items:
                        if category not in base_spec:
                            base_spec[category] = {}
                        base_spec[category].update(custom_items)
                
                base_profile['persona_spec'] = base_spec
            except Exception as e:
                log.warning("Custom Specs konnten nicht geladen werden: %s", e)
        
        return base_profile
    except FileNotFoundError:
        log.warning("%s nicht gefunden.", profile_file)
        return {"persona_spec": {"persona_type": {}, "core_traits_details": {}, "knowledge_areas": {}, "expression_styles": {}}}
    except Exception as e:
        log.error("Fehler beim Laden des Persona-Profils: %s", e)
        return {"persona_spec": {"persona_type": {}, "core_traits_details": {}, "knowledge_areas": {}, "expression_styles": {}}}


def load_char_config(config_file: str = 'instructions/personas/active/persona_config.json') -> Dict[str, Any]:
    """
    Lädt die aktuelle Persona-Konfiguration (was ausgewählt ist)
    
    Args:
        config_file: Pfad zur persona_config.json
        
    Returns:
        Dictionary mit der aktuellen Auswahl (name, age, gender, persona, core_traits, knowledge, expression)
    """
    ensure_active_persona_config()
    try:
        full_path = get_config_path(config_file)
        with open(full_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data.get('persona_settings', {})
    except FileNotFoundError:
        log.warning("%s nicht gefunden. Verwende Default.", config_file)
        return {
            "name": "Assistant",
            "age": 18,
            "gender": "divers",
            "persona": "KI",
            "core_traits": ["freundlich", "intelligent"],
            "knowledge": ["Allgemeinwissen"],
            "expression": "normal"
        }
    except Exception as e:
        log.error("Fehler beim Laden der Persona-Konfiguration: %s", e)
        return {
            "name": "Assistant",
            "age": 18,
            "gender": "divers",
            "persona": "KI",
            "core_traits": [],
            "knowledge": [],
            "expression": "normal"
        }


def get_active_persona_id(config_file: str = 'instructions/personas/active/persona_config.json') -> str:
    """
    Gibt die ID der aktuell aktiven Persona zurück.
    
    Returns:
        Persona-ID als String ('default' oder eine UUID)
    """
    ensure_active_persona_config()
    try:
        full_path = get_config_path(config_file)
        with open(full_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data.get('active_persona_id', 'default')
    except Exception:
        return 'default'


def set_active_persona_id(persona_id: str, config_file: str = 'instructions/personas/active/persona_config.json') -> bool:
    """
    Setzt die ID der aktiven Persona in der Config.
    
    Args:
        persona_id: ID der Persona ('default' oder UUID)
        
    Returns:
        True bei Erfolg
    """
    try:
        full_path = get_config_path(config_file)
        with open(full_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        data['active_persona_id'] = persona_id
        
        with open(full_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log.error("Fehler beim Setzen der aktiven Persona-ID: %s", e)
        return False


def save_char_config(config_data: Dict[str, Any], config_file: str = 'instructions/personas/active/persona_config.json') -> bool:
    """
    Speichert die Persona-Konfiguration (behält active_persona_id bei)
    
    Args:
        config_data: Dictionary mit name, persona, core_traits, knowledge, expression
        config_file: Pfad zur persona_config.json
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        full_path = get_config_path(config_file)
        
        # Bestehende Daten laden um active_persona_id beizubehalten
        existing_data = {}
        try:
            with open(full_path, 'r', encoding='utf-8') as file:
                existing_data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        
        wrapped_data = {
            "active_persona_id": existing_data.get("active_persona_id", "default"),
            "persona_settings": config_data
        }
        
        with open(full_path, 'w', encoding='utf-8') as file:
            json.dump(wrapped_data, file, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log.error("Fehler beim Speichern der Persona-Konfiguration: %s", e)
        return False


def get_available_char_options(profile_file: str = 'instructions/personas/spec/persona_spec.json') -> Dict[str, Any]:
    """
    Gibt alle verfügbaren Optionen aus dem Persona-Profil zurück.
    Reihenfolge: Default-Einträge zuerst, dann Custom-Einträge.
    
    Args:
        profile_file: Pfad zur persona_spec.json
        
    Returns:
        Dictionary mit persona_types, core_traits, knowledge, expression_styles
    """
    try:
        # Base-Profil separat laden (ohne Custom-Merge)
        full_path = get_config_path(profile_file)
        with open(full_path, 'r', encoding='utf-8') as f:
            base_profile = json.load(f)
        base_spec = base_profile.get('persona_spec', {})
        
        # Custom Specs separat laden
        custom_spec_path = get_config_path('instructions/personas/spec/custom_spec/custom_spec.json')
        custom_spec = {}
        if os.path.exists(custom_spec_path):
            try:
                with open(custom_spec_path, 'r', encoding='utf-8') as f:
                    custom_data = json.load(f)
                custom_spec = custom_data.get('persona_spec', {})
            except Exception:
                pass
        
        # Für jede Kategorie: Default-Keys zuerst, dann Custom-Keys anhängen
        def ordered_keys(base_cat, custom_cat):
            base_keys = list(base_spec.get(base_cat, {}).keys())
            custom_keys = [k for k in custom_spec.get(custom_cat, {}).keys() if k not in base_keys]
            return base_keys + custom_keys
        
        return {
            "persona_types": ordered_keys('persona_type', 'persona_type'),
            "core_traits": ordered_keys('core_traits_details', 'core_traits_details'),
            "knowledge": ordered_keys('knowledge_areas', 'knowledge_areas'),
            "expression_styles": ordered_keys('expression_styles', 'expression_styles'),
            "scenarios": ordered_keys('scenarios', 'scenarios')
        }
    except Exception as e:
        log.error("Fehler beim Abrufen verfügbarer Optionen: %s", e)
        return {
            "persona_types": ["KI"],
            "core_traits": [],
            "knowledge": [],
            "expression_styles": [],
            "scenarios": []
        }


# ===== Created Personas Management =====

CREATED_PERSONAS_DIR = os.path.join(BASE_DIR, 'instructions', 'created_personas')
DEFAULT_PERSONA_FILE = 'instructions/personas/default/default_persona.json'
ACTIVE_PERSONA_FILE = 'instructions/personas/active/persona_config.json'


def ensure_active_persona_config():
    """
    Stellt sicher, dass persona_config.json existiert.
    Falls nicht, wird sie aus default_persona.json mit active_persona_id='default' erstellt.
    """
    active_path = get_config_path(ACTIVE_PERSONA_FILE)
    if not os.path.exists(active_path):
        log.info("persona_config.json fehlt – erstelle aus default_persona.json")
        try:
            default_path = get_config_path(DEFAULT_PERSONA_FILE)
            with open(default_path, 'r', encoding='utf-8') as f:
                default_data = json.load(f)
            
            active_data = {
                "active_persona_id": "default",
                "persona_settings": default_data.get('persona_settings', {})
            }
            
            os.makedirs(os.path.dirname(active_path), exist_ok=True)
            with open(active_path, 'w', encoding='utf-8') as f:
                json.dump(active_data, f, ensure_ascii=False, indent=2)
            
            log.info("persona_config.json erfolgreich aus Default erstellt")
        except Exception as e:
            log.error("Fehler beim Erstellen der persona_config.json: %s", e)


def ensure_created_personas_dir():
    """Stellt sicher, dass das created_personas Verzeichnis existiert"""
    os.makedirs(CREATED_PERSONAS_DIR, exist_ok=True)


def load_default_persona() -> Dict[str, Any]:
    """Lädt die Standard-Persona aus default_persona.json"""
    try:
        full_path = get_config_path(DEFAULT_PERSONA_FILE)
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('persona_settings', {})
    except Exception as e:
        log.error("Fehler beim Laden der Standard-Persona: %s", e)
        return {
            "name": "Assistant",
            "age": 18,
            "gender": "divers",
            "persona": "KI",
            "core_traits": ["freundlich", "intelligent"],
            "knowledge": ["Allgemeinwissen"],
            "expression": "normal"
        }


def list_created_personas() -> list:
    """Listet alle erstellten Personas aus dem created_personas Ordner"""
    ensure_created_personas_dir()
    personas = []
    
    # Standard-Persona immer als erstes hinzufügen
    default_config = load_default_persona()
    active_config = load_char_config()
    
    default_entry = {
        "id": "default",
        "name": default_config.get("name", "Assistant"),
        "age": default_config.get("age", None),
        "gender": default_config.get("gender", None),
        "persona": default_config.get("persona", "KI"),
        "core_traits": default_config.get("core_traits", []),
        "knowledge": default_config.get("knowledge", []),
        "expression": default_config.get("expression", None),
        "scenarios": default_config.get("scenarios", []),
        "background": default_config.get("background", ""),
        "start_msg_enabled": default_config.get("start_msg_enabled", False),
        "start_msg": default_config.get("start_msg", ""),
        "avatar": default_config.get("avatar", None),
        "avatar_type": default_config.get("avatar_type", None),
        "is_default": True,
        "is_active": _configs_match(active_config, default_config)
    }
    personas.append(default_entry)
    
    # Erstellte Personas laden
    for filename in sorted(os.listdir(CREATED_PERSONAS_DIR)):
        if filename.endswith('.json'):
            try:
                filepath = os.path.join(CREATED_PERSONAS_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                settings = data.get('persona_settings', {})
                persona_id = data.get('id', filename.replace('.json', ''))
                entry = {
                    "id": persona_id,
                    "name": settings.get("name", "Unbenannt"),
                    "age": settings.get("age", 18),
                    "gender": settings.get("gender", "divers"),
                    "persona": settings.get("persona", "KI"),
                    "core_traits": settings.get("core_traits", []),
                    "knowledge": settings.get("knowledge", []),
                    "expression": settings.get("expression", "normal"),
                    "scenarios": settings.get("scenarios", []),
                    "background": settings.get("background", ""),
                    "start_msg_enabled": settings.get("start_msg_enabled", False),
                    "start_msg": settings.get("start_msg", ""),
                    "avatar": settings.get("avatar", None),
                    "avatar_type": settings.get("avatar_type", None),
                    "is_default": False,
                    "is_active": _configs_match(active_config, settings)
                }
                personas.append(entry)
            except Exception as e:
                log.error("Fehler beim Laden von %s: %s", filename, e)
    
    return personas


def _configs_match(config_a: Dict, config_b: Dict) -> bool:
    """Prüft ob zwei Persona-Configs übereinstimmen (alle relevanten Felder)"""
    return (
        config_a.get("name") == config_b.get("name") and
        config_a.get("age") == config_b.get("age") and
        config_a.get("gender") == config_b.get("gender") and
        config_a.get("persona") == config_b.get("persona") and
        sorted(config_a.get("core_traits", [])) == sorted(config_b.get("core_traits", [])) and
        sorted(config_a.get("knowledge", [])) == sorted(config_b.get("knowledge", [])) and
        config_a.get("expression") == config_b.get("expression") and
        sorted(config_a.get("scenarios", [])) == sorted(config_b.get("scenarios", [])) and
        config_a.get("background", "") == config_b.get("background", "") and
        config_a.get("start_msg_enabled", False) == config_b.get("start_msg_enabled", False) and
        config_a.get("start_msg", "") == config_b.get("start_msg", "")
    )


def save_created_persona(config_data: Dict[str, Any]) -> Optional[str]:
    """
    Speichert eine neue Persona im created_personas Ordner
    und erstellt die zugehörige Persona-Datenbank.
    Gibt die ID zurück oder None bei Fehler.
    """
    ensure_created_personas_dir()
    try:
        persona_id = str(uuid.uuid4())[:8]
        filename = f"{persona_id}.json"
        filepath = os.path.join(CREATED_PERSONAS_DIR, filename)
        
        save_data = {
            "id": persona_id,
            "persona_settings": config_data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        # Erstelle die zugehörige Persona-Datenbank
        create_persona_db(persona_id)
        
        return persona_id
    except Exception as e:
        log.error("Fehler beim Speichern der Persona: %s", e)
        return None


def update_created_persona(persona_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Aktualisiert eine bestehende Persona (Name bleibt unveränderlich).
    Gibt True bei Erfolg zurück.
    """
    if persona_id == "default":
        return False
    
    ensure_created_personas_dir()
    filepath = os.path.join(CREATED_PERSONAS_DIR, f"{persona_id}.json")
    
    try:
        if not os.path.exists(filepath):
            return False
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        settings = data.get('persona_settings', {})
        original_name = settings.get('name')
        
        # Name nie überschreiben
        update_data.pop('name', None)
        
        # Felder aktualisieren
        settings.update(update_data)
        settings['name'] = original_name  # Sicherstellen
        data['persona_settings'] = settings
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Wenn diese Persona aktuell aktiv ist, Config neu laden
        if get_active_persona_id() == persona_id:
            activate_persona(persona_id)
        
        return True
    except Exception as e:
        log.error("Fehler beim Aktualisieren der Persona %s: %s", persona_id, e)
        return False


def delete_created_persona(persona_id: str) -> bool:
    """Löscht eine erstellte Persona anhand ihrer ID und entfernt die zugehörige DB"""
    if persona_id == "default":
        return False  # Standard kann nicht gelöscht werden
    
    ensure_created_personas_dir()
    filepath = os.path.join(CREATED_PERSONAS_DIR, f"{persona_id}.json")
    
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            # Lösche die zugehörige Persona-Datenbank
            delete_persona_db(persona_id)
            return True
        return False
    except Exception as e:
        log.error("Fehler beim Löschen der Persona %s: %s", persona_id, e)
        return False


def load_persona_by_id(persona_id: str) -> Optional[Dict[str, Any]]:
    """Lädt eine Persona anhand ihrer ID"""
    if persona_id == "default":
        return load_default_persona()
    
    ensure_created_personas_dir()
    filepath = os.path.join(CREATED_PERSONAS_DIR, f"{persona_id}.json")
    
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('persona_settings', {})
        return None
    except Exception as e:
        log.error("Fehler beim Laden der Persona %s: %s", persona_id, e)
        return None


def _invalidate_prompt_engine_cache():
    """Invalidiert den PromptEngine-Cache nach Persona-Wechsel (lazy import um Zirkularität zu vermeiden)."""
    try:
        from utils.provider import get_prompt_engine
        engine = get_prompt_engine()
        if engine:
            engine.invalidate_cache()
            log.info("PromptEngine-Cache nach Persona-Wechsel invalidiert")
    except Exception as e:
        log.warning("PromptEngine-Cache konnte nicht invalidiert werden: %s", e)


def activate_persona(persona_id: str) -> bool:
    """Aktiviert eine Persona (kopiert sie in die aktive Config inkl. Avatar und setzt ID)"""
    config = load_persona_by_id(persona_id)
    if config is None:
        return False
    
    # Avatar-Daten bleiben in der Config (kein Stripping mehr)
    success = save_char_config(config)
    if success:
        set_active_persona_id(persona_id)
        # PromptEngine-Cache invalidieren damit System-Prompt mit neuer Persona gebaut wird
        _invalidate_prompt_engine_cache()
    return success


def restore_default_persona() -> bool:
    """Stellt die Standard-Persona als aktive Config inkl. Avatar wieder her"""
    default_config = load_default_persona()
    
    # Avatar-Daten bleiben in der Config (kein Stripping mehr)
    success = save_char_config(default_config)
    if success:
        set_active_persona_id('default')
        # PromptEngine-Cache invalidieren damit System-Prompt mit neuer Persona gebaut wird
        _invalidate_prompt_engine_cache()
    return success


def build_character_description_from_config(
    config: Dict[str, Any],
    profile_file: str = 'instructions/personas/spec/persona_spec.json'
) -> Dict[str, Any]:
    """
    Baut die Charakterbeschreibung aus einem übergebenen Config-Dict (ohne Datei zu lesen/speichern).
    Wird für die Live-Vorschau im Creator verwendet.
    
    Args:
        config: Dictionary mit persona_config Daten (name, age, gender, persona, core_traits, etc.)
        profile_file: Pfad zur persona_spec.json (alle verfügbaren Optionen)
        
    Returns:
        Dictionary mit char_name, identity, core, behavior, comms, voice, greeting, desc
    """
    return _build_character_description_impl(config, profile_file)


def build_character_description(
    config_file: str = 'instructions/personas/active/persona_config.json',
    profile_file: str = 'instructions/personas/spec/persona_spec.json'
) -> Dict[str, Any]:
    """
    Baut dynamisch die vollständige Charakterbeschreibung aus persona_config und persona_spec zusammen
    
    Args:
        config_file: Pfad zur persona_config.json (aktuelle Auswahl)
        profile_file: Pfad zur persona_spec.json (alle verfügbaren Optionen)
        
    Returns:
        Dictionary mit char_name, identity, core, behavior, comms, voice, greeting
    """
    config = load_char_config(config_file)
    return _build_character_description_impl(config, profile_file)


def _build_character_description_impl(
    config: Dict[str, Any],
    profile_file: str = 'instructions/personas/spec/persona_spec.json'
) -> Dict[str, Any]:
    """
    Interne Implementierung: Baut die Charakterbeschreibung aus config-Dict und profile-Datei.
    """
    try:
        # Lade Profile (alle Optionen)
        profile = load_char_profile(profile_file)
        
        # Extrahiere Profil-Daten
        persona_profile = profile.get('persona_spec', {})
        persona_types = persona_profile.get('persona_type', {})
        core_traits_details = persona_profile.get('core_traits_details', {})
        knowledge_areas = persona_profile.get('knowledge_areas', {})
        expression_styles = persona_profile.get('expression_styles', {})
        scenarios_details = persona_profile.get('scenarios', {})
        
        # === IDENTITY ===
        char_name = config.get('name', 'Assistant')
        char_age = config.get('age', 18)
        char_gender = config.get('gender', 'divers')
        persona_type = config.get('persona', 'KI')
        persona_type_desc = persona_types.get(persona_type, '')
        
        # Baue Identity-Text
        identity_parts = []
        identity_parts.append(f"Name: {char_name}")
        identity_parts.append(f"Alter: {char_age}")
        identity_parts.append(f"Geschlecht: {char_gender}")
        identity_parts.append(f"Persona: {persona_type}")
        if persona_type_desc:
            identity_parts.append(f"Beschreibung: {persona_type_desc}")
        
        identity = '\n'.join(identity_parts)
        
        # === CORE (Personality Traits) ===
        selected_traits = config.get('core_traits', [])
        
        core_parts = []
        if selected_traits:
            core_parts.append("Persönlichkeitsmerkmale:")
            
            for trait in selected_traits:
                trait_data = core_traits_details.get(trait, {})
                if isinstance(trait_data, dict):
                    trait_desc = trait_data.get('description', trait)
                    behaviors = trait_data.get('behaviors', [])
                    
                    core_parts.append(f"\n{trait}: {trait_desc}")
                    if behaviors:
                        for behavior in behaviors:
                            core_parts.append(f"  - {behavior}")
                else:
                    core_parts.append(f"\n{trait}")
        
        core = '\n'.join(core_parts) if core_parts else ''
        
        # === KNOWLEDGE ===
        selected_knowledge = config.get('knowledge', [])
        knowledge_parts = []
        
        if selected_knowledge:
            knowledge_parts.append("Wissensgebiete:")
            for knowledge in selected_knowledge:
                knowledge_desc = knowledge_areas.get(knowledge, knowledge)
                knowledge_parts.append(f"  - {knowledge}: {knowledge_desc}")
        
        knowledge_text = '\n'.join(knowledge_parts) if knowledge_parts else ''
        
        # === EXPRESSION / COMMUNICATION STYLE ===
        selected_expression = config.get('expression', 'normal')
        expression_data = expression_styles.get(selected_expression, {})
        
        comms_parts = []
        if expression_data:
            expr_name = expression_data.get('name', selected_expression)
            expr_desc = expression_data.get('description', '')
            expr_chars = expression_data.get('characteristics', [])
            
            comms_parts.append(f"Kommunikationsstil: {expr_name}")
            if expr_desc:
                comms_parts.append(expr_desc)
            if expr_chars:
                comms_parts.append("Eigenschaften:")
                for char in expr_chars:
                    comms_parts.append(f"  - {char}")
        
        comms = '\n'.join(comms_parts) if comms_parts else ''
        
        # === SCENARIO (nur für nicht-KI Personas) ===
        scenario_text = ''
        if persona_type != 'KI':
            selected_scenarios = config.get('scenarios', [])
            if selected_scenarios:
                scenario_parts = []
                scenario_parts.append("Szenario / Setting:")
                for scenario_key in selected_scenarios:
                    scenario_data = scenarios_details.get(scenario_key, {})
                    if isinstance(scenario_data, dict):
                        sc_name = scenario_data.get('name', scenario_key)
                        sc_desc = scenario_data.get('description', '')
                        sc_setting = scenario_data.get('setting', [])
                        
                        scenario_parts.append(f"\n{sc_name}: {sc_desc}")
                        if sc_setting:
                            for s in sc_setting:
                                scenario_parts.append(f"  - {s}")
                    else:
                        scenario_parts.append(f"\n{scenario_key}")
                scenario_text = '\n'.join(scenario_parts)
        
        # === BACKGROUND (Hintergrundgeschichte) ===
        background_text = config.get('background', '').strip()
        
        # Greeting: Nur wenn start_msg aktiviert ist
        start_msg_enabled = config.get('start_msg_enabled', False)
        start_msg_text = config.get('start_msg', '').strip()
        
        if start_msg_enabled and start_msg_text:
            greeting = start_msg_text
        else:
            greeting = None
        
        # === BEHAVIOR & VOICE (optional) ===
        behavior = ''
        voice = ''
        
        # Kombiniere alles für desc
        desc_parts = [identity]
        if core:
            desc_parts.append(core)
        if knowledge_text:
            desc_parts.append(knowledge_text)
        if comms:
            desc_parts.append(comms)
        if scenario_text:
            desc_parts.append(scenario_text)
        if background_text:
            desc_parts.append(f"Hintergrund:\n{background_text}")
        
        return {
            'char_name': char_name,
            'identity': identity,
            'core': core,
            'behavior': behavior,
            'comms': comms,
            'voice': voice,
            'greeting': greeting,
            'start_msg_enabled': start_msg_enabled,
            'background': background_text,
            'desc': '\n\n'.join(desc_parts)
        }
        
    except Exception as e:
        log.error("Fehler beim Zusammenbauen der Charakterbeschreibung: %s", e)
        # Fallback
        return {
            'char_name': 'Assistant',
            'identity': 'Eine freundliche Assistentin',
            'core': '',
            'behavior': '',
            'comms': '',
            'voice': '',
            'greeting': None,
            'start_msg_enabled': False,
            'background': '',
            'desc': 'Eine freundliche Assistentin'
        }
