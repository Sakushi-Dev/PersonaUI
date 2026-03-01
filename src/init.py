"""PersonaUI - Initialization and Bootstrap.

Entry point for PersonaUI. Ensures that:
  1. A virtual environment (.venv) exists
  2. ALL dependencies are installed
  3. Then launches app.py as a new process

Called by start.bat / start.exe.
app.py can then use all imports directly.
"""

import os
import sys
import subprocess
import importlib.util
import zipfile
import shutil
import threading
import itertools
from urllib.request import urlretrieve


# Switch to src directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

# install.py uses only stdlib - load directly to bypass the __init__.py chain
# (splash_screen -> utils -> startup -> claude_api -> anthropic).
# This way the import works even when dependencies are not yet installed.
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
#  Launch Options laden (config/launch_options.txt)
# ═══════════════════════════════════════════════════════════════════════════

def _load_launch_options():
    """Liest launch_options.txt aus config/ und gibt die Optionen als Liste zurück."""
    root_dir = os.path.dirname(SCRIPT_DIR)
    launch_file = os.path.join(root_dir, 'config', 'launch_options.txt')
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
    """Display a visual progress bar for the download."""
    downloaded = block_num * block_size
    if total_size > 0:
        percent = min(100, downloaded * 100 // total_size)
        mb_down = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        bar_width = 30
        filled = int(bar_width * percent / 100)
        bar = '█' * filled + '░' * (bar_width - filled)
        print(f"\r  {_DIM}downloading{_RESET} {bar} {mb_down:.1f}/{mb_total:.1f} MB ({percent}%)", end='', flush=True)
    else:
        mb_down = downloaded / (1024 * 1024)
        print(f"\r  {_DIM}downloading{_RESET} {mb_down:.1f} MB", end='', flush=True)


def _install_pip_with_progress(venv_python, req_path):
    """Installs pip packages from requirements.txt with a visual progress bar."""
    # Count total packages
    with open(req_path, 'r', encoding='utf-8') as f:
        packages = [l.strip() for l in f if l.strip() and not l.strip().startswith('#')]
    total = len(packages)
    if total == 0:
        return True

    installed = 0
    bar_width = 30

    def _render_bar():
        pct = int(installed * 100 / total) if total else 100
        filled = int(bar_width * pct / 100)
        bar = '\u2588' * filled + '\u2591' * (bar_width - filled)
        print(f"\r  {_DIM}installing{_RESET} {bar} {installed}/{total} packages ({pct}%)", end='', flush=True)

    _render_bar()

    for pkg in packages:
        result = subprocess.run(
            [venv_python, '-m', 'pip', 'install', pkg],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
        )
        if result.returncode != 0:
            print()  # newline
            _print_error(f"Failed to install {pkg}")
            if result.stderr:
                for line in result.stderr.strip().splitlines()[-3:]:
                    print(f"    {_DIM}{line}{_RESET}")
            return False
        installed += 1
        _render_bar()

    print()  # newline after bar
    return True


def _download_and_install_node():
    """Downloads Node.js and extracts it to bin/node/."""
    url = _get_node_download_url()
    is_zip = url.endswith('.zip')
    archive_name = os.path.basename(url)
    archive_path = os.path.join(ROOT_DIR, 'bin', archive_name)

    os.makedirs(os.path.join(ROOT_DIR, 'bin'), exist_ok=True)

    # Download
    print(f"  {_DIM}Downloading Node.js {_NODE_VERSION}...{_RESET}")
    try:
        urlretrieve(url, archive_path, reporthook=_download_progress)
        print()  # newline after progress bar
    except Exception as e:
        print()
        _print_error(f"Download failed: {e}")
        return False

    # Extract
    print(f"  {_DIM}Extracting Node.js...{_RESET}")
    try:
        # determine extracted folder name upfront
        extracted_name = archive_name.replace('.zip', '').replace('.tar.gz', '')
        extracted_path = os.path.join(ROOT_DIR, 'bin', extracted_name)

        # clean up existing directories to avoid conflicts
        if os.path.exists(extracted_path):
            shutil.rmtree(extracted_path)
        if os.path.exists(LOCAL_NODE_DIR):
            shutil.rmtree(LOCAL_NODE_DIR)

        with _Spinner("Extracting archive"):
            if is_zip:
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(os.path.join(ROOT_DIR, 'bin'))
            else:
                import tarfile
                with tarfile.open(archive_path, 'r:gz') as tf:
                    tf.extractall(os.path.join(ROOT_DIR, 'bin'))

        # rename to bin/node/ (with retry for Windows file locks)
        import time
        last_err = None
        for attempt in range(5):
            try:
                shutil.move(extracted_path, LOCAL_NODE_DIR)
                last_err = None
                break
            except OSError as rename_err:
                last_err = rename_err
                time.sleep(1)
        if last_err:
            raise last_err

    except Exception as e:
        _print_error(f"Extraction failed: {e}")
        return False
    finally:
        # clean up archive
        if os.path.exists(archive_path):
            os.remove(archive_path)

    return True


def _ensure_npm():
    """Ensures npm is available.
    
    Checks system PATH first, then local bin/node/.
    If not found, downloads Node.js automatically.
    Returns the path to npm or None on failure.
    """
    # 1. Check system PATH
    npm = _find_npm_in_path()
    if npm:
        return npm

    # 2. Check local installation
    npm = _find_local_npm()
    if npm:
        return npm

    # 3. Ask user and download
    print()
    print(f"  {_YELLOW}{_BOLD}Node.js is required{_RESET} to build and serve the frontend.")
    print(f"  {_DIM}Version {_NODE_VERSION} (~33 MB will be downloaded to bin/node/).{_RESET}")
    print()
    try:
        answer = input(f"  {_BOLD}Download Node.js now? [Y/n]{_RESET} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = 'n'
    print()

    if answer in ('', 'y', 'yes'):
        if _download_and_install_node():
            npm = _find_local_npm()
            if npm:
                _print_ok(f"Node.js {_NODE_VERSION} installed to bin/node/")
                return npm
        _print_error("Failed to install Node.js.")
    else:
        _print_warn("Node.js download skipped by user.")
    return None


def _node_modules_ok():
    """Checks if node_modules exists in the frontend directory and is not empty."""
    nm_dir = os.path.join(FRONTEND_DIR, 'node_modules')
    return os.path.isdir(nm_dir) and len(os.listdir(nm_dir)) > 0


def _get_node_env():
    """Returns an environ dict with bin/node/ added to PATH.
    
    Required so npm subprocesses (vite, etc.) can find 'node',
    even when Node.js is only installed locally in bin/node/.
    """
    env = os.environ.copy()
    if os.path.isdir(LOCAL_NODE_DIR):
        # On Windows node.exe is directly in bin/node/
        # On Linux/Mac it's in bin/node/bin/
        if sys.platform == 'win32':
            node_bin = LOCAL_NODE_DIR
        else:
            node_bin = os.path.join(LOCAL_NODE_DIR, 'bin')
        env['PATH'] = node_bin + os.pathsep + env.get('PATH', '')
    return env


def _install_node_modules(npm_path):
    """Runs 'npm install' in the frontend directory."""
    result = subprocess.run(
        [npm_path, 'install'],
        cwd=FRONTEND_DIR,
        env=_get_node_env()
    )
    return result.returncode == 0


def _frontend_built_ok():
    """Checks if the React build (frontend/dist/index.html) exists."""
    return os.path.isfile(os.path.join(FRONTEND_DIR, 'dist', 'index.html'))


def _build_frontend(npm_path):
    """Runs 'npm run build' in the frontend directory."""
    result = subprocess.run(
        [npm_path, 'run', 'build'],
        cwd=FRONTEND_DIR,
        env=_get_node_env()
    )
    return result.returncode == 0


def _ensure_frontend(npm_path):
    """Ensures node_modules are installed and dist/ is built.
    
    Returns True if everything succeeded.
    """
    # 1. npm install (if node_modules missing)
    if not _node_modules_ok():
        print(f"  {_DIM}Installing frontend dependencies (npm install)...{_RESET}")
        if not _install_node_modules(npm_path):
            _print_error("npm install failed!")
            return False
        _print_ok("Frontend dependencies installed")

    # 2. npm run build (if dist/ missing)
    if not _frontend_built_ok():
        print(f"  {_DIM}Building frontend (npm run build)...{_RESET}")
        if not _build_frontend(npm_path):
            _print_error("Frontend build failed!")
            return False
        _print_ok("Frontend built successfully")

    return True


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers — styled terminal output
# ═══════════════════════════════════════════════════════════════════════════

# ANSI color / style codes (disabled when not supported)
def _supports_ansi():
    """Check if the terminal supports ANSI escape codes."""
    if os.environ.get('NO_COLOR'):
        return False
    if sys.platform == 'win32':
        # Windows 10 build 14393+ supports ANSI via Virtual Terminal
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            # enable VIRTUAL_TERMINAL_PROCESSING (0x0004)
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            return True
        except Exception:
            return False
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

_ANSI = _supports_ansi()
_BOLD    = '\033[1m'  if _ANSI else ''
_DIM     = '\033[2m'  if _ANSI else ''
_GREEN   = '\033[32m' if _ANSI else ''
_RED     = '\033[31m' if _ANSI else ''
_YELLOW  = '\033[33m' if _ANSI else ''
_CYAN    = '\033[36m' if _ANSI else ''
_RESET   = '\033[0m'  if _ANSI else ''


def _print_header():
    print()
    print(f"  {_CYAN}{_BOLD}╔══════════════════════════════════════════╗{_RESET}")
    print(f"  {_CYAN}{_BOLD}║                                          ║{_RESET}")
    print(f"  {_CYAN}{_BOLD}║      PersonaUI  ·  First-Time Setup      ║{_RESET}")
    print(f"  {_CYAN}{_BOLD}║                                          ║{_RESET}")
    print(f"  {_CYAN}{_BOLD}╚══════════════════════════════════════════╝{_RESET}")
    print()


def _print_step(step, total, msg):
    dots = '●' * step + '○' * (total - step)
    print(f"  {_BOLD}[{step}/{total}]{_RESET} {dots}  {msg}")


def _print_ok(msg):
    print(f"  {_GREEN}{_BOLD} ✓ {_RESET} {msg}")


def _print_warn(msg):
    print(f"  {_YELLOW}{_BOLD} ! {_RESET} {msg}")


def _print_error(msg):
    print(f"  {_RED}{_BOLD} ✗ {_RESET} {msg}")

class _Spinner:
    """Animated spinner for long-running operations.
    
    Usage:
        with _Spinner("Preparing environment"):
            do_something_slow()
    """
    _FRAMES = ['\u280b', '\u2819', '\u2839', '\u2838', '\u283c', '\u2834', '\u2826', '\u2827', '\u2807', '\u280f']  # braille dots

    def __init__(self, text):
        self._text = text
        self._stop = threading.Event()
        self._thread = None

    def _animate(self):
        for frame in itertools.cycle(self._FRAMES):
            if self._stop.is_set():
                break
            print(f"\r  {_CYAN}{frame}{_RESET} {_DIM}{self._text}{_RESET}  ", end='', flush=True)
            self._stop.wait(0.08)

    def __enter__(self):
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()
        # clear spinner line
        print(f"\r{' ' * (len(self._text) + 10)}\r", end='', flush=True)

def _ensure_prompts():
    """Copies missing prompt files from _defaults/ to the prompts folder.

    Only restores files that don't exist yet — never overwrites user-modified prompts.
    Mirrors the reset logic but is non-destructive.
    Handles subdirectories (e.g. _meta/) recursively.
    """
    prompts_dir = os.path.join(SCRIPT_DIR, 'instructions', 'prompts')
    defaults_dir = os.path.join(prompts_dir, '_defaults')
    if not os.path.isdir(defaults_dir):
        return

    restored = 0

    for root, _dirs, files in os.walk(defaults_dir):
        # Compute the relative path from _defaults/ to get the target dir in prompts/
        rel = os.path.relpath(root, defaults_dir)
        target_dir = os.path.join(prompts_dir, rel) if rel != '.' else prompts_dir

        for filename in files:
            if not filename.endswith('.json'):
                continue
            src = os.path.join(root, filename)
            dst = os.path.join(target_dir, filename)
            if not os.path.exists(dst):
                try:
                    os.makedirs(target_dir, exist_ok=True)
                    shutil.copy2(src, dst)
                    restored += 1
                except Exception:
                    pass

    if restored:
        _print_ok(f"{restored} missing prompt file(s) restored from defaults")


def _fatal(msg):
    """Display error and exit."""
    _print_error(msg)
    print()
    input(f"  {_DIM}Press Enter to exit...{_RESET}")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
#  Main logic
# ═══════════════════════════════════════════════════════════════════════════

def main():
    _merge_launch_options()
    venv_python = _get_venv_python()
    app_path = os.path.join(SCRIPT_DIR, 'app.py')
    first_setup = False

    # ─── Step 1: Already running inside .venv with everything installed? ───
    if _running_in_venv():
        # Quick check: all packages present?
        all_ok, installed, missing = check_dependencies()
        if all_ok:
            # Check frontend deps & build
            if not _node_modules_ok() or not _frontend_built_ok():
                npm_path = _ensure_npm()
                if npm_path:
                    _ensure_frontend(npm_path)

            # Ensure prompt files exist (non-destructive restore from _defaults)
            _ensure_prompts()

            # All ready — launch app.py directly (same process via exec)
            sys.argv[0] = app_path
            code = open(app_path, encoding='utf-8-sig').read()
            exec(compile(code, app_path, 'exec'), {
                '__name__': '__main__',
                '__file__': app_path,
            })
            return

        # Missing packages — install and restart app.py
        _print_warn(f"Missing packages: {', '.join(missing)}")
        print(f"  {_DIM}Installing...{_RESET}\n")
        ok, msg = install_dependencies()
        if not ok:
            _fatal(msg)
        _print_ok("Packages installed!")
        # Restart so imports work
        result = subprocess.run([sys.executable, app_path] + sys.argv[1:])
        sys.exit(result.returncode)

    # ─── Step 2: Not in venv — first-time setup ───

    print(f"\n  {_CYAN}{_BOLD}PersonaUI{_RESET}\n")

    # Check Python version
    ok, ver, msg = check_python_version()
    if not ok:
        _fatal(msg)

    # Check / create .venv
    with _Spinner("Preparing environment"):
        venv_ok, venv_existed, venv_msg = check_venv()
    if not venv_ok:
        _fatal(venv_msg)

    if not venv_existed:
        first_setup = True

    # Check if all packages are installed in .venv
    with _Spinner("Checking dependencies"):
        result = subprocess.run(
            [venv_python, '-c', 'from splash_screen.utils.install import check_dependencies; ok,_,m = check_dependencies(); exit(0 if ok else 1)'],
            capture_output=True, text=True, cwd=SCRIPT_DIR
        )
    all_installed = (result.returncode == 0)

    if all_installed and not first_setup:
        # Ensure prompt files exist (non-destructive restore from _defaults)
        _ensure_prompts()
        # Everything present — launch directly in venv
        result = subprocess.run([venv_python, app_path] + sys.argv[1:])
        sys.exit(result.returncode)

    # ─── Step 3: Installation required ───
    _print_header()

    total_steps = 4
    step = 0

    # Upgrade pip
    step += 1
    _print_step(step, total_steps, "Upgrading pip...")
    with _Spinner("Updating pip"):
        subprocess.run(
            [venv_python, '-m', 'pip', 'install', '--upgrade', 'pip'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    _print_ok("pip is up to date")

    # Install all Python dependencies
    step += 1
    req_path = _get_requirements_path()
    _print_step(step, total_steps, "Installing Python dependencies...")
    if not _install_pip_with_progress(venv_python, req_path):
        _fatal("Failed to install Python dependencies!")
    _print_ok("All packages installed")

    # Set up frontend (Node.js + npm install + npm run build)
    step += 1
    _print_step(step, total_steps, "Setting up frontend...")
    npm_path = _ensure_npm()
    if npm_path:
        print()
        if not _ensure_frontend(npm_path):
            _print_warn("Frontend setup failed — legacy frontend will be used.")
    else:
        _print_warn("Frontend will not be available without Node.js.")

    # Launch
    step += 1
    _print_step(step, total_steps, "Launching PersonaUI...")
    print(f"\n  {_DIM}{'─' * 42}{_RESET}\n")

    # Ensure prompt files exist (non-destructive restore from _defaults)
    _ensure_prompts()

    result = subprocess.run([venv_python, app_path] + sys.argv[1:])
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
