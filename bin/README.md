# PersonaUI – bin/ Verzeichnis

## Übersicht

Dieses Verzeichnis enthält die Starter- und Hilfsskripte für PersonaUI.
Alle `.bat`-Dateien verwenden **automatische Root-Erkennung** (`%~dp0`) und
funktionieren sowohl aus `bin/` als auch aus dem Projekt-Root.

---

## Skripte

### start.bat

Hauptstarter für PersonaUI.

- **Root-Erkennung:** Prüft ob `src\app.py` relativ zum eigenen Pfad
  existiert – einmal direkt (→ Root) und einmal eine Ebene höher (→ `bin/`).
- **Python-Suche:** Bevorzugt `.venv`, dann System-Python, dann `py`-Launcher.
  Falls nichts gefunden: bietet automatische Installation via `install_py12.bat` an.
- **Launch Options:** Liest `launch_options.txt` aus dem Root und übergibt
  die darin definierten Optionen zusätzlich an `init.py`.
- **Ablauf:** `start.bat` → `init.py` (Ersteinrichtung/venv/pip) → `app.py`
- **EXE:** Kann mit *Bat To Exe Converter* in `PersonaUI.exe` umgewandelt werden.
  Die EXE wird im **Projekt-Root** abgelegt und funktioniert dank Root-Erkennung
  identisch zur `.bat`-Variante in `bin/`.

### reset.bat

Setzt PersonaUI vollständig zurück (Datenbanken, Einstellungen, Personas, etc.).

- **Root-Erkennung:** Prüft ob `src\reset.py` existiert – gleiche Logik
  wie `start.bat`.
- **Python:** Nutzt direkt den venv-Python-Pfad (`.venv\Scripts\python.exe`).
  Setzt voraus, dass `start.bat` mindestens einmal ausgeführt wurde.
- **GUI:** Öffnet ein PyWebView-Fenster mit Bestätigungs-Dialog und
  animierter Reset-Sequenz. Fallback auf Konsolen-Reset wenn PyWebView
  nicht verfügbar ist.
- **EXE:** Kann mit *Bat To Exe Converter* in `reset.exe`
  umgewandelt werden. Die EXE wird im **Projekt-Root** abgelegt.

### update.bat

Aktualisiert PersonaUI über Git auf den neuesten Stand.

- **Root-Erkennung:** Wechselt via `cd /d "%~dp0.."` ins Projekt-Root.
- **Ablauf:** `git fetch` → Commit-Vergleich → `git merge origin/main`
  → `pip install -r requirements.txt --upgrade`
- Speichert den letzten Update-Commit in `.last_update_commit` um bei
  erneutem Aufruf unnötige Updates zu vermeiden.

### install_py12.bat

Hilfsskript zur automatischen Installation von Python 3.12.
Wird von `start.bat` aufgerufen falls kein Python gefunden wird.

---

## EXE-Konvertierung

`start.bat` und `reset.bat` enthalten die Header-Kommentare für den
[Bat To Exe Converter](https://www.battoexeconverter.com/).

| Bat-Datei   | EXE-Name             | Ablageort    |
|-------------|----------------------|--------------|
| start.bat   | PersonaUI.exe        | Projekt-Root |
| reset.bat   | reset.exe            | Projekt-Root |

Die EXE-Dateien erkennen automatisch, dass sie im Root liegen
(`src\` existiert direkt) und setzen alle Pfade entsprechend.

---

## Start aus bin/ vs. Root

PersonaUI kann **gleichwertig** aus beiden Orten gestartet werden:

```
PersonaUI/
├── PersonaUI.exe          ← Start als EXE (Root)
├── PersonaUI-Reset.exe    ← Reset als EXE (Root)
├── launch_options.txt     ← Startoptionen
├── bin/
│   ├── start.bat          ← Start als BAT (bin/)
│   ├── reset.bat          ← Reset als BAT (bin/)
│   └── update.bat         ← Update als BAT (bin/)
└── src/
    └── ...
```

Es gibt keinen Unterschied – die Root-Erkennung stellt sicher, dass
immer die korrekten Pfade verwendet werden.

---

## launch_options.txt

Im Projekt-Root kann eine `launch_options.txt` angelegt werden.
Diese Datei wird beim Start automatisch gelesen. Optionen werden
als Kommandozeilen-Argumente an PersonaUI weitergegeben.

**Format:**
- Eine Option pro Zeile
- Zeilen mit `#` am Anfang sind Kommentare
- Leere Zeilen werden ignoriert

**Verfügbare Optionen:**

| Option      | Beschreibung                                              |
|-------------|-----------------------------------------------------------|
| `--no-gui`  | Startet ohne PyWebView-Fenster (reiner Browser-Modus)     |

**Beispiel:**
```
# Kein GUI-Fenster, nur Browser
--no-gui
```
