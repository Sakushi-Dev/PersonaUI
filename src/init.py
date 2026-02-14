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

    total_steps = 3
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

    # Starten
    step += 1
    _print_step(step, total_steps, "Starte PersonaUI...")
    print()

    result = subprocess.run([venv_python, app_path] + sys.argv[1:])
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
