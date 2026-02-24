"""
Tests for PromptEngine – Phase 1.

Tests:
- PlaceholderResolver (all 3 phases)
- PromptLoader (loading, error handling)
- PromptValidator (schema, cross-references)
- PromptEngine (build_system_prompt, build_prefill, resolve_prompt)
- Migrator (placeholder conversion)
"""

import os
import json
import shutil
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# Test base directory: creates a temporary instructions/ setup
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), '_prompt_engine_fixtures')


# ===== Fixtures =====

@pytest.fixture
def temp_instructions_dir(tmp_path):
    """Creates a temporary instructions/ directory with all JSON files."""
    instructions_dir = tmp_path / 'instructions'
    instructions_dir.mkdir()
    prompts_dir = instructions_dir / 'prompts'
    prompts_dir.mkdir()

    # Manifest
    manifest = {
        "version": "2.0",
        "prompts": {
            "impersonation": {
                "name": "Impersonation",
                "description": "Rollenanweisung",
                "category": "system",
                "type": "text",
                "target": "system_prompt",
                "position": "system_prompt",
                "order": 100,
                "enabled": True,
                "domain_file": "chat.json",
                "tags": ["core"]
            },
            "system_rule": {
                "name": "System-Regeln",
                "description": "Grundregeln",
                "category": "system",
                "type": "text",
                "target": "system_prompt",
                "position": "system_prompt",
                "order": 200,
                "enabled": True,
                "domain_file": "chat.json",
                "tags": ["core"]
            },
            "persona_description": {
                "name": "Persona-Beschreibung",
                "description": "Character-Description",
                "category": "persona",
                "type": "text",
                "target": "system_prompt",
                "position": "system_prompt",
                "order": 300,
                "enabled": True,
                "domain_file": "chat.json",
                "tags": ["persona"]
            },
            "consent_agreement": {
                "name": "Consent Agreement",
                "description": "Nur experimental",
                "category": "system",
                "type": "text",
                "target": "system_prompt",
                "position": "system_prompt",
                "order": 700,
                "enabled": True,
                "variant_condition": "experimental",
                "domain_file": "chat.json",
                "tags": ["experimental"]
            },
            "remember": {
                "name": "Remember",
                "description": "Prefill",
                "category": "prefill",
                "type": "text",
                "target": "prefill",
                "position": "prefill",
                "order": 100,
                "enabled": True,
                "domain_file": "prefill.json",
                "tags": ["prefill"]
            },
            "consent_dialog": {
                "name": "Consent Dialog",
                "description": "Multi-Turn",
                "category": "dialog_injection",
                "type": "multi_turn",
                "target": "message",
                "position": "consent_dialog",
                "order": 100,
                "enabled": True,
                "variant_condition": "experimental",
                "domain_file": "consent_dialog.json",
                "tags": ["experimental"]
            },
            "afterthought_system_note": {
                "name": "Afterthought-Note",
                "description": "System-Hinweis",
                "category": "afterthought",
                "type": "text",
                "target": "system_prompt",
                "position": "system_prompt_append",
                "order": 800,
                "enabled": True,
                "domain_file": "afterthought.json",
                "tags": ["afterthought"]
            }
        }
    }
    meta_dir = prompts_dir / '_meta'
    meta_dir.mkdir()
    (meta_dir / 'prompt_manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # Placeholder registry
    registry = {
        "version": "2.0",
        "placeholders": {
            "char_name": {
                "name": "Persona name",
                "source": "persona_config",
                "source_path": "persona_settings.name",
                "type": "string",
                "default": "Assistant",
                "category": "persona",
                "resolve_phase": "static"
            },
            "user_name": {
                "name": "Benutzername",
                "source": "user_profile",
                "source_path": "user_name",
                "type": "string",
                "default": "User",
                "category": "user",
                "resolve_phase": "static"
            },
            "language": {
                "name": "Sprache",
                "source": "runtime",
                "type": "string",
                "default": "de",
                "category": "system",
                "resolve_phase": "runtime"
            },
            "char_description": {
                "name": "Beschreibung",
                "source": "computed",
                "compute_function": "build_character_description",
                "type": "string",
                "default": "",
                "category": "persona",
                "resolve_phase": "computed"
            },
            "elapsed_time": {
                "name": "Vergangene Zeit",
                "source": "runtime",
                "type": "string",
                "default": "",
                "category": "afterthought",
                "resolve_phase": "runtime"
            }
        }
    }
    (meta_dir / 'placeholder_registry.json').write_text(
        json.dumps(registry, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # Chat Domain
    chat_domain = {
        "impersonation": {
            "variants": {
                "default": {
                    "content": "**IMPERSONATION**\n\nDu bist ein Charakter."
                }
            },
            "placeholders_used": []
        },
        "system_rule": {
            "variants": {
                "default": {
                    "content": "Du bist {{char_name}} und sprichst {{language}}. User: {{user_name}}."
                }
            },
            "placeholders_used": ["char_name", "language", "user_name"]
        },
        "persona_description": {
            "variants": {
                "default": {
                    "content": "PERSONA\n\nName: {{char_name}}\n\n{{char_description}}"
                },
                "experimental": {
                    "content": "EXPERIMENTAL PERSONA\n\nName: {{char_name}}\n\n{{char_description}}\n\nNSFW traits hier."
                }
            },
            "placeholders_used": ["char_name", "char_description"]
        },
        "consent_agreement": {
            "variants": {
                "experimental": {
                    "content": "AGREEMENT: {{user_name}} und {{char_name}} stimmen zu."
                }
            },
            "placeholders_used": ["user_name", "char_name"]
        }
    }
    (prompts_dir / 'chat.json').write_text(
        json.dumps(chat_domain, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # Prefill Domain
    prefill_domain = {
        "remember": {
            "variants": {
                "default": {
                    "content": "Ich bleibe als {{char_name}} in meiner Rolle."
                },
                "experimental": {
                    "content": "Ich bin {{char_name}}. Rolle, 20-200 Wörter."
                }
            },
            "placeholders_used": ["char_name"]
        }
    }
    (prompts_dir / 'prefill.json').write_text(
        json.dumps(prefill_domain, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # Consent Dialog Domain
    consent_domain = {
        "consent_dialog": {
            "variants": {
                "experimental": {
                    "messages": [
                        {"role": "assistant", "content": "Bevor wir starten..."},
                        {"role": "user", "content": "Ja, einverstanden."},
                        {"role": "assistant", "content": "Danke."}
                    ]
                }
            },
            "placeholders_used": []
        }
    }
    (prompts_dir / 'consent_dialog.json').write_text(
        json.dumps(consent_domain, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # Afterthought Domain
    afterthought_domain = {
        "afterthought_system_note": {
            "variants": {
                "default": {
                    "content": "\n\n=== NACHGEDANKE-SYSTEM ==="
                }
            },
            "placeholders_used": []
        }
    }
    (prompts_dir / 'afterthought.json').write_text(
        json.dumps(afterthought_domain, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # Persona config (for static resolution)
    personas_dir = instructions_dir / 'personas' / 'active'
    personas_dir.mkdir(parents=True)
    persona_config = {
        "active_persona_id": "test123",
        "persona_settings": {
            "name": "TestPersona",
            "age": 25,
            "gender": "weiblich",
            "persona": "Fee",
            "core_traits": ["mutig", "neugierig"],
            "knowledge": ["Magie", "Geschichte"],
            "expression": "normal"
        }
    }
    (personas_dir / 'persona_config.json').write_text(
        json.dumps(persona_config, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # user_profile.json (for user_name resolution)
    # The resolver looks relative to instructions_dir parent
    settings_dir = tmp_path / 'settings'
    settings_dir.mkdir(parents=True, exist_ok=True)
    user_profile = {
        "user_name": "TestUser"
    }
    (settings_dir / 'user_profile.json').write_text(
        json.dumps(user_profile, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    return str(instructions_dir)


# ===== PlaceholderResolver Tests =====

class TestPlaceholderResolver:
    """Tests for PlaceholderResolver."""

    def _create_resolver(self, temp_instructions_dir):
        """Helper: Creates PlaceholderResolver with loaded registry."""
        from src.utils.prompt_engine.placeholder_resolver import PlaceholderResolver
        
        registry_path = os.path.join(temp_instructions_dir, 'prompts', '_meta', 'placeholder_registry.json')
        with open(registry_path, 'r', encoding='utf-8') as f:
            registry_data = json.load(f)
        
        return PlaceholderResolver(registry_data, temp_instructions_dir)

    def test_resolve_simple_placeholder(self, temp_instructions_dir):
        """Simple placeholder is resolved."""
        resolver = self._create_resolver(temp_instructions_dir)

        result = resolver.resolve_text(
            "Hallo {{char_name}}, Sprache: {{language}}",
            variant='default',
            runtime_vars={'language': 'de'}
        )

        assert 'TestPersona' in result
        assert 'de' in result
        assert '{{language}}' not in result

    def test_unknown_placeholder_stays(self, temp_instructions_dir):
        """Unknown placeholders remain as {{key}}."""
        resolver = self._create_resolver(temp_instructions_dir)

        result = resolver.resolve_text("Wert: {{unknown_key}}")
        assert '{{unknown_key}}' in result

    def test_static_cache(self, temp_instructions_dir):
        """Static-Werte werden gecached."""
        resolver = self._create_resolver(temp_instructions_dir)

        # First call: cache empty
        assert resolver._static_cache == {}

        resolver.resolve_text("{{char_name}}")

        # Cache should now be populated
        assert 'char_name' in resolver._static_cache
        assert resolver._static_cache['char_name'] == 'TestPersona'

    def test_invalidate_cache(self, temp_instructions_dir):
        """Cache wird bei invalidate_cache() geleert."""
        resolver = self._create_resolver(temp_instructions_dir)

        resolver.resolve_text("{{char_name}}")
        assert resolver._static_cache != {}

        resolver.invalidate_cache()
        assert resolver._static_cache == {}

    def test_runtime_vars_override(self, temp_instructions_dir):
        """Runtime-Variablen überschreiben statische + computed Werte."""
        resolver = self._create_resolver(temp_instructions_dir)

        result = resolver.resolve_text(
            "Name: {{char_name}}",
            runtime_vars={'char_name': 'OverrideName'}
        )
        assert 'OverrideName' in result

    def test_empty_text(self, temp_instructions_dir):
        """Leerer Text wird unverändert zurückgegeben."""
        resolver = self._create_resolver(temp_instructions_dir)

        assert resolver.resolve_text('') == ''
        assert resolver.resolve_text(None) is None

    def test_multiple_same_placeholder(self, temp_instructions_dir):
        """Mehrfach verwendeter Placeholder wird überall aufgelöst."""
        resolver = self._create_resolver(temp_instructions_dir)

        result = resolver.resolve_text("{{char_name}} sagt: Ich bin {{char_name}}.")
        assert result == "TestPersona sagt: Ich bin TestPersona."

    def test_get_all_values(self, temp_instructions_dir):
        """get_all_values gibt Dict mit allen aufgelösten Werten zurück."""
        resolver = self._create_resolver(temp_instructions_dir)

        values = resolver.get_all_values(variant='default', runtime_vars={'language': 'de'})
        assert isinstance(values, dict)
        assert values.get('char_name') == 'TestPersona'
        assert values.get('language') == 'de'


# ===== Loader Tests =====

class TestPromptLoader:
    """Tests für den PromptLoader."""

    def test_load_manifest(self, temp_instructions_dir):
        """Manifest wird korrekt geladen."""
        from src.utils.prompt_engine.loader import PromptLoader

        loader = PromptLoader(temp_instructions_dir)
        manifest = loader.load_manifest()

        assert manifest['version'] == '2.0'
        assert 'impersonation' in manifest['prompts']
        assert 'system_rule' in manifest['prompts']

    def test_load_domain_file(self, temp_instructions_dir):
        """Domain-Datei wird korrekt geladen."""
        from src.utils.prompt_engine.loader import PromptLoader

        loader = PromptLoader(temp_instructions_dir)
        chat = loader.load_domain_file('chat.json')

        assert 'impersonation' in chat
        assert 'variants' in chat['impersonation']

    def test_load_missing_file_raises(self, temp_instructions_dir):
        """Fehlende Datei wirft FileNotFoundError."""
        from src.utils.prompt_engine.loader import PromptLoader

        loader = PromptLoader(temp_instructions_dir)
        with pytest.raises(FileNotFoundError):
            loader.load_domain_file('nonexistent.json')

    def test_load_all_domains(self, temp_instructions_dir):
        """Alle Domain-Dateien werden geladen."""
        from src.utils.prompt_engine.loader import PromptLoader

        loader = PromptLoader(temp_instructions_dir)
        manifest = loader.load_manifest()
        domains, errors = loader.load_all_domains(manifest)

        assert 'chat.json' in domains
        assert 'prefill.json' in domains
        assert 'consent_dialog.json' in domains
        assert len(errors) == 0

    def test_load_all_domains_missing_file(self, temp_instructions_dir):
        """Fehlende Domain-Datei wird als Error gemeldet, nicht als Crash."""
        from src.utils.prompt_engine.loader import PromptLoader

        loader = PromptLoader(temp_instructions_dir)
        manifest = {
            "prompts": {
                "test": {"domain_file": "missing.json"}
            }
        }
        domains, errors = loader.load_all_domains(manifest)
        assert 'missing.json' not in domains
        assert len(errors) == 1

    def test_atomic_write(self, temp_instructions_dir):
        """Atomares Schreiben funktioniert."""
        from src.utils.prompt_engine.loader import PromptLoader

        loader = PromptLoader(temp_instructions_dir)

        test_data = {"test": "value", "nested": {"key": "val"}}
        loader.save_domain_file('test_write.json', test_data)

        # Lesen und prüfen
        result = loader.load_domain_file('test_write.json')
        assert result == test_data

    def test_file_exists(self, temp_instructions_dir):
        """file_exists prüft Domain-Dateien korrekt."""
        from src.utils.prompt_engine.loader import PromptLoader

        loader = PromptLoader(temp_instructions_dir)
        assert loader.file_exists('chat.json')
        assert not loader.file_exists('nonexistent.json')

    def test_manifest_exists(self, temp_instructions_dir):
        """manifest_exists prüft Manifest korrekt."""
        from src.utils.prompt_engine.loader import PromptLoader

        loader = PromptLoader(temp_instructions_dir)
        assert loader.manifest_exists()

    def test_registry_exists(self, temp_instructions_dir):
        """registry_exists prüft Registry korrekt."""
        from src.utils.prompt_engine.loader import PromptLoader

        loader = PromptLoader(temp_instructions_dir)
        assert loader.registry_exists()

    def test_save_manifest(self, temp_instructions_dir):
        """Manifest kann gespeichert werden."""
        from src.utils.prompt_engine.loader import PromptLoader

        loader = PromptLoader(temp_instructions_dir)
        original = loader.load_manifest()
        original['version'] = '3.0'
        loader.save_manifest(original)

        reloaded = loader.load_manifest()
        assert reloaded['version'] == '3.0'


# ===== Validator Tests =====

class TestPromptValidator:
    """Tests für den PromptValidator."""

    def test_valid_manifest(self):
        """Gültiges Manifest produziert keine Fehler."""
        from src.utils.prompt_engine.validator import PromptValidator

        validator = PromptValidator()
        manifest = {
            "version": "2.0",
            "prompts": {
                "test": {
                    "name": "Test",
                    "type": "text",
                    "target": "system_prompt",
                    "position": "system_prompt",
                    "order": 100,
                    "enabled": True,
                    "domain_file": "chat.json"
                }
            }
        }
        errors = validator.validate_manifest(manifest)
        assert len(errors) == 0

    def test_missing_required_fields(self):
        """Fehlende Pflichtfelder werden erkannt."""
        from src.utils.prompt_engine.validator import PromptValidator

        validator = PromptValidator()
        manifest = {
            "version": "2.0",
            "prompts": {
                "test": {
                    "name": "Test"
                    # type, target, position, order, enabled, domain_file fehlen
                }
            }
        }
        errors = validator.validate_manifest(manifest)
        assert len(errors) >= 5  # Mindestens 5 fehlende Felder

    def test_invalid_category(self):
        """Ungültige Kategorie wird erkannt."""
        from src.utils.prompt_engine.validator import PromptValidator

        validator = PromptValidator()
        manifest = {
            "version": "2.0",
            "prompts": {
                "test": {
                    "name": "Test",
                    "category": "invalid_category",
                    "type": "text",
                    "target": "system_prompt",
                    "position": "system_prompt",
                    "order": 100,
                    "enabled": True,
                    "domain_file": "chat.json"
                }
            }
        }
        errors = validator.validate_manifest(manifest)
        assert any('invalid_category' in e for e in errors)

    def test_invalid_type(self):
        """Ungültiger type wird erkannt."""
        from src.utils.prompt_engine.validator import PromptValidator

        validator = PromptValidator()
        manifest = {
            "version": "2.0",
            "prompts": {
                "test": {
                    "name": "Test",
                    "type": "unknown_type",
                    "target": "system_prompt",
                    "position": "system_prompt",
                    "order": 100,
                    "enabled": True,
                    "domain_file": "chat.json"
                }
            }
        }
        errors = validator.validate_manifest(manifest)
        assert any('unknown_type' in e for e in errors)

    def test_cross_reference_validation(self):
        """Fehlende Domain-Datei Referenz wird erkannt."""
        from src.utils.prompt_engine.validator import PromptValidator

        validator = PromptValidator()
        manifest = {
            "prompts": {
                "test": {
                    "domain_file": "nonexistent.json"
                }
            }
        }
        errors = validator.validate_cross_references(manifest, {'chat.json', 'prefill.json'})
        assert len(errors) == 1
        assert 'nonexistent.json' in errors[0]

    def test_domain_validation_missing_prompt(self):
        """Prompt-ID aus Manifest fehlt in Domain-Datei."""
        from src.utils.prompt_engine.validator import PromptValidator

        validator = PromptValidator()
        domain_data = {}  # leer
        manifest_prompts = {"test": {"type": "text"}}
        errors = validator.validate_domain(domain_data, manifest_prompts)
        assert len(errors) == 1
        assert 'test' in errors[0]

    def test_domain_validation_missing_content(self):
        """Variant ohne 'content' wird erkannt."""
        from src.utils.prompt_engine.validator import PromptValidator

        validator = PromptValidator()
        domain_data = {
            "test": {
                "variants": {
                    "default": {}  # 'content' fehlt
                }
            }
        }
        manifest_prompts = {"test": {"type": "text"}}
        errors = validator.validate_domain(domain_data, manifest_prompts)
        assert len(errors) >= 1

    def test_placeholder_warnings(self):
        """Undeclared Placeholder generieren Warnungen."""
        from src.utils.prompt_engine.validator import PromptValidator

        validator = PromptValidator()
        domain_data = {
            "test": {
                "variants": {
                    "default": {
                        "content": "Text mit {{char_name}} und {{unknown_ph}}"
                    }
                },
                "placeholders_used": ["char_name"]
            }
        }
        registry = {
            "placeholders": {
                "char_name": {}
            }
        }
        warnings = validator.validate_placeholders(domain_data, registry)
        # unknown_ph ist nicht in Registry UND nicht in placeholders_used
        assert len(warnings) >= 1

    def test_validate_all(self, temp_instructions_dir):
        """validate_all gibt errors + warnings zurück."""
        from src.utils.prompt_engine.validator import PromptValidator
        from src.utils.prompt_engine.loader import PromptLoader

        loader = PromptLoader(temp_instructions_dir)
        manifest = loader.load_manifest()
        domains, _ = loader.load_all_domains(manifest)
        registry = loader.load_registry()

        validator = PromptValidator()
        result = validator.validate_all(manifest, domains, registry)

        assert isinstance(result, dict)
        assert 'errors' in result
        assert 'warnings' in result
        assert isinstance(result['errors'], list)
        assert isinstance(result['warnings'], list)


# ===== PromptEngine Tests =====

class TestPromptEngine:
    """Tests für die PromptEngine."""

    def _make_engine(self, instructions_dir):
        """Erstellt eine PromptEngine mit gemockten Compute-Functions."""
        from src.utils.prompt_engine import PromptEngine

        engine = PromptEngine(instructions_dir)

        # Compute-Functions mocken (die importieren config/time_context)
        if engine._resolver:
            engine._resolver._compute_functions = {
                'build_character_description': lambda: 'Test-Beschreibung',
                'get_time_context.current_date': lambda: '11.02.2026',
                'get_time_context.current_time': lambda: '14:30',
                'get_time_context.current_weekday': lambda: 'Mittwoch',
            }
        return engine

    def test_build_system_prompt_default(self, temp_instructions_dir):
        """System-Prompt wird korrekt zusammengebaut (default variant)."""
        engine = self._make_engine(temp_instructions_dir)
        result = engine.build_system_prompt(
            variant='default',
            runtime_vars={'language': 'de'}
        )

        # Impersonation sollte enthalten sein
        assert '**IMPERSONATION**' in result
        # System Rule mit aufgelöstem Placeholder
        assert 'TestPersona' in result
        assert 'de' in result
        # Persona Description
        assert 'Test-Beschreibung' in result
        # Consent Agreement sollte NICHT drin sein (nur experimental)
        assert 'AGREEMENT' not in result

    def test_build_system_prompt_experimental(self, temp_instructions_dir):
        """System-Prompt enthält Consent Agreement bei experimental variant."""
        engine = self._make_engine(temp_instructions_dir)
        result = engine.build_system_prompt(
            variant='experimental',
            runtime_vars={'language': 'de'}
        )

        # Experimental Persona-Beschreibung
        assert 'EXPERIMENTAL PERSONA' in result
        # Consent Agreement sollte drin sein
        assert 'AGREEMENT' in result

    def test_variant_condition_filtering(self, temp_instructions_dir):
        """Prompts mit variant_condition werden nur bei passender Variante eingebaut."""
        engine = self._make_engine(temp_instructions_dir)

        result_default = engine.build_system_prompt(variant='default', runtime_vars={'language': 'de'})
        result_experimental = engine.build_system_prompt(variant='experimental', runtime_vars={'language': 'de'})

        # consent_agreement hat variant_condition='experimental'
        assert 'AGREEMENT' not in result_default
        assert 'AGREEMENT' in result_experimental

    def test_build_system_prompt_order(self, temp_instructions_dir):
        """Prompts werden in korrekter Order-Reihenfolge zusammengebaut."""
        engine = self._make_engine(temp_instructions_dir)
        result = engine.build_system_prompt(variant='default', runtime_vars={'language': 'de'})

        # Impersonation (order 100) kommt vor System Rule (order 200)
        imp_pos = result.index('**IMPERSONATION**')
        rule_pos = result.index('TestPersona')
        assert imp_pos < rule_pos

    def test_build_prefill_default(self, temp_instructions_dir):
        """Prefill wird korrekt gebaut (default)."""
        engine = self._make_engine(temp_instructions_dir)
        result = engine.build_prefill(variant='default')

        assert 'TestPersona' in result
        assert 'Rolle' in result

    def test_build_prefill_experimental(self, temp_instructions_dir):
        """Prefill wählt korrekte Variante (experimental)."""
        engine = self._make_engine(temp_instructions_dir)
        result = engine.build_prefill(variant='experimental')

        assert 'TestPersona' in result
        assert '20-200' in result

    def test_get_consent_dialog(self, temp_instructions_dir):
        """Consent Dialog wird als Message-Array zurückgegeben."""
        engine = self._make_engine(temp_instructions_dir)
        dialog = engine.get_consent_dialog(variant='experimental')

        assert dialog is not None
        assert len(dialog) == 3
        assert dialog[0]['role'] == 'assistant'
        assert dialog[1]['role'] == 'user'
        assert dialog[2]['role'] == 'assistant'

    def test_consent_dialog_none_for_default(self, temp_instructions_dir):
        """Consent Dialog gibt None bei default variant."""
        engine = self._make_engine(temp_instructions_dir)
        dialog = engine.get_consent_dialog(variant='default')

        assert dialog is None

    def test_get_system_prompt_append(self, temp_instructions_dir):
        """System-Prompt-Append wird korrekt zurückgegeben."""
        engine = self._make_engine(temp_instructions_dir)
        result = engine.get_system_prompt_append()

        assert 'NACHGEDANKE-SYSTEM' in result

    def test_system_prompt_excludes_append(self, temp_instructions_dir):
        """build_system_prompt enthält NICHT die system_prompt_append Prompts."""
        engine = self._make_engine(temp_instructions_dir)
        result = engine.build_system_prompt(variant='default', runtime_vars={'language': 'de'})

        # NACHGEDANKE-SYSTEM hat position=system_prompt_append, wird separat behandelt
        assert 'NACHGEDANKE-SYSTEM' not in result

    def test_reload(self, temp_instructions_dir):
        """Reload lädt Dateien neu."""
        engine = self._make_engine(temp_instructions_dir)
        assert engine.is_loaded

        # Reload sollte ohne Fehler durchlaufen
        engine.reload()
        assert engine.is_loaded

    def test_resolve_single_prompt(self, temp_instructions_dir):
        """Einzelner Prompt wird aufgelöst."""
        engine = self._make_engine(temp_instructions_dir)
        result = engine.resolve_prompt('impersonation')

        assert result is not None
        assert '**IMPERSONATION**' in result

    def test_resolve_nonexistent_prompt(self, temp_instructions_dir):
        """Nicht-existenter Prompt gibt None zurück."""
        engine = self._make_engine(temp_instructions_dir)
        result = engine.resolve_prompt('nonexistent_id')

        assert result is None

    def test_get_all_prompts(self, temp_instructions_dir):
        """Alle Prompts werden zurückgegeben."""
        engine = self._make_engine(temp_instructions_dir)
        prompts = engine.get_all_prompts()

        assert len(prompts) == 7
        assert 'impersonation' in prompts
        assert 'system_rule' in prompts
        assert 'consent_dialog' in prompts

    def test_get_prompt(self, temp_instructions_dir):
        """Einzelner Prompt mit Content + Metadata."""
        engine = self._make_engine(temp_instructions_dir)
        prompt = engine.get_prompt('impersonation')

        assert prompt is not None
        assert prompt['id'] == 'impersonation'
        assert 'meta' in prompt
        assert 'content' in prompt
        assert prompt['meta']['type'] == 'text'

    def test_get_prompts_by_target(self, temp_instructions_dir):
        """Prompts können nach target gefiltert werden."""
        engine = self._make_engine(temp_instructions_dir)

        system_prompts = engine.get_prompts_by_target('system_prompt')
        assert len(system_prompts) >= 3  # impersonation, system_rule, persona_description, ...

        prefill_prompts = engine.get_prompts_by_target('prefill')
        assert len(prefill_prompts) >= 1  # remember

        message_prompts = engine.get_prompts_by_target('message')
        assert len(message_prompts) >= 1  # consent_dialog

    def test_validate_all(self, temp_instructions_dir):
        """Validierung liefert errors + warnings."""
        engine = self._make_engine(temp_instructions_dir)
        result = engine.validate_all()

        assert isinstance(result, dict)
        assert 'errors' in result
        assert 'warnings' in result

    def test_is_loaded_false_for_empty_dir(self, tmp_path):
        """Engine ist nicht geladen wenn Verzeichnis leer ist."""
        from src.utils.prompt_engine import PromptEngine

        empty_dir = tmp_path / 'empty'
        empty_dir.mkdir()

        engine = PromptEngine(str(empty_dir))
        assert not engine.is_loaded
        assert len(engine.load_errors) > 0

    def test_save_prompt(self, temp_instructions_dir):
        """Prompt kann gespeichert werden."""
        engine = self._make_engine(temp_instructions_dir)

        success = engine.save_prompt('impersonation', {
            'content': {
                'variants': {
                    'default': {
                        'content': 'Neuer Content.'
                    }
                },
                'placeholders_used': []
            }
        })
        assert success

        # Reload und prüfen
        engine.reload()
        engine._resolver._compute_functions = {
            'build_character_description': lambda: '',
            'get_time_context.current_date': lambda: '',
            'get_time_context.current_time': lambda: '',
            'get_time_context.current_weekday': lambda: '',
        }
        result = engine.resolve_prompt('impersonation')
        assert result == 'Neuer Content.'

    def test_delete_prompt(self, temp_instructions_dir):
        """User-Prompt kann gelöscht werden, System-Prompt nicht."""
        engine = self._make_engine(temp_instructions_dir)

        # System-Prompt kann NICHT gelöscht werden
        success = engine.delete_prompt('afterthought_system_note')
        assert not success
        assert engine.get_prompt('afterthought_system_note') is not None

        # User-Prompt erstellen und dann löschen
        data = {
            'id': 'test_user_prompt',
            'meta': {
                'name': 'Test User Prompt',
                'domain_file': 'test_user.json',
                'order': 999,
                'enabled': True,
                'phase': 'main',
            },
            'content': {'variants': {'default': {'content': 'Test Content'}}}
        }
        result_id = engine.create_prompt(data)
        assert result_id == 'test_user_prompt'

        success = engine.delete_prompt('test_user_prompt')
        assert success
        assert engine.get_prompt('test_user_prompt') is None

    def test_invalidate_cache(self, temp_instructions_dir):
        """Cache invalidation funktioniert über Engine."""
        engine = self._make_engine(temp_instructions_dir)

        # Resolve einmal um Cache aufzubauen
        engine.resolve_prompt('system_rule', runtime_vars={'language': 'de'})

        # Cache invalidieren
        engine.invalidate_cache()
        assert engine._resolver._static_cache == {}


# ===== Migrator Tests =====

class TestMigrator:
    """Tests für den Migrator."""

    def test_convert_known_placeholders(self):
        """Bekannte Placeholder werden konvertiert."""
        from src.utils.prompt_engine.migrator import PromptMigrator

        migrator = PromptMigrator()

        input_text = "Hallo {char_name}, du sprichst {language}."
        result = migrator.convert_placeholders(input_text)

        assert result == "Hallo {{char_name}}, du sprichst {{language}}."

    def test_unknown_placeholders_untouched(self):
        """Unbekannte {key} bleiben als einfache {key} stehen."""
        from src.utils.prompt_engine.migrator import PromptMigrator

        migrator = PromptMigrator()

        # Unbekannter Key sollte unverändert bleiben
        input_text = "Text mit {random_unknown_key}."
        result = migrator.convert_placeholders(input_text)

        assert result == "Text mit {random_unknown_key}."

    def test_json_syntax_untouched(self):
        """JSON-Syntax bleibt unverändert (Nicht-\\w-Zeichen)."""
        from src.utils.prompt_engine.migrator import PromptMigrator

        migrator = PromptMigrator()

        input_text = '{"key": "value"}'
        result = migrator.convert_placeholders(input_text)

        # JSON: { gefolgt von " ist kein \\w, daher nicht gematcht
        assert result == '{"key": "value"}'

    def test_mixed_placeholders(self):
        """Mix aus bekannten und unbekannten Placeholder."""
        from src.utils.prompt_engine.migrator import PromptMigrator

        migrator = PromptMigrator()

        input_text = "Name: {char_name}, Unbekannt: {something_else}"
        result = migrator.convert_placeholders(input_text)

        assert '{{char_name}}' in result
        assert '{something_else}' in result  # Einfache Klammern bleiben

    def test_parity_check_identical(self):
        """Parity-Vergleich erkennt identische Texte nach Whitespace-Normalisierung."""
        from src.utils.prompt_engine.migrator import PromptMigrator

        migrator = PromptMigrator()

        old = "  Hallo   Welt  \n\n  Test  "
        new = "Hallo Welt Test"

        assert migrator.verify_parity('test', 'default', old, new)

    def test_parity_check_different(self):
        """Parity-Vergleich erkennt unterschiedliche Texte."""
        from src.utils.prompt_engine.migrator import PromptMigrator

        migrator = PromptMigrator()

        assert not migrator.verify_parity('test', 'default', "Hallo", "Tschüss")

    def test_dry_run(self, tmp_path):
        """Dry-Run schreibt keine Dateien."""
        from src.utils.prompt_engine.migrator import PromptMigrator

        instructions_dir = tmp_path / 'instructions'
        instructions_dir.mkdir()
        system_dir = instructions_dir / 'system' / 'main'
        system_dir.mkdir(parents=True)

        # Erstelle eine Test-Datei
        (system_dir / 'impersonation.txt').write_text("Test {char_name}", encoding='utf-8')

        migrator = PromptMigrator(str(instructions_dir))
        result = migrator.migrate(dry_run=True)

        assert len(result['migrated_files']) >= 1
        # prompts/ Verzeichnis sollte NICHT erstellt worden sein
        assert not os.path.exists(str(instructions_dir / 'prompts'))

    def test_skips_existing_migration(self, tmp_path):
        """Migration wird übersprungen wenn JSON-Dateien bereits existieren."""
        from src.utils.prompt_engine.migrator import PromptMigrator

        instructions_dir = tmp_path / 'instructions'
        instructions_dir.mkdir()
        prompts_dir = instructions_dir / 'prompts'
        prompts_dir.mkdir()
        meta_dir = prompts_dir / '_meta'
        meta_dir.mkdir()
        (meta_dir / 'prompt_manifest.json').write_text('{}', encoding='utf-8')

        migrator = PromptMigrator(str(instructions_dir))
        result = migrator.migrate()

        assert len(result['warnings']) >= 1
        assert 'bereits' in result['warnings'][0].lower() or 'existieren' in result['warnings'][0].lower()


# ===== Architektur-Tests =====

class TestArchitecture:
    """Stellt sicher, dass PromptEngine keine unerlaubten Imports hat."""

    def _get_engine_dir(self):
        """Gibt den Pfad zum prompt_engine/ Verzeichnis zurück."""
        # src/tests/test_prompt_engine/test_prompt_engine.py → workspace root → src/utils/prompt_engine
        tests_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        workspace_root = os.path.dirname(os.path.dirname(tests_dir))
        return os.path.join(workspace_root, 'src', 'utils', 'prompt_engine')

    def test_no_flask_imports(self):
        """prompt_engine/ darf kein Flask importieren."""
        import ast

        engine_dir = self._get_engine_dir()

        for filename in os.listdir(engine_dir):
            if not filename.endswith('.py'):
                continue
            filepath = os.path.join(engine_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source, filename)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith('flask'), \
                            f"{filename} importiert flask: {alias.name}"
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert not node.module.startswith('flask'), \
                            f"{filename} importiert flask: {node.module}"

    def test_no_pywebview_imports(self):
        """prompt_engine/ darf kein PyWebView importieren."""
        import ast

        engine_dir = self._get_engine_dir()

        for filename in os.listdir(engine_dir):
            if not filename.endswith('.py'):
                continue
            filepath = os.path.join(engine_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source, filename)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith('webview'), \
                            f"{filename} importiert webview: {alias.name}"
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert not node.module.startswith('webview'), \
                            f"{filename} importiert webview: {node.module}"

    def test_all_modules_exist(self):
        """Alle erwarteten Module existieren."""
        engine_dir = self._get_engine_dir()
        expected = ['__init__.py', 'engine.py', 'loader.py',
                    'placeholder_resolver.py', 'validator.py', 'migrator.py']
        for name in expected:
            assert os.path.exists(os.path.join(engine_dir, name)), \
                f"Modul fehlt: {name}"
