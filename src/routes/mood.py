"""
Mood API Routes

Endpoints for managing persona mood state and settings.
All endpoints support mood enable/disable via moodEnabled setting.
"""

from flask import Blueprint, jsonify, request
from functools import wraps

from utils.logger import log
from utils.provider import get_mood_service
from utils.settings import _read_setting
from utils.config import get_active_persona_id

mood_bp = Blueprint('mood', __name__)


def handle_route_error(route_name: str):
    """Decorator for consistent error handling in mood routes."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log.error(f"Error in mood route '{route_name}': {e}")
                return jsonify({
                    'error': f'Mood {route_name} failed',
                    'details': str(e)
                }), 500
        return wrapper
    return decorator


def resolve_persona_id() -> str:
    """Get active persona ID using existing config utility."""
    try:
        return get_active_persona_id()
    except Exception as e:
        log.warning(f"Could not resolve persona ID: {e}")
        return 'default'


def check_mood_enabled():
    """Check if mood system is enabled, return appropriate response if disabled."""
    if not _read_setting('moodEnabled', True):
        return jsonify({'enabled': False}), 200
    return None


@mood_bp.route('/mood', methods=['GET'])
@handle_route_error('get_mood')
def get_mood():
    """Get current mood state with decay applied."""
    
    # Check if mood system is enabled
    disabled_response = check_mood_enabled()
    if disabled_response:
        return disabled_response
    
    persona_id = resolve_persona_id()
    mood_service = get_mood_service()
    
    mood_state = mood_service.get_mood(persona_id)
    
    return jsonify({
        'enabled': True,
        'mood': mood_state,
        'persona_id': persona_id
    })


@mood_bp.route('/mood/history', methods=['GET'])
@handle_route_error('get_history')
def get_mood_history():
    """Get mood history for the current persona."""
    
    # Check if mood system is enabled
    disabled_response = check_mood_enabled()
    if disabled_response:
        return disabled_response
    
    persona_id = resolve_persona_id()
    limit = request.args.get('limit', 50, type=int)
    
    # Validate limit
    if limit < 1 or limit > 1000:
        return jsonify({
            'error': 'Invalid limit',
            'details': 'Limit must be between 1 and 1000'
        }), 400
    
    mood_service = get_mood_service()
    history = mood_service.get_history(persona_id, limit)
    
    return jsonify({
        'enabled': True,
        'history': history,
        'persona_id': persona_id,
        'limit': limit
    })


@mood_bp.route('/mood/settings', methods=['POST'])
@handle_route_error('update_settings')
def update_mood_settings():
    """Update mood system settings (sensitivity and decay rate)."""
    
    # Check if mood system is enabled
    disabled_response = check_mood_enabled()
    if disabled_response:
        return disabled_response
    
    data = request.get_json()
    if not data:
        return jsonify({
            'error': 'No JSON data provided'
        }), 400
    
    persona_id = resolve_persona_id()
    mood_service = get_mood_service()
    
    # Validate and extract settings
    sensitivity = data.get('sensitivity')
    decay_rate = data.get('decay_rate')
    
    if sensitivity is not None:
        if not isinstance(sensitivity, (int, float)) or not (0.0 <= sensitivity <= 1.0):
            return jsonify({
                'error': 'Invalid sensitivity',
                'details': 'Sensitivity must be a number between 0.0 and 1.0'
            }), 400
    
    if decay_rate is not None:
        if not isinstance(decay_rate, (int, float)) or decay_rate < 0.0:
            return jsonify({
                'error': 'Invalid decay_rate', 
                'details': 'Decay rate must be a number >= 0.0'
            }), 400
    
    # Update settings
    try:
        mood_service.update_settings(persona_id, sensitivity, decay_rate)
    except ValueError as e:
        return jsonify({
            'error': 'Setting validation failed',
            'details': str(e)
        }), 400
    
    # Return current settings
    from utils.settings import _read_setting
    current_settings = {
        'sensitivity': _read_setting('moodSensitivity', 0.5),
        'decay_rate': _read_setting('moodDecayRate', 0.1),
        'enabled': _read_setting('moodEnabled', True)
    }
    
    return jsonify({
        'enabled': True,
        'settings': current_settings,
        'persona_id': persona_id
    })


@mood_bp.route('/mood/reset', methods=['POST'])
@handle_route_error('reset_mood')
def reset_mood():
    """Reset mood state to baseline values."""
    
    # Check if mood system is enabled
    disabled_response = check_mood_enabled()
    if disabled_response:
        return disabled_response
    
    persona_id = resolve_persona_id()
    mood_service = get_mood_service()
    
    baseline_state = mood_service.reset_mood(persona_id)
    
    return jsonify({
        'enabled': True,
        'mood': baseline_state,
        'persona_id': persona_id,
        'message': 'Mood state reset to baseline'
    })