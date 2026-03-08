#!/usr/bin/env sh
# ══════════════════════════════════════════════════════════════════════
#  PersonaUI – Start (Termux / Android)
# ══════════════════════════════════════════════════════════════════════
#  Startet PersonaUI im Browser-Modus (--no-gui) auf Termux.
#  Nutzung: sh start_termux.sh  ODER  bash start_termux.sh
# ══════════════════════════════════════════════════════════════════════
set -e

# Pfad bestimmen (sh-kompatibel, kein BASH_SOURCE nötig)
SELF_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)" || SELF_DIR="$(pwd)"

# Projektverzeichnis bestimmen
if [ -f "$SELF_DIR/src/app.py" ]; then
    ROOT="$SELF_DIR"
elif [ -f "$SELF_DIR/../../src/app.py" ]; then
    ROOT="$(cd "$SELF_DIR/../.." && pwd)"
elif [ -f "$(pwd)/src/app.py" ]; then
    ROOT="$(pwd)"
else
    echo "[FEHLER] src/app.py nicht gefunden!"
    echo "  Gesucht in: $SELF_DIR"
    echo "  und in:     $(pwd)"
    echo ""
    echo "  Bitte starte das Script aus dem PersonaUI-Ordner:"
    echo "    cd /pfad/zu/personaui && bash start_termux.sh"
    exit 1
fi

VENV_PY="$ROOT/.venv/bin/python"
INIT="$ROOT/src/personaui.py"
INSTALL_SCRIPT="$ROOT/bin/install_termux.sh"

# Prüfe ob Installation nötig ist (kein Python, kein venv, oder kein Node)
needs_install=false

if ! command -v python3 >/dev/null 2>&1 && [ ! -x "$VENV_PY" ]; then
    needs_install=true
elif [ ! -x "$VENV_PY" ]; then
    needs_install=true
elif ! "$VENV_PY" -c "import flask" 2>/dev/null; then
    needs_install=true
elif ! command -v node >/dev/null 2>&1; then
    needs_install=true
fi

if [ "$needs_install" = true ]; then
    if [ -f "$INSTALL_SCRIPT" ]; then
        echo "Erstinstallation erforderlich - starte install_termux.sh ..."
        echo ""
        bash "$INSTALL_SCRIPT"
        echo ""
    else
        echo "[FEHLER] Installation noetig, aber bin/install_termux.sh nicht gefunden!"
        exit 1
    fi
fi

# Python bestimmen
if [ -x "$VENV_PY" ]; then
    PYTHON_CMD="$VENV_PY"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "[FEHLER] Python nicht gefunden!"
    exit 1
fi

# Wake-Lock aktivieren (verhindert dass Android Termux beendet)
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock 2>/dev/null || true
fi

echo "Starte PersonaUI (Browser-Modus)..."
echo ""

# Browser öffnen sobald der Server bereit ist (im Hintergrund)
(
    # Warte bis der Server auf Port 5000 antwortet
    for _ in $(seq 1 30); do
        if curl -s -o /dev/null http://localhost:5000/api/health 2>/dev/null; then
            # termux-open-url öffnet den Standard-Browser auf Android
            if command -v termux-open-url &>/dev/null; then
                termux-open-url "http://localhost:5000"
            elif command -v xdg-open &>/dev/null; then
                xdg-open "http://localhost:5000"
            fi
            break
        fi
        sleep 1
    done
) &

# --no-gui erzwingen + --force-build + Launch Options laden
"$PYTHON_CMD" "$INIT" --no-gui --force-build "$@"
