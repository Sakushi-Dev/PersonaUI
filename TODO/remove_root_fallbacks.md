# TODO: Remove Root Fallback Files

## What?
`version.json` and `changelog.json` currently exist **in two locations**:
- `config/version.json` ← primary (new)
- `config/changelog.json` ← primary (new)
- `version.json` ← fallback copy in root (legacy)
- `changelog.json` ← fallback copy in root (legacy)

## Why?
Old installations (≤ v0.3.0) look for `version.json` and `changelog.json` in the project root.
Without the fallback copies, the update check would fail for those clients and they would never see available updates.

## When to remove?
Once it can be assumed that no old installations (≤ v0.3.0) are still in use.

## Steps to complete
1. Delete `version.json` and `changelog.json` from the root directory
2. Remove fallback logic from the following files:
   - `src/splash_screen/utils/update_check.py` → remove `_VERSION_FILE_FALLBACK`, `_CHANGELOG_FILE_FALLBACK` and the fallback loops/lines
   - `bin/update.bat` → remove PowerShell fallback in the `for /f` lines (local + remote version)
3. Check `.gitignore` for any entries that may need updating
4. Test: Verify update check works (local + remote) without fallback

## Affected files
- `version.json` (root) — delete
- `changelog.json` (root) — delete
- `src/splash_screen/utils/update_check.py` — remove fallback
- `bin/update.bat` — remove fallback

---
*Created: 2026-02-24 (v0.3.0 → folder structure refactor)*
