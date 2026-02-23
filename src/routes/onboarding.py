"""
Onboarding Routes – First-Run Setup Sequenz
"""
from flask import Blueprint, redirect, url_for
import os
import json
from routes.helpers import success_response, handle_route_error
from utils.logger import log
from routes.react_frontend import serve_react_app

onboarding_bp = Blueprint('onboarding', __name__)

ONBOARDING_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings', 'onboarding.json')


def is_onboarding_complete():
    """Prüft ob das Onboarding bereits abgeschlossen wurde."""
    try:
        if os.path.exists(ONBOARDING_FILE):
            with open(ONBOARDING_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('completed', False)
    except (json.JSONDecodeError, OSError):
        pass
    return False


@onboarding_bp.route('/onboarding')
def onboarding():
    """Zeigt die Onboarding-Seite an (React SPA)."""
    return serve_react_app()


@onboarding_bp.route('/api/onboarding/complete', methods=['POST'])
@handle_route_error('complete_onboarding')
def complete_onboarding():
    """Markiert das Onboarding als abgeschlossen."""
    try:
        os.makedirs(os.path.dirname(ONBOARDING_FILE), exist_ok=True)
        with open(ONBOARDING_FILE, 'w', encoding='utf-8') as f:
            json.dump({'completed': True, 'disclaimer_accepted': False}, f, indent=2)
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
        data = {}
        if os.path.exists(ONBOARDING_FILE):
            with open(ONBOARDING_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        data['disclaimer_accepted'] = True
        os.makedirs(os.path.dirname(ONBOARDING_FILE), exist_ok=True)
        with open(ONBOARDING_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
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
    disclaimer_accepted = False
    try:
        if os.path.exists(ONBOARDING_FILE):
            with open(ONBOARDING_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            disclaimer_accepted = data.get('disclaimer_accepted', False)
    except (json.JSONDecodeError, OSError):
        pass
    return success_response(completed=is_onboarding_complete(), disclaimer_accepted=disclaimer_accepted)
