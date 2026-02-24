"""PersonaUI Reset – Starts the reset with pywebview GUI."""

import os
import sys
import json
import time
import threading
import subprocess

# IMPORTANT: Change to src directory for correct paths
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

from reset_screen import load_reset_html, reset_sequence
from reset_screen import collect_personas, PRESETS, PRESET_ORDER


def _inject_data(window):
    """Injects preset and persona data into JS and initializes the UI."""
    personas = collect_personas()

    presets_json = json.dumps(PRESETS, ensure_ascii=False)
    order_json = json.dumps(PRESET_ORDER, ensure_ascii=False)
    personas_json = json.dumps(personas, ensure_ascii=False)

    window.evaluate_js(f"window._PRESETS = {presets_json};")
    window.evaluate_js(f"window._PRESET_ORDER = {order_json};")
    window.evaluate_js(f"window._PERSONAS = {personas_json};")
    window.evaluate_js("initResetUI();")


def run_reset(window):
    """Waits for confirmation in the GUI, then executes the reset."""

    # Brief wait until DOM is ready
    time.sleep(0.5)

    # Inject data
    try:
        _inject_data(window)
    except Exception:
        pass

    # Wait for confirmation or cancellation
    while True:
        time.sleep(0.2)
        try:
            confirmed = window.evaluate_js("isConfirmed()")
            cancelled = window.evaluate_js("isCancelled()")
        except Exception:
            return  # Window closed

        if cancelled:
            time.sleep(1)
            try:
                window.destroy()
            except Exception:
                pass
            return

        if confirmed:
            break

    # Read selected preset and personas
    preset_id = 'full'
    selected_personas = []
    try:
        preset_id = window.evaluate_js("getSelectedPreset()") or 'full'
        raw = window.evaluate_js("getSelectedPersonas()")
        if raw:
            selected_personas = json.loads(raw)
    except Exception:
        pass

    # Execute reset
    reset_sequence(window, preset_id=preset_id, selected_persona_ids=selected_personas)

    # Wait for "Launch" or "Close"
    while True:
        time.sleep(0.3)
        try:
            should_start = window.evaluate_js("shouldStartApp()")
            should_close = window.evaluate_js("shouldCloseApp()")
        except Exception:
            return  # Window closed

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
            # Launch PersonaUI
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
        # Fallback: Simple console reset
        print()
        print("========================================")
        print("  PERSONAUI - RESET")
        print("========================================")
        print()
        print("PyWebView not installed. Console mode.")
        print()
        print("WARNING: All data will be deleted!")
        print("  - Chat messages, sessions")
        print("  - Settings, API key")
        print("  - Created personas, avatars")
        print()
        confirm = input("Continue? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("Cancelled.")
            sys.exit(0)

        print()
        # Inline-Reset ohne GUI
        import glob
        import shutil

        src = script_dir
        data_dir = os.path.join(src, 'data')

        # Databases
        for f in glob.glob(os.path.join(data_dir, '*.db')):
            try: os.remove(f)
            except: pass
        for f in glob.glob(os.path.join(data_dir, '*.db.backup')):
            try: os.remove(f)
            except: pass
        print("[1/11] Databases deleted")

        # .env
        env_path = os.path.join(src, '.env')
        if os.path.exists(env_path):
            os.remove(env_path)
        print("[2/11] .env deleted")

        # Settings
        for name in ['server_settings.json', 'user_settings.json', 'user_profile.json', 'window_settings.json', 'onboarding.json', 'cycle_state.json', 'emoji_usage.json', 'cortex_settings.json']:
            fp = os.path.join(src, 'settings', name)
            if os.path.exists(fp):
                os.remove(fp)
        print("[3/11] Settings deleted")

        # Personas + Custom Specs
        for f in glob.glob(os.path.join(src, 'instructions', 'created_personas', '*.json')):
            try: os.remove(f)
            except: pass
        cs = os.path.join(src, 'instructions', 'personas', 'spec', 'custom_spec', 'custom_spec.json')
        if os.path.exists(cs):
            os.remove(cs)
        print("[4/11] Personas & custom specs deleted")

        # Active persona
        ac = os.path.join(src, 'instructions', 'personas', 'active', 'persona_config.json')
        if os.path.exists(ac):
            os.remove(ac)
        print("[5/11] Active persona removed")

        # Cortex custom memory files
        cortex_custom = os.path.join(src, 'instructions', 'personas', 'cortex', 'custom')
        if os.path.isdir(cortex_custom):
            for entry in os.listdir(cortex_custom):
                entry_path = os.path.join(cortex_custom, entry)
                if entry == '.gitkeep':
                    continue
                if os.path.isdir(entry_path):
                    try: shutil.rmtree(entry_path)
                    except: pass
                elif os.path.isfile(entry_path):
                    try: os.remove(entry_path)
                    except: pass
        print("[6/11] Cortex memory deleted")

        # Persona notes
        persona_notes_dir = os.path.join(src, 'data', 'persona_notes')
        if os.path.isdir(persona_notes_dir):
            for entry in os.listdir(persona_notes_dir):
                entry_path = os.path.join(persona_notes_dir, entry)
                if entry in ('.gitkeep', 'default'):
                    continue
                if os.path.isdir(entry_path):
                    try: shutil.rmtree(entry_path)
                    except: pass
                elif os.path.isfile(entry_path):
                    try: os.remove(entry_path)
                    except: pass
        print("[7/11] Persona notes deleted")

        # Logs
        for f in glob.glob(os.path.join(src, 'logs', '*.log*')):
            try: os.remove(f)
            except: pass
        print("[8/11] Logs deleted")

        # Custom Avatare (now in frontend/public/avatar/costum/)
        root_dir = os.path.dirname(src)
        custom_dir = os.path.join(root_dir, 'frontend', 'public', 'avatar', 'costum')
        if os.path.isdir(custom_dir):
            for f in os.listdir(custom_dir):
                if f != '.gitkeep':
                    try: os.remove(os.path.join(custom_dir, f))
                    except: pass
        # Remove avatar index.json (rebuilt automatically on next start)
        avatar_index = os.path.join(root_dir, 'frontend', 'public', 'avatar', 'index.json')
        if os.path.exists(avatar_index):
            try: os.remove(avatar_index)
            except: pass
        print("[9/11] Custom avatars deleted")

        # __pycache__
        for root, dirs, _ in os.walk(src, topdown=False):
            for d in dirs:
                if d == '__pycache__':
                    try: shutil.rmtree(os.path.join(root, d))
                    except: pass
        print("[10/11] Cache deleted")

        # Prompts to factory defaults
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
            # _meta/ subdirectory
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
            print(f"[11/11] {restored} prompt file(s) restored")
        else:
            print("[11/11] WARNING: _defaults/ not found, prompt reset skipped")

        print()
        print("Reset complete!")
        print("Start PersonaUI with start.bat")
        print()
        input("Press Enter to exit...")
