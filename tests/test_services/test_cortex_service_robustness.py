"""
Tests für Step 7: CortexService Robustness Fixes

Testet:
- 7B#1: Atomare Schreibvorgänge (tempfile + os.replace)
- 7B#2: Dateigröße-Limit (MAX_CORTEX_FILE_SIZE)
- 7B#7: In-Memory-Cache mit Write-Through
- 7B#15: Thread-Tracking im Tier-Checker
- 7B#16: Prompt-Injection-Hardening in Guidance-Templates
"""

import json
import os
import threading
import time
import pytest
from unittest.mock import patch, MagicMock

from utils.cortex_service import CortexService, MAX_CORTEX_FILE_SIZE


# ═════════════════════════════════════════════════════════════════════════════
#  7B#1: Atomare Schreibvorgänge
# ═════════════════════════════════════════════════════════════════════════════

class TestAtomicWrites:
    """Prüft dass write_file() atomar schreibt (tempfile + os.replace)."""

    def test_write_creates_file(self, tmp_path):
        """Normaler Schreibvorgang erstellt die Datei korrekt."""
        cortex_dir = tmp_path / "cortex" / "default"
        cortex_dir.mkdir(parents=True)
        (cortex_dir / "memory.md").write_text("", encoding="utf-8")
        (cortex_dir / "soul.md").write_text("", encoding="utf-8")
        (cortex_dir / "relationship.md").write_text("", encoding="utf-8")

        api_client = MagicMock()
        service = CortexService(api_client)

        with patch.object(service, 'get_cortex_path', return_value=str(cortex_dir)), \
             patch.object(service, 'ensure_cortex_files'):
            service.write_file('default', 'memory.md', 'Test Content')

        assert (cortex_dir / "memory.md").read_text(encoding="utf-8") == 'Test Content'

    def test_write_no_tmp_files_left(self, tmp_path):
        """Nach erfolgreichem Schreiben bleiben keine .tmp Dateien übrig."""
        cortex_dir = tmp_path / "cortex" / "default"
        cortex_dir.mkdir(parents=True)
        for f in ['memory.md', 'soul.md', 'relationship.md']:
            (cortex_dir / f).write_text("", encoding="utf-8")

        api_client = MagicMock()
        service = CortexService(api_client)

        with patch.object(service, 'get_cortex_path', return_value=str(cortex_dir)), \
             patch.object(service, 'ensure_cortex_files'):
            service.write_file('default', 'memory.md', 'Content')

        tmp_files = list(cortex_dir.glob('*.tmp'))
        assert len(tmp_files) == 0

    def test_write_overwrites_completely(self, tmp_path):
        """Schreibvorgang überschreibt alten Inhalt vollständig."""
        cortex_dir = tmp_path / "cortex" / "default"
        cortex_dir.mkdir(parents=True)
        (cortex_dir / "memory.md").write_text("Old Content hier", encoding="utf-8")
        (cortex_dir / "soul.md").write_text("", encoding="utf-8")
        (cortex_dir / "relationship.md").write_text("", encoding="utf-8")

        api_client = MagicMock()
        service = CortexService(api_client)

        with patch.object(service, 'get_cortex_path', return_value=str(cortex_dir)), \
             patch.object(service, 'ensure_cortex_files'):
            service.write_file('default', 'memory.md', 'New Content')

        assert (cortex_dir / "memory.md").read_text(encoding="utf-8") == 'New Content'

    def test_write_invalid_filename_raises(self, tmp_path):
        """Ungültiger Dateiname wirft ValueError."""
        api_client = MagicMock()
        service = CortexService(api_client)

        with pytest.raises(ValueError, match="Ungültige Cortex-Datei"):
            service.write_file('default', 'evil.md', 'content')


# ═════════════════════════════════════════════════════════════════════════════
#  7B#2: Dateigröße-Limit
# ═════════════════════════════════════════════════════════════════════════════

class TestFileSizeLimit:
    """Prüft dass write_file() Content auf MAX_CORTEX_FILE_SIZE kürzt."""

    def test_within_limit_unchanged(self, tmp_path):
        """Content innerhalb des Limits wird unverändert geschrieben."""
        cortex_dir = tmp_path / "cortex" / "default"
        cortex_dir.mkdir(parents=True)
        for f in ['memory.md', 'soul.md', 'relationship.md']:
            (cortex_dir / f).write_text("", encoding="utf-8")

        api_client = MagicMock()
        service = CortexService(api_client)
        content = "A" * 1000  # Weit unter dem Limit

        with patch.object(service, 'get_cortex_path', return_value=str(cortex_dir)), \
             patch.object(service, 'ensure_cortex_files'):
            service.write_file('default', 'memory.md', content)

        result = (cortex_dir / "memory.md").read_text(encoding="utf-8")
        assert len(result) == 1000

    def test_exceeds_limit_truncated(self, tmp_path):
        """Content über dem Limit wird gekürzt."""
        cortex_dir = tmp_path / "cortex" / "default"
        cortex_dir.mkdir(parents=True)
        for f in ['memory.md', 'soul.md', 'relationship.md']:
            (cortex_dir / f).write_text("", encoding="utf-8")

        api_client = MagicMock()
        service = CortexService(api_client)
        content = "B" * (MAX_CORTEX_FILE_SIZE + 5000)  # Weit über dem Limit

        with patch.object(service, 'get_cortex_path', return_value=str(cortex_dir)), \
             patch.object(service, 'ensure_cortex_files'):
            service.write_file('default', 'memory.md', content)

        result = (cortex_dir / "memory.md").read_text(encoding="utf-8")
        assert len(result) == MAX_CORTEX_FILE_SIZE

    def test_exactly_at_limit(self, tmp_path):
        """Content genau am Limit wird nicht gekürzt."""
        cortex_dir = tmp_path / "cortex" / "default"
        cortex_dir.mkdir(parents=True)
        for f in ['memory.md', 'soul.md', 'relationship.md']:
            (cortex_dir / f).write_text("", encoding="utf-8")

        api_client = MagicMock()
        service = CortexService(api_client)
        content = "C" * MAX_CORTEX_FILE_SIZE

        with patch.object(service, 'get_cortex_path', return_value=str(cortex_dir)), \
             patch.object(service, 'ensure_cortex_files'):
            service.write_file('default', 'memory.md', content)

        result = (cortex_dir / "memory.md").read_text(encoding="utf-8")
        assert len(result) == MAX_CORTEX_FILE_SIZE

    def test_max_cortex_file_size_constant(self):
        """MAX_CORTEX_FILE_SIZE hat den erwarteten Wert."""
        assert MAX_CORTEX_FILE_SIZE == 8000


# ═════════════════════════════════════════════════════════════════════════════
#  7B#7: In-Memory-Cache
# ═════════════════════════════════════════════════════════════════════════════

class TestCortexCache:
    """Prüft den In-Memory-Cache mit Write-Through."""

    def _make_service_with_dir(self, tmp_path):
        """Erstellt einen CortexService mit temporären Dateien."""
        cortex_dir = tmp_path / "cortex" / "default"
        cortex_dir.mkdir(parents=True)
        (cortex_dir / "memory.md").write_text("Cached Memory", encoding="utf-8")
        (cortex_dir / "soul.md").write_text("Cached Soul", encoding="utf-8")
        (cortex_dir / "relationship.md").write_text("Cached Rel", encoding="utf-8")

        api_client = MagicMock()
        service = CortexService(api_client)
        return service, cortex_dir

    def test_read_populates_cache(self, tmp_path):
        """Erster read_file() befüllt den Cache."""
        service, cortex_dir = self._make_service_with_dir(tmp_path)

        with patch.object(service, 'get_cortex_path', return_value=str(cortex_dir)), \
             patch.object(service, 'ensure_cortex_files'):
            result = service.read_file('default', 'memory.md')

        assert result == "Cached Memory"
        assert 'default' in service._cache
        assert service._cache['default']['memory.md'] == "Cached Memory"

    def test_second_read_uses_cache(self, tmp_path):
        """Zweiter read_file() nutzt den Cache (kein Disk-Zugriff)."""
        service, cortex_dir = self._make_service_with_dir(tmp_path)

        with patch.object(service, 'get_cortex_path', return_value=str(cortex_dir)), \
             patch.object(service, 'ensure_cortex_files'):
            # Erster Read
            service.read_file('default', 'memory.md')

            # Datei auf Disk ändern (simuliert externen Zugriff)
            (cortex_dir / "memory.md").write_text("Changed on Disk", encoding="utf-8")

            # Zweiter Read → sollte NICHT die Datei-Änderung sehen (Cache-Hit)
            result = service.read_file('default', 'memory.md')

        assert result == "Cached Memory"  # Cache-Wert, nicht Disk-Wert

    def test_write_updates_cache(self, tmp_path):
        """write_file() aktualisiert den Cache (Write-Through)."""
        service, cortex_dir = self._make_service_with_dir(tmp_path)

        with patch.object(service, 'get_cortex_path', return_value=str(cortex_dir)), \
             patch.object(service, 'ensure_cortex_files'):
            # Cache befüllen
            service.read_file('default', 'memory.md')
            assert service._cache['default']['memory.md'] == "Cached Memory"

            # Schreiben → Cache Update
            service.write_file('default', 'memory.md', 'New Content')
            assert service._cache['default']['memory.md'] == 'New Content'

            # Read gibt jetzt den neuen Wert zurück
            result = service.read_file('default', 'memory.md')
            assert result == 'New Content'

    def test_delete_clears_cache(self, tmp_path):
        """delete_cortex_dir() räumt den Cache auf."""
        service, cortex_dir = self._make_service_with_dir(tmp_path)

        # Custom Persona zum Testen
        custom_dir = tmp_path / "cortex" / "custom" / "abc123"
        custom_dir.mkdir(parents=True)
        for f in ['memory.md', 'soul.md', 'relationship.md']:
            (custom_dir / f).write_text("Custom", encoding="utf-8")

        # Cache befüllen
        service._cache['abc123'] = {'memory.md': 'Custom'}

        # delete_cortex_dir
        with patch('utils.cortex_service.delete_cortex_dir', return_value=True) as mock_del:
            service.delete_cortex_dir('abc123')

        assert 'abc123' not in service._cache

    def test_cache_has_lock(self):
        """Service hat ein _cache_lock für Thread-Safety."""
        api_client = MagicMock()
        service = CortexService(api_client)
        assert isinstance(service._cache_lock, type(threading.Lock()))


# ═════════════════════════════════════════════════════════════════════════════
#  7B#15: Thread-Tracking
# ═════════════════════════════════════════════════════════════════════════════

class TestThreadTracking:
    """Prüft das Thread-Tracking im Tier-Checker."""

    def test_active_updates_dict_exists(self):
        """_active_updates Dict und _active_lock existieren."""
        from utils.cortex.tier_checker import _active_updates, _active_lock
        assert isinstance(_active_updates, dict)
        # Lock-Typ prüfen (threading.Lock() ist _thread.lock in CPython)
        assert hasattr(_active_lock, 'acquire')
        assert hasattr(_active_lock, 'release')

    def test_no_threading_enumerate_usage(self):
        """tier_checker.py verwendet NICHT threading.enumerate()."""
        import utils.cortex.tier_checker as tc
        source_path = tc.__file__
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert 'threading.enumerate()' not in source


# ═════════════════════════════════════════════════════════════════════════════
#  7B#16: Prompt-Injection-Hardening
# ═════════════════════════════════════════════════════════════════════════════

class TestPromptInjectionHardening:
    """Prüft dass Guidance-Templates Anti-Injection-Regeln enthalten."""

    def test_externalized_template_has_hardening(self):
        """cortex_update_system.json enthält Anti-Injection-Regeln."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'src', 'instructions', 'prompts', 'cortex_update_system.json'
        )
        with open(template_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        content = data['cortex_update_system']['variants']['default']['content']
        assert 'ONLY facts and observations' in content
        assert 'NEVER write behavioral instructions' in content
        assert 'diary, not a rulebook' in content
        assert 'Keep compact' in content

    def test_defaults_template_matches(self):
        """_defaults/cortex_update_system.json hat dieselben Regeln."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'src', 'instructions', 'prompts', '_defaults', 'cortex_update_system.json'
        )
        with open(template_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        content = data['cortex_update_system']['variants']['default']['content']
        assert 'ONLY facts and observations' in content
        assert 'NEVER write behavioral instructions' in content

    def test_fallback_prompt_has_hardening(self):
        """Fallback-System-Prompt in update_service.py enthält Anti-Injection-Regeln."""
        import utils.cortex.update_service as us
        source_path = us.__file__
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert 'ONLY facts and observations' in source
        assert 'NEVER write behavioral instructions' in source
        assert 'diary, not a rulebook' in source


# ═════════════════════════════════════════════════════════════════════════════
#  7B#9: SSE Done Event Frontend Matching
# ═════════════════════════════════════════════════════════════════════════════

class TestSSEDoneEventMatching:
    """Prüft dass Frontend und Backend dasselbe Feld für Cortex-Daten verwenden."""

    def test_backend_sends_cortex_field(self):
        """chat.py sendet done_payload['cortex']."""
        chat_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'src', 'routes', 'chat.py'
        )
        with open(chat_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "done_payload['cortex']" in source
        assert "done_payload['cortex_update']" not in source

    def test_frontend_reads_cortex_field(self):
        """useMessages.js prüft data.cortex (nicht data.cortex_update)."""
        hook_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'frontend', 'src', 'features', 'chat', 'hooks', 'useMessages.js'
        )
        with open(hook_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert 'data.cortex?.triggered' in source
        assert 'data.cortex_update' not in source
