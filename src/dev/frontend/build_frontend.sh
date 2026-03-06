#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
#  PersonaUI – Frontend Build (Linux/macOS)
# ══════════════════════════════════════════════════════════════════════
set -e

echo "╔══════════════════════════════════════════════╗"
echo "║       PersonaUI - Frontend Build              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Pfade bestimmen (Skript liegt in src/dev/frontend/)
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SELF_DIR/../../../frontend/package.json" ]]; then
    ROOT="$(cd "$SELF_DIR/../../.." && pwd)"
elif [[ -f "$SELF_DIR/src/app.py" ]]; then
    ROOT="$SELF_DIR"
elif [[ -f "$SELF_DIR/../src/app.py" ]]; then
    ROOT="$(cd "$SELF_DIR/.." && pwd)"
else
    echo "[FEHLER] Projektverzeichnis nicht gefunden!"
    exit 1
fi

FRONTEND_DIR="$ROOT/frontend"
NODE_DIR="$ROOT/bin/node"
NPM=""

# 1. Frontend-Verzeichnis prüfen
echo "[1/4] Prüfe Frontend-Verzeichnis..."
if [[ ! -f "$FRONTEND_DIR/package.json" ]]; then
    echo "  [FEHLER] frontend/package.json nicht gefunden!"
    exit 1
fi
echo "  [OK] $FRONTEND_DIR"
echo ""

# 2. Node.js prüfen
echo "[2/4] Prüfe Node.js..."
if [[ -x "$NODE_DIR/bin/npm" ]]; then
    NPM="$NODE_DIR/bin/npm"
    export PATH="$NODE_DIR/bin:$PATH"
    echo "  [OK] Lokales Node.js gefunden."
elif command -v npm &>/dev/null; then
    NPM="npm"
    echo "  [OK] System Node.js gefunden."
else
    echo "  [FEHLER] Node.js / npm nicht gefunden!"
    exit 1
fi
echo ""

# 3. Dependencies installieren
echo "[3/4] Prüfe Dependencies..."
cd "$FRONTEND_DIR"

if [[ ! -d "node_modules" ]]; then
    echo "  node_modules fehlt - installiere..."
    "$NPM" install
    echo "  [OK] Dependencies installiert."
else
    echo "  [OK] node_modules vorhanden."
fi
echo ""

# 4. Build ausführen
echo "[4/4] Baue Frontend (vite build)..."
echo ""

"$NPM" run build

echo ""
echo "══════════════════════════════════════════════"
echo "  [OK] Frontend erfolgreich kompiliert!"
echo "  Output: frontend/dist/"
echo "══════════════════════════════════════════════"
echo ""
