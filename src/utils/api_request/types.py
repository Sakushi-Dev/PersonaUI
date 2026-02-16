"""
Typen und Konfiguration für API-Requests.

Zentrale Dataclasses für einheitliche Request-Konfiguration und Response-Struktur.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class RequestConfig:
    """Konfiguration für einen API-Request"""
    system_prompt: str
    messages: List[Dict[str, str]]
    model: Optional[str] = None           # None → Default aus settings
    max_tokens: int = 500
    temperature: float = 0.7
    stream: bool = False                  # True only for chat + afterthought followup
    prefill: Optional[str] = None         # Appended as last assistant message
    request_type: str = 'generic'         # 'chat', 'afterthought_decision', 'afterthought_followup',
                                          # 'memory_summary', 'spec_autofill', 'session_title', 'test'


@dataclass
class ApiResponse:
    """Einheitliche Response-Struktur für Non-Stream Requests"""
    success: bool
    content: str = ''
    error: Optional[str] = None
    usage: Optional[Dict[str, int]] = None  # {'input_tokens': x, 'output_tokens': y}
    raw_response: Any = None                # Originale Anthropic-Response (optional)
    stop_reason: Optional[str] = None


@dataclass
class StreamEvent:
    """Event innerhalb eines Streams"""
    event_type: str    # 'chunk', 'done', 'error'
    data: Any          # str (chunk), dict (done), str (error)
