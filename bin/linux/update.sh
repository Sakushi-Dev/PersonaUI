#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
#  PersonaUI – Update (Linux/macOS)
# ══════════════════════════════════════════════════════════════════════
set -e

echo "╔══════════════════════════════════════════════╗"
echo "║         PersonaUI - Update                   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ──────────────────────────────────────────────
#  Pfade bestimmen
# ──────────────────────────────────────────────

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SELF_DIR/src/app.py" ]]; then
    ROOT="$SELF_DIR"
elif [[ -f "$SELF_DIR/../../src/app.py" ]]; then
    ROOT="$(cd "$SELF_DIR/../.." && pwd)"
else
    echo "[FEHLER] Projektverzeichnis nicht gefunden!"
    exit 1
fi

cd "$ROOT"
echo "[INFO] Project directory: $(pwd)"
echo ""

# ──────────────────────────────────────────────
#  1. Check Git
# ──────────────────────────────────────────────

echo "[1/6] Checking Git..."
if ! command -v git &>/dev/null; then
    echo "  [ERROR] Git is not installed!"
    echo "  Install with: sudo apt install git  (or your package manager)"
    exit 1
fi
echo "  [OK] Git found."
echo ""

# ──────────────────────────────────────────────
#  2. Fetch remote
# ──────────────────────────────────────────────

echo "[2/6] Fetching latest information from origin/main..."
if ! git fetch origin main; then
    echo "  [ERROR] Could not fetch origin/main!"
    echo "  Check your network connection."
    exit 1
fi
echo "  [OK] Remote updated."
echo ""

# ──────────────────────────────────────────────
#  3. Compare versions
# ──────────────────────────────────────────────

echo "[3/6] Checking for updates..."

# Parse local version from config/version.ini
LOCAL_VERSION="unknown"
if [[ -f "config/version.ini" ]]; then
    LOCAL_VERSION=$(python3 -c "import configparser; c=configparser.ConfigParser(); c.read('config/version.ini'); print(c.get('version','version',fallback='unknown'))" 2>/dev/null || echo "unknown")
fi
echo "  [INFO] Current version: $LOCAL_VERSION"

# Parse remote version from origin/main:config/version.ini
REMOTE_VERSION="unknown"
REMOTE_INI=$(git show origin/main:config/version.ini 2>/dev/null || echo "")
if [[ -n "$REMOTE_INI" ]]; then
    REMOTE_VERSION=$(echo "$REMOTE_INI" | python3 -c "import sys,configparser; c=configparser.ConfigParser(); c.read_string(sys.stdin.read()); print(c.get('version','version',fallback='unknown'))" 2>/dev/null || echo "unknown")
fi
echo "  [INFO] Remote version:  $REMOTE_VERSION"

if [[ "$LOCAL_VERSION" == "$REMOTE_VERSION" ]]; then
    echo ""
    echo "  PersonaUI is already up to date! (v$LOCAL_VERSION)"
    echo ""
    exit 0
fi

echo ""
echo "  [INFO] New version available: v$REMOTE_VERSION (current: v$LOCAL_VERSION)"
echo ""

# ──────────────────────────────────────────────
#  4. Perform update
# ──────────────────────────────────────────────

echo "[4/6] Performing update..."

# Abort any stuck merge
git merge --abort 2>/dev/null || true

# Reset to remote
if ! git reset --hard origin/main; then
    echo "  [ERROR] Could not reset to origin/main."
    echo "  Try deleting the folder and cloning fresh."
    exit 1
fi
echo "  [OK] Code updated."
echo ""

# ──────────────────────────────────────────────
#  5. Update dependencies
# ──────────────────────────────────────────────

echo "[5/6] Updating dependencies..."

if [[ -f ".venv/bin/activate" ]]; then
    source .venv/bin/activate
    pip install -r requirements.txt --quiet --upgrade 2>/dev/null
    echo "  [OK] Dependencies updated."
else
    echo "  [WARNING] No virtual environment found."
    echo "  Run bin/start.sh first."
fi

# ──────────────────────────────────────────────
#  6. Rebuild frontend
# ──────────────────────────────────────────────

echo "[6/6] Rebuilding frontend..."

if [[ -f "src/dev/frontend/build_frontend.sh" ]]; then
    bash "src/dev/frontend/build_frontend.sh" || echo "  [WARNING] Frontend build failed. UI may be outdated."
elif [[ -d "frontend" ]] && command -v npm &>/dev/null; then
    cd frontend && npm run build && cd .. || echo "  [WARNING] Frontend build failed."
else
    echo "  [WARNING] Frontend build skipped (npm not found)."
fi
echo ""

# ──────────────────────────────────────────────
#  Update state file
# ──────────────────────────────────────────────

cat > "src/settings/update_state.json" <<EOF
{
  "version": "$REMOTE_VERSION"
}
EOF

echo "╔══════════════════════════════════════════════╗"
echo "║         Update successful!                   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  PersonaUI has been updated to v$REMOTE_VERSION"
echo ""
echo "  Restart PersonaUI with: bin/start.sh"
echo ""
