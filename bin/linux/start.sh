#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
#  PersonaUI – Start (Linux/macOS)
# ══════════════════════════════════════════════════════════════════════
set -e

echo "Initialisiere PersonaUI..."

# ══════════════════════════════════════════════════════════════════════
#  Pfade bestimmen
# ══════════════════════════════════════════════════════════════════════

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prüfe ob wir in bin/linux/ oder im Root sind
if [[ -f "$SELF_DIR/src/app.py" ]]; then
    ROOT="$SELF_DIR"
elif [[ -f "$SELF_DIR/../../src/app.py" ]]; then
    ROOT="$(cd "$SELF_DIR/../.." && pwd)"
else
    echo "[FEHLER] src/app.py nicht gefunden!"
    echo "Bitte starte die Anwendung aus dem PersonaUI Ordner."
    exit 1
fi

VENV_PY="$ROOT/.venv/bin/python"
INIT="$ROOT/src/personaui.py"

# ══════════════════════════════════════════════════════════════════════
#  Python prüfen
# ══════════════════════════════════════════════════════════════════════

PYTHON_CMD=""

# 1. venv Python bevorzugen
if [[ -x "$VENV_PY" ]]; then
    PYTHON_CMD="$VENV_PY"
# 2. python3 prüfen
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
# 3. python prüfen
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo ""
    echo "  Python wurde nicht gefunden!"
    echo "  Python 3.10+ wird fuer PersonaUI benoetigt."
    echo ""
    echo "  Installiere Python mit deinem Paketmanager:"
    echo "    Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "    Fedora:        sudo dnf install python3 python3-pip"
    echo "    Arch:          sudo pacman -S python python-pip"
    echo "    macOS:         brew install python"
    echo ""
    exit 1
fi

# ══════════════════════════════════════════════════════════════════════
#  Launch Options laden (config/launch_options.txt)
# ══════════════════════════════════════════════════════════════════════

LAUNCH_OPTS=""
LAUNCH_FILE="$ROOT/config/launch_options.txt"

if [[ -f "$LAUNCH_FILE" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Kommentare und leere Zeilen überspringen
        line="${line%%#*}"
        line="$(echo "$line" | xargs)"  # trim
        if [[ -n "$line" ]]; then
            LAUNCH_OPTS="$LAUNCH_OPTS $line"
        fi
    done < "$LAUNCH_FILE"
fi

# ══════════════════════════════════════════════════════════════════════
#  App starten (personaui.py → installiert bei Bedarf → startet app.py)
# ══════════════════════════════════════════════════════════════════════

"$PYTHON_CMD" "$INIT" "$@" $LAUNCH_OPTS
EXIT_CODE=$?

if [[ $EXIT_CODE -ne 0 ]]; then
    echo ""
    echo "Ein Fehler ist aufgetreten! (Exit Code: $EXIT_CODE)"
    read -rp "Enter drücken zum Beenden..."
fi
