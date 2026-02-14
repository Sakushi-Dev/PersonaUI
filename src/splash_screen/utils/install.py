"""Installations-Prüfung und Setup für PersonaUI.

Prüft Python-Version, virtuelle Umgebung und Abhängigkeiten.
Wird von init.py als Bootstrap-Modul importiert.
"""

import os
import sys
import subprocess
import importlib
import importlib.util


# ---------------------------------------------------------------------------
#  Konfiguration
# ---------------------------------------------------------------------------

MIN_PYTHON_MAJOR = 3
MIN_PYTHON_MINOR = 10


# ---------------------------------------------------------------------------
#  Hilfsfunktionen
# ---------------------------------------------------------------------------

def _get_project_root():
    """Gibt das Projekt-Root (PersonaUI/) zurück."""
    # src/splash_screen/utils/install.py → 3x hoch = src/, 4x = PersonaUI/
    return os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )


def _get_requirements_path():
    """Pfad zur requirements.txt."""
    return os.path.join(_get_project_root(), 'requirements.txt')


def _get_venv_python():
    """Pfad zur Python-Executable in .venv."""
    root = _get_project_root()
    if sys.platform == 'win32':
        return os.path.join(root, '.venv', 'Scripts', 'python.exe')
    return os.path.join(root, '.venv', 'bin', 'python')


def _running_in_venv():
    """Prüft ob wir bereits in der .venv laufen."""
    return (
        hasattr(sys, 'real_prefix')
        or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    )


# ---------------------------------------------------------------------------
#  Schritt 1: Python-Version prüfen
# ---------------------------------------------------------------------------

def check_python_version():
    """Prüft ob die Python-Version >= 3.10 ist.

    Returns:
        tuple: (ok: bool, version_str: str, message: str)
    """
    major = sys.version_info.major
    minor = sys.version_info.minor
    micro = sys.version_info.micro
    version_str = f"{major}.{minor}.{micro}"

    if major < MIN_PYTHON_MAJOR or (major == MIN_PYTHON_MAJOR and minor < MIN_PYTHON_MINOR):
        return (
            False,
            version_str,
            f"Python {version_str} ist zu alt. Mindestens Python {MIN_PYTHON_MAJOR}.{MIN_PYTHON_MINOR} erforderlich!",
        )

    return (True, version_str, f"Python {version_str} - kompatibel")


# ---------------------------------------------------------------------------
#  Schritt 2: Virtuelle Umgebung prüfen / erstellen
# ---------------------------------------------------------------------------

def check_venv():
    """Prüft ob .venv existiert und erstellt sie bei Bedarf.

    Returns:
        tuple: (ok: bool, already_existed: bool, message: str)
    """
    venv_python = _get_venv_python()

    if os.path.exists(venv_python):
        return (True, True, ".venv existiert bereits")

    # .venv erstellen
    root = _get_project_root()
    venv_path = os.path.join(root, '.venv')

    try:
        subprocess.run(
            [sys.executable, '-m', 'venv', venv_path],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        return (False, False, f"Konnte .venv nicht erstellen: {e.stderr.strip()}")
    except Exception as e:
        return (False, False, f"Konnte .venv nicht erstellen: {e}")

    if os.path.exists(venv_python):
        return (True, False, ".venv erfolgreich erstellt")

    return (False, False, ".venv konnte nicht erstellt werden (python.exe fehlt)")


# ---------------------------------------------------------------------------
#  Schritt 3: Abhängigkeiten prüfen und installieren
# ---------------------------------------------------------------------------

def _parse_requirements():
    """Liest requirements.txt und gibt Liste der Paketnamen zurück."""
    req_path = _get_requirements_path()
    packages = []

    if not os.path.exists(req_path):
        return packages

    with open(req_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Paketname extrahieren (vor >=, ==, <, etc.)
            for sep in ('>=', '<=', '==', '!=', '~=', '>', '<', '['):
                if sep in line:
                    line = line[:line.index(sep)]
                    break
            pkg = line.strip()
            if pkg:
                packages.append(pkg)

    return packages


def _check_package_installed(pkg_name):
    """Prüft ob ein Paket in der Umgebung verfügbar ist.

    Wichtig: Wir importieren das Modul absichtlich NICHT, weil einige Libraries
    beim Import Side-Effects oder Environment-Checks ausführen (z.B. `pywebview`),
    was die reine Installationsprüfung fälschlich fehlschlagen lassen kann.
    """
    # Häufige Mappings: Paketname → Importname
    import_mappings = {
        'python-dotenv': 'dotenv',
        'pillow': 'PIL',
        'pyyaml': 'yaml',
        'pywebview': 'webview',
    }
    import_name = import_mappings.get(pkg_name.lower(), pkg_name.replace('-', '_'))

    try:
        return importlib.util.find_spec(import_name) is not None
    except Exception:
        return False


def check_dependencies():
    """Prüft welche Pakete installiert sind und welche fehlen.

    Returns:
        tuple: (all_ok: bool, installed: list[str], missing: list[str])
    """
    packages = _parse_requirements()
    installed = []
    missing = []

    for pkg in packages:
        if _check_package_installed(pkg):
            installed.append(pkg)
        else:
            missing.append(pkg)

    return (len(missing) == 0, installed, missing)


def install_dependencies():
    """Installiert alle Abhängigkeiten aus requirements.txt.

    Returns:
        tuple: (ok: bool, message: str)
    """
    req_path = _get_requirements_path()
    if not os.path.exists(req_path):
        return (False, "requirements.txt nicht gefunden")

    venv_python = _get_venv_python()
    if not os.path.exists(venv_python):
        # Fallback auf aktuellen Interpreter
        venv_python = sys.executable

    try:
        result = subprocess.run(
            [venv_python, '-m', 'pip', 'install', '-r', req_path],
            check=True,
            capture_output=True,
            text=True,
        )
        return (True, "Alle Pakete erfolgreich installiert")
    except subprocess.CalledProcessError as e:
        return (False, f"Installation fehlgeschlagen:\n{e.stderr.strip()}")
    except Exception as e:
        return (False, f"Installation fehlgeschlagen: {e}")
