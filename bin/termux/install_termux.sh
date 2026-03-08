#!/data/data/com.termux/files/usr/bin/bash
# ══════════════════════════════════════════════════════════════════════
#  PersonaUI – Vollständige Installation für Termux (Android)
# ══════════════════════════════════════════════════════════════════════
#
#  Dieses Script installiert alle Abhängigkeiten für PersonaUI
#  auf einem Android-Gerät mit Termux.
#
#  Nutzung:
#    1. Termux öffnen
#    2. bash install_termux.sh
#       (oder: chmod +x install_termux.sh && ./install_termux.sh)
#
#  Was passiert:
#    - Termux-Pakete (Python, Node.js, Build-Tools) werden installiert
#    - Python venv wird eingerichtet
#    - Pip-Pakete werden installiert (Pillow als Termux-Paket für Speed)
#    - React-Frontend wird gebaut
#    - --no-gui Modus wird aktiviert (kein PyWebView auf Android)
#
# ══════════════════════════════════════════════════════════════════════
set -e

# ──────────────────────────────────────────────
#  Farben & Hilfs-Funktionen
# ──────────────────────────────────────────────

BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[32m'
RED='\033[31m'
YELLOW='\033[33m'
CYAN='\033[36m'
RESET='\033[0m'

print_header() {
    echo ""
    echo -e "  ${CYAN}${BOLD}╔══════════════════════════════════════════════════╗${RESET}"
    echo -e "  ${CYAN}${BOLD}║                                                  ║${RESET}"
    echo -e "  ${CYAN}${BOLD}║     PersonaUI  ·  Termux Installation (Android)  ║${RESET}"
    echo -e "  ${CYAN}${BOLD}║                                                  ║${RESET}"
    echo -e "  ${CYAN}${BOLD}╚══════════════════════════════════════════════════╝${RESET}"
    echo ""
}

print_step() {
    local step=$1
    local total=$2
    local msg=$3
    echo ""
    echo -e "  ${BOLD}[${step}/${total}]${RESET} ${msg}"
    echo -e "  ${DIM}$(printf '─%.0s' {1..44})${RESET}"
}

print_ok() {
    echo -e "  ${GREEN}${BOLD} ✓ ${RESET} $1"
}

print_warn() {
    echo -e "  ${YELLOW}${BOLD} ! ${RESET} $1"
}

print_error() {
    echo -e "  ${RED}${BOLD} ✗ ${RESET} $1"
}

print_info() {
    echo -e "  ${DIM}$1${RESET}"
}

fail() {
    print_error "$1"
    echo ""
    exit 1
}

TOTAL_STEPS=7

# ──────────────────────────────────────────────
#  Termux-Erkennung
# ──────────────────────────────────────────────

if [[ ! -d "/data/data/com.termux" ]]; then
    echo ""
    print_error "Dieses Script ist nur fuer Termux (Android) gedacht!"
    echo ""
    print_info "Fuer Linux/macOS nutze: bin/start.sh"
    print_info "Fuer Windows nutze:     bin/start.bat"
    echo ""
    exit 1
fi

# ──────────────────────────────────────────────
#  Projektverzeichnis bestimmen
# ──────────────────────────────────────────────

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SELF_DIR/src/app.py" ]]; then
    ROOT="$SELF_DIR"
elif [[ -f "$SELF_DIR/../src/app.py" ]]; then
    ROOT="$(cd "$SELF_DIR/.." && pwd)"
else
    fail "src/app.py nicht gefunden! Bitte starte aus dem PersonaUI-Ordner."
fi

FRONTEND_DIR="$ROOT/frontend"
VENV_DIR="$ROOT/.venv"
VENV_PY="$VENV_DIR/bin/python"
REQ_FILE="$ROOT/requirements.txt"
LAUNCH_FILE="$ROOT/config/launch_options.ini"

print_header
print_info "Projektverzeichnis: $ROOT"
echo ""

# ══════════════════════════════════════════════════════════════════════
#  Step 1: Termux-Paketquellen aktualisieren
# ══════════════════════════════════════════════════════════════════════

print_step 1 $TOTAL_STEPS "Termux-Paketquellen aktualisieren"

# Termux-Repos umstellen falls nötig (alte Bintray-Repos sind offline)
if command -v termux-change-repo &>/dev/null; then
    print_info "Falls Paketquellen veraltet sind: termux-change-repo ausfuehren"
fi

pkg update -y && pkg upgrade -y
print_ok "Paketquellen aktualisiert"

# ══════════════════════════════════════════════════════════════════════
#  Step 2: System-Pakete installieren
# ══════════════════════════════════════════════════════════════════════

print_step 2 $TOTAL_STEPS "System-Pakete installieren"

# --- Python + pip ---
print_info "Python & pip..."
pkg install -y python python-pip
print_ok "Python installiert: $(python3 --version 2>&1)"

# --- Pillow als vorkompiliertes Termux-Paket (SCHNELL, kein Kompilieren) ---
# python-pillow in Termux enthält die C-Erweiterungen bereits fertig gebaut.
# Das spart ~10 Minuten Kompilierzeit auf einem Smartphone.
print_info "Pillow (vorkompiliert)..."
pkg install -y python-pillow
print_ok "Pillow (Termux-Paket) installiert"

# --- Build-Tools für evtl. nötige C-Erweiterungen (pyyaml etc.) ---
print_info "Build-Tools..."
pkg install -y build-essential
print_ok "Build-Tools installiert (clang, make, etc.)"

# --- Bibliotheken für native Python-Pakete ---
print_info "Native Bibliotheken..."
pkg install -y libyaml            # pyyaml C-Erweiterung
pkg install -y libffi             # cffi (wird von einigen Paketen benötigt)
pkg install -y openssl            # SSL/TLS für pip und httpx/anthropic
print_ok "Native Bibliotheken installiert"

# --- Node.js (für React-Frontend) ---
print_info "Node.js & npm..."
pkg install -y nodejs
print_ok "Node.js installiert: $(node --version 2>&1)"
print_ok "npm installiert: $(npm --version 2>&1)"

# --- Git (für Updates) ---
print_info "Git..."
pkg install -y git
print_ok "Git installiert"

# ══════════════════════════════════════════════════════════════════════
#  Step 3: Speicherzugriff einrichten
# ══════════════════════════════════════════════════════════════════════

print_step 3 $TOTAL_STEPS "Speicherzugriff pruefen"

if [[ ! -d "$HOME/storage" ]]; then
    print_info "Speicherzugriff wird angefordert..."
    print_info "(Bitte die Android-Berechtigung akzeptieren)"
    termux-setup-storage || true
    sleep 2
    if [[ -d "$HOME/storage" ]]; then
        print_ok "Speicherzugriff eingerichtet"
    else
        print_warn "Speicherzugriff nicht eingerichtet (optional)"
        print_warn "Kann spaeter mit 'termux-setup-storage' nachgeholt werden"
    fi
else
    print_ok "Speicherzugriff bereits vorhanden"
fi

# ══════════════════════════════════════════════════════════════════════
#  Step 4: Python Virtual Environment einrichten
# ══════════════════════════════════════════════════════════════════════

print_step 4 $TOTAL_STEPS "Python Virtual Environment einrichten"

if [[ -x "$VENV_PY" ]]; then
    print_ok ".venv existiert bereits"
    # Prüfe ob --system-site-packages aktiv ist (für Pillow-Zugriff)
    if ! "$VENV_PY" -c "import PIL" 2>/dev/null; then
        print_warn "Bestehende .venv hat keinen Zugriff auf System-Pillow"
        print_info "Erstelle .venv neu mit --system-site-packages..."
        rm -rf "$VENV_DIR"
    fi
fi

if [[ ! -x "$VENV_PY" ]]; then
    print_info "Erstelle .venv mit --system-site-packages..."
    print_info "(Erlaubt Zugriff auf Termux-Pillow ohne Neukompilierung)"
    python3 -m venv --system-site-packages "$VENV_DIR"

    if [[ -x "$VENV_PY" ]]; then
        print_ok ".venv erstellt"
    else
        fail ".venv konnte nicht erstellt werden!"
    fi
fi

# pip im venv aktualisieren
print_info "pip aktualisieren..."
"$VENV_PY" -m pip install --upgrade pip --quiet
print_ok "pip aktualisiert"

# ══════════════════════════════════════════════════════════════════════
#  Step 5: Python-Abhängigkeiten installieren
# ══════════════════════════════════════════════════════════════════════

print_step 5 $TOTAL_STEPS "Python-Abhaengigkeiten installieren"

if [[ ! -f "$REQ_FILE" ]]; then
    fail "requirements.txt nicht gefunden: $REQ_FILE"
fi

# Pakete zählen (ohne Kommentare/Leerzeilen)
TOTAL_PKGS=$(grep -cE '^[^#[:space:]]' "$REQ_FILE" || echo 0)
INSTALLED=0
SKIPPED=0
FAILED=0

while IFS= read -r line || [[ -n "$line" ]]; do
    # Kommentare und leere Zeilen überspringen
    line="$(echo "$line" | sed 's/#.*//' | xargs)"
    [[ -z "$line" ]] && continue

    # Paketnamen extrahieren (vor >=, ==, etc.)
    pkg_name="$(echo "$line" | sed 's/[><=!~].*//' | xargs)"
    pkg_lower="$(echo "$pkg_name" | tr '[:upper:]' '[:lower:]')"

    # --- pywebview überspringen (kein GUI auf Android) ---
    if [[ "$pkg_lower" == "pywebview" ]]; then
        print_warn "Uebersprungen: pywebview (kein GUI auf Android, --no-gui Modus wird genutzt)"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    # --- Pillow: bereits als Termux-Paket installiert ---
    if [[ "$pkg_lower" == "pillow" ]]; then
        if "$VENV_PY" -c "import PIL; print(PIL.__version__)" 2>/dev/null; then
            print_ok "Pillow bereits verfuegbar (Termux-Paket)"
            SKIPPED=$((SKIPPED + 1))
            continue
        fi
    fi

    # --- pytest: nur für Entwicklung, optional ---
    if [[ "$pkg_lower" == "pytest" || "$pkg_lower" == "pytest-mock" ]]; then
        print_info "Installiere $line (Test-Abhaengigkeit)..."
    else
        print_info "Installiere $line..."
    fi

    if "$VENV_PY" -m pip install "$line" --quiet 2>/dev/null; then
        INSTALLED=$((INSTALLED + 1))
        print_ok "$pkg_name installiert"
    else
        # Retry ohne --quiet für Fehler-Diagnose
        echo ""
        if "$VENV_PY" -m pip install "$line" 2>&1 | tail -5; then
            INSTALLED=$((INSTALLED + 1))
            print_ok "$pkg_name installiert (2. Versuch)"
        else
            print_warn "$pkg_name konnte nicht installiert werden"
            FAILED=$((FAILED + 1))
        fi
    fi

done < "$REQ_FILE"

echo ""
print_ok "Pakete: $INSTALLED installiert, $SKIPPED uebersprungen, $FAILED fehlgeschlagen"

if [[ $FAILED -gt 0 ]]; then
    print_warn "Einige Pakete konnten nicht installiert werden."
    print_warn "PersonaUI kann trotzdem funktionieren, wenn nur optionale Pakete fehlen."
fi

# ══════════════════════════════════════════════════════════════════════
#  Step 6: React-Frontend bauen
# ══════════════════════════════════════════════════════════════════════

print_step 6 $TOTAL_STEPS "React-Frontend bauen"

if [[ ! -d "$FRONTEND_DIR" ]]; then
    print_warn "Frontend-Verzeichnis nicht gefunden, uebersprungen"
else
    cd "$FRONTEND_DIR"

    # npm install
    if [[ ! -d "node_modules" ]] || [[ ! -f "node_modules/.package-lock.json" ]]; then
        print_info "npm install (Frontend-Abhaengigkeiten)..."
        npm install
        print_ok "Frontend-Abhaengigkeiten installiert"
    else
        print_ok "node_modules bereits vorhanden"
    fi

    # npm run build
    if [[ ! -f "dist/index.html" ]]; then
        print_info "npm run build (Frontend kompilieren)..."
        npm run build
        if [[ -f "dist/index.html" ]]; then
            print_ok "Frontend erfolgreich gebaut"
        else
            print_warn "Frontend-Build fehlgeschlagen (App nutzt Fallback-UI)"
        fi
    else
        print_ok "Frontend bereits gebaut (dist/index.html vorhanden)"
    fi

    cd "$ROOT"
fi

# ══════════════════════════════════════════════════════════════════════
#  Step 7: Konfiguration fuer Android anpassen
# ══════════════════════════════════════════════════════════════════════

print_step 7 $TOTAL_STEPS "Konfiguration fuer Android anpassen"

# --no-gui aktivieren (PyWebView nicht verfuegbar auf Android)
DEFAULT_LAUNCH="$ROOT/config/default/launch_options.ini"
if [[ -f "$LAUNCH_FILE" ]]; then
    if grep -q "^no_gui\s*=\s*true" "$LAUNCH_FILE"; then
        print_ok "no_gui bereits aktiviert"
    else
        # no_gui auf true setzen
        sed -i 's/^no_gui\s*=.*/no_gui = true/' "$LAUNCH_FILE"
        print_ok "no_gui aktiviert in launch_options.ini"
    fi
else
    # Aus Default kopieren und no_gui aktivieren
    mkdir -p "$ROOT/config"
    if [[ -f "$DEFAULT_LAUNCH" ]]; then
        cp "$DEFAULT_LAUNCH" "$LAUNCH_FILE"
        sed -i 's/^no_gui\s*=.*/no_gui = true/' "$LAUNCH_FILE"
    else
        cat > "$LAUNCH_FILE" << 'EOF'
[app]
no_gui = true
dev_mode = false
force_build = false

[server]
port = 5000
host = 127.0.0.1

[startup]
check_updates = true
show_splash = true
show_console = false

[dev]
vite_port = 5173
log_level = info
EOF
    fi
    print_ok "launch_options.ini erstellt mit no_gui = true"
fi

# .env Datei prüfen
ENV_FILE="$ROOT/src/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    print_info "Hinweis: .env Datei wird beim ersten Start automatisch erstellt."
    print_info "Du kannst deinen Anthropic API-Key dort eintragen:"
    print_info "  $ENV_FILE"
fi

# ══════════════════════════════════════════════════════════════════════
#  Fertig!
# ══════════════════════════════════════════════════════════════════════

echo ""
echo -e "  ${CYAN}${BOLD}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "  ${CYAN}${BOLD}║                                                  ║${RESET}"
echo -e "  ${GREEN}${BOLD}  ║     ✓  Installation abgeschlossen!               ║${RESET}"
echo -e "  ${CYAN}${BOLD}║                                                  ║${RESET}"
echo -e "  ${CYAN}${BOLD}╚══════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${BOLD}So startest du PersonaUI:${RESET}"
echo ""
echo -e "    ${CYAN}cd $ROOT${RESET}"
echo -e "    ${CYAN}bash bin/start.sh${RESET}"
echo ""
echo -e "  ${BOLD}Dann im Browser oeffnen:${RESET}"
echo -e "    ${CYAN}http://localhost:5000${RESET}"
echo ""
echo -e "  ${DIM}Hinweise:${RESET}"
echo -e "  ${DIM}• PersonaUI laeuft im Browser-Modus (--no-gui)${RESET}"
echo -e "  ${DIM}• PyWebView ist auf Android nicht verfuegbar${RESET}"
echo -e "  ${DIM}• API-Key in src/.env eintragen (ANTHROPIC_API_KEY=...)${RESET}"
echo -e "  ${DIM}• Termux im Hintergrund laufen lassen (Notification ziehen)${RESET}"
echo -e "  ${DIM}• Termux Wake-Lock aktivieren: termux-wake-lock${RESET}"
echo ""
