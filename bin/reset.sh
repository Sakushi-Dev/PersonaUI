#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
#  PersonaUI – Reset (Linux/macOS)
# ══════════════════════════════════════════════════════════════════════

echo "Starte PersonaUI Reset..."
echo ""

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SELF_DIR/src/reset.py" ]]; then
    ROOT="$SELF_DIR"
elif [[ -f "$SELF_DIR/../src/reset.py" ]]; then
    ROOT="$(cd "$SELF_DIR/.." && pwd)"
else
    echo "[FEHLER] src/reset.py nicht gefunden!"
    echo "Bitte starte die Anwendung aus dem PersonaUI Ordner."
    exit 1
fi

VENV_PY="$ROOT/.venv/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
    echo "[FEHLER] .venv nicht gefunden! Bitte zuerst bin/start.sh ausfuehren."
    exit 1
fi

cd "$ROOT/src"

"$VENV_PY" reset.py
EXIT_CODE=$?

if [[ $EXIT_CODE -ne 0 ]]; then
    echo ""
    echo "Ein Fehler ist aufgetreten!"
    read -rp "Enter drücken zum Beenden..."
fi
