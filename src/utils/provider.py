"""
Zentraler Zugriff auf Shared-Instanzen.
Ersetzt das set_claude_api() Pattern in 4 Route-Modulen.

Usage in app.py:
    from utils.provider import init_services
    init_services()

Usage in routes:
    from utils.provider import get_api_client, get_chat_service
"""

from typing import Optional


_api_client = None
_chat_service = None
_prompt_engine = None


def init_services(api_key: str = None):
    """
    Einmal in app.py aufrufen – initialisiert alles.

    Args:
        api_key: Optionaler API-Key (sonst aus ENV)
    """
    global _api_client, _chat_service
    from .api_request import ApiClient
    from .services import ChatService

    _api_client = ApiClient(api_key=api_key)
    _chat_service = ChatService(_api_client)


def get_api_client():
    """Gibt den zentralen ApiClient zurück"""
    if _api_client is None:
        raise RuntimeError("ApiClient nicht initialisiert – init_services() in app.py aufrufen")
    return _api_client


def get_chat_service():
    """Gibt den ChatService zurück"""
    if _chat_service is None:
        raise RuntimeError("ChatService nicht initialisiert – init_services() in app.py aufrufen")
    return _chat_service


def get_prompt_engine():
    """Gibt die Singleton PromptEngine Instanz zurück."""
    global _prompt_engine
    if _prompt_engine is None:
        try:
            from .prompt_engine import PromptEngine
            _prompt_engine = PromptEngine()
        except Exception as e:
            from .logger import log
            log.warning("PromptEngine konnte nicht initialisiert werden: %s", e)
            return None
    return _prompt_engine


def reset_prompt_engine():
    """Setzt die Engine zurück (für Tests oder Reload)."""
    global _prompt_engine
    _prompt_engine = None
