"""
Emoji Routes - Emoji usage/favorites persistence (file-based)
"""
from flask import Blueprint, request
import os
import json

from utils.logger import log
from routes.helpers import success_response, error_response, handle_route_error

emoji_bp = Blueprint('emoji', __name__)

EMOJI_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'settings', 'emoji_usage.json'
)


def _load_usage() -> dict:
    """Load emoji usage counts from JSON file."""
    try:
        if os.path.exists(EMOJI_FILE):
            with open(EMOJI_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        log.error("Error loading emoji usage: %s", e)
        return {}


def _save_usage(usage: dict) -> bool:
    """Save emoji usage counts to JSON file."""
    try:
        os.makedirs(os.path.dirname(EMOJI_FILE), exist_ok=True)
        with open(EMOJI_FILE, 'w', encoding='utf-8') as f:
            json.dump(usage, f, ensure_ascii=False)
        return True
    except Exception as e:
        log.error("Error saving emoji usage: %s", e)
        return False


@emoji_bp.route('/api/emoji-usage', methods=['GET'])
@handle_route_error('get_emoji_usage')
def get_emoji_usage():
    """Returns emoji usage counts."""
    usage = _load_usage()
    return success_response(usage=usage)


@emoji_bp.route('/api/emoji-usage', methods=['PUT'])
@handle_route_error('update_emoji_usage')
def update_emoji_usage():
    """
    Increment usage for a single emoji.

    Expects JSON: { "emoji": "😀" }
    Returns: { "success": true, "usage": { ... } }
    """
    data = request.get_json()
    if not data or 'emoji' not in data:
        return error_response('Missing emoji')

    emoji = data['emoji']
    usage = _load_usage()
    usage[emoji] = usage.get(emoji, 0) + 1

    if _save_usage(usage):
        return success_response(usage=usage)
    return error_response('Save failed', 500)
