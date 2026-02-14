"""
Tests für Phase 5 – Export, Import, Factory Reset, Integrity.

Testet:
- export_prompt_set (ZIP-Export)
- import_prompt_set (Replace, Merge, Overwrite)
- factory_reset (Wiederherstellung aus _defaults)
- validate_integrity (Korruptionserkennung + Recovery)
"""

import os
import json
import shutil
import zipfile
import pytest

# ===== Shared Fixture =====

@pytest.fixture
def engine_dir(tmp_path):
    """Erstellt ein temporäres instructions/ Setup mit _defaults/ für Tests."""
    instructions_dir = tmp_path / 'instructions'
    instructions_dir.mkdir()
    prompts_dir = instructions_dir / 'prompts'
    prompts_dir.mkdir()
    defaults_dir = prompts_dir / '_defaults'
    defaults_dir.mkdir()

    # Manifest
    manifest = {
        "version": "2.0",
        "prompts": {
            "test_prompt": {
                "name": "Test",
                "description": "Ein Test-Prompt",
                "category": "system",
                "type": "text",
                "target": "system_prompt",
                "position": "system_prompt",
                "order": 100,
                "enabled": True,
                "domain_file": "test.json",
                "tags": ["test"]
            }
        }
    }
    meta_dir = prompts_dir / '_meta'
    meta_dir.mkdir()
    (meta_dir / 'prompt_manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # Registry
    registry = {
        "version": "2.0",
        "placeholders": {
            "char_name": {
                "name": "Persona-Name",
                "source": "persona_config",
                "source_path": "persona_settings.name",
                "type": "string",
                "default": "Assistant",
                "category": "persona",
                "resolve_phase": "static"
            }
        }
    }
    (meta_dir / 'placeholder_registry.json').write_text(
        json.dumps(registry, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # Domain-Datei
    domain = {
        "test_prompt": {
            "variants": {
                "default": {"content": "Original content."}
            },
            "placeholders_used": []
        }
    }
    (prompts_dir / 'test.json').write_text(
        json.dumps(domain, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # _defaults: Kopien
    defaults_meta_dir = defaults_dir / '_meta'
    defaults_meta_dir.mkdir()
    for filename in ('prompt_manifest.json', 'placeholder_registry.json'):
        src = meta_dir / filename
        shutil.copy2(str(src), str(defaults_meta_dir / filename))
    shutil.copy2(str(prompts_dir / 'test.json'), str(defaults_dir / 'test.json'))

    # Persona Config (für Resolver)
    personas_dir = instructions_dir / 'personas' / 'active'
    personas_dir.mkdir(parents=True)
    persona_config = {
        "active_persona_id": "test",
        "persona_settings": {"name": "TestPersona"}
    }
    (personas_dir / 'persona_config.json').write_text(
        json.dumps(persona_config, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # Settings (für user_name)
    settings_dir = tmp_path / 'settings'
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / 'user_profile.json').write_text(
        json.dumps({"user_name": "TestUser"}, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    return str(instructions_dir)


def _make_engine(instructions_dir):
    """Erstellt eine PromptEngine ohne echte compute-functions."""
    from src.utils.prompt_engine import PromptEngine
    engine = PromptEngine(instructions_dir)
    if engine._resolver:
        engine._resolver._compute_functions = {}
    return engine


# ===== Export Tests =====

class TestExportPromptSet:
    """Tests für export_prompt_set()."""

    def test_export_creates_zip(self, engine_dir, tmp_path):
        """Export erstellt eine ZIP-Datei."""
        engine = _make_engine(engine_dir)
        output = str(tmp_path / 'export' / 'test_export.zip')

        result = engine.export_prompt_set(output)
        assert os.path.exists(result)
        assert result == output

    def test_export_zip_contents(self, engine_dir, tmp_path):
        """ZIP enthält Manifest, Registry, Domain-Dateien und Metadata."""
        engine = _make_engine(engine_dir)
        output = str(tmp_path / 'export.zip')
        engine.export_prompt_set(output)

        with zipfile.ZipFile(output, 'r') as zf:
            names = zf.namelist()
            assert '_meta/prompt_manifest.json' in names
            assert '_meta/placeholder_registry.json' in names
            assert 'prompts/test.json' in names
            assert 'metadata.json' in names

    def test_export_metadata_content(self, engine_dir, tmp_path):
        """Metadata enthält erwartete Felder."""
        engine = _make_engine(engine_dir)
        output = str(tmp_path / 'export.zip')
        engine.export_prompt_set(output)

        with zipfile.ZipFile(output, 'r') as zf:
            metadata = json.loads(zf.read('metadata.json'))
            assert 'export_date' in metadata
            assert metadata['version'] == '2.0'
            assert metadata['prompt_count'] == 1
            assert 'test.json' in metadata['domain_files']

    def test_export_excludes_defaults(self, engine_dir, tmp_path):
        """_defaults/ wird nicht mit exportiert."""
        engine = _make_engine(engine_dir)
        output = str(tmp_path / 'export.zip')
        engine.export_prompt_set(output)

        with zipfile.ZipFile(output, 'r') as zf:
            names = zf.namelist()
            assert not any('_defaults' in n for n in names)


# ===== Import Tests =====

class TestImportPromptSet:
    """Tests für import_prompt_set()."""

    def _create_import_zip(self, tmp_path, domain_content="Imported content."):
        """Erstellt ein Import-ZIP."""
        zip_path = str(tmp_path / 'import.zip')
        manifest = {
            "version": "3.0",
            "prompts": {
                "test_prompt": {
                    "name": "Imported Test",
                    "type": "text",
                    "target": "system_prompt",
                    "position": "system_prompt",
                    "order": 100,
                    "enabled": True,
                    "domain_file": "test.json"
                },
                "new_prompt": {
                    "name": "New",
                    "type": "text",
                    "target": "system_prompt",
                    "position": "system_prompt",
                    "order": 200,
                    "enabled": True,
                    "domain_file": "new.json"
                }
            }
        }
        domain = {
            "test_prompt": {
                "variants": {"default": {"content": domain_content}},
                "placeholders_used": []
            }
        }
        new_domain = {
            "new_prompt": {
                "variants": {"default": {"content": "Brand new prompt."}},
                "placeholders_used": []
            }
        }

        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('_meta/prompt_manifest.json', json.dumps(manifest, indent=2))
            zf.writestr('prompts/test.json', json.dumps(domain, indent=2))
            zf.writestr('prompts/new.json', json.dumps(new_domain, indent=2))
            zf.writestr('metadata.json', json.dumps({"export_date": "2026-01-01"}))

        return zip_path

    def test_import_replace(self, engine_dir, tmp_path):
        """Import-Modus 'replace' ersetzt alles."""
        engine = _make_engine(engine_dir)
        zip_path = self._create_import_zip(tmp_path)

        result = engine.import_prompt_set(zip_path, merge_mode='replace')
        assert result['imported'] >= 2  # manifest + domain
        assert len(result['errors']) == 0

        # Manifest Version sollte jetzt 3.0 sein
        manifest = engine._loader.load_manifest()
        assert manifest['version'] == '3.0'

    def test_import_merge_skips_existing(self, engine_dir, tmp_path):
        """Import-Modus 'merge' überspringt bestehende Dateien."""
        engine = _make_engine(engine_dir)
        zip_path = self._create_import_zip(tmp_path)

        result = engine.import_prompt_set(zip_path, merge_mode='merge')
        assert result['skipped'] >= 1  # manifest + test.json existieren
        # new.json sollte importiert worden sein
        new_path = os.path.join(engine_dir, 'prompts', 'new.json')
        assert os.path.exists(new_path)

    def test_import_overwrite_replaces_existing(self, engine_dir, tmp_path):
        """Import-Modus 'overwrite' überschreibt bestehende Dateien."""
        engine = _make_engine(engine_dir)
        zip_path = self._create_import_zip(tmp_path, domain_content="Overwritten!")

        result = engine.import_prompt_set(zip_path, merge_mode='overwrite')
        assert result['imported'] >= 2
        assert result['skipped'] == 0

    def test_import_invalid_mode_raises(self, engine_dir, tmp_path):
        """Ungültiger merge_mode wirft ValueError."""
        engine = _make_engine(engine_dir)
        zip_path = self._create_import_zip(tmp_path)

        with pytest.raises(ValueError, match='invalid'):
            engine.import_prompt_set(zip_path, merge_mode='invalid')

    def test_import_missing_zip_raises(self, engine_dir):
        """Fehlende ZIP-Datei wirft FileNotFoundError."""
        engine = _make_engine(engine_dir)

        with pytest.raises(FileNotFoundError):
            engine.import_prompt_set('/nonexistent/file.zip')

    def test_import_invalid_zip_returns_error(self, engine_dir, tmp_path):
        """Ungültige ZIP-Datei gibt Fehler zurück."""
        bad_path = str(tmp_path / 'bad.zip')
        with open(bad_path, 'w') as f:
            f.write("not a zip file")

        engine = _make_engine(engine_dir)
        result = engine.import_prompt_set(bad_path)
        assert len(result['errors']) > 0

    def test_import_zip_without_manifest_returns_error(self, engine_dir, tmp_path):
        """ZIP ohne Manifest gibt Fehler zurück."""
        zip_path = str(tmp_path / 'no_manifest.zip')
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('prompts/test.json', '{}')

        engine = _make_engine(engine_dir)
        result = engine.import_prompt_set(zip_path)
        assert len(result['errors']) > 0
        assert 'manifest' in result['errors'][0].lower()

    def test_roundtrip_export_import(self, engine_dir, tmp_path):
        """Export → Import roundtrip erhält Daten."""
        engine = _make_engine(engine_dir)

        # Export
        export_path = str(tmp_path / 'roundtrip.zip')
        engine.export_prompt_set(export_path)

        # Domain-Datei modifizieren
        prompts_dir = os.path.join(engine_dir, 'prompts')
        modified = {"test_prompt": {"variants": {"default": {"content": "Modified!"}}, "placeholders_used": []}}
        with open(os.path.join(prompts_dir, 'test.json'), 'w', encoding='utf-8') as f:
            json.dump(modified, f)

        # Import (replace)
        result = engine.import_prompt_set(export_path, merge_mode='replace')
        assert len(result['errors']) == 0

        # Prüfen: Original wiederhergestellt
        domain = engine._loader.load_domain_file('test.json')
        assert domain['test_prompt']['variants']['default']['content'] == 'Original content.'


# ===== Factory Reset Tests =====

class TestFactoryReset:
    """Tests für factory_reset()."""

    def test_factory_reset_restores_files(self, engine_dir):
        """Factory Reset stellt Dateien aus _defaults/ wieder her."""
        engine = _make_engine(engine_dir)

        # Domain-Datei modifizieren
        prompts_dir = os.path.join(engine_dir, 'prompts')
        modified = {"test_prompt": {"variants": {"default": {"content": "Modified!"}}, "placeholders_used": []}}
        with open(os.path.join(prompts_dir, 'test.json'), 'w', encoding='utf-8') as f:
            json.dump(modified, f)

        # Reset
        result = engine.factory_reset()
        assert result['restored'] >= 1
        assert len(result['errors']) == 0

        # Prüfen: Original wiederhergestellt
        domain = engine._loader.load_domain_file('test.json')
        assert domain['test_prompt']['variants']['default']['content'] == 'Original content.'

    def test_factory_reset_restores_manifest(self, engine_dir):
        """Factory Reset stellt auch Manifest wieder her."""
        engine = _make_engine(engine_dir)

        # Manifest modifizieren
        manifest = engine._loader.load_manifest()
        manifest['version'] = '999.0'
        engine._loader.save_manifest(manifest)

        result = engine.factory_reset()
        assert result['restored'] >= 1

        # Manifest sollte wieder original sein
        manifest = engine._loader.load_manifest()
        assert manifest['version'] == '2.0'

    def test_factory_reset_no_defaults_dir(self, tmp_path):
        """Factory Reset ohne _defaults/ Verzeichnis gibt Fehler."""
        instructions_dir = tmp_path / 'instructions'
        instructions_dir.mkdir()
        prompts_dir = instructions_dir / 'prompts'
        prompts_dir.mkdir()

        # Minimal-Manifest zum Laden
        meta_dir = prompts_dir / '_meta'
        meta_dir.mkdir()
        manifest = {"version": "1.0", "prompts": {}}
        (meta_dir / 'prompt_manifest.json').write_text(
            json.dumps(manifest), encoding='utf-8'
        )
        registry = {"version": "1.0", "placeholders": {}}
        (meta_dir / 'placeholder_registry.json').write_text(
            json.dumps(registry), encoding='utf-8'
        )

        engine = _make_engine(str(instructions_dir))
        result = engine.factory_reset()
        assert len(result['errors']) > 0
        assert 'nicht gefunden' in result['errors'][0] or '_defaults' in result['errors'][0]


# ===== Validate Integrity Tests =====

class TestValidateIntegrity:
    """Tests für validate_integrity()."""

    def test_all_valid(self, engine_dir):
        """Alle Dateien valide → valid=True."""
        engine = _make_engine(engine_dir)
        result = engine.validate_integrity()

        assert result['valid'] is True
        assert result['checked'] >= 3  # manifest + registry + domain
        assert result['recovered'] == 0
        assert len(result['errors']) == 0

    def test_corrupt_file_recovery_from_defaults(self, engine_dir):
        """Korrupte Datei wird aus _defaults/ wiederhergestellt."""
        prompts_dir = os.path.join(engine_dir, 'prompts')
        domain_path = os.path.join(prompts_dir, 'test.json')

        # Datei korrumpieren (kein .bak vorhanden)
        with open(domain_path, 'w') as f:
            f.write("NOT VALID JSON!!!")

        engine = _make_engine(engine_dir)
        result = engine.validate_integrity()

        assert result['recovered'] >= 1

    def test_missing_file_recovery_from_defaults(self, engine_dir):
        """Fehlende Domain-Datei wird aus _defaults/ wiederhergestellt."""
        prompts_dir = os.path.join(engine_dir, 'prompts')
        domain_path = os.path.join(prompts_dir, 'test.json')

        # Datei löschen
        os.remove(domain_path)

        engine = _make_engine(engine_dir)
        result = engine.validate_integrity()

        assert result['recovered'] >= 1
        assert os.path.exists(domain_path)

    def test_unrecoverable_corruption(self, tmp_path):
        """Nicht-wiederherstellbare Korruption → valid=False."""
        instructions_dir = tmp_path / 'instructions'
        instructions_dir.mkdir()
        prompts_dir = instructions_dir / 'prompts'
        prompts_dir.mkdir()

        # Korruptes Manifest (ohne _defaults und ohne .bak)
        meta_dir = prompts_dir / '_meta'
        meta_dir.mkdir()
        (meta_dir / 'prompt_manifest.json').write_text("{CORRUPT", encoding='utf-8')
        (meta_dir / 'placeholder_registry.json').write_text(
            json.dumps({"version": "1.0", "placeholders": {}}), encoding='utf-8'
        )

        engine = _make_engine(str(instructions_dir))
        result = engine.validate_integrity()

        assert result['valid'] is False
        assert len(result['errors']) > 0
