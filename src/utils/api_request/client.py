"""
Zentraler API-Client für Anthropic.

Einziger Zugang zur Anthropic API.
Verarbeitet sowohl Stream- als auch Non-Stream-Requests
über eine einheitliche Konfiguration (RequestConfig).
"""

import os
import anthropic
from typing import Generator

from .types import RequestConfig, ApiResponse, StreamEvent
from .response_cleaner import clean_api_response
from ..settings_defaults import get_api_model_default
from ..logger import log


class ApiClient:
    """
    Einziger Zugang zur Anthropic API.
    Verarbeitet sowohl Stream- als auch Non-Stream-Requests
    über eine einheitliche Konfiguration (RequestConfig).
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialisiert/reinitialisiert den Anthropic-Client"""
        if self.api_key and self.api_key.strip():
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                log.info("ApiClient erfolgreich initialisiert")
            except Exception as e:
                log.error("Fehler beim Initialisieren des ApiClient: %s", e)
                self.client = None
        else:
            log.warning("Kein API-Key konfiguriert. Bitte in den Einstellungen setzen.")
            self.client = None

    def update_api_key(self, api_key: str) -> bool:
        """
        API-Key aktualisieren und Client neu initialisieren.

        Args:
            api_key: Der neue Anthropic API Key

        Returns:
            True bei Erfolg, False bei Fehler
        """
        if not api_key or not api_key.strip():
            log.error("Leerer API-Key")
            return False

        try:
            self.api_key = api_key.strip()
            self.client = anthropic.Anthropic(api_key=self.api_key)
            log.info("ApiClient erfolgreich aktualisiert")
            return True
        except Exception as e:
            log.error("Fehler beim Aktualisieren des ApiClient: %s", e)
            self.client = None
            return False

    @property
    def is_ready(self) -> bool:
        """Prüft ob Client einsatzbereit ist"""
        return self.client is not None

    def _resolve_model(self, model: str = None) -> str:
        """Löst das Modell auf: explizit > default"""
        return model or get_api_model_default()

    def _prepare_messages(self, config: RequestConfig) -> list:
        """
        Bereitet die Messages für den API-Call vor.
        Hängt ggf. den Prefill als letzte Assistant-Message an.
        """
        messages = list(config.messages)
        if config.prefill:
            messages.append({'role': 'assistant', 'content': config.prefill})
        return messages

    def request(self, config: RequestConfig) -> ApiResponse:
        """
        Synchroner API-Request. Verwendet für:
        - Afterthought-Decision
        - Memory-Summary
        - Spec-Autofill
        - Session-Title
        - Test-Requests

        Args:
            config: RequestConfig mit allen Parametern

        Returns:
            ApiResponse mit content, usage, error
        """
        if not self.is_ready:
            return ApiResponse(
                success=False,
                error='ApiClient nicht initialisiert – kein API-Key konfiguriert'
            )

        model = self._resolve_model(config.model)
        messages = self._prepare_messages(config)

        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                system=config.system_prompt,
                messages=messages
            )

            content = response.content[0].text.strip() if response.content else ''
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    'input_tokens': getattr(response.usage, 'input_tokens', 0) or 0,
                    'output_tokens': getattr(response.usage, 'output_tokens', 0) or 0
                }

            return ApiResponse(
                success=True,
                content=content,
                usage=usage,
                raw_response=response,
                stop_reason=getattr(response, 'stop_reason', None)
            )

        except anthropic.APIError as e:
            error_str = str(e)
            log.error("API-Fehler bei %s: %s", config.request_type, e)
            if 'credit balance' in error_str.lower():
                return ApiResponse(success=False, error='credit_balance_exhausted')
            return ApiResponse(success=False, error=error_str)

        except Exception as e:
            log.error("Unerwarteter Fehler bei %s: %s", config.request_type, e)
            return ApiResponse(success=False, error=str(e))

    def stream(self, config: RequestConfig) -> Generator[StreamEvent, None, None]:
        """
        Streaming API-Request (SSE). Verwendet für:
        - Chat
        - Afterthought-Followup

        Args:
            config: RequestConfig mit allen Parametern

        Yields:
            StreamEvent('chunk', text)
            StreamEvent('done', {'response': str, 'stats': dict})
            StreamEvent('error', error_message)
        """
        if not self.is_ready:
            yield StreamEvent('error', 'ApiClient nicht initialisiert – kein API-Key konfiguriert')
            return

        model = self._resolve_model(config.model)
        messages = self._prepare_messages(config)

        try:
            full_text = ""
            output_tokens = 0
            api_input_tokens = 0

            with self.client.messages.stream(
                model=model,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                system=config.system_prompt,
                messages=messages
            ) as stream_ctx:
                for text in stream_ctx.text_stream:
                    full_text += text
                    yield StreamEvent('chunk', text)

                # Final Message nach Stream-Ende holen
                final_message = stream_ctx.get_final_message()
                if hasattr(final_message, 'usage') and final_message.usage:
                    output_tokens = getattr(final_message.usage, 'output_tokens', 0) or 0
                    api_input_tokens = getattr(final_message.usage, 'input_tokens', 0) or 0
                    log.info("API Usage - Input: %d, Output: %d", api_input_tokens, output_tokens)

            # Bereinige die vollständige Antwort
            cleaned_response = clean_api_response(full_text)

            yield StreamEvent('done', {
                'response': cleaned_response,
                'raw_response': full_text,
                'api_input_tokens': api_input_tokens,
                'output_tokens': output_tokens
            })

        except anthropic.APIError as e:
            error_str = str(e)
            log.error("API Stream Fehler bei %s: %s", config.request_type, e)
            if 'credit balance' in error_str.lower():
                yield StreamEvent('error', 'credit_balance_exhausted')
            else:
                yield StreamEvent('error', error_str)

        except Exception as e:
            error_str = str(e)
            log.error("Unerwarteter Stream Fehler bei %s: %s", config.request_type, e)
            if 'credit balance' in error_str.lower():
                yield StreamEvent('error', 'credit_balance_exhausted')
            else:
                yield StreamEvent('error', error_str)
