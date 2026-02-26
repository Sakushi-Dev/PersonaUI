"""
Tests für Step 4: Cortex Prompts & Placeholders.

Testet:
- Engine: _should_include_block(), _clean_resolved_text(), resolve_prompt_by_id(), get_domain_data()
- Engine: build_system_prompt() mit requires_any-Filterung und NON_CHAT_CATEGORIES
- Validator: 'cortex' in VALID_CATEGORIES, validate_requires_any()
- CortexService: Section-Header-Wrapping in get_cortex_for_prompt()
- ChatService: _load_cortex_context() Setting-Gate
- PlaceholderResolver: build_cortex_persona_context Compute-Funktion
- CortexUpdateService: PromptEngine-Integration mit Fallback
"""

import pytest
import os
import json
from unittest.mock import patch, MagicMock


# ═══════════════════════════════════════════════════════════════════════════════
# Engine: _should_include_block
# ═══════════════════════════════════════════════════════════════════════════════

class TestShouldIncludeBlock:
    """PromptEngine._should_include_block()"""

    @pytest.fixture
    def engine(self):
        """Erstellt eine PromptEngine-Instanz."""
        from utils.prompt_engine.engine import PromptEngine
        return PromptEngine()

    def test_no_requires_any_always_included(self, engine):
        """Block ohne requires_any wird immer eingeschlossen."""
        meta = {'enabled': True, 'category': 'system'}
        assert engine._should_include_block(meta, {}, 'default') is True

    def test_requires_any_all_empty_excluded(self, engine):
        """Block mit requires_any wird ausgeschlossen wenn alle Werte leer."""
        meta = {
            'enabled': True,
            'requires_any': ['cortex_memory', 'cortex_soul', 'cortex_relationship']
        }
        runtime_vars = {
            'cortex_memory': '',
            'cortex_soul': '',
            'cortex_relationship': '',
        }
        assert engine._should_include_block(meta, runtime_vars, 'default') is False

    def test_requires_any_one_filled_included(self, engine):
        """Block wird eingeschlossen wenn mindestens ein Wert non-empty."""
        meta = {
            'enabled': True,
            'requires_any': ['cortex_memory', 'cortex_soul', 'cortex_relationship']
        }
        runtime_vars = {
            'cortex_memory': '### Erinnerungen\n\nMax hat eine Katze',
            'cortex_soul': '',
            'cortex_relationship': '',
        }
        assert engine._should_include_block(meta, runtime_vars, 'default') is True

    def test_requires_any_all_filled_included(self, engine):
        """Block mit allen non-empty Werten wird eingeschlossen."""
        meta = {
            'enabled': True,
            'requires_any': ['cortex_memory', 'cortex_soul']
        }
        runtime_vars = {
            'cortex_memory': 'Memory content',
            'cortex_soul': 'Soul content',
        }
        assert engine._should_include_block(meta, runtime_vars, 'default') is True

    def test_requires_any_no_runtime_vars_excluded(self, engine):
        """Block mit requires_any aber ohne runtime_vars wird ausgeschlossen."""
        meta = {
            'enabled': True,
            'requires_any': ['cortex_memory']
        }
        assert engine._should_include_block(meta, None, 'default') is False

    def test_requires_any_whitespace_only_excluded(self, engine):
        """Whitespace-only Werte zählen als leer."""
        meta = {
            'enabled': True,
            'requires_any': ['cortex_memory']
        }
        runtime_vars = {'cortex_memory': '   \n  '}
        assert engine._should_include_block(meta, runtime_vars, 'default') is False

    def test_disabled_block_excluded(self, engine):
        """Deaktivierter Block wird immer ausgeschlossen."""
        meta = {'enabled': False}
        assert engine._should_include_block(meta, {}, 'default') is False


# ═══════════════════════════════════════════════════════════════════════════════
# Engine: _clean_resolved_text
# ═══════════════════════════════════════════════════════════════════════════════

class TestCleanResolvedText:
    """PromptEngine._clean_resolved_text()"""

    @pytest.fixture
    def engine(self):
        from utils.prompt_engine.engine import PromptEngine
        return PromptEngine()

    def test_triple_newlines_reduced(self, engine):
        """3+ Newlines werden auf 2 reduziert."""
        text = "Part 1\n\n\nPart 2"
        assert engine._clean_resolved_text(text) == "Part 1\n\nPart 2"

    def test_many_newlines_reduced(self, engine):
        """5 Newlines werden auf 2 reduziert."""
        text = "Part 1\n\n\n\n\nPart 2"
        assert engine._clean_resolved_text(text) == "Part 1\n\nPart 2"

    def test_double_newlines_preserved(self, engine):
        """2 Newlines bleiben erhalten."""
        text = "Part 1\n\nPart 2"
        assert engine._clean_resolved_text(text) == "Part 1\n\nPart 2"

    def test_leading_trailing_whitespace_stripped(self, engine):
        """Führende/nachfolgende Whitespace wird entfernt."""
        text = "  \n\nContent\n\n  "
        assert engine._clean_resolved_text(text) == "Content"

    def test_empty_string(self, engine):
        assert engine._clean_resolved_text("") == ""

    def test_multiple_gaps(self, engine):
        """Mehrere Lücken werden jeweils bereinigt."""
        text = "A\n\n\nB\n\n\n\nC"
        assert engine._clean_resolved_text(text) == "A\n\nB\n\nC"


# ═══════════════════════════════════════════════════════════════════════════════
# Engine: NON_CHAT_CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════════

class TestNonChatCategories:
    """Cortex-Kategorie wird aus normalem Chat-Prompt ausgeschlossen."""

    @pytest.fixture
    def engine(self):
        from utils.prompt_engine.engine import PromptEngine
        return PromptEngine()

    def test_cortex_excluded_from_default_build(self, engine):
        """Cortex-Blocks werden ohne category_filter NICHT in den System-Prompt aufgenommen."""
        prompt = engine.build_system_prompt(variant='default')
        # cortex_update_system enthält "Du bist {{char_name}}. Du bist nicht eine KI"
        # Dieser Text darf NICHT im normalen Chat-Prompt auftauchen
        assert 'Du bist nicht eine KI' not in (prompt or '')

    def test_cortex_included_with_filter(self, engine):
        """Cortex-Blocks werden MIT category_filter='cortex' aufgelöst."""
        prompt = engine.build_system_prompt(variant='default', category_filter='cortex')
        # Der Cortex-Update System-Prompt sollte aufgelöst werden
        assert prompt is not None
        if prompt:  # Kann leer sein wenn keine Persona aktiv
            assert len(prompt) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Engine: resolve_prompt_by_id & get_domain_data
# ═══════════════════════════════════════════════════════════════════════════════

class TestResolvePromptById:
    """PromptEngine.resolve_prompt_by_id()"""

    @pytest.fixture
    def engine(self):
        from utils.prompt_engine.engine import PromptEngine
        return PromptEngine()

    def test_valid_prompt_id(self, engine):
        """Bekannte Prompt-ID wird aufgelöst."""
        result = engine.resolve_prompt_by_id('cortex_update_user_message', runtime_vars={
            'cortex_conversation_text': 'Test conversation'
        })
        assert 'Test conversation' in result

    def test_unknown_prompt_id_raises(self, engine):
        """Unbekannte Prompt-ID wirft KeyError."""
        with pytest.raises(KeyError):
            engine.resolve_prompt_by_id('nonexistent_prompt_xyz')


class TestGetDomainData:
    """PromptEngine.get_domain_data()"""

    @pytest.fixture
    def engine(self):
        from utils.prompt_engine.engine import PromptEngine
        return PromptEngine()

    def test_cortex_update_tools_has_tool_descriptions(self, engine):
        """cortex_update_tools Domain-Daten enthalten tool_descriptions."""
        data = engine.get_domain_data('cortex_update_tools')
        assert 'tool_descriptions' in data
        assert 'read_file' in data['tool_descriptions']
        assert 'write_file' in data['tool_descriptions']

    def test_tool_descriptions_have_fields(self, engine):
        """Tool-Descriptions haben tool_description und filename_description."""
        data = engine.get_domain_data('cortex_update_tools')
        read_desc = data['tool_descriptions']['read_file']
        assert 'tool_description' in read_desc
        assert 'filename_description' in read_desc

    def test_unknown_prompt_returns_empty(self, engine):
        """Unbekannte Prompt-ID gibt leeres Dict zurück."""
        data = engine.get_domain_data('nonexistent_xyz')
        assert data == {}


# ═══════════════════════════════════════════════════════════════════════════════
# Validator
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidatorCortex:
    """Validator-Erweiterungen für Cortex."""

    def test_cortex_is_valid_category(self):
        """'cortex' ist eine gültige Kategorie."""
        from utils.prompt_engine.validator import VALID_CATEGORIES
        assert 'cortex' in VALID_CATEGORIES

    def test_validate_requires_any_valid(self):
        """Gültige requires_any-Referenzen erzeugen keine Warnungen."""
        from utils.prompt_engine.validator import PromptValidator
        validator = PromptValidator()
        manifest = {
            'prompts': {
                'test_block': {
                    'requires_any': ['cortex_memory', 'cortex_soul']
                }
            }
        }
        registry = {
            'placeholders': {
                'cortex_memory': {},
                'cortex_soul': {},
            }
        }
        warnings = validator.validate_requires_any(manifest, registry)
        assert len(warnings) == 0

    def test_validate_requires_any_unknown_key(self):
        """Unbekannte requires_any-Keys erzeugen Warnungen."""
        from utils.prompt_engine.validator import PromptValidator
        validator = PromptValidator()
        manifest = {
            'prompts': {
                'test_block': {
                    'requires_any': ['nonexistent_key']
                }
            }
        }
        registry = {'placeholders': {}}
        warnings = validator.validate_requires_any(manifest, registry)
        assert len(warnings) == 1
        assert 'nonexistent_key' in warnings[0]

    def test_validate_requires_any_no_requires(self):
        """Blöcke ohne requires_any erzeugen keine Warnungen."""
        from utils.prompt_engine.validator import PromptValidator
        validator = PromptValidator()
        manifest = {
            'prompts': {
                'normal_block': {'category': 'system'}
            }
        }
        registry = {'placeholders': {}}
        warnings = validator.validate_requires_any(manifest, registry)
        assert len(warnings) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# CortexService: Section Headers
# ═══════════════════════════════════════════════════════════════════════════════

class TestCortexServiceSectionHeaders:
    """get_cortex_for_prompt() wraps non-empty files with section headers."""

    @pytest.fixture
    def cortex_setup(self, tmp_path):
        """CortexService mit temporärem Cortex-Verzeichnis."""
        import utils.cortex_service as cortex_module
        from utils.cortex_service import CortexService, ensure_cortex_dir

        original_base = cortex_module.CORTEX_BASE_DIR
        original_default = cortex_module.CORTEX_DEFAULT_DIR
        original_custom = cortex_module.CORTEX_CUSTOM_DIR

        test_base = str(tmp_path / 'cortex')
        test_default = str(tmp_path / 'cortex' / 'default')
        test_custom = str(tmp_path / 'cortex' / 'custom')

        cortex_module.CORTEX_BASE_DIR = test_base
        cortex_module.CORTEX_DEFAULT_DIR = test_default
        cortex_module.CORTEX_CUSTOM_DIR = test_custom

        service = CortexService(MagicMock())
        ensure_cortex_dir('default')

        yield service

        cortex_module.CORTEX_BASE_DIR = original_base
        cortex_module.CORTEX_DEFAULT_DIR = original_default
        cortex_module.CORTEX_CUSTOM_DIR = original_custom

    def test_empty_files_return_empty_strings(self, cortex_setup):
        """Leere Dateien → leere Strings (kein Header)."""
        # Dateien explizit leeren (Templates haben Vorbefüllung)
        cortex_setup.write_file('default', 'memory.md', '')
        cortex_setup.write_file('default', 'soul.md', '')
        cortex_setup.write_file('default', 'relationship.md', '')
        result = cortex_setup.get_cortex_for_prompt('default')
        assert result['cortex_memory'] == ''
        assert result['cortex_soul'] == ''
        assert result['cortex_relationship'] == ''

    def test_filled_file_gets_header(self, cortex_setup):
        """Befüllte Datei bekommt Section-Header."""
        cortex_setup.write_file('default', 'memory.md', 'Max liebt Katzen')
        result = cortex_setup.get_cortex_for_prompt('default')
        assert result['cortex_memory'] == '### Memories & Knowledge\n\nMax liebt Katzen'

    def test_soul_header(self, cortex_setup):
        """Soul-Datei bekommt richtigen Header."""
        cortex_setup.write_file('default', 'soul.md', 'Ich bin ehrlich')
        result = cortex_setup.get_cortex_for_prompt('default')
        assert result['cortex_soul'] == '### Identity & Inner Self\n\nIch bin ehrlich'

    def test_relationship_header(self, cortex_setup):
        """Relationship-Datei bekommt richtigen Header."""
        cortex_setup.write_file('default', 'relationship.md', 'Wir verstehen uns')
        result = cortex_setup.get_cortex_for_prompt('default')
        assert result['cortex_relationship'] == '### Relationship & Shared History\n\nWir verstehen uns'

    def test_mixed_empty_and_filled(self, cortex_setup):
        """Nur befüllte Dateien bekommen Header, leere bleiben leer."""
        # Alle erst leeren, dann nur memory befüllen
        cortex_setup.write_file('default', 'memory.md', 'Content')
        cortex_setup.write_file('default', 'soul.md', '')
        cortex_setup.write_file('default', 'relationship.md', '')
        result = cortex_setup.get_cortex_for_prompt('default')
        assert result['cortex_memory'] != ''
        assert result['cortex_soul'] == ''
        assert result['cortex_relationship'] == ''


# ═══════════════════════════════════════════════════════════════════════════════
# ChatService: _load_cortex_context
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoadCortexContext:
    """ChatService._load_cortex_context() Setting-Gate."""

    def _make_service(self, mock_api_client=None):
        from utils.services.chat_service import ChatService
        with patch('utils.services.chat_service.ChatService.__init__', lambda self, api_client: None):
            service = ChatService.__new__(ChatService)
        service.api_client = mock_api_client or MagicMock()
        service._engine = MagicMock()
        return service

    @patch('utils.services.chat_service._read_setting')
    def test_disabled_returns_empty(self, mock_setting):
        """cortexEnabled=false gibt leere Strings zurück."""
        mock_setting.return_value = False
        service = self._make_service()
        result = service._load_cortex_context('test_persona')
        assert result == {'cortex_memory': '', 'cortex_soul': '', 'cortex_relationship': ''}

    @patch('utils.services.chat_service._read_setting')
    @patch('utils.provider.get_cortex_service')
    def test_enabled_loads_data(self, mock_cortex_provider, mock_setting):
        """cortexEnabled=true lädt Cortex-Daten."""
        mock_setting.return_value = True
        mock_cortex = MagicMock()
        mock_cortex.get_cortex_for_prompt.return_value = {
            'cortex_memory': '### Erinnerungen & Wissen\n\nTest',
            'cortex_soul': '',
            'cortex_relationship': '',
        }
        mock_cortex_provider.return_value = mock_cortex

        service = self._make_service()
        result = service._load_cortex_context('test_persona')
        assert result['cortex_memory'] == '### Erinnerungen & Wissen\n\nTest'

    @patch('utils.services.chat_service._read_setting')
    @patch('utils.provider.get_cortex_service')
    def test_exception_returns_empty(self, mock_cortex_provider, mock_setting):
        """Bei Fehler werden leere Strings zurückgegeben."""
        mock_setting.return_value = True
        mock_cortex_provider.side_effect = Exception("Service error")

        service = self._make_service()
        result = service._load_cortex_context('test_persona')
        assert result == {'cortex_memory': '', 'cortex_soul': '', 'cortex_relationship': ''}


# ═══════════════════════════════════════════════════════════════════════════════
# CortexUpdateService: PromptEngine Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestCortexUpdateServiceEngine:
    """CortexUpdateService PromptEngine-Integration mit Fallback."""

    @pytest.fixture
    def service(self):
        from utils.cortex.update_service import CortexUpdateService
        return CortexUpdateService()

    def test_build_cortex_tools_fallback(self, service):
        """Ohne PromptEngine werden Fallback-Tools verwendet."""
        with patch.object(service, '_get_prompt_engine', return_value=None):
            tools = service._build_cortex_tools()
        assert len(tools) == 2
        assert tools[0]['name'] == 'read_file'
        assert tools[1]['name'] == 'write_file'

    def test_build_cortex_tools_from_engine(self, service):
        """Mit PromptEngine werden Tool-Descriptions aus Domain-Data geladen."""
        mock_engine = MagicMock()
        mock_engine.get_domain_data.return_value = {
            'tool_descriptions': {
                'read_file': {
                    'tool_description': 'Custom Read Description',
                    'filename_description': 'Custom Filename Desc'
                },
                'write_file': {
                    'tool_description': 'Custom Write Description',
                    'filename_description': 'Custom Filename Desc',
                    'content_description': 'Custom Content Desc'
                }
            }
        }
        with patch.object(service, '_get_prompt_engine', return_value=mock_engine):
            tools = service._build_cortex_tools()

        assert tools[0]['description'] == 'Custom Read Description'
        assert tools[1]['description'] == 'Custom Write Description'

    def test_build_messages_fallback(self, service):
        """Ohne PromptEngine wird Fallback-Message gebaut."""
        conversation = [
            {'role': 'user', 'content': 'Hallo'},
            {'role': 'assistant', 'content': 'Hi!'},
        ]
        with patch.object(service, '_get_prompt_engine', return_value=None):
            messages = service._build_messages(conversation, 'Mia', 'Alex')
        assert len(messages) == 1
        assert 'Hallo' in messages[0]['content']
        assert 'Alex' in messages[0]['content']

    def test_build_messages_with_engine(self, service):
        """Mit PromptEngine wird User-Message über resolve_prompt_by_id gebaut."""
        mock_engine = MagicMock()
        mock_engine.resolve_prompt_by_id.return_value = 'Engine-generated message with conversation'

        conversation = [
            {'role': 'user', 'content': 'Hi'},
        ]
        with patch.object(service, '_get_prompt_engine', return_value=mock_engine):
            messages = service._build_messages(conversation, 'Mia', 'Alex')

        assert messages[0]['content'] == 'Engine-generated message with conversation'
        mock_engine.resolve_prompt_by_id.assert_called_once()

    def test_system_prompt_fallback(self, service):
        """Ohne PromptEngine wird Fallback-System-Prompt verwendet."""
        mock_character = {
            'char_name': 'Bot',
            'identity': 'Test Identity',
            'core': '',
            'background': ''
        }
        with patch.object(service, '_get_prompt_engine', return_value=None):
            prompt = service._build_cortex_system_prompt('Bot', 'User', mock_character)
        assert 'You are Bot' in prompt

    def test_system_prompt_with_engine(self, service):
        """Mit PromptEngine wird System-Prompt über build_system_prompt gebaut."""
        mock_engine = MagicMock()
        mock_engine.build_system_prompt.return_value = 'Engine-generated system prompt'

        with patch.object(service, '_get_prompt_engine', return_value=mock_engine):
            prompt = service._build_cortex_system_prompt('Bot', 'User', {})

        assert prompt == 'Engine-generated system prompt'
        mock_engine.build_system_prompt.assert_called_once_with(
            variant='default',
            category_filter='cortex'
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PlaceholderResolver: cortex_persona_context
# ═══════════════════════════════════════════════════════════════════════════════

class TestCortexPersonaContextCompute:
    """_compute_cortex_persona_context() Compute-Funktion."""

    @pytest.fixture
    def resolver(self):
        from utils.prompt_engine.placeholder_resolver import PlaceholderResolver
        registry = {
            'placeholders': {
                'cortex_persona_context': {
                    'resolve_phase': 'computed',
                    'compute_function': 'build_cortex_persona_context',
                    'default': ''
                }
            }
        }
        return PlaceholderResolver(registry, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'instructions'))

    @patch('utils.config.load_character')
    def test_builds_context_from_character(self, mock_load_char, resolver):
        """Baut Persona-Kontext aus identity, core und background."""
        mock_load_char.return_value = {
            'identity': 'Mia, 22',
            'core': 'Warmherzig',
            'background': 'Kleine Stadt'
        }
        result = resolver._compute_cortex_persona_context()
        assert 'Mia, 22' in result
        assert 'Warmherzig' in result
        assert 'Hintergrund: Kleine Stadt' in result

    @patch('utils.config.load_character')
    def test_empty_fields_skipped(self, mock_load_char, resolver):
        """Leere Felder werden übersprungen."""
        mock_load_char.return_value = {
            'identity': 'Bot',
            'core': '',
            'background': ''
        }
        result = resolver._compute_cortex_persona_context()
        assert result == 'Bot'
        assert 'Hintergrund' not in result

    @patch('utils.config.load_character')
    def test_exception_returns_empty(self, mock_load_char, resolver):
        """Bei Fehler wird leerer String zurückgegeben."""
        mock_load_char.side_effect = Exception("No character loaded")
        result = resolver._compute_cortex_persona_context()
        assert result == ''


# ═══════════════════════════════════════════════════════════════════════════════
# Registry & Manifest Integrity
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegistryAndManifestIntegrity:
    """Prüft dass alle Config-Dateien korrekt sind."""

    @pytest.fixture
    def base_path(self):
        src_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        return os.path.join(src_dir, 'src', 'instructions', 'prompts')

    def test_cortex_placeholders_in_registry(self, base_path):
        """Alle 5 Cortex-Placeholders existieren in der Registry."""
        registry_path = os.path.join(base_path, '_meta', 'placeholder_registry.json')
        with open(registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        placeholders = registry['placeholders']
        for key in ['cortex_memory', 'cortex_soul', 'cortex_relationship',
                     'cortex_persona_context', 'cortex_conversation_text']:
            assert key in placeholders, f"Placeholder '{key}' fehlt in Registry"

    def test_cortex_manifest_entries(self, base_path):
        """Alle 4 Cortex-Manifest-Einträge existieren."""
        manifest_path = os.path.join(base_path, '_meta', 'prompt_manifest.json')
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        prompts = manifest['prompts']
        for prompt_id in ['cortex_context', 'cortex_update_system',
                          'cortex_update_user_message', 'cortex_update_tools']:
            assert prompt_id in prompts, f"Manifest-Eintrag '{prompt_id}' fehlt"

    def test_cortex_context_has_requires_any(self, base_path):
        """cortex_context hat requires_any Feld."""
        manifest_path = os.path.join(base_path, '_meta', 'prompt_manifest.json')
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        cortex_meta = manifest['prompts']['cortex_context']
        assert 'requires_any' in cortex_meta
        assert 'cortex_memory' in cortex_meta['requires_any']

    def test_defaults_mirror_active(self, base_path):
        """_defaults/ Manifest und Registry sind Spiegel der aktiven Versionen."""
        for filename in ['_meta/prompt_manifest.json', '_meta/placeholder_registry.json']:
            active_path = os.path.join(base_path, filename)
            defaults_path = os.path.join(base_path, '_defaults', filename)
            with open(active_path, 'r', encoding='utf-8') as f:
                active = json.load(f)
            with open(defaults_path, 'r', encoding='utf-8') as f:
                defaults = json.load(f)
            # Prüfe dass Cortex-Einträge in beiden existieren
            if 'prompts' in active:
                for key in ['cortex_context', 'cortex_update_system']:
                    assert key in active.get('prompts', {}), f"{key} fehlt in active"
                    assert key in defaults.get('prompts', {}), f"{key} fehlt in defaults"

    def test_domain_files_exist(self, base_path):
        """Alle Domain-Dateien und _defaults-Kopien existieren."""
        for filename in ['cortex_context.json', 'cortex_update_system.json',
                         'cortex_update_user_message.json', 'cortex_update_tools.json']:
            assert os.path.exists(os.path.join(base_path, filename)), \
                f"Domain-Datei '{filename}' fehlt"
            assert os.path.exists(os.path.join(base_path, '_defaults', filename)), \
                f"_defaults/{filename} fehlt"

    def test_cortex_enabled_in_defaults(self):
        """cortexEnabled existiert in defaults.json."""
        src_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        defaults_path = os.path.join(src_dir, 'src', 'settings', 'defaults.json')
        with open(defaults_path, 'r', encoding='utf-8') as f:
            defaults = json.load(f)
        assert 'cortexEnabled' in defaults
        assert defaults['cortexEnabled'] is True
