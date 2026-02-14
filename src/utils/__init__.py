"""
Utils Package für die Simple Chat Anwendung
"""

from .database import (
    init_all_dbs,
    get_chat_history,
    get_conversation_context,
    save_message,
    clear_chat_history,
    get_message_count
)

from .api_request import ApiClient

from .config import (
    load_character,
    load_char_config,
    load_char_profile,
    save_char_config,
    build_character_description,
    build_character_description_from_config,
    get_available_char_options,
    load_avatar,
    save_avatar_config
)

__all__ = [
    'init_all_dbs',
    'get_chat_history',
    'get_conversation_context',
    'save_message',
    'clear_chat_history',
    'get_message_count',
    'ApiClient',
    'load_character',
    'load_char_config',
    'load_char_profile',
    'save_char_config',
    'build_character_description',
    'build_character_description_from_config',
    'get_available_char_options',
    'load_avatar',
    'save_avatar_config'
]