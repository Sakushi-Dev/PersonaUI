"""
Commands Routes – Backend-Endpunkte für Slash-Kommandos.

Jedes Kommando, das serverseitige Logik benötigt, bekommt hier einen Endpoint.
Route-Prefix: /api/commands/
"""
import os
import sys
import subprocess

from flask import Blueprint, request
from routes.helpers import success_response, error_response, handle_route_error, resolve_persona_id
from utils.logger import log

commands_bp = Blueprint('commands', __name__)

# Pfade
_ROOT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..')    # src/routes/.. → src/
)
_PROJECT_ROOT = os.path.normpath(os.path.join(_ROOT_DIR, '..'))  # → Projekt-Root

def _get_build_script():
    """Returns the path to the build script for the current platform."""
    if sys.platform == 'win32':
        return os.path.join(_PROJECT_ROOT, 'src', 'dev', 'frontend', 'build_frontend.bat')
    return os.path.join(_PROJECT_ROOT, 'src', 'dev', 'frontend', 'build_frontend.sh')


@commands_bp.route('/api/commands/rebuild-frontend', methods=['POST'])
@handle_route_error('rebuild_frontend')
def rebuild_frontend():
    """
    Startet das Build-Script als unabhängigen Prozess.
    Der Flask-Server wird dadurch nicht blockiert.
    """
    build_script = _get_build_script()
    
    # Fallback: npm run build direkt ausführen wenn kein Script existiert
    if not os.path.isfile(build_script):
        frontend_dir = os.path.join(_PROJECT_ROOT, 'frontend')
        if not os.path.isdir(frontend_dir):
            return error_response('Frontend-Verzeichnis nicht gefunden', 404)
        
        log.info('[rebuild] Kein Build-Script gefunden, starte npm run build direkt...')
        try:
            npm_cmd = 'npm.cmd' if sys.platform == 'win32' else 'npm'
            subprocess.Popen(
                [npm_cmd, 'run', 'build'],
                cwd=frontend_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            log.error('[rebuild] Fehler beim Starten von npm run build: %s', exc)
            return error_response(f'Build konnte nicht gestartet werden: {exc}', 500)
        
        return success_response(message='Frontend-Build gestartet (npm run build)')

    log.info('[rebuild] Starte Build-Script: %s', build_script)

    try:
        if sys.platform == 'win32':
            subprocess.Popen(
                ['cmd', '/c', 'start', 'PersonaUI - Frontend Build', 'cmd', '/c', build_script],
                cwd=_PROJECT_ROOT,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        else:
            subprocess.Popen(
                ['bash', build_script],
                cwd=_PROJECT_ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception as exc:
        log.error('[rebuild] Fehler beim Starten des Build-Scripts: %s', exc)
        return error_response(f'Build-Script konnte nicht gestartet werden: {exc}', 500)

    log.info('[rebuild] Build-Script gestartet.')
    return success_response(message='Build-Script gestartet')


# ═══════════════════════════════════════════════════════════════
#  /onboarding – Start-Sequenz erneut aktivieren
# ═══════════════════════════════════════════════════════════════

@commands_bp.route('/api/commands/reset-onboarding', methods=['POST'])
@handle_route_error('reset_onboarding')
def reset_onboarding():
    """
    Slash Command: /onboarding — Setzt das Onboarding zurück.
    Beim nächsten Seitenaufruf wird die Start-Sequenz erneut angezeigt.
    """
    try:
        from utils.settings_manager import save_section
        save_section('initialization', {'completed': False})
        log.info('[/onboarding] Onboarding zurückgesetzt – wird beim nächsten Laden angezeigt.')
        return success_response(message='Onboarding zurückgesetzt – Seite wird neu geladen.')
    except Exception as exc:
        log.error('[/onboarding] Fehler beim Zurücksetzen: %s', exc)
        return error_response(f'Onboarding konnte nicht zurückgesetzt werden: {exc}', 500)


# ═══════════════════════════════════════════════════════════════
#  /cortex – Manueller Cortex-Update + Zähler-Reset
# ═══════════════════════════════════════════════════════════════

@commands_bp.route('/api/commands/cortex-update', methods=['POST'])
@handle_route_error('cortex_update')
def cortex_update():
    """
    Slash Command: /cortex — Sofortiger Cortex-Update + Zähler-Reset.

    Prüft:
    - Cortex aktiviert?
    - Session hat Nachrichten?

    Startet Background-Update und gibt Progress-Daten zurück.
    """
    from utils.database import get_message_count
    from utils.database import get_all_sessions
    from utils.cortex.tier_tracker import set_cycle_base, get_progress
    from utils.cortex.tier_checker import (
        _load_cortex_config,
        _get_context_limit,
        _calculate_threshold,
        _start_background_cortex_update,
        DEFAULT_FREQUENCY,
    )

    # 1. Cortex aktiviert?
    config = _load_cortex_config()
    if not config.get("enabled", False):
        return error_response("Cortex ist deaktiviert", 400)

    # 2. Persona bestimmen
    persona_id = resolve_persona_id()

    # 3. Neueste Session ermitteln
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')

    if not session_id:
        sessions = get_all_sessions(persona_id)
        if not sessions:
            return error_response("Keine aktive Session", 400)
        session_id = sessions[0]['id']

    # 4. Session hat Nachrichten?
    message_count = get_message_count(session_id=session_id, persona_id=persona_id)
    if message_count == 0:
        return error_response("Keine Nachrichten in der Session", 400)

    # 5. Zähler-Reset: cycle_base = aktuelle message_count
    set_cycle_base(persona_id, session_id, message_count)

    # 6. Background-Update starten
    _start_background_cortex_update(persona_id, session_id)

    log.info(
        "[/cortex] Manueller Cortex-Update gestartet — Persona: %s, Session: %s, "
        "Messages: %d",
        persona_id, session_id, message_count
    )

    # 7. Progress-Daten für Frontend (nach Reset = 0%)
    frequency = config.get("frequency", DEFAULT_FREQUENCY)
    context_limit = _get_context_limit()
    threshold = _calculate_threshold(context_limit, frequency)
    progress = get_progress(persona_id, session_id, message_count, threshold)

    return success_response(
        message="Cortex-Update gestartet",
        cortex={
            "triggered": True,
            "progress": progress,
            "frequency": frequency
        }
    )
