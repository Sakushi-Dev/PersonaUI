"""
Zentrales Logging-Modul für PersonaUI.

Stellt einen vorkonfigurierten Logger bereit, der sowohl in eine
rotierende Log-Datei als auch auf die Konsole schreibt.

Verwendung in jedem Modul:
    from utils.logger import log
    log.info("Server gestartet")
    log.warning("Config nicht gefunden")
    log.error("API-Fehler: %s", err)
    log.debug("Prompt-Aufbau: %s", prompt)
"""

import os
import logging
from logging.handlers import RotatingFileHandler

# ---------------------------------------------------------------------------
# Pfade
# ---------------------------------------------------------------------------
_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # src/
_LOG_DIR = os.path.join(_SRC_DIR, 'logs')
_LOG_FILE = os.path.join(_LOG_DIR, 'personaui.log')

# ---------------------------------------------------------------------------
# Log-Verzeichnis sicherstellen
# ---------------------------------------------------------------------------
os.makedirs(_LOG_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Logger anlegen
# ---------------------------------------------------------------------------
log = logging.getLogger('personaui')
log.setLevel(logging.DEBUG)  # Alles erfassen – Handler filtern selektiv

# Verhindere doppelte Handler bei Reload
if not log.handlers:

    # Format
    _fmt = logging.Formatter(
        fmt='%(asctime)s  %(levelname)-8s  [%(name)s.%(module)s]  %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # --- Datei-Handler (rotierend) -----------------------------------------
    _file_handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=5 * 1024 * 1024,   # 5 MB pro Datei
        backupCount=3,               # max. 3 Backup-Dateien
        encoding='utf-8',
    )
    _file_handler.setLevel(logging.DEBUG)
    _file_handler.setFormatter(_fmt)
    log.addHandler(_file_handler)

    # --- Konsolen-Handler --------------------------------------------------
    _console_handler = logging.StreamHandler()
    _console_handler.setLevel(logging.INFO)  # Konsole: nur INFO+
    _console_handler.setFormatter(_fmt)
    log.addHandler(_console_handler)

# Verhindere Weitergabe an Root-Logger (vermeidet doppelte Ausgabe)
log.propagate = False
