"""Editor API Bridge – Python <-> JavaScript Kommunikation.

Alle Methoden werden über ``window.pywebview.api.*`` aus JavaScript
aufgerufen.  Komplexe Eingaben kommen als JSON-Strings, Rückgaben sind
Dicts/Listen (pywebview serialisiert automatisch).
"""

import re
import json
from typing import Dict, List
from utils.prompt_engine import PromptEngine
from utils.logger import log

_PH_PATTERN = re.compile(r'\{\{(\w+)\}\}')


class EditorApi:
    """Python API-Bridge für den WebUI Editor."""

    def __init__(self):
        self.engine = PromptEngine()
        log.info("EditorApi initialisiert")

    # ===== Prompt-Operationen ================================================

    def get_all_prompts(self) -> dict:
        """Alle Prompts mit Metadata + Varianten-Info für die Sidebar."""
        try:
            prompts = self.engine.get_all_prompts()
            result = {}
            for prompt_id, meta in prompts.items():
                prompt_data = self.engine.get_prompt(prompt_id)
                variants = []
                if prompt_data and prompt_data.get('content'):
                    variants = list(
                        prompt_data['content'].get('variants', {}).keys()
                    )
                result[prompt_id] = {**meta, 'variants': variants}
            return {"status": "ok", "prompts": result}
        except Exception as e:
            log.error("get_all_prompts fehlgeschlagen: %s", e)
            return {"status": "error", "message": str(e)}

    def get_prompt(self, prompt_id: str) -> dict:
        """Ein einzelner Prompt mit Content + Metadata."""
        try:
            prompt = self.engine.get_prompt(prompt_id)
            if not prompt:
                return {
                    "status": "error",
                    "message": f"Prompt '{prompt_id}' nicht gefunden",
                }
            return {"status": "ok", "prompt": prompt}
        except Exception as e:
            log.error("get_prompt fehlgeschlagen: %s", e)
            return {"status": "error", "message": str(e)}

    def save_prompt(self, prompt_id: str, data_json: str) -> dict:
        """Speichert Prompt-Änderungen.  ``data_json`` ist ein JSON-String."""
        try:
            data = json.loads(data_json)
            success = self.engine.save_prompt(prompt_id, data)
            if success:
                log.info("Prompt '%s' gespeichert", prompt_id)
                return {"status": "ok"}
            return {"status": "error", "message": "Speichern fehlgeschlagen"}
        except Exception as e:
            log.error("save_prompt fehlgeschlagen: %s", e)
            return {"status": "error", "message": str(e)}

    def create_prompt(self, data_json: str) -> dict:
        """Erstellt einen neuen Prompt."""
        try:
            data = json.loads(data_json)
            new_id = self.engine.create_prompt(data)
            if new_id:
                log.info("Prompt '%s' erstellt", new_id)
                return {"status": "ok", "id": new_id}
            return {"status": "error", "message": "Erstellen fehlgeschlagen"}
        except Exception as e:
            log.error("create_prompt fehlgeschlagen: %s", e)
            return {"status": "error", "message": str(e)}

    def duplicate_prompt(self, source_id: str, new_id: str, new_name: str) -> dict:
        """Erstellt eine Kopie eines bestehenden Prompts."""
        try:
            source = self.engine.get_prompt(source_id)
            if not source:
                return {"status": "error", "message": f"Quell-Prompt '{source_id}' nicht gefunden"}

            data = {
                'id': new_id,
                'meta': {**source['meta'], 'name': new_name, 'order': source['meta'].get('order', 0) + 10},
                'content': source.get('content', {'variants': {'default': {'content': ''}}})
            }

            result_id = self.engine.create_prompt(data)
            if result_id:
                log.info("Prompt '%s' dupliziert als '%s'", source_id, new_id)
                return {"status": "ok", "id": result_id}
            return {"status": "error", "message": "Duplizieren fehlgeschlagen"}
        except Exception as e:
            log.error("duplicate_prompt fehlgeschlagen: %s", e)
            return {"status": "error", "message": str(e)}

    def delete_prompt(self, prompt_id: str) -> dict:
        """Löscht einen Prompt. System-Prompts können nicht gelöscht werden."""
        try:
            # Check if it's a system prompt (can only be disabled)
            if not self.engine._is_user_prompt(prompt_id):
                return {"status": "error",
                        "message": "System-Prompts können nicht gelöscht werden. "
                                   "Stattdessen deaktivieren."}
            success = self.engine.delete_prompt(prompt_id)
            if success:
                log.info("Prompt '%s' gelöscht", prompt_id)
                return {"status": "ok"}
            return {"status": "error", "message": "Löschen fehlgeschlagen"}
        except Exception as e:
            log.error("delete_prompt fehlgeschlagen: %s", e)
            return {"status": "error", "message": str(e)}

    def toggle_prompt(self, prompt_id: str, enabled: bool) -> dict:
        """Aktiviert/Deaktiviert einen Prompt."""
        try:
            success = self.engine.toggle_prompt(prompt_id, enabled)
            if success:
                state = "aktiviert" if enabled else "deaktiviert"
                log.info("Prompt '%s' %s", prompt_id, state)
                return {"status": "ok"}
            return {"status": "error", "message": "Toggle fehlgeschlagen"}
        except Exception as e:
            log.error("toggle_prompt fehlgeschlagen: %s", e)
            return {"status": "error", "message": str(e)}

    def reorder_prompts(self, new_order_json: str) -> dict:
        """Aktualisiert Reihenfolge.  ``new_order_json`` = ``{id: order}``."""
        try:
            order_data = json.loads(new_order_json)
            success = self.engine.reorder_prompts(order_data)
            if success:
                return {"status": "ok"}
            return {"status": "error", "message": "Reorder fehlgeschlagen"}
        except Exception as e:
            log.error("reorder_prompts fehlgeschlagen: %s", e)
            return {"status": "error", "message": str(e)}

    def search_prompts(self, query: str) -> dict:
        """Durchsucht alle Prompt-Namen und Inhalte."""
        try:
            query_lower = query.lower()
            results = []
            prompts = self.engine.get_all_prompts()
            for prompt_id, meta in prompts.items():
                # Name / ID / Description durchsuchen
                name_match = query_lower in (meta.get('name', '') + ' ' + prompt_id + ' ' + meta.get('description', '')).lower()
                # Content durchsuchen
                content_match = False
                prompt_data = self.engine.get_prompt(prompt_id)
                if prompt_data:
                    for variant_data in prompt_data.get('content', {}).get('variants', {}).values():
                        text = variant_data.get('content', '')
                        if text and query_lower in text.lower():
                            content_match = True
                            break
                if name_match or content_match:
                    results.append({
                        'id': prompt_id,
                        'name': meta.get('name', prompt_id),
                        'category': meta.get('category', 'custom'),
                        'match_type': 'name' if name_match else 'content'
                    })
            return {"status": "ok", "results": results}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ===== Placeholder-Operationen ===========================================

    def get_all_placeholders(self) -> dict:
        """Alle registrierten Placeholder."""
        try:
            placeholders = self.engine.get_all_placeholders()
            return {"status": "ok", "placeholders": placeholders}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_placeholder_values(self, variant: str = 'default') -> dict:
        """Alle aufgelösten Placeholder-Werte (Cache wird vorher geleert für aktuelle Daten)."""
        try:
            self.engine.invalidate_cache()
            values = self.engine.get_current_values(variant)
            return {"status": "ok", "values": values}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_placeholder_usages(self) -> dict:
        """Für jeden Placeholder: in welchen Prompts wird er verwendet?"""
        try:
            registry = self.engine.get_all_placeholders()
            prompts = self.engine.get_all_prompts()

            # Sammle alle Placeholder-Verwendungen aus Content
            usage_map: Dict[str, List[str]] = {key: [] for key in registry}
            all_used_keys: set = set()

            for prompt_id, meta in prompts.items():
                prompt_data = self.engine.get_prompt(prompt_id)
                if not prompt_data:
                    continue
                for variant_data in prompt_data.get('content', {}).get('variants', {}).values():
                    text = variant_data.get('content', '')
                    if not text:
                        continue
                    for match in _PH_PATTERN.finditer(text):
                        key = match.group(1)
                        all_used_keys.add(key)
                        if key not in usage_map:
                            usage_map[key] = []
                        if prompt_id not in usage_map[key]:
                            usage_map[key].append(prompt_id)

            # Orphaned: in Prompts verwendet, aber nicht in Registry
            orphaned = {k: usage_map[k] for k in all_used_keys if k not in registry}

            # Unused: in Registry, aber nirgends verwendet
            unused = [k for k in registry if not usage_map.get(k)]

            return {
                "status": "ok",
                "usages": usage_map,
                "orphaned": orphaned,
                "unused": unused,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def update_placeholders_used(self, prompt_id: str, placeholders_json: str) -> dict:
        """Aktualisiert die placeholders_used-Liste eines Prompts."""
        try:
            placeholders = json.loads(placeholders_json)
            success = self.engine.update_placeholders_used(prompt_id, placeholders)
            if success:
                log.info("placeholders_used für '%s' aktualisiert: %s", prompt_id, placeholders)
                return {"status": "ok"}
            return {"status": "error", "message": "Update fehlgeschlagen"}
        except Exception as e:
            log.error("update_placeholders_used fehlgeschlagen: %s", e)
            return {"status": "error", "message": str(e)}

    def create_placeholder(self, data_json: str) -> dict:
        """Erstellt einen neuen statischen Placeholder."""
        try:
            data = json.loads(data_json)
            key = data.get('key', '').strip()
            if not key:
                return {"status": "error", "message": "Key ist Pflichtfeld"}
            if not re.match(r'^[a-z][a-z0-9_]*$', key):
                return {"status": "error", "message": "Key: nur Kleinbuchstaben, Zahlen und _ erlaubt"}

            success = self.engine.create_placeholder(key, data)
            if success:
                log.info("Placeholder '%s' erstellt", key)
                return {"status": "ok", "key": key}
            return {"status": "error", "message": f"Placeholder '{key}' existiert bereits oder Fehler"}
        except Exception as e:
            log.error("create_placeholder fehlgeschlagen: %s", e)
            return {"status": "error", "message": str(e)}

    def delete_placeholder(self, key: str) -> dict:
        """Löscht einen statischen Placeholder."""
        try:
            success = self.engine.delete_placeholder(key)
            if success:
                log.info("Placeholder '%s' gelöscht", key)
                return {"status": "ok"}
            return {"status": "error", "message": f"Placeholder '{key}' nicht gefunden oder nicht löschbar"}
        except Exception as e:
            log.error("delete_placeholder fehlgeschlagen: %s", e)
            return {"status": "error", "message": str(e)}

    # ===== Reset =============================================================

    def reset_prompt_to_default(self, prompt_id: str) -> dict:
        """Setzt einen Prompt auf Factory-Default zurück."""
        try:
            success = self.engine.reset_prompt_to_default(prompt_id)
            if success:
                log.info("Prompt '%s' auf Default zurückgesetzt", prompt_id)
                return {"status": "ok"}
            return {"status": "error", "message": "Reset fehlgeschlagen – kein Default vorhanden"}
        except Exception as e:
            log.error("reset_prompt_to_default fehlgeschlagen: %s", e)
            return {"status": "error", "message": str(e)}

    # ===== Preview ===========================================================

    def preview_prompt(self, prompt_id: str, variant: str = 'default') -> dict:
        """Einzelnen Prompt aufgelöst anzeigen."""
        try:
            self.engine.invalidate_cache()
            resolved = self.engine.resolve_prompt(prompt_id, variant)
            return {"status": "ok", "content": resolved or ''}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def preview_full_system(self, variant: str = 'default') -> dict:
        """Vollständigen System-Prompt als Preview."""
        try:
            self.engine.invalidate_cache()
            system_prompt = self.engine.build_system_prompt(variant)
            prefill = self.engine.build_prefill(variant)
            first_assistant = self.engine.get_first_assistant_content(variant)
            append = self.engine.get_system_prompt_append(variant)

            return {
                "status": "ok",
                "system_prompt": system_prompt,
                "system_prompt_append": append,
                "prefill": prefill,
                "first_assistant": first_assistant,
                "system_tokens_est": len(system_prompt) // 4,
                "prefill_tokens_est": len(prefill) // 4 if prefill else 0,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def preview_category(self, category: str, variant: str = 'default') -> dict:
        """Preview für eine bestimmte Kategorie (chat, afterthought, summary, spec_autofill)."""
        try:
            self.engine.invalidate_cache()
            blocks = []
            total_tokens = 0

            for prompt_id, meta in sorted(
                self.engine.get_all_prompts().items(),
                key=lambda x: x[1].get('order', 9999)
            ):
                if meta.get('category') != category:
                    continue
                if not meta.get('enabled', True):
                    continue

                prompt_type = meta.get('type', 'text')

                if prompt_type == 'multi_turn':
                    # Multi-turn: Messages als Content-String formatieren
                    resolved = self._resolve_multi_turn_content(prompt_id, variant)
                else:
                    resolved = ''
                    try:
                        resolved = self.engine.resolve_prompt(prompt_id, variant) or ''
                    except Exception:
                        pass

                tokens = len(resolved) // 4 if resolved else 0
                total_tokens += tokens
                blocks.append({
                    'id': prompt_id,
                    'name': meta.get('name', prompt_id),
                    'target': meta.get('target', ''),
                    'position': meta.get('position', ''),
                    'type': prompt_type,
                    'content': resolved,
                    'tokens_est': tokens,
                })

            return {
                "status": "ok",
                "category": category,
                "blocks": blocks,
                "total_tokens_est": total_tokens,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def preview_chat(self, variant: str = 'default') -> dict:
        """Preview für den Chat-Request: alle Prompts die im Chat an die API gehen.

        Gibt Blöcke zurück, aufgeteilt nach 'section':
        - 'system': target=system_prompt (System-Prompt)
        - 'message': target=message oder target=prefill (Messages/Prefill)
        """
        try:
            self.engine.invalidate_cache()
            chat_categories = {'system', 'persona', 'context', 'prefill', 'dialog_injection'}
            system_blocks = []
            message_blocks = []
            total_tokens = 0

            for prompt_id, meta in sorted(
                self.engine.get_all_prompts().items(),
                key=lambda x: x[1].get('order', 9999)
            ):
                if meta.get('category') not in chat_categories:
                    continue
                if not meta.get('enabled', True):
                    continue

                prompt_type = meta.get('type', 'text')
                target = meta.get('target', 'system_prompt')

                if prompt_type == 'multi_turn':
                    resolved = self._resolve_multi_turn_content(prompt_id, variant)
                else:
                    resolved = ''
                    try:
                        resolved = self.engine.resolve_prompt(prompt_id, variant) or ''
                    except Exception:
                        pass

                tokens = len(resolved) // 4 if resolved else 0
                total_tokens += tokens
                block = {
                    'id': prompt_id,
                    'name': meta.get('name', prompt_id),
                    'category': meta.get('category', ''),
                    'target': target,
                    'position': meta.get('position', ''),
                    'type': prompt_type,
                    'content': resolved,
                    'tokens_est': tokens,
                }

                if target == 'system_prompt':
                    block['section'] = 'system'
                    system_blocks.append(block)
                else:
                    block['section'] = 'message'
                    message_blocks.append(block)

            return {
                "status": "ok",
                "system_blocks": system_blocks,
                "message_blocks": message_blocks,
                "total_tokens_est": total_tokens,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_compositor_data(self, variant: str = 'default') -> dict:
        """Aufgeschlüsselte Compositor-Daten: jeder Prompt-Block einzeln.

        Gruppiert nach API-Request-Typ (chat, afterthought, summary, spec_autofill, utility).
        Innerhalb jeder Gruppe: System- und Message-Blöcke getrennt.
        """
        try:
            self.engine.invalidate_cache()
            prompts = self.engine.get_all_prompts()
            blocks = []

            # Mapping: category → request_type
            CATEGORY_TO_REQUEST = {
                'system': 'chat',
                'persona': 'chat',
                'context': 'chat',
                'prefill': 'chat',
                'dialog_injection': 'chat',
                'afterthought': 'afterthought',
                'summary': 'summary',
                'spec_autofill': 'spec_autofill',
                'utility': 'utility',
                'cortex': 'cortex',
                'custom': 'chat',
            }

            for prompt_id, meta in sorted(prompts.items(), key=lambda x: x[1].get('order', 9999)):
                prompt_type = meta.get('type', 'text')
                target = meta.get('target', '')

                if prompt_type == 'multi_turn':
                    resolved = self._resolve_multi_turn_content(prompt_id, variant)
                else:
                    resolved = ''
                    try:
                        resolved = self.engine.resolve_prompt(prompt_id, variant) or ''
                    except Exception:
                        pass

                category = meta.get('category', 'custom')
                request_type = CATEGORY_TO_REQUEST.get(category, 'chat')

                # Section: system vs message
                section = 'system' if target == 'system_prompt' else 'message'

                blocks.append({
                    'id': prompt_id,
                    'name': meta.get('name', prompt_id),
                    'category': category,
                    'target': target,
                    'position': meta.get('position', ''),
                    'order': meta.get('order', 9999),
                    'enabled': meta.get('enabled', True),
                    'variant_condition': meta.get('variant_condition'),
                    'type': prompt_type,
                    'request_type': request_type,
                    'section': section,
                    'content': resolved,
                    'tokens_est': len(resolved) // 4 if resolved else 0,
                })

            return {"status": "ok", "blocks": blocks, "variant": variant}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ===== Utilities =========================================================

    def _resolve_multi_turn_content(self, prompt_id: str, variant: str) -> str:
        """Löst multi_turn Prompts auf und gibt einen lesbaren String zurück."""
        try:
            prompt_data = self.engine.get_prompt(prompt_id)
            if not prompt_data:
                return ''

            meta = prompt_data.get('meta', {})
            content_data = prompt_data.get('content', {})

            # Check variant_condition
            variant_condition = meta.get('variant_condition')
            if variant_condition and variant_condition != variant:
                return ''

            variants = content_data.get('variants', {})
            variant_data = variants.get(variant) or variants.get('default')
            if not variant_data or 'messages' not in variant_data:
                return ''

            messages = variant_data['messages']
            parts = []
            for msg in messages:
                role = msg.get('role', 'user').upper()
                content = msg.get('content', '')
                parts.append(f"[{role}]: {content}")
            return '\n\n'.join(parts)
        except Exception:
            return ''

    def validate_all(self) -> dict:
        """Validiert alle Prompts und Placeholder."""
        try:
            result = self.engine.validate_all()
            return {
                "status": "ok",
                "errors": result.get('errors', []),
                "warnings": result.get('warnings', []),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def reload(self) -> dict:
        """Lädt alle JSON-Dateien neu von Disk."""
        try:
            self.engine.reload()
            return {"status": "ok", "message": "Erfolgreich neu geladen"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_engine_info(self) -> dict:
        """Grundlegende Engine-Informationen für die Status-Bar."""
        try:
            prompts = self.engine.get_all_prompts()
            placeholders = self.engine.get_all_placeholders()
            load_errors = self.engine.load_errors
            return {
                "status": "ok",
                "prompt_count": len(prompts),
                "placeholder_count": len(placeholders),
                "load_errors": load_errors,
                "is_loaded": self.engine.is_loaded,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_categories(self) -> dict:
        """Verfügbare Kategorien (abgeleitet aus vorhandenen Prompts)."""
        try:
            prompts = self.engine.get_all_prompts()
            categories = sorted(set(
                meta.get('category', 'unknown')
                for meta in prompts.values()
            ))
            return {"status": "ok", "categories": categories}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_domain_files(self) -> dict:
        """Verfügbare Domain-Dateien."""
        try:
            prompts = self.engine.get_all_prompts()
            domain_files = sorted(set(
                meta.get('domain_file', '')
                for meta in prompts.values()
                if meta.get('domain_file')
            ))
            return {"status": "ok", "domain_files": domain_files}
        except Exception as e:
            return {"status": "error", "message": str(e)}
