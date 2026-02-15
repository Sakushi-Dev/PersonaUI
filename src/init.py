"""PersonaUI - Initialisierung und Bootstrap.

Entry-Point für PersonaUI. Stellt sicher, dass:
  1. Eine virtuelle Umgebung (.venv) existiert
  2. ALLE Abhängigkeiten installiert sind
  3. Dann app.py als neuen Prozess startet

Wird von start.bat / start.exe aufgerufen.
app.py kann somit alle Imports direkt verwenden.
"""

import os
import sys
import subprocess
import importlib.util
import zipfile
import shutil
from urllib.request import urlretrieve


# Wechsle ins src Verzeichnis
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

# install.py nutzt nur stdlib → direkt laden um die __init__.py-Kette
# (splash_screen → utils → startup → claude_api → anthropic) zu umgehen.
# So funktioniert der Import auch wenn Abhängigkeiten noch nicht installiert sind.
_install_path = os.path.join(SCRIPT_DIR, 'splash_screen', 'utils', 'install.py')
_spec = importlib.util.spec_from_file_location('_install', _install_path)
_install_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_install_mod)

check_python_version = _install_mod.check_python_version
check_venv = _install_mod.check_venv
check_dependencies = _install_mod.check_dependencies
install_dependencies = _install_mod.install_dependencies
_get_venv_python = _install_mod._get_venv_python
_running_in_venv = _install_mod._running_in_venv
_get_requirements_path = _install_mod._get_requirements_path


# ═══════════════════════════════════════════════════════════════════════════
#  Launch Options laden (launch_options.txt im Root)
# ═══════════════════════════════════════════════════════════════════════════

def _load_launch_options():
    """Liest launch_options.txt aus dem Root und gibt die Optionen als Liste zurück."""
    root_dir = os.path.dirname(SCRIPT_DIR)
    launch_file = os.path.join(root_dir, 'launch_options.txt')
    options = []
    if os.path.exists(launch_file):
        with open(launch_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    options.extend(line.split())
    return options


def _merge_launch_options():
    """Fügt launch_options.txt-Optionen in sys.argv ein (ohne Duplikate)."""
    options = _load_launch_options()
    for opt in options:
        if opt not in sys.argv:
            sys.argv.append(opt)


# ═══════════════════════════════════════════════════════════════════════════
#  Node.js / Frontend-Abhängigkeiten
# ═══════════════════════════════════════════════════════════════════════════

ROOT_DIR = os.path.dirname(SCRIPT_DIR)
FRONTEND_DIR = os.path.join(ROOT_DIR, 'frontend')
LOCAL_NODE_DIR = os.path.join(ROOT_DIR, 'bin', 'node')

# Node.js LTS-Version für automatischen Download
_NODE_VERSION = 'v22.14.0'


def _get_node_download_url():
    """Gibt die Download-URL für Node.js als ZIP/tar.gz zurück."""
    if sys.platform == 'win32':
        arch = 'x64'  # Standard für die meisten Windows-Systeme
        return f'https://nodejs.org/dist/{_NODE_VERSION}/node-{_NODE_VERSION}-win-{arch}.zip'
    elif sys.platform == 'darwin':
        arch = 'arm64' if os.uname().machine == 'arm64' else 'x64'
        return f'https://nodejs.org/dist/{_NODE_VERSION}/node-{_NODE_VERSION}-darwin-{arch}.tar.gz'
    else:
        arch = 'x64'
        return f'https://nodejs.org/dist/{_NODE_VERSION}/node-{_NODE_VERSION}-linux-{arch}.tar.gz'


def _find_npm_in_path():
    """Sucht npm im System-PATH. Gibt den Pfad zurück oder None."""
    npm_name = 'npm.cmd' if sys.platform == 'win32' else 'npm'
    result = subprocess.run(
        ['where' if sys.platform == 'win32' else 'which', npm_name],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return result.stdout.strip().splitlines()[0]
    return None


def _find_local_npm():
    """Sucht npm in der lokalen Node.js-Installation (bin/node/)."""
    if sys.platform == 'win32':
        npm_path = os.path.join(LOCAL_NODE_DIR, 'npm.cmd')
    else:
        npm_path = os.path.join(LOCAL_NODE_DIR, 'bin', 'npm')
    if os.path.isfile(npm_path):
        return npm_path
    return None


def _download_progress(block_num, block_size, total_size):
    """Fortschrittsanzeige für den Download."""
    downloaded = block_num * block_size
    if total_size > 0:
        percent = min(100, downloaded * 100 // total_size)
        mb_down = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        print(f"\r  Herunterladen: {mb_down:.1f}/{mb_total:.1f} MB ({percent}%)", end='', flush=True)
    else:
        mb_down = downloaded / (1024 * 1024)
        print(f"\r  Herunterladen: {mb_down:.1f} MB", end='', flush=True)


def _download_and_install_node():
    """Lädt Node.js herunter und extrahiert es nach bin/node/."""
    url = _get_node_download_url()
    is_zip = url.endswith('.zip')
    archive_name = os.path.basename(url)
    archive_path = os.path.join(ROOT_DIR, 'bin', archive_name)

    os.makedirs(os.path.join(ROOT_DIR, 'bin'), exist_ok=True)

    # Download
    print(f"  Node.js {_NODE_VERSION} wird heruntergeladen...")
    try:
        urlretrieve(url, archive_path, reporthook=_download_progress)
        print()  # Neue Zeile nach Fortschrittsanzeige
    except Exception as e:
        print()
        _print_error(f"Download fehlgeschlagen: {e}")
        return False

    # Entpacken
    print("  Entpacke Node.js...")
    try:
        if is_zip:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                zf.extractall(os.path.join(ROOT_DIR, 'bin'))
        else:
            import tarfile
            with tarfile.open(archive_path, 'r:gz') as tf:
                tf.extractall(os.path.join(ROOT_DIR, 'bin'))

        # Der extrahierte Ordner heisst z.B. node-v22.14.0-win-x64
        # Umbenennen zu bin/node/
        extracted_name = archive_name.replace('.zip', '').replace('.tar.gz', '')
        extracted_path = os.path.join(ROOT_DIR, 'bin', extracted_name)

        if os.path.exists(LOCAL_NODE_DIR):
            shutil.rmtree(LOCAL_NODE_DIR)
        os.rename(extracted_path, LOCAL_NODE_DIR)

    except Exception as e:
        _print_error(f"Entpacken fehlgeschlagen: {e}")
        return False
    finally:
        # Archiv aufräumen
        if os.path.exists(archive_path):
            os.remove(archive_path)

    return True


def _ensure_npm():
    """Stellt sicher, dass npm verfügbar ist.
    
    Sucht zuerst im System-PATH, dann lokal in bin/node/.
    Falls nicht gefunden, wird Node.js automatisch heruntergeladen.
    Gibt den Pfad zu npm zurück oder None bei Fehler.
    """
    # 1. System-PATH prüfen
    npm = _find_npm_in_path()
    if npm:
        return npm

    # 2. Lokale Installation prüfen
    npm = _find_local_npm()
    if npm:
        return npm

    # 3. Automatisch herunterladen und installieren
    print("  Node.js/npm nicht gefunden – wird automatisch installiert...")
    if _download_and_install_node():
        npm = _find_local_npm()
        if npm:
            _print_ok(f"Node.js {_NODE_VERSION} installiert nach bin/node/")
            return npm

    _print_error("Node.js konnte nicht automatisch installiert werden.")
    return None


def _node_modules_ok():
    """Prüft ob node_modules im Frontend-Verzeichnis existiert und nicht leer ist."""
    nm_dir = os.path.join(FRONTEND_DIR, 'node_modules')
    return os.path.isdir(nm_dir) and len(os.listdir(nm_dir)) > 0


def _get_node_env():
    """Gibt ein environ-dict zurück, in dem bin/node/ im PATH steht.
    
    Nötig damit npm-Subprozesse (vite, etc.) 'node' finden,
    auch wenn Node.js nur lokal in bin/node/ installiert ist.
    """
    env = os.environ.copy()
    if os.path.isdir(LOCAL_NODE_DIR):
        # Auf Windows liegt node.exe direkt in bin/node/
        # Auf Linux/Mac in bin/node/bin/
        if sys.platform == 'win32':
            node_bin = LOCAL_NODE_DIR
        else:
            node_bin = os.path.join(LOCAL_NODE_DIR, 'bin')
        env['PATH'] = node_bin + os.pathsep + env.get('PATH', '')
    return env


def _install_node_modules(npm_path):
    """Führt 'npm install' im Frontend-Verzeichnis aus."""
    result = subprocess.run(
        [npm_path, 'install'],
        cwd=FRONTEND_DIR,
        env=_get_node_env()
    )
    return result.returncode == 0


def _frontend_built_ok():
    """Prüft ob der React-Build (frontend/dist/index.html) existiert."""
    return os.path.isfile(os.path.join(FRONTEND_DIR, 'dist', 'index.html'))


def _build_frontend(npm_path):
    """Führt 'npm run build' im Frontend-Verzeichnis aus."""
    result = subprocess.run(
        [npm_path, 'run', 'build'],
        cwd=FRONTEND_DIR,
        env=_get_node_env()
    )
    return result.returncode == 0


def _ensure_frontend(npm_path):
    """Stellt sicher, dass node_modules installiert und dist/ gebaut ist.
    
    Gibt True zurück wenn alles erfolgreich war.
    """
    # 1. npm install (falls node_modules fehlt)
    if not _node_modules_ok():
        print("  Frontend-Abhaengigkeiten werden installiert (npm install)...")
        if not _install_node_modules(npm_path):
            _print_error("npm install fehlgeschlagen!")
            return False
        _print_ok("Frontend-Abhaengigkeiten installiert")

    # 2. npm run build (falls dist/ fehlt)
    if not _frontend_built_ok():
        print("  Frontend wird gebaut (npm run build)...")
        if not _build_frontend(npm_path):
            _print_error("Frontend-Build fehlgeschlagen!")
            return False
        _print_ok("Frontend erfolgreich gebaut")

    return True


# ═══════════════════════════════════════════════════════════════════════════
#  Hilfsfunktionen
# ═══════════════════════════════════════════════════════════════════════════

def _print_header():
    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║       PersonaUI - Ersteinrichtung    ║")
    print("  ╚══════════════════════════════════════╝")
    print()


def _print_step(step, total, msg):
    print(f"  [{step}/{total}] {msg}")


def _print_ok(msg):
    print(f"  [OK] {msg}")


def _print_error(msg):
    print(f"  [FEHLER] {msg}")


def _fatal(msg):
    """Fehler anzeigen und beenden."""
    _print_error(msg)
    print()
    input("  Druecke Enter zum Beenden...")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
#  Hauptlogik
# ═══════════════════════════════════════════════════════════════════════════

def main():
    _merge_launch_options()
    venv_python = _get_venv_python()
    app_path = os.path.join(SCRIPT_DIR, 'app.py')
    first_setup = False

    # ─── Schritt 1: Laufen wir bereits in der .venv mit allem installiert? ───
    if _running_in_venv():
        # Schnellprüfung: Alle Pakete da?
        all_ok, installed, missing = check_dependencies()
        if all_ok:
            # Frontend-Abhängigkeiten prüfen & bauen
            if not _node_modules_ok() or not _frontend_built_ok():
                npm_path = _ensure_npm()
                if npm_path:
                    _ensure_frontend(npm_path)

            # Alles bereit → app.py direkt starten (im selben Prozess via exec)
            # exec ersetzt diesen Prozess komplett durch app.py
            sys.argv[0] = app_path
            code = open(app_path, encoding='utf-8-sig').read()
            exec(compile(code, app_path, 'exec'), {
                '__name__': '__main__',
                '__file__': app_path,
            })
            return

        # Pakete fehlen → installieren und app.py neu starten
        print(f"  Fehlende Pakete: {', '.join(missing)}")
        print("  Installation laeuft...\n")
        ok, msg = install_dependencies()
        if not ok:
            _fatal(msg)
        _print_ok("Pakete installiert!")
        # Neustart damit imports funktionieren
        result = subprocess.run([sys.executable, app_path] + sys.argv[1:])
        sys.exit(result.returncode)

    # ─── Schritt 2: Nicht in venv → Ersteinrichtung ───

    # Python-Version prüfen
    ok, ver, msg = check_python_version()
    if not ok:
        _fatal(msg)

    # .venv prüfen/erstellen
    venv_ok, venv_existed, venv_msg = check_venv()
    if not venv_ok:
        _fatal(venv_msg)

    if not venv_existed:
        first_setup = True

    # Prüfe ob in der .venv alle Pakete installiert sind
    # (nutze venv Python um zu prüfen was dort installiert ist)
    result = subprocess.run(
        [venv_python, '-c', 'from splash_screen.utils.install import check_dependencies; ok,_,m = check_dependencies(); exit(0 if ok else 1)'],
        capture_output=True, text=True, cwd=SCRIPT_DIR
    )
    all_installed = (result.returncode == 0)

    if all_installed and not first_setup:
        # Alles da → direkt in venv starten
        result = subprocess.run([venv_python, app_path] + sys.argv[1:])
        sys.exit(result.returncode)

    # ─── Schritt 3: Installation notwendig ───
    _print_header()

    total_steps = 4
    step = 0

    # pip upgraden
    step += 1
    _print_step(step, total_steps, "pip wird aktualisiert...")
    subprocess.run(
        [venv_python, '-m', 'pip', 'install', '--upgrade', 'pip'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    _print_ok("pip aktualisiert")

    # Alle Abhängigkeiten installieren
    step += 1
    req_path = _get_requirements_path()
    _print_step(step, total_steps, f"Abhaengigkeiten werden installiert...")
    print()
    result = subprocess.run(
        [venv_python, '-m', 'pip', 'install', '-r', req_path],
    )
    print()
    if result.returncode != 0:
        _fatal("Installation der Abhaengigkeiten fehlgeschlagen!")
    _print_ok("Alle Pakete installiert")

    # Frontend einrichten (Node.js + npm install + npm run build)
    step += 1
    _print_step(step, total_steps, "Frontend wird eingerichtet...")
    npm_path = _ensure_npm()
    if npm_path:
        print()
        if not _ensure_frontend(npm_path):
            _print_error("Frontend-Einrichtung fehlgeschlagen – Legacy-Frontend wird verwendet.")
    else:
        print("  [WARNUNG] Frontend wird ohne Node.js nicht verfuegbar sein.")

    # Starten
    step += 1
    _print_step(step, total_steps, "Starte PersonaUI...")
    print()

    result = subprocess.run([venv_python, app_path] + sys.argv[1:])
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
