#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
#  PersonaUI – Prompt Editor (Linux/macOS)
# ══════════════════════════════════════════════════════════════════════

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SELF_DIR/src/app.py" ]]; then
    ROOT="$SELF_DIR"
elif [[ -f "$SELF_DIR/../src/app.py" ]]; then
    ROOT="$(cd "$SELF_DIR/.." && pwd)"
else
    echo "[FEHLER] src/app.py nicht gefunden!"
    echo "Bitte starte die Anwendung aus dem PersonaUI Ordner."
    exit 1
fi

VENV_PY="$ROOT/.venv/bin/python"
PYTHON_CMD=""

# 1. venv Python bevorzugen
if [[ -x "$VENV_PY" ]]; then
    PYTHON_CMD="$VENV_PY"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "[FEHLER] Python wurde nicht gefunden!"
    echo "Bitte zuerst bin/start.sh ausfuehren."
    exit 1
fi

cd "$ROOT/src"
"$PYTHON_CMD" -m prompt_editor.editor

if [[ $? -ne 0 ]]; then
    echo ""
    echo "Ein Fehler ist aufgetreten!"
    read -rp "Enter drücken zum Beenden..."
fi
