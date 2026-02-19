"""
Commands Routes – Backend-Endpunkte für Slash-Kommandos.

Jedes Kommando, das serverseitige Logik benötigt, bekommt hier einen Endpoint.
Route-Prefix: /api/commands/
"""
import os
import subprocess

from flask import Blueprint
from routes.helpers import success_response, error_response, handle_route_error
from utils.logger import log

commands_bp = Blueprint('commands', __name__)

# Pfade
_ROOT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..')    # src/routes/.. → src/
)
_PROJECT_ROOT = os.path.normpath(os.path.join(_ROOT_DIR, '..'))  # → Projekt-Root
_BUILD_SCRIPT = os.path.join(_PROJECT_ROOT, 'src', 'dev', 'frontend', 'build_frontend.bat')


@commands_bp.route('/api/commands/rebuild-frontend', methods=['POST'])
@handle_route_error('rebuild_frontend')
def rebuild_frontend():
    """
    Startet build_frontend.bat als unabhängigen Prozess in einem eigenen Konsolenfenster.
    Der Flask-Server wird dadurch nicht blockiert.
    """
    if not os.path.isfile(_BUILD_SCRIPT):
        return error_response('build_frontend.bat nicht gefunden', 404)

    log.info('[rebuild] Starte Build-Script: %s', _BUILD_SCRIPT)

    try:
        # Eigenes Konsolenfenster, komplett vom Server-Prozess entkoppelt
        subprocess.Popen(
            ['cmd', '/c', 'start', 'PersonaUI - Frontend Build', 'cmd', '/c', _BUILD_SCRIPT],
            cwd=_PROJECT_ROOT,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0,
        )
    except Exception as exc:
        log.error('[rebuild] Fehler beim Starten des Build-Scripts: %s', exc)
        return error_response(f'Build-Script konnte nicht gestartet werden: {exc}', 500)

    log.info('[rebuild] Build-Script gestartet (eigenes Fenster).')
    return success_response(message='Build-Script gestartet – siehe Konsolenfenster')
