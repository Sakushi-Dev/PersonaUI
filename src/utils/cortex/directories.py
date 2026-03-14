"""
Cortex directory management — create, ensure, delete persona cortex dirs.
"""

import os
import shutil

from ..logger import log
from . import constants
from .templates_loader import get_templates


def get_cortex_dir(persona_id: str = 'default') -> str:
    """Returns the cortex directory path for a persona."""
    if not persona_id:
        persona_id = 'default'
    return os.path.join(constants.DATA_DIR, persona_id, 'cortex')


def ensure_cortex_dir(persona_id: str) -> str:
    """
    Ensures cortex dir exists with all template files.
    Returns the directory path.
    """
    cortex_dir = get_cortex_dir(persona_id)
    os.makedirs(cortex_dir, exist_ok=True)

    for filename, template_content in get_templates().items():
        filepath = os.path.join(cortex_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(template_content)
            log.info("Cortex-Template erstellt: %s/%s", persona_id, filename)

    return cortex_dir


def create_cortex_dir(persona_id: str) -> bool:
    """Creates cortex directory for a new persona with all templates."""
    try:
        ensure_cortex_dir(persona_id)
        log.info("Cortex-Verzeichnis erstellt für Persona: %s", persona_id)
        return True
    except Exception as e:
        log.error("Fehler beim Erstellen des Cortex-Verzeichnisses für %s: %s",
                  persona_id, e)
        return False


def delete_cortex_dir(persona_id: str) -> bool:
    """Deletes cortex directory for a persona."""
    if persona_id == 'default':
        log.warning("Default Cortex-Verzeichnis kann nicht gelöscht werden!")
        return False

    cortex_dir = get_cortex_dir(persona_id)
    try:
        if os.path.exists(cortex_dir):
            shutil.rmtree(cortex_dir)
            log.info("Cortex-Verzeichnis gelöscht: %s", persona_id)
            return True
        return False
    except Exception as e:
        log.error("Fehler beim Löschen des Cortex-Verzeichnisses für %s: %s",
                  persona_id, e)
        return False


def ensure_cortex_dirs() -> int:
    """
    Startup function: ensures cortex directories exist for default persona
    and all custom personas from created_personas/.
    Returns number of directories checked.
    """
    count = 0

    # 1. Default persona
    ensure_cortex_dir('default')
    count += 1

    # 2. All custom personas
    personas_dir = os.path.join(constants.BASE_DIR, 'instructions', 'created_personas')
    if not os.path.isdir(personas_dir):
        return count

    for filename in os.listdir(personas_dir):
        if not filename.endswith('.json'):
            continue
        persona_id = filename[:-5]
        if persona_id:
            ensure_cortex_dir(persona_id)
            count += 1

    log.info("Cortex-Verzeichnisse geprüft: %d Personas", count)
    return count
