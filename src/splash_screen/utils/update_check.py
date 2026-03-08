"""Update check: Compares local version against origin/main to detect new releases."""

import configparser
import os
import subprocess
from packaging.version import Version, InvalidVersion

# ── Paths ──────────────────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)  # PersonaUI/
_VERSION_FILE = os.path.join(_PROJECT_ROOT, 'config', 'version.ini')


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
    """Read the current version from config/version.ini."""
    try:
        if os.path.exists(_VERSION_FILE):
            cp = configparser.ConfigParser()
            cp.read(_VERSION_FILE, encoding='utf-8')
            ver = cp.get('version', 'version', fallback=None)
            if ver:
                return ver.strip()
    except (configparser.Error, OSError):
        pass
    return None


# ── Remote version ─────────────────────────────────────────────────────────

def get_remote_version() -> tuple[str | None, str | None]:
    """Fetch origin/main and read version.ini from the remote branch.
    
    Returns:
        (version, error) tuple. Error is None on success, or a descriptive string.
    """
    # Fetch latest state
    fetch_result = _run_git('fetch', 'origin', 'main', '--quiet')
    if fetch_result is None:
        return None, 'no_network'

    # Read version.ini from origin/main
    raw = _run_git('show', 'origin/main:config/version.ini')
    if not raw:
        return None, 'no_version_file'

    try:
        cp = configparser.ConfigParser()
        cp.read_string(raw)
        ver = cp.get('version', 'version', fallback=None)
        if ver:
            return ver.strip(), None
        return None, 'no_version_field'
    except configparser.Error:
        return None, 'invalid_ini'


# ── Update state ───────────────────────────────────────────────────────────

def get_installed_version() -> str | None:
    """Read the last successfully installed version from settings.json (update_state)."""
    try:
        from utils.settings_manager import load_section
        data = load_section('update_state')
        return data.get('version') or None
    except Exception:
        pass
    return None


def save_installed_version(version: str):
    """Save the current version to settings.json (update_state) after a successful update."""
    try:
        from utils.settings_manager import save_section
        save_section('update_state', {'version': version})
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
            - error (str|None): Error message if something went wrong
    """
    result = {
        'available': False,
        'local_version': None,
        'remote_version': None,
        'error': None,
    }

    # 1. Read local version
    local_ver = get_local_version()
    result['local_version'] = local_ver

    if not local_ver:
        result['error'] = 'Local version.ini not found or invalid'
        return result

    # 2. Fetch & read remote version
    remote_ver, fetch_error = get_remote_version()
    result['remote_version'] = remote_ver

    if fetch_error == 'no_network':
        result['error'] = 'Could not fetch remote version (no network?)'
        return result
    elif fetch_error == 'no_version_file':
        result['error'] = None
        return result
    elif fetch_error:
        result['error'] = f'Remote version.ini issue: {fetch_error}'
        return result

    # 3. Compare versions
    if is_newer(remote_ver, local_ver):
        result['available'] = True

    # 4. First-run: seed update_state if it doesn't exist yet
    if not get_installed_version():
        save_installed_version(local_ver)

    return result
