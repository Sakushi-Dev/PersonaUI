"""
Tests für Step 6: API Integration

Testet:
- 6A: Cortex Tier-Check in api_regenerate (done-Event enthält cortex-Feld)
- 6B: ensure_cortex_dirs() — Startup-Funktion
- 6C: Settings-Migration (memoriesEnabled → cortexEnabled, cortex_settings.json)
- 6D: /cortex Slash Command Endpoint
"""

import json
import os
from unittest.mock import patch

# ─── Konstanten ──────────────────────────────────────────────────────────────

# src/tests/test_integration/ → src/tests/ → src/ → workspace root
_WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC_DIR = os.path.join(_WORKSPACE, 'src')


# ═════════════════════════════════════════════════════════════════════════════
#  6B: ensure_cortex_dirs() Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestEnsureCortexDirs:
    """Testet die Startup-Funktion ensure_cortex_dirs()."""

    def _make_temp_structure(self, tmp_path):
        """Erstellt temporäre Verzeichnisstruktur für den Test."""
        cortex_base = tmp_path / "instructions" / "personas" / "cortex"
        cortex_base.mkdir(parents=True)
        personas_dir = tmp_path / "instructions" / "created_personas"
        personas_dir.mkdir(parents=True)
        return cortex_base, personas_dir

    @patch('utils.cortex_service.BASE_DIR')
    @patch('utils.cortex_service.CORTEX_BASE_DIR')
    @patch('utils.cortex_service.CORTEX_DEFAULT_DIR')
    @patch('utils.cortex_service.CORTEX_CUSTOM_DIR')
    def test_creates_default_dir(self, mock_custom, mock_default, mock_base, mock_basedir, tmp_path):
        """Default-Cortex-Verzeichnis wird erstellt."""
        cortex_base, personas_dir = self._make_temp_structure(tmp_path)
        mock_basedir.__str__ = lambda x: str(tmp_path)
        mock_base.__str__ = lambda x: str(cortex_base)
        mock_default.__str__ = lambda x: str(cortex_base / "default")
        mock_custom.__str__ = lambda x: str(cortex_base / "custom")

        # Patche die Module-level Variablen korrekt
        with patch('utils.cortex_service.BASE_DIR', str(tmp_path)), \
             patch('utils.cortex_service.CORTEX_BASE_DIR', str(cortex_base)), \
             patch('utils.cortex_service.CORTEX_DEFAULT_DIR', str(cortex_base / "default")), \
             patch('utils.cortex_service.CORTEX_CUSTOM_DIR', str(cortex_base / "custom")):

            from utils.cortex_service import ensure_cortex_dirs
            count = ensure_cortex_dirs()

            assert count >= 1
            assert (cortex_base / "default").exists()
            assert (cortex_base / "default" / "memory.md").exists()
            assert (cortex_base / "default" / "soul.md").exists()
            assert (cortex_base / "default" / "relationship.md").exists()

    @patch('utils.cortex_service.BASE_DIR')
    @patch('utils.cortex_service.CORTEX_BASE_DIR')
    @patch('utils.cortex_service.CORTEX_DEFAULT_DIR')
    @patch('utils.cortex_service.CORTEX_CUSTOM_DIR')
    def test_creates_custom_persona_dirs(self, mock_custom, mock_default, mock_base, mock_basedir, tmp_path):
        """Erstellt Cortex-Verzeichnisse für Custom-Personas."""
        cortex_base, personas_dir = self._make_temp_structure(tmp_path)

        # Erstelle 2 Persona-Dateien
        (personas_dir / "abc123.json").write_text('{}', encoding='utf-8')
        (personas_dir / "def456.json").write_text('{}', encoding='utf-8')

        with patch('utils.cortex_service.BASE_DIR', str(tmp_path)), \
             patch('utils.cortex_service.CORTEX_BASE_DIR', str(cortex_base)), \
             patch('utils.cortex_service.CORTEX_DEFAULT_DIR', str(cortex_base / "default")), \
             patch('utils.cortex_service.CORTEX_CUSTOM_DIR', str(cortex_base / "custom")):

            from utils.cortex_service import ensure_cortex_dirs
            count = ensure_cortex_dirs()

            assert count == 3  # default + 2 custom
            assert (cortex_base / "custom" / "abc123" / "memory.md").exists()
            assert (cortex_base / "custom" / "def456" / "soul.md").exists()

    @patch('utils.cortex_service.BASE_DIR')
    @patch('utils.cortex_service.CORTEX_BASE_DIR')
    @patch('utils.cortex_service.CORTEX_DEFAULT_DIR')
    @patch('utils.cortex_service.CORTEX_CUSTOM_DIR')
    def test_idempotent(self, mock_custom, mock_default, mock_base, mock_basedir, tmp_path):
        """Wiederholter Aufruf überschreibt keine bestehenden Dateien."""
        cortex_base, personas_dir = self._make_temp_structure(tmp_path)

        with patch('utils.cortex_service.BASE_DIR', str(tmp_path)), \
             patch('utils.cortex_service.CORTEX_BASE_DIR', str(cortex_base)), \
             patch('utils.cortex_service.CORTEX_DEFAULT_DIR', str(cortex_base / "default")), \
             patch('utils.cortex_service.CORTEX_CUSTOM_DIR', str(cortex_base / "custom")):

            from utils.cortex_service import ensure_cortex_dirs

            # 1. Aufruf
            ensure_cortex_dirs()

            # Schreibe Custom-Content
            mem_path = cortex_base / "default" / "memory.md"
            mem_path.write_text("Custom Content!", encoding='utf-8')

            # 2. Aufruf — Datei sollte NICHT überschrieben werden
            ensure_cortex_dirs()

            assert mem_path.read_text(encoding='utf-8') == "Custom Content!"

    @patch('utils.cortex_service.BASE_DIR')
    @patch('utils.cortex_service.CORTEX_BASE_DIR')
    @patch('utils.cortex_service.CORTEX_DEFAULT_DIR')
    @patch('utils.cortex_service.CORTEX_CUSTOM_DIR')
    def test_no_personas_dir(self, mock_custom, mock_default, mock_base, mock_basedir, tmp_path):
        """Kein Fehler wenn created_personas/ nicht existiert."""
        cortex_base = tmp_path / "instructions" / "personas" / "cortex"
        cortex_base.mkdir(parents=True)
        # created_personas NICHT erstellen

        with patch('utils.cortex_service.BASE_DIR', str(tmp_path)), \
             patch('utils.cortex_service.CORTEX_BASE_DIR', str(cortex_base)), \
             patch('utils.cortex_service.CORTEX_DEFAULT_DIR', str(cortex_base / "default")), \
             patch('utils.cortex_service.CORTEX_CUSTOM_DIR', str(cortex_base / "custom")):

            from utils.cortex_service import ensure_cortex_dirs
            count = ensure_cortex_dirs()

            assert count == 1  # Nur default


# ═════════════════════════════════════════════════════════════════════════════
#  6C: Settings-Migration Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestSettingsMigration:
    """Testet die Settings-Migration (memoriesEnabled → cortexEnabled)."""

    def test_migrate_memories_true(self, tmp_path):
        """memoriesEnabled: true → cortexEnabled: true."""
        settings_file = tmp_path / "user_settings.json"
        settings_file.write_text(json.dumps({
            "memoriesEnabled": True,
            "darkMode": False
        }), encoding='utf-8')

        with patch('utils.settings_migration._USER_SETTINGS_FILE', str(settings_file)), \
             patch('utils.settings_migration._CORTEX_SETTINGS_FILE', str(tmp_path / "cortex_settings.json")):
            from utils.settings_migration import _migrate_memories_to_cortex
            _migrate_memories_to_cortex()

        result = json.loads(settings_file.read_text(encoding='utf-8'))
        assert result['cortexEnabled'] is True
        assert 'memoriesEnabled' not in result
        assert result['darkMode'] is False

    def test_migrate_memories_false(self, tmp_path):
        """memoriesEnabled: false → cortexEnabled: false."""
        settings_file = tmp_path / "user_settings.json"
        settings_file.write_text(json.dumps({
            "memoriesEnabled": False,
        }), encoding='utf-8')

        with patch('utils.settings_migration._USER_SETTINGS_FILE', str(settings_file)):
            from utils.settings_migration import _migrate_memories_to_cortex
            _migrate_memories_to_cortex()

        result = json.loads(settings_file.read_text(encoding='utf-8'))
        assert result['cortexEnabled'] is False
        assert 'memoriesEnabled' not in result

    def test_already_migrated(self, tmp_path):
        """Bereits migriert — kein Crash, keine Änderung."""
        settings_file = tmp_path / "user_settings.json"
        original = {"cortexEnabled": True, "darkMode": True}
        settings_file.write_text(json.dumps(original), encoding='utf-8')

        with patch('utils.settings_migration._USER_SETTINGS_FILE', str(settings_file)):
            from utils.settings_migration import _migrate_memories_to_cortex
            _migrate_memories_to_cortex()

        result = json.loads(settings_file.read_text(encoding='utf-8'))
        assert result == original

    def test_no_settings_file(self, tmp_path):
        """Neuinstallation — keine user_settings.json → kein Crash."""
        non_existent = tmp_path / "not_here.json"

        with patch('utils.settings_migration._USER_SETTINGS_FILE', str(non_existent)):
            from utils.settings_migration import _migrate_memories_to_cortex
            _migrate_memories_to_cortex()  # Kein Fehler

    def test_idempotent_migration(self, tmp_path):
        """Mehrfacher Aufruf → identisches Ergebnis."""
        settings_file = tmp_path / "user_settings.json"
        settings_file.write_text(json.dumps({
            "memoriesEnabled": True,
        }), encoding='utf-8')

        with patch('utils.settings_migration._USER_SETTINGS_FILE', str(settings_file)):
            from utils.settings_migration import _migrate_memories_to_cortex
            _migrate_memories_to_cortex()
            _migrate_memories_to_cortex()  # 2. Aufruf ändert nichts

        result = json.loads(settings_file.read_text(encoding='utf-8'))
        assert result['cortexEnabled'] is True
        assert 'memoriesEnabled' not in result

    def test_corrupt_settings(self, tmp_path):
        """Korrupte user_settings.json → Fehler geloggt, kein Crash."""
        settings_file = tmp_path / "user_settings.json"
        settings_file.write_text("{invalid json", encoding='utf-8')

        with patch('utils.settings_migration._USER_SETTINGS_FILE', str(settings_file)):
            from utils.settings_migration import _migrate_memories_to_cortex
            _migrate_memories_to_cortex()  # Kein Fehler


class TestEnsureCortexSettings:
    """Testet cortex_settings.json Erstanlage und Key-Ergänzung."""

    def test_creates_new_file(self, tmp_path):
        """Erstellt cortex_settings.json wenn nicht vorhanden."""
        settings_file = tmp_path / "cortex_settings.json"

        with patch('utils.settings_migration._CORTEX_SETTINGS_FILE', str(settings_file)):
            from utils.settings_migration import _ensure_cortex_settings
            _ensure_cortex_settings()

        assert settings_file.exists()
        result = json.loads(settings_file.read_text(encoding='utf-8'))
        assert result['enabled'] is True
        assert result['frequency'] == 'medium'

    def test_preserves_existing_values(self, tmp_path):
        """Überschreibt keine bestehenden Werte."""
        settings_file = tmp_path / "cortex_settings.json"
        settings_file.write_text(json.dumps({
            "enabled": False,
            "frequency": "rare"
        }), encoding='utf-8')

        with patch('utils.settings_migration._CORTEX_SETTINGS_FILE', str(settings_file)):
            from utils.settings_migration import _ensure_cortex_settings
            _ensure_cortex_settings()

        result = json.loads(settings_file.read_text(encoding='utf-8'))
        assert result['enabled'] is False
        assert result['frequency'] == 'rare'

    def test_adds_missing_keys(self, tmp_path):
        """Ergänzt fehlende Keys."""
        settings_file = tmp_path / "cortex_settings.json"
        settings_file.write_text(json.dumps({
            "enabled": False
        }), encoding='utf-8')

        with patch('utils.settings_migration._CORTEX_SETTINGS_FILE', str(settings_file)):
            from utils.settings_migration import _ensure_cortex_settings
            _ensure_cortex_settings()

        result = json.loads(settings_file.read_text(encoding='utf-8'))
        assert result['enabled'] is False  # Bestehender Wert bleibt
        assert result['frequency'] == 'medium'  # Neuer Key ergänzt

    def test_corrupt_existing_file(self, tmp_path):
        """Korrupte cortex_settings.json → Fehler geloggt, kein Crash."""
        settings_file = tmp_path / "cortex_settings.json"
        settings_file.write_text("not json!", encoding='utf-8')

        with patch('utils.settings_migration._CORTEX_SETTINGS_FILE', str(settings_file)):
            from utils.settings_migration import _ensure_cortex_settings
            _ensure_cortex_settings()  # Kein Crash


class TestMigrateSettings:
    """Testet die kombinierte migrate_settings() Funktion."""

    def test_full_migration(self, tmp_path):
        """Vollständige Migration: beide Schritte."""
        user_settings = tmp_path / "user_settings.json"
        user_settings.write_text(json.dumps({"memoriesEnabled": True}), encoding='utf-8')
        cortex_settings = tmp_path / "cortex_settings.json"

        with patch('utils.settings_migration._USER_SETTINGS_FILE', str(user_settings)), \
             patch('utils.settings_migration._CORTEX_SETTINGS_FILE', str(cortex_settings)):
            from utils.settings_migration import migrate_settings
            migrate_settings()

        user_result = json.loads(user_settings.read_text(encoding='utf-8'))
        assert user_result['cortexEnabled'] is True
        assert 'memoriesEnabled' not in user_result

        cortex_result = json.loads(cortex_settings.read_text(encoding='utf-8'))
        assert cortex_result['enabled'] is True
        assert cortex_result['frequency'] == 'medium'


# ═════════════════════════════════════════════════════════════════════════════
#  6D: Cortex Slash Command Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestCortexUpdateEndpoint:
    """Testet den POST /api/commands/cortex-update Endpoint."""

    def test_successful_cortex_update_config_check(self, tmp_path):
        """Prüft dass _load_cortex_config mit enabled=True funktioniert."""
        settings_dir = tmp_path / "settings"
        settings_dir.mkdir()
        (settings_dir / "cortex_settings.json").write_text(
            json.dumps({"enabled": True, "frequency": "often"}), encoding='utf-8'
        )

        from utils.cortex.tier_checker import _load_cortex_config
        with patch('utils.cortex.tier_checker._BASE_DIR', str(tmp_path)):
            config = _load_cortex_config()
            assert config['enabled'] is True
            assert config['frequency'] == 'often'

    def test_cortex_disabled_returns_error(self, tmp_path):
        """Cortex deaktiviert → _load_cortex_config gibt enabled=False."""
        settings_file = tmp_path / "cortex_settings.json"
        settings_file.write_text(json.dumps({"enabled": False, "frequency": "medium"}), encoding='utf-8')

        from utils.cortex.tier_checker import _load_cortex_config
        with patch('utils.cortex.tier_checker._BASE_DIR', str(tmp_path)):
            # cortex_settings.json muss unter tmp_path/settings/ liegen
            settings_dir = tmp_path / "settings"
            settings_dir.mkdir()
            (settings_dir / "cortex_settings.json").write_text(
                json.dumps({"enabled": False, "frequency": "medium"}), encoding='utf-8'
            )
            config = _load_cortex_config()
            assert config['enabled'] is False

    def test_tier_checker_imports_available(self):
        """Prüft dass alle nötigen tier_checker Funktionen importierbar sind."""
        from utils.cortex.tier_checker import (
            _load_cortex_config,
            _get_context_limit,
            _calculate_threshold,
            _start_background_cortex_update,
            DEFAULT_FREQUENCY,
        )
        assert callable(_load_cortex_config)
        assert callable(_get_context_limit)
        assert callable(_calculate_threshold)
        assert callable(_start_background_cortex_update)
        assert isinstance(DEFAULT_FREQUENCY, str)

    def test_tier_tracker_imports_available(self):
        """Prüft dass alle nötigen tier_tracker Funktionen importierbar sind."""
        from utils.cortex.tier_tracker import set_cycle_base, get_progress
        assert callable(set_cycle_base)
        assert callable(get_progress)


# ═════════════════════════════════════════════════════════════════════════════
#  6A: Chat.py Integration Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestChatRouteImports:
    """Prüft dass chat.py alle nötigen Cortex-Imports hat."""

    def test_check_and_trigger_import(self):
        """check_and_trigger_cortex_update ist importierbar."""
        from utils.cortex.tier_checker import check_and_trigger_cortex_update
        assert callable(check_and_trigger_cortex_update)

    def test_chat_route_has_cortex_import(self):
        """chat.py importiert check_and_trigger_cortex_update."""
        chat_path = os.path.join(SRC_DIR, 'routes', 'chat.py')
        with open(chat_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert 'check_and_trigger_cortex_update' in source

    def test_regenerate_has_cortex_check(self):
        """api_regenerate() enthält Cortex-Trigger-Check."""
        chat_path = os.path.join(SRC_DIR, 'routes', 'chat.py')
        with open(chat_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # Finde den regenerate-Bereich und prüfe auf cortex check
        regen_idx = source.find('def api_regenerate')
        assert regen_idx > 0
        regen_section = source[regen_idx:]
        assert 'check_and_trigger_cortex_update' in regen_section
        assert 'cortex_info' in regen_section


# ═════════════════════════════════════════════════════════════════════════════
#  6B: Startup Integration Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestStartupIntegration:
    """Prüft die Startup-Verdrahtung."""

    def test_startup_has_ensure_cortex_dirs(self):
        """startup.py ruft ensure_cortex_dirs() auf."""
        startup_path = os.path.join(SRC_DIR, 'splash_screen', 'utils', 'startup.py')
        with open(startup_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert 'ensure_cortex_dirs' in source
        assert 'from utils.cortex_service import ensure_cortex_dirs' in source

    def test_startup_has_migrate_settings(self):
        """startup.py ruft migrate_settings() auf."""
        startup_path = os.path.join(SRC_DIR, 'splash_screen', 'utils', 'startup.py')
        with open(startup_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert 'migrate_settings' in source

    def test_app_fallback_has_cortex_init(self):
        """app.py Fallback-Pfade rufen ensure_cortex_dirs() und migrate_settings() auf."""
        app_path = os.path.join(SRC_DIR, 'app.py')
        with open(app_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert source.count('ensure_cortex_dirs') >= 2  # Mindestens 2 Fallback-Stellen
        assert source.count('migrate_settings') >= 2

    def test_defaults_json_has_cortex_enabled(self):
        """defaults.json enthält cortexEnabled statt memoriesEnabled."""
        defaults_path = os.path.join(SRC_DIR, 'settings', 'defaults.json')
        with open(defaults_path, 'r', encoding='utf-8') as f:
            defaults = json.load(f)
        assert 'cortexEnabled' in defaults
        assert 'memoriesEnabled' not in defaults

    def test_defaults_json_has_cortex_frequency(self):
        """defaults.json enthält cortexFrequency."""
        defaults_path = os.path.join(SRC_DIR, 'settings', 'defaults.json')
        with open(defaults_path, 'r', encoding='utf-8') as f:
            defaults = json.load(f)
        assert 'cortexFrequency' in defaults
        assert defaults['cortexFrequency'] == 'medium'


# ═════════════════════════════════════════════════════════════════════════════
#  6D: Frontend Command Registration Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestFrontendCortexCommand:
    """Prüft die Frontend-Registrierung des /cortex Commands."""

    def test_builtin_commands_has_cortex(self):
        """builtinCommands.js registriert /cortex."""
        cmd_path = os.path.join(
            _WORKSPACE,
            'frontend', 'src', 'features', 'chat', 'slashCommands', 'builtinCommands.js'
        )
        with open(cmd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "name: 'cortex'" in source
        assert '/api/commands/cortex-update' in source
        assert 'cortex-update' in source

    def test_commands_route_has_endpoint(self):
        """commands.py hat den cortex-update Endpoint."""
        cmd_path = os.path.join(SRC_DIR, 'routes', 'commands.py')
        with open(cmd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert '/api/commands/cortex-update' in source
        assert 'def cortex_update' in source


# ═════════════════════════════════════════════════════════════════════════════
#  Provider / Route Registration Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestProviderAndRoutes:
    """Prüft dass Provider und Routen korrekt verdrahtet sind."""

    def test_provider_has_cortex_service(self):
        """provider.py hat CortexService statt MemoryService."""
        provider_path = os.path.join(SRC_DIR, 'utils', 'provider.py')
        with open(provider_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert 'CortexService' in source
        assert 'get_cortex_service' in source
        assert 'MemoryService' not in source

    def test_routes_register_cortex_bp(self):
        """routes/__init__.py registriert cortex_bp."""
        routes_init_path = os.path.join(SRC_DIR, 'routes', '__init__.py')
        with open(routes_init_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert 'cortex_bp' in source
        assert 'memory_bp' not in source

    def test_no_memory_imports_in_chat_service(self):
        """chat_service.py hat keine Memory-Imports mehr."""
        cs_path = os.path.join(SRC_DIR, 'utils', 'services', 'chat_service.py')
        with open(cs_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert '_load_memory_context' not in source
        assert 'MemoryService' not in source
        assert '_load_cortex_context' in source
