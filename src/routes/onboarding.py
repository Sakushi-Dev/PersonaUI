"""
Onboarding Routes - First-Run Setup Sequenz
"""
from flask import Blueprint, render_template, redirect, url_for
import os
import json
from routes.helpers import success_response, handle_route_error
from utils.logger import log

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
    """Zeigt die Onboarding-Seite an."""
    if is_onboarding_complete():
        return redirect(url_for('main.index'))
    return render_template('onboarding.html')


@onboarding_bp.route('/api/onboarding/complete', methods=['POST'])
@handle_route_error('complete_onboarding')
def complete_onboarding():
    """Markiert das Onboarding als abgeschlossen."""
    try:
        os.makedirs(os.path.dirname(ONBOARDING_FILE), exist_ok=True)
        with open(ONBOARDING_FILE, 'w', encoding='utf-8') as f:
            json.dump({'completed': True}, f, indent=2)
        log.info("Onboarding abgeschlossen.")
        return success_response()
    except Exception as e:
        log.error("Fehler beim Markieren des Onboarding: %s", e)
        return success_response()  # Trotzdem OK, damit Redirect funktioniert
