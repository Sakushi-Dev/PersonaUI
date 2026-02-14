"""PersonaUI Reset – Startet den Reset mit pywebview-GUI."""

import os
import sys
import time
import threading
import subprocess

# WICHTIG: Wechsle ins src Verzeichnis für korrekte Pfade
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

from reset_screen import load_reset_html, reset_sequence


def run_reset(window):
    """Wartet auf Bestätigung im GUI und führt dann den Reset aus."""

    # Warte auf Bestätigung oder Abbruch
    while True:
        time.sleep(0.2)
        try:
            confirmed = window.evaluate_js("isConfirmed()")
            cancelled = window.evaluate_js("isCancelled()")
        except Exception:
            return  # Fenster geschlossen

        if cancelled:
            time.sleep(1)
            try:
                window.destroy()
            except Exception:
                pass
            return

        if confirmed:
            break

    # Reset ausführen
    reset_sequence(window)

    # Warte auf "Starten" oder "Schließen"
    while True:
        time.sleep(0.3)
        try:
            should_start = window.evaluate_js("shouldStartApp()")
            should_close = window.evaluate_js("shouldCloseApp()")
        except Exception:
            return  # Fenster geschlossen

        if should_close:
            try:
                window.destroy()
            except Exception:
                pass
            return

        if should_start:
            try:
                window.destroy()
            except Exception:
                pass
            # PersonaUI starten
            root_dir = os.path.dirname(script_dir)
            exe_path = os.path.join(root_dir, 'PersonaUI.exe')
            if os.path.exists(exe_path):
                subprocess.Popen(
                    [exe_path],
                    cwd=root_dir,
                )
            else:
                # Fallback: start.bat in bin/
                start_bat = os.path.join(root_dir, 'bin', 'start.bat')
                if os.path.exists(start_bat):
                    subprocess.Popen(
                        ['cmd', '/c', start_bat],
                        cwd=root_dir,
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
            return


if __name__ == '__main__':
    try:
        import webview

        window = webview.create_window(
            'PersonaUI – Reset',
            html=load_reset_html(),
            width=900,
            height=620,
            min_size=(700, 500),
            resizable=True,
            text_select=True,
        )

        reset_thread = threading.Thread(
            target=run_reset,
            args=(window,),
            daemon=True,
        )

        def _on_shown():
            reset_thread.start()

        window.events.shown += _on_shown

        webview.start()
        os._exit(0)

    except ImportError:
        # Fallback: Einfacher Konsolen-Reset
        print()
        print("========================================")
        print("  PERSONAUI - RESET")
        print("========================================")
        print()
        print("PyWebView nicht installiert. Konsolen-Modus.")
        print()
        print("WARNUNG: Alle Daten werden geloescht!")
        print("  - Chat-Nachrichten, Sitzungen")
        print("  - Einstellungen, API-Schluessel")
        print("  - Erstellte Personas, Avatare")
        print()
        confirm = input("Fortfahren? (ja/nein): ").strip().lower()
        if confirm != 'ja':
            print("Abbruch.")
            sys.exit(0)

        print()
        # Inline-Reset ohne GUI
        import glob
        import shutil

        src = script_dir
        data_dir = os.path.join(src, 'data')

        # Datenbanken
        for f in glob.glob(os.path.join(data_dir, '*.db')):
            try: os.remove(f)
            except: pass
        for f in glob.glob(os.path.join(data_dir, '*.db.backup')):
            try: os.remove(f)
            except: pass
        print("[1/8] Datenbanken geloescht")

        # .env
        env_path = os.path.join(src, '.env')
        if os.path.exists(env_path):
            os.remove(env_path)
        print("[2/8] .env geloescht")

        # Settings
        for name in ['server_settings.json', 'user_settings.json', 'user_profile.json', 'window_settings.json', 'onboarding.json']:
            fp = os.path.join(src, 'settings', name)
            if os.path.exists(fp):
                os.remove(fp)
        print("[3/8] Einstellungen geloescht")

        # Personas + Custom Specs
        for f in glob.glob(os.path.join(src, 'instructions', 'created_personas', '*.json')):
            try: os.remove(f)
            except: pass
        cs = os.path.join(src, 'instructions', 'personas', 'spec', 'custom_spec', 'custom_spec.json')
        if os.path.exists(cs):
            os.remove(cs)
        print("[4/8] Personas & Custom Specs geloescht")

        # Active persona
        ac = os.path.join(src, 'instructions', 'personas', 'active', 'persona_config.json')
        if os.path.exists(ac):
            os.remove(ac)
        print("[5/8] Aktive Persona entfernt")

        # Logs
        for f in glob.glob(os.path.join(src, 'logs', '*.log*')):
            try: os.remove(f)
            except: pass
        print("[6/8] Logs geloescht")

        # Custom Avatare
        custom_dir = os.path.join(src, 'static', 'images', 'custom')
        if os.path.isdir(custom_dir):
            for f in os.listdir(custom_dir):
                if f != '.gitkeep':
                    try: os.remove(os.path.join(custom_dir, f))
                    except: pass
        print("[7/8] Custom Avatare geloescht")

        # __pycache__
        for root, dirs, _ in os.walk(src, topdown=False):
            for d in dirs:
                if d == '__pycache__':
                    try: shutil.rmtree(os.path.join(root, d))
                    except: pass
        print("[8/9] Cache geloescht")

        # Prompts auf Factory-Defaults
        instructions_dir = os.path.join(src, 'instructions')
        prompts_dir = os.path.join(instructions_dir, 'prompts')
        defaults_dir = os.path.join(prompts_dir, '_defaults')
        restored = 0
        if os.path.isdir(defaults_dir):
            for filename in os.listdir(defaults_dir):
                if not filename.endswith('.json'):
                    continue
                s = os.path.join(defaults_dir, filename)
                d = os.path.join(prompts_dir, filename)
                try:
                    shutil.copy2(s, d)
                    restored += 1
                except: pass
            # _meta/ Unterordner
            defaults_meta = os.path.join(defaults_dir, '_meta')
            if os.path.isdir(defaults_meta):
                meta_dir = os.path.join(prompts_dir, '_meta')
                os.makedirs(meta_dir, exist_ok=True)
                for filename in os.listdir(defaults_meta):
                    if not filename.endswith('.json'):
                        continue
                    s = os.path.join(defaults_meta, filename)
                    d = os.path.join(meta_dir, filename)
                    try:
                        shutil.copy2(s, d)
                        restored += 1
                    except: pass
            print(f"[9/9] {restored} Prompt-Dateien wiederhergestellt")
        else:
            print("[9/9] WARNUNG: _defaults/ nicht gefunden, Prompt-Reset uebersprungen")

        print()
        print("Reset abgeschlossen!")
        print("Starten Sie PersonaUI mit start.bat")
        print()
        input("Druecke Enter zum Beenden...")
