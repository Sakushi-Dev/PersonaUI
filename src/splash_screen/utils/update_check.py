"""Update-Check: Prüft ob auf origin/main eine neue stabile Version verfügbar ist."""

import json
import os
import subprocess

# Pfad zur Marker-Datei, die den letzten Update-Commit speichert
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)  # PersonaUI/
_SRC_DIR = os.path.join(_PROJECT_ROOT, 'src')
_MARKER_FILE = os.path.join(_SRC_DIR, 'settings', 'update_state.json')


def _run_git(*args: str) -> str | None:
    """Führt einen Git-Befehl aus und gibt stdout zurück (oder None bei Fehler)."""
    try:
        result = subprocess.run(
            ['git'] + list(args),
            cwd=_PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def get_last_update_commit() -> str | None:
    """Liest den gespeicherten Commit-Hash des letzten Updates."""
    try:
        if os.path.exists(_MARKER_FILE):
            with open(_MARKER_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('commit') or None
    except (json.JSONDecodeError, OSError):
        pass
    return None


def save_current_main_commit():
    """Speichert den aktuellen origin/main Commit als 'letztes Update'."""
    commit = _run_git('rev-parse', 'origin/main')
    if commit:
        try:
            os.makedirs(os.path.dirname(_MARKER_FILE), exist_ok=True)
            with open(_MARKER_FILE, 'w', encoding='utf-8') as f:
                json.dump({'commit': commit}, f, indent=2)
        except Exception:
            pass


def check_for_update() -> dict:
    """Prüft ob eine neue stabile Version auf origin/main verfügbar ist.

    Returns:
        dict mit:
            - available (bool): True wenn neues Update vorhanden
            - current (str|None): Aktueller gespeicherter Commit
            - remote (str|None): Neuester Commit auf origin/main
            - new_commits (int): Anzahl neuer Commits seit letztem Update
            - error (str|None): Fehlermeldung falls etwas schiefging
    """
    result = {
        'available': False,
        'current': None,
        'remote': None,
        'new_commits': 0,
        'error': None,
    }

    # 1. Fetch origin/main (leise, ohne Ausgabe)
    fetch_out = _run_git('fetch', 'origin', 'main', '--quiet')
    if fetch_out is None:
        # Fetch fehlgeschlagen (kein Netz, kein Git, etc.)
        result['error'] = 'Fetch fehlgeschlagen (kein Netzwerk?)'
        return result

    # 2. Aktuellen origin/main Commit-Hash holen
    remote_commit = _run_git('rev-parse', 'origin/main')
    if not remote_commit:
        result['error'] = 'origin/main nicht gefunden'
        return result
    result['remote'] = remote_commit

    # 3. Gespeicherten Commit lesen (Marker-Datei)
    last_commit = get_last_update_commit()
    result['current'] = last_commit

    # 4. Falls kein Marker existiert → ersten Marker setzen, kein Update melden
    if not last_commit:
        save_current_main_commit()
        return result

    # 5. Vergleichen
    if last_commit == remote_commit:
        return result  # Kein Update

    # 6. Anzahl neuer Commits zählen
    count_str = _run_git('rev-list', '--count', f'{last_commit}..{remote_commit}')
    try:
        result['new_commits'] = int(count_str) if count_str else 0
    except ValueError:
        result['new_commits'] = 0

    if result['new_commits'] > 0:
        result['available'] = True

    return result
