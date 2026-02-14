"""
merge_to_defaults.py
====================
Kopiert alle aktuellen Prompt-Dateien (inkl. _meta/) aus
  src/instructions/prompts/
nach
  src/instructions/prompts/_defaults/

Damit wird der aktuelle Stand als neuer Default hinterlegt.

Verwendung:
    python src/dev/prompts/merge_to_defaults.py          # Vorschau (dry-run)
    python src/dev/prompts/merge_to_defaults.py --apply   # Tatsächlich kopieren
"""

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

# ── Pfade ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[3]          # PersonaUI/
PROMPTS_DIR  = PROJECT_ROOT / "src" / "instructions" / "prompts"
DEFAULTS_DIR = PROMPTS_DIR / "_defaults"

# Ordner, die NICHT in die Defaults kopiert werden sollen
EXCLUDE_DIRS = {"_defaults", "__pycache__"}


def collect_source_files(base: Path) -> list[Path]:
    """Sammelt alle JSON-Dateien rekursiv, außer _defaults/ selbst."""
    files: list[Path] = []
    for item in sorted(base.rglob("*.json")):
        # Prüfen ob der Pfad in einem ausgeschlossenen Ordner liegt
        rel = item.relative_to(base)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        files.append(item)
    return files


def merge(apply: bool = False) -> None:
    if not PROMPTS_DIR.is_dir():
        print(f"FEHLER: Quellverzeichnis nicht gefunden: {PROMPTS_DIR}")
        sys.exit(1)

    source_files = collect_source_files(PROMPTS_DIR)

    if not source_files:
        print("Keine Prompt-Dateien gefunden.")
        sys.exit(0)

    copied   = 0
    skipped  = 0
    new      = 0
    updated  = 0

    print("=" * 60)
    print("  Merge aktuelle Prompts → _defaults")
    print("=" * 60)
    print(f"  Quelle:  {PROMPTS_DIR}")
    print(f"  Ziel:    {DEFAULTS_DIR}")
    print(f"  Modus:   {'APPLY' if apply else 'DRY-RUN (Vorschau)'}")
    print("=" * 60)
    print()

    for src_file in source_files:
        rel       = src_file.relative_to(PROMPTS_DIR)
        dest_file = DEFAULTS_DIR / rel

        # Prüfen ob sich etwas geändert hat
        if dest_file.exists():
            if filecmp.cmp(src_file, dest_file, shallow=False):
                skipped += 1
                continue
            status = "UPDATE"
            updated += 1
        else:
            status = "NEU   "
            new += 1

        print(f"  [{status}]  {rel}")

        if apply:
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dest_file)
            copied += 1

    # Dateien in _defaults die in prompts/ nicht mehr existieren
    removed = 0
    if DEFAULTS_DIR.is_dir():
        for def_file in sorted(DEFAULTS_DIR.rglob("*.json")):
            rel = def_file.relative_to(DEFAULTS_DIR)
            # _meta/user_manifest.json existiert nur in prompts/_meta, 
            # nicht in _defaults – überspringen falls es dort nicht hingehört
            src_counterpart = PROMPTS_DIR / rel
            if not src_counterpart.exists():
                print(f"  [ENTF. ]  {rel}  (in Quelle nicht mehr vorhanden)")
                if apply:
                    def_file.unlink()
                removed += 1

    print()
    print("-" * 60)
    print(f"  Neu:        {new}")
    print(f"  Aktualisiert: {updated}")
    print(f"  Unverändert:  {skipped}")
    print(f"  Entfernt:     {removed}")

    if apply:
        print(f"\n  ✓ {copied} Dateien kopiert, {removed} entfernt.")
    else:
        total_changes = new + updated + removed
        if total_changes:
            print(f"\n  → {total_changes} Änderung(en) erkannt.")
            print("  → Erneut mit --apply ausführen um zu übernehmen.")
        else:
            print("\n  Alles bereits synchron – keine Änderungen nötig.")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aktuelle Prompts (inkl. _meta) als Defaults setzen."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Änderungen tatsächlich durchführen (ohne: nur Vorschau).",
    )
    args = parser.parse_args()
    merge(apply=args.apply)


if __name__ == "__main__":
    main()
