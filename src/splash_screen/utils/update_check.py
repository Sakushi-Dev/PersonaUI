"""Update check: Compares local version against origin/main to detect new releases."""

import json
import os
import subprocess
from packaging.version import Version, InvalidVersion

# ── Paths ──────────────────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)  # PersonaUI/
_VERSION_FILE = os.path.join(_PROJECT_ROOT, 'config', 'version.json')
_VERSION_FILE_FALLBACK = os.path.join(_PROJECT_ROOT, 'version.json')  # Legacy fallback
_CHANGELOG_FILE = os.path.join(_PROJECT_ROOT, 'config', 'changelog.json')
_CHANGELOG_FILE_FALLBACK = os.path.join(_PROJECT_ROOT, 'changelog.json')  # Legacy fallback
_UPDATE_STATE_FILE = os.path.join(_PROJECT_ROOT, 'src', 'settings', 'update_state.json')


# ── Git helper ─────────────────────────────────────────────────────────────

def _run_git(*args: str) -> str | None:
    """Run a git command and return stdout (or None on failure)."""
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


# ── Local version ──────────────────────────────────────────────────────────

def get_local_version() -> str | None:
    """Read the current version from the local version.json."""
    for path in (_VERSION_FILE, _VERSION_FILE_FALLBACK):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                ver = data.get('version') or None
                if ver:
                    return ver
        except (json.JSONDecodeError, OSError):
            continue
    return None


# ── Remote version ─────────────────────────────────────────────────────────

def get_remote_version() -> tuple[str | None, str | None]:
    """Fetch origin/main and read version.json from the remote branch.
    
    Returns:
        (version, error) tuple. Error is None on success, or a descriptive string.
    """
    # Fetch latest state
    fetch_result = _run_git('fetch', 'origin', 'main', '--quiet')
    if fetch_result is None:
        return None, 'no_network'

    # Read version.json from origin/main (try config/ first, fallback to root)
    raw = _run_git('show', 'origin/main:config/version.json')
    if not raw:
        raw = _run_git('show', 'origin/main:version.json')  # Legacy fallback
    if not raw:
        return None, 'no_version_file'

    try:
        data = json.loads(raw)
        ver = data.get('version')
        if ver:
            return ver, None
        return None, 'no_version_field'
    except (json.JSONDecodeError, KeyError):
        return None, 'invalid_json'


def get_remote_changelog() -> list[dict] | None:
    """Read changelog.json from origin/main (config/ primary, root fallback)."""
    raw = _run_git('show', 'origin/main:config/changelog.json')
    if not raw:
        raw = _run_git('show', 'origin/main:changelog.json')  # Legacy fallback
    if raw:
        try:
            data = json.loads(raw)
            return data.get('versions', [])
        except (json.JSONDecodeError, KeyError):
            pass
    return None


# ── Update state ───────────────────────────────────────────────────────────

def get_installed_version() -> str | None:
    """Read the last successfully installed version from update_state.json."""
    try:
        if os.path.exists(_UPDATE_STATE_FILE):
            with open(_UPDATE_STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('version') or None
    except (json.JSONDecodeError, OSError):
        pass
    return None


def save_installed_version(version: str):
    """Save the current version to update_state.json after a successful update."""
    try:
        os.makedirs(os.path.dirname(_UPDATE_STATE_FILE), exist_ok=True)
        with open(_UPDATE_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'version': version}, f, indent=2)
    except Exception:
        pass


# ── Version comparison ─────────────────────────────────────────────────────

def _normalize_version(v: str) -> str:
    """Convert version strings like '0.2.0-alpha' to PEP 440 format '0.2.0a0'."""
    return v.replace('-alpha', 'a0').replace('-beta', 'b0').replace('-rc', 'rc0')


def is_newer(remote_ver: str, local_ver: str) -> bool:
    """Return True if remote_ver is strictly newer than local_ver."""
    try:
        return Version(_normalize_version(remote_ver)) > Version(_normalize_version(local_ver))
    except InvalidVersion:
        return remote_ver != local_ver


# ── Main check ─────────────────────────────────────────────────────────────

def check_for_update() -> dict:
    """Check if a newer version is available on origin/main.

    Returns:
        dict with:
            - available (bool): True if a new version is available
            - local_version (str|None): Currently installed version
            - remote_version (str|None): Latest version on origin/main
            - remote_changelog (list|None): Version history from origin/main
            - error (str|None): Error message if something went wrong
    """
    result = {
        'available': False,
        'local_version': None,
        'remote_version': None,
        'remote_changelog': None,
        'error': None,
    }

    # 1. Read local version
    local_ver = get_local_version()
    result['local_version'] = local_ver

    if not local_ver:
        result['error'] = 'Local version.json not found or invalid'
        return result

    # 2. Fetch & read remote version
    remote_ver, fetch_error = get_remote_version()
    result['remote_version'] = remote_ver

    if fetch_error == 'no_network':
        result['error'] = 'Could not fetch remote version (no network?)'
        return result
    elif fetch_error == 'no_version_file':
        # Remote doesn't have version.json yet — nothing to compare against
        result['error'] = None  # Not an error, just no version tracking on remote yet
        return result
    elif fetch_error:
        result['error'] = f'Remote version.json issue: {fetch_error}'
        return result

    # 3. Compare versions
    if is_newer(remote_ver, local_ver):
        result['available'] = True
        result['remote_changelog'] = get_remote_changelog()

    # 4. First-run: seed update_state.json if it doesn't exist yet
    if not get_installed_version():
        save_installed_version(local_ver)

    return result
