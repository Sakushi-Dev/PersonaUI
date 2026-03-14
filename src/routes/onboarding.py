"""
Onboarding Routes – First-Run Setup Sequenz
"""
from flask import Blueprint
import os
import json
from routes.helpers import success_response, handle_route_error
from utils.logger import log
from utils.settings_manager import load_section, save_section
from routes.react_frontend import serve_react_app

onboarding_bp = Blueprint('onboarding', __name__)


def is_onboarding_complete():
    """Prüft ob das Onboarding bereits abgeschlossen wurde."""
    data = load_section('initialization')
    return data.get('completed', False)


@onboarding_bp.route('/onboarding')
def onboarding():
    """Zeigt die Onboarding-Seite an (React SPA)."""
    return serve_react_app()


@onboarding_bp.route('/api/onboarding/complete', methods=['POST'])
@handle_route_error('complete_onboarding')
def complete_onboarding():
    """Markiert das Onboarding als abgeschlossen."""
    try:
        save_section('initialization', {'completed': True, 'disclaimerAccepted': False})
        log.info("Onboarding abgeschlossen.")
        return success_response()
    except Exception as e:
        log.error("Fehler beim Markieren des Onboarding: %s", e)
        return success_response()  # Trotzdem OK, damit Redirect funktioniert


@onboarding_bp.route('/api/onboarding/accept-disclaimer', methods=['POST'])
@handle_route_error('accept_disclaimer')
def accept_disclaimer():
    """Markiert den Disclaimer als akzeptiert."""
    try:
        data = load_section('initialization')
        data['disclaimerAccepted'] = True
        save_section('initialization', data)
        log.info("Disclaimer akzeptiert.")
        return success_response()
    except Exception as e:
        log.error("Fehler beim Akzeptieren des Disclaimers: %s", e)
        return success_response()


@onboarding_bp.route('/api/shutdown', methods=['POST'])
@handle_route_error('shutdown')
def shutdown_server():
    """Fährt den Server herunter."""
    import threading
    import time

    log.info("Server wird heruntergefahren (Benutzeranfrage).")

    def do_shutdown():
        time.sleep(0.5)
        import os as _os
        _os._exit(0)

    threading.Thread(target=do_shutdown, daemon=True).start()
    return success_response(message='Server wird beendet...')


@onboarding_bp.route('/api/onboarding/status', methods=['GET'])
@handle_route_error('onboarding_status')
def onboarding_status():
    """Prüft ob das Onboarding bereits abgeschlossen wurde (für React SPA)."""
    data = load_section('initialization')
    disclaimer_accepted = data.get('disclaimerAccepted', False)
    return success_response(completed=is_onboarding_complete(), disclaimer_accepted=disclaimer_accepted)
