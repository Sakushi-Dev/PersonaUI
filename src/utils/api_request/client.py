"""
Zentraler API-Client für Anthropic.

Einziger Zugang zur Anthropic API.
Verarbeitet sowohl Stream- als auch Non-Stream-Requests
über eine einheitliche Konfiguration (RequestConfig).
"""

import os
import anthropic
from typing import Generator, Callable, Tuple

from .types import RequestConfig, ApiResponse, StreamEvent
from .response_cleaner import clean_api_response
from ..settings_defaults import get_api_model_default
from ..logger import log


# Typ-Alias für den Tool-Executor Callback
# (tool_name, tool_input) → (success, result_text)
ToolExecutor = Callable[[str, dict], Tuple[bool, str]]

# Sicherheitslimit für Tool-Call Rounds
MAX_TOOL_ROUNDS = 10


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

            # Clean the complete response
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

    def tool_request(
        self,
        config: RequestConfig,
        executor: ToolExecutor
    ) -> ApiResponse:
        """
        API-Request mit Tool-Use Loop. Verwendet für:
        - Cortex-Updates (Dateien lesen/schreiben via tool_use)

        Der Loop läuft so lange, bis die API mit stop_reason='end_turn'
        antwortet oder MAX_TOOL_ROUNDS erreicht ist.

        Args:
            config: RequestConfig mit tools=[...] und allen Parametern
            executor: Callback (tool_name, tool_input) → (success, result_text)
                      Führt die tatsächliche Tool-Logik aus

        Returns:
            ApiResponse mit:
                - content: Finaler Text der KI (nach allen Tool-Calls)
                - tool_results: Liste aller ausgeführten Tool-Calls mit Ergebnissen
                - usage: Kumulierte Token-Usage über alle Rounds
                - stop_reason: 'end_turn', 'max_tokens', oder 'max_tool_rounds'
        """
        if not self.is_ready:
            return ApiResponse(
                success=False,
                error='ApiClient nicht initialisiert – kein API-Key konfiguriert'
            )

        if not config.tools:
            return ApiResponse(
                success=False,
                error='tool_request() benötigt config.tools – keine Tool-Definitionen angegeben'
            )

        model = self._resolve_model(config.model)
        messages = self._prepare_messages(config)
        all_tool_results = []
        total_input_tokens = 0
        total_output_tokens = 0

        try:
            for round_num in range(1, MAX_TOOL_ROUNDS + 1):
                log.info(
                    "Tool-Request Round %d/%d für %s",
                    round_num, MAX_TOOL_ROUNDS, config.request_type
                )

                # ── API-Call ─────────────────────────────────────────
                response = self.client.messages.create(
                    model=model,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    system=config.system_prompt,
                    tools=config.tools,
                    messages=messages
                )

                # ── Usage akkumulieren ───────────────────────────────
                if hasattr(response, 'usage') and response.usage:
                    total_input_tokens += getattr(response.usage, 'input_tokens', 0) or 0
                    total_output_tokens += getattr(response.usage, 'output_tokens', 0) or 0

                # ── Abbruch bei end_turn oder max_tokens ─────────────
                if response.stop_reason != "tool_use":
                    final_text = self._extract_text_from_content(response.content)
                    log.info(
                        "Tool-Request abgeschlossen nach %d Rounds (stop_reason=%s)",
                        round_num, response.stop_reason
                    )
                    return ApiResponse(
                        success=True,
                        content=final_text,
                        usage={
                            'input_tokens': total_input_tokens,
                            'output_tokens': total_output_tokens
                        },
                        raw_response=response,
                        stop_reason=response.stop_reason,
                        tool_results=all_tool_results if all_tool_results else None
                    )

                # ── Tool-Calls verarbeiten ───────────────────────────
                # Assistant-Antwort (mit ToolUseBlocks) an Messages anhängen
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # Alle ToolUseBlocks extrahieren und ausführen
                tool_result_contents = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tool_input = block.input
                    tool_use_id = block.id

                    log.info(
                        "Tool-Call: %s(input=%s) [id=%s]",
                        tool_name, tool_input, tool_use_id
                    )

                    # Tool ausführen via Executor-Callback
                    try:
                        success, result_text = executor(tool_name, tool_input)
                    except Exception as exec_err:
                        log.error("Tool-Executor Fehler bei %s: %s", tool_name, exec_err)
                        success = False
                        result_text = f"Fehler bei Tool-Ausführung: {exec_err}"

                    # Ergebnis protokollieren
                    tool_record = {
                        'round': round_num,
                        'tool_name': tool_name,
                        'tool_input': tool_input,
                        'tool_use_id': tool_use_id,
                        'success': success,
                        'result': result_text
                    }
                    all_tool_results.append(tool_record)

                    # tool_result für API-Antwort aufbauen
                    tool_result_contents.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result_text,
                        **({"is_error": True} if not success else {})
                    })

                    log.info(
                        "Tool-Result: %s → success=%s, result=%s",
                        tool_name, success,
                        result_text[:100] + '...' if len(result_text) > 100 else result_text
                    )

                # Tool-Results als user-Message anhängen
                messages.append({
                    "role": "user",
                    "content": tool_result_contents
                })

            # ── MAX_TOOL_ROUNDS erreicht ─────────────────────────────
            log.warning(
                "Tool-Request für %s nach %d Rounds abgebrochen (Sicherheitslimit)",
                config.request_type, MAX_TOOL_ROUNDS
            )
            return ApiResponse(
                success=True,
                content=self._extract_text_from_content(response.content),
                usage={
                    'input_tokens': total_input_tokens,
                    'output_tokens': total_output_tokens
                },
                raw_response=response,
                stop_reason='max_tool_rounds',
                tool_results=all_tool_results if all_tool_results else None
            )

        except anthropic.APIError as e:
            error_str = str(e)
            log.error("API-Fehler bei tool_request %s: %s", config.request_type, e)
            if 'credit balance' in error_str.lower():
                return ApiResponse(success=False, error='credit_balance_exhausted')
            return ApiResponse(success=False, error=error_str)

        except Exception as e:
            log.error("Unerwarteter Fehler bei tool_request %s: %s", config.request_type, e)
            return ApiResponse(success=False, error=str(e))

    @staticmethod
    def _extract_text_from_content(content) -> str:
        """
        Extrahiert Text aus dem content-Array einer Anthropic Response.
        Ignoriert ToolUseBlock-Objekte, sammelt nur TextBlock.text.

        Args:
            content: Liste von ContentBlock-Objekten (TextBlock, ToolUseBlock, ...)

        Returns:
            Zusammengefügter Text aller TextBlocks
        """
        if not content:
            return ''

        text_parts = []
        for block in content:
            if hasattr(block, 'text'):
                text_parts.append(block.text)

        return '\n'.join(text_parts).strip()
