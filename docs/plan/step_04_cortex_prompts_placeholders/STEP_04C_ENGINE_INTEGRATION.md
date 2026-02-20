# Schritt 4C: Engine Integration

## Übersicht

Dieses Dokument beschreibt die Integration der Cortex-Placeholders und -Templates (aus 4A/4B) in die bestehende PromptEngine. Zentrale Frage: **Welche Code-Änderungen braucht die Engine, um den `cortex_context`-Block korrekt zu laden, bedingt einzuschließen und als Teil des System-Prompts auszugeben?**

| Aspekt | Status |
|---|---|
| Manifest-Eintrag (`cortex_context`) | Neuer Eintrag in `prompt_manifest.json` — reine Config |
| Domain-Datei (`cortex_context.json`) | Neue Datei — wird automatisch geladen |
| Placeholder-Registry (3 Cortex-Keys) | Neue Einträge — werden automatisch gemergt |
| `requires_any`-Prüfung | **Neues Feature** — minimaler Code-Eingriff in `engine.py` |
| `cortexEnabled`-Setting | **Neues Setting** — Gate im ChatService |
| Post-Processing (Leerzeilen) | Kleiner Eingriff in `_resolve_prompt_content()` |
| Validator-Update (`cortex`-Kategorie) | 1 Zeile in `validator.py` |

---

## 1. Analyse: Was die Engine bereits kann

### 1.1 `_load_all()` — Automatische Discovery

Die `_load_all()`-Methode (engine.py, Zeile 75–170) lädt:

1. **System-Manifest** → `_loader.load_manifest()` → `prompt_manifest.json`
2. **User-Manifest** → `_loader.load_user_manifest()` → `user_manifest.json`
3. **Merged Manifest** → `_merge_manifests()` — System als Basis, User obendrauf
4. **System-Registry** → `_loader.load_registry()` → `placeholder_registry.json`
5. **User-Registry** → `_loader.load_user_registry()` → `user_placeholder_registry.json`
6. **Merged Registry** → `_merge_registries()`
7. **Domain-Dateien** → `_loader.load_all_domains(manifest)` — iteriert über alle `domain_file`-Referenzen im Manifest

**Für Cortex bedeutet das:**
- Sobald `cortex_context` im Manifest steht und auf `cortex_context.json` zeigt, wird die Domain-Datei **automatisch** geladen.
- Sobald die 3 Cortex-Placeholders in `placeholder_registry.json` stehen, werden sie **automatisch** in die merged Registry aufgenommen.
- **Kein Code-Eingriff in `_load_all()` nötig.**

### 1.2 `build_system_prompt()` — Block-Assembly

Die Methode (engine.py, Zeile 375–415) baut den System-Prompt:

```python
def build_system_prompt(self, variant='default', runtime_vars=None, category_filter=None):
    prompts = self.get_prompts_by_target('system_prompt', category_filter)
    parts: List[str] = []

    NON_CHAT_CATEGORIES = {'summary', 'spec_autofill'}

    for prompt_data in prompts:
        meta = prompt_data['meta']
        position = meta.get('position', 'system_prompt')

        if position == 'system_prompt_append':
            continue
        if not category_filter and meta.get('category') in NON_CHAT_CATEGORIES:
            continue

        content = self._resolve_prompt_content(prompt_data, variant, runtime_vars)
        if content:
            parts.append(content)

    return "\n\n".join(parts)
```

**Für Cortex:**
- `cortex_context` hat `category: "context"` → wird von `NON_CHAT_CATEGORIES` **nicht** gefiltert ✓
- `cortex_context` hat `position: "system_prompt"` → passiert den `system_prompt_append`-Check ✓
- `cortex_context` hat `enabled: true` → wird durch `get_prompts_by_target()` einbezogen ✓
- `cortex_context` hat `order: 2000` → wird als **letzter** Block sortiert ✓

**Problem:** Wenn alle Cortex-Placeholders leer sind, resolved das Template zu:

```
**INNERE WELT — SELBSTWISSEN**

Die folgenden Abschnitte beschreiben dein tiefstes Wissen...

Integriere dieses Wissen natürlich...



**ENDE INNERE WELT**
```

Das ist ein leerer Rahmen — verschwendet Tokens und verwirrt das Modell. Hier brauchen wir `requires_any`.

### 1.3 `_resolve_prompt_content()` — Variante + Placeholder-Auflösung

Die Methode (engine.py, Zeile 653–693) handhabt:

1. **`variant_condition`** — Prompt wird übersprungen wenn Variante nicht matcht
2. **Variant-Fallback** — Erst spezifische Variante, dann `default`
3. **Placeholder-Resolution** — `self._resolver.resolve_text(raw_content, variant, runtime_vars)`

```python
def _resolve_prompt_content(self, prompt_data, variant='default', runtime_vars=None):
    meta = prompt_data.get('meta', {})
    content_data = prompt_data.get('content', {})

    # variant_condition prüfen
    variant_condition = meta.get('variant_condition')
    if variant_condition and variant_condition != variant:
        return ''

    # Variante wählen
    variants = content_data.get('variants', {})
    variant_data = variants.get(variant) or variants.get('default')
    if not variant_data:
        return ''

    raw_content = variant_data.get('content', '')
    if not raw_content:
        return ''

    # Placeholder auflösen
    if self._resolver:
        return self._resolver.resolve_text(raw_content, variant, runtime_vars)
    return raw_content
```

**Für Cortex:**
- `cortex_context` hat keine `variant_condition` → wird für alle Varianten generiert ✓
- Das Template hat eine `default`-Variante → Fallback greift immer ✓
- `runtime_vars` enthält `cortex_memory`, `cortex_soul`, `cortex_relationship` → werden korrekt resolved ✓

**Es gibt KEINEN eingebauten Mechanismus für `requires_any`.** Der Content wird immer resolved, auch wenn alle Placeholders zu leeren Strings werden.

### 1.4 `variant_condition` — Bestehendes Conditional-Pattern

`variant_condition` ist der einzige bestehende Mechanismus zum bedingten Überspringen eines Blocks. Er prüft die **aktive Variante** (`default` vs. `experimental`), nicht den **Inhalt von Placeholders**.

```python
variant_condition = meta.get('variant_condition')
if variant_condition and variant_condition != variant:
    return ''
```

**Nicht nutzbar für Cortex**, weil wir nicht auf Variante, sondern auf Placeholder-Inhalte prüfen müssen.

### 1.5 `get_prompts_by_target()` — enabled-Filter

```python
def get_prompts_by_target(self, target, category_filter=None):
    result = []
    for prompt_id, meta in self._manifest.get('prompts', {}).items():
        if meta.get('target') != target:
            continue
        if not meta.get('enabled', True):    # ← enabled-Check
            continue
        if category_filter and meta.get('category') != category_filter:
            continue
        # ... load domain data ...
    result.sort(key=lambda x: x['meta'].get('order', 9999))
    return result
```

**Für Cortex:** `enabled: true` im Manifest → Block wird einbezogen. Der User kann ihn im Prompt-Editor deaktivieren.

### 1.6 PlaceholderResolver — Drei-Phasen-Resolution

```python
def _build_variables(self, variant='default', runtime_vars=None):
    variables = {}
    variables.update(self._resolve_static())     # Phase 1: persona_config, user_profile
    variables.update(self._resolve_computed())    # Phase 2: compute functions
    if runtime_vars:
        variables.update(runtime_vars)            # Phase 3: runtime_vars (überschreibt!)
    return variables
```

- `cortex_memory`, `cortex_soul`, `cortex_relationship` sind als `resolve_phase: "runtime"` registriert
- Sie werden in Phase 1/2 **nicht** verarbeitet (weil `resolve_phase != 'static'` und `!= 'computed'`)
- In Phase 3 werden sie aus `runtime_vars` übernommen
- Wenn `runtime_vars` sie nicht enthält, bleiben sie als `{{cortex_memory}}` im Text stehen (kein Crash)

**Kein Code-Eingriff im PlaceholderResolver nötig.**

---

## 2. Engine-Änderungen: `requires_any`

### 2.1 Kernfrage: Braucht die Engine eine Code-Änderung?

**Ja, eine minimale.** Die Engine hat aktuell keinen Mechanismus, um einen Block basierend auf **Placeholder-Inhalten** zu überspringen. Die bestehenden Filter sind:

| Filter | Prüft | Ausreichend für Cortex? |
|---|---|---|
| `enabled` | Bool im Manifest | Nein — statisch, nicht content-abhängig |
| `variant_condition` | Aktive Variante | Nein — prüft Variante, nicht Content |
| `NON_CHAT_CATEGORIES` | Kategorie-Set | Nein — `context` ist keine Non-Chat-Kategorie |
| `category_filter` | Expliziter Parameter | Nein — extern gesteuert, nicht content-abhängig |

### 2.2 Alternative: Ohne Engine-Änderung

Man **könnte** argumentieren: "Wenn alle Cortex-Vars leer sind, resolved das Template zwar zu einem leeren Rahmen, aber der Rahmen hat ja keinen Inhalt — das ist harmlos."

**Gegenargumente:**

1. **Token-Verschwendung:** Der Rahmentext ("INNERE WELT — SELBSTWISSEN", Framing-Absätze, "ENDE INNERE WELT") umfasst ca. 80 Tokens — bei jeder Nachricht, auch ohne Cortex-Daten.
2. **Modell-Verwirrung:** Ein leerer "Innere Welt"-Block signalisiert dem Modell, dass Erinnerungen/Persönlichkeit vorhanden *sein sollten*, aber nichts da ist. Das kann zu Halluzinationen führen.
3. **Sauberkeit:** Alle leeren Blöcke wegzulassen ist das bewährte Pattern. `_resolve_prompt_content()` gibt `''` zurück wenn kein Content → Block wird nicht aufgenommen. Dasselbe sollte für "Hat Content, aber alle Placeholders darin sind leer" gelten.

**Entscheidung: `requires_any` implementieren** — als generisches, wiederverwendbares Feature.

### 2.3 Implementierung: `_should_include_block()`

Eine neue private Methode prüft, ob ein Block eingeschlossen werden soll. Wird in `build_system_prompt()` aufgerufen — **vor** dem `_resolve_prompt_content()`-Aufruf, um unnötige Resolution zu vermeiden.

**Neue Methode in `engine.py`:**

```python
def _should_include_block(self, meta: Dict[str, Any],
                          runtime_vars: Optional[Dict[str, str]] = None,
                          variant: str = 'default') -> bool:
    """Prüft ob ein Prompt-Block ins Ergebnis aufgenommen werden soll.

    Prüft:
    1. enabled-Flag (bereits durch get_prompts_by_target() gefiltert, aber Sicherheit)
    2. requires_any — Block nur einschließen wenn mindestens ein
       gelisteter Placeholder einen non-empty Wert hat

    Args:
        meta: Manifest-Metadaten des Prompts
        runtime_vars: Aufrufer-Variablen (für requires_any-Check)
        variant: Aktive Variante

    Returns:
        True wenn Block eingeschlossen werden soll
    """
    if not meta.get('enabled', True):
        return False

    requires = meta.get('requires_any')
    if requires:
        # Alle Variablen für den Check zusammenbauen
        all_vars = {}
        if self._resolver:
            all_vars = self._resolver.get_all_values(variant, runtime_vars)
        elif runtime_vars:
            all_vars = runtime_vars

        has_content = any(
            all_vars.get(key, '').strip()
            for key in requires
        )
        if not has_content:
            return False

    return True
```

### 2.4 Einbau in `build_system_prompt()`

**Vorher:**

```python
for prompt_data in prompts:
    meta = prompt_data['meta']
    position = meta.get('position', 'system_prompt')

    if position == 'system_prompt_append':
        continue
    if not category_filter and meta.get('category') in NON_CHAT_CATEGORIES:
        continue

    content = self._resolve_prompt_content(prompt_data, variant, runtime_vars)
    if content:
        parts.append(content)
```

**Nachher:**

```python
for prompt_data in prompts:
    meta = prompt_data['meta']
    position = meta.get('position', 'system_prompt')

    if position == 'system_prompt_append':
        continue
    if not category_filter and meta.get('category') in NON_CHAT_CATEGORIES:
        continue

    # NEU: requires_any-Check (z.B. Cortex-Block nur bei vorhandenem Content)
    if not self._should_include_block(meta, runtime_vars, variant):
        continue

    content = self._resolve_prompt_content(prompt_data, variant, runtime_vars)
    if content:
        parts.append(content)
```

### 2.5 Performance-Überlegung

`_should_include_block()` ruft `self._resolver.get_all_values()` auf, was alle drei Phasen durchläuft. Das könnte teuer sein, **aber**:

1. `requires_any` wird nur von Blöcken genutzt, die es explizit deklarieren (aktuell nur `cortex_context`)
2. Phase 1 (static) ist gecacht — kostet fast nichts
3. Phase 2 (computed) wird sowieso für die Resolution gebraucht — kein Zusatzaufwand
4. Phase 3 (runtime) ist ein simples dict.update — O(n) mit n = Anzahl runtime_vars

**Optimierung (optional):** Alternativ kann `_should_include_block()` nur `runtime_vars` prüfen statt `get_all_values()`, da alle `requires_any`-Keys runtime-Placeholders sind:

```python
# Optimierte Version — nur für runtime_vars
requires = meta.get('requires_any')
if requires and runtime_vars:
    has_content = any(
        runtime_vars.get(key, '').strip()
        for key in requires
    )
    if not has_content:
        return False
elif requires:
    # Kein runtime_vars übergeben → Block überspringen
    return False
```

**Empfehlung: Optimierte Version verwenden**, da `requires_any` absehbar nur mit runtime-Placeholders verwendet wird. Das spart den `get_all_values()`-Overhead.

### 2.6 Generischer Nutzen

`requires_any` ist nicht Cortex-spezifisch. Es kann in Zukunft für jeden Block verwendet werden, der bedingt auf Placeholder-Inhalten basiert:

| Anwendungsfall | `requires_any` |
|---|---|
| Cortex-Block: Nur wenn Cortex-Daten vorhanden | `["cortex_memory", "cortex_soul", "cortex_relationship"]` |
| Memory-Block: Nur wenn Memory-Entries vorhanden | `["memory_entries"]` (zukünftig möglich) |
| Aftertought nur wenn elapsed_time gesetzt | `["elapsed_time"]` (hypothetisch) |

---

## 3. Umgang mit leerem Cortex-Content

### 3.1 Drei Szenarien

| Szenario | `requires_any`-Ergebnis | Block im Prompt |
|---|---|---|
| Alle 3 Cortex-Dateien befüllt | `True` (alle non-empty) | Vollständiger Block mit allen Sektionen |
| 1–2 Dateien befüllt, Rest leer | `True` (mindestens eine non-empty) | Block mit befüllten Sektionen, leere Sektionen fehlen |
| Alle 3 Dateien leer | `False` (alle empty) | **Block wird komplett übersprungen** |

### 3.2 Szenario 2: Teilweise befüllte Cortex-Dateien

Der `CortexService.get_cortex_for_prompt()` gibt für leere Dateien einen leeren String zurück. Im Template entsteht:

```
**INNERE WELT — SELBSTWISSEN**

Framing-Text...

### Erinnerungen & Wissen
Max liebt Katzen, Max arbeitet als Entwickler...



**ENDE INNERE WELT**
```

Die doppelten Leerzeilen (wo `cortex_soul` und `cortex_relationship` leer sind) sind kosmetisch störend.

### 3.3 Post-Processing: Leerzeilen bereinigen

Die `_resolve_prompt_content()`-Methode wird um einen Post-Processing-Schritt ergänzt:

**Vorher:**

```python
if self._resolver:
    return self._resolver.resolve_text(raw_content, variant, runtime_vars)
return raw_content
```

**Nachher:**

```python
if self._resolver:
    resolved = self._resolver.resolve_text(raw_content, variant, runtime_vars)
    return self._clean_resolved_text(resolved)
return raw_content
```

**Neue Methode:**

```python
def _clean_resolved_text(self, text: str) -> str:
    """Bereinigt aufgelösten Prompt-Text: überschüssige Leerzeilen entfernen.

    Nach der Placeholder-Resolution können 3+ aufeinanderfolgende Newlines
    entstehen (wenn Placeholders zu leeren Strings resolven). Diese werden
    auf maximal 2 Newlines reduziert.
    """
    import re
    return re.sub(r'\n{3,}', '\n\n', text).strip()
```

**Hinweis:** Dieses Post-Processing gilt für **alle** Prompts, nicht nur Cortex. Es ist ein generisches Verbesserung, die keine bestehenden Prompts bricht (da kein Prompt absichtlich 3+ Newlines verwendet).

---

## 4. Manifest-Integration

### 4.1 Neuer Eintrag in `prompt_manifest.json`

Der Eintrag wird im **System-Manifest** (`src/instructions/prompts/_meta/prompt_manifest.json`) hinzugefügt:

```json
"cortex_context": {
  "name": "Cortex-Kontext",
  "description": "Inneres Selbstwissen der Persona — Erinnerungen, Identität, Beziehungsdynamik (aus Cortex-Dateien)",
  "category": "context",
  "type": "text",
  "target": "system_prompt",
  "position": "system_prompt",
  "order": 2000,
  "enabled": true,
  "domain_file": "cortex_context.json",
  "requires_any": ["cortex_memory", "cortex_soul", "cortex_relationship"],
  "tags": ["context", "cortex", "memory", "identity", "relationship"]
}
```

### 4.2 Position im Manifest

Der Eintrag wird **nach** `continuity_guard` (order 1600) eingefügt. Alle bestehenden Prompts behalten ihre Order-Werte. Lücke zwischen 1600 und 2000 lässt Raum für zukünftige Blöcke.

### 4.3 Defaults-Kopie

Eine identische Kopie muss in `src/instructions/prompts/_defaults/_meta/prompt_manifest.json` eingefügt werden, damit Factory-Reset den Eintrag wiederherstellen kann.

Ebenso wird `cortex_context.json` nach `_defaults/cortex_context.json` kopiert.

### 4.4 Manifest-Lade-Flow

```
_load_all()
  ├── load_manifest() → liest prompt_manifest.json
  │     → enthält "cortex_context" mit domain_file: "cortex_context.json"
  │
  ├── load_all_domains(manifest)
  │     → sammelt alle domain_file-Referenzen aus manifest.prompts
  │     → lädt cortex_context.json automatisch
  │     → self._domains['cortex_context.json'] = { cortex_context: { variants: { ... } } }
  │
  └── PlaceholderResolver(merged_registry, instructions_dir)
        → merged_registry enthält cortex_memory, cortex_soul, cortex_relationship
        → Phase 1/2 ignorieren sie (resolve_phase: "runtime")
        → Phase 3 übernimmt sie aus runtime_vars
```

---

## 5. Registry-Integration

### 5.1 Drei neue Einträge in `placeholder_registry.json`

```json
"cortex_memory": {
  "name": "Cortex Memory",
  "description": "Inhalt der memory.md — Faktenwissen, Vorlieben, wichtige Details über den User",
  "source": "runtime",
  "type": "string",
  "default": "",
  "category": "cortex",
  "resolve_phase": "runtime"
},
"cortex_soul": {
  "name": "Cortex Soul",
  "description": "Inhalt der soul.md — Persönlichkeitsentwicklung, innere Haltung, emotionale Muster",
  "source": "runtime",
  "type": "string",
  "default": "",
  "category": "cortex",
  "resolve_phase": "runtime"
},
"cortex_relationship": {
  "name": "Cortex Relationship",
  "description": "Inhalt der relationship.md — Beziehungsdynamik, gemeinsame Geschichte, Vertrauenslevel",
  "source": "runtime",
  "type": "string",
  "default": "",
  "category": "cortex",
  "resolve_phase": "runtime"
}
```

### 5.2 Defaults-Kopie

Identische Einträge müssen auch in `src/instructions/prompts/_defaults/_meta/placeholder_registry.json` eingefügt werden.

### 5.3 Resolution-Verhalten

| Szenario | Ergebnis |
|---|---|
| `runtime_vars` enthält `cortex_memory: "Max liebt Katzen"` | `{{cortex_memory}}` → `Max liebt Katzen` |
| `runtime_vars` enthält `cortex_memory: ""` | `{{cortex_memory}}` → `` (leerer String) |
| `runtime_vars` enthält `cortex_memory` nicht | `{{cortex_memory}}` → `{{cortex_memory}}` (unreolved, bleibt stehen) |
| `runtime_vars` ist `None` | `{{cortex_memory}}` → `{{cortex_memory}}` (unresolved) |

---

## 6. Validator-Update

### 6.1 Neue Kategorie `cortex`

Die Datei `src/utils/prompt_engine/validator.py` definiert erlaubte Kategorien:

```python
VALID_CATEGORIES = {
    'system', 'persona', 'context', 'prefill',
    'dialog_injection', 'afterthought', 'summary',
    'spec_autofill', 'utility', 'custom'
}
```

Die Cortex-Placeholders verwenden `category: "cortex"` in der Registry. Der Cortex-Block im **Manifest** verwendet `category: "context"`.

**Benötigte Änderung:** Keine im `VALID_CATEGORIES`-Set des Manifest-Validators, da der Manifest-Eintrag `"context"` nutzt.

Allerdings: Der **Placeholder-Validator** (`validate_placeholders()`) prüft ob verwendete Placeholders in der Registry existieren. Da die Cortex-Placeholders in der Registry stehen, passiert diese Prüfung automatisch.

**Optional:** Falls der Validator in Zukunft auch Placeholder-Kategorien validiert, sollte `"cortex"` als gültige Placeholder-Kategorie definiert werden. Aktuell gibt es keine solche Prüfung.

### 6.2 `requires_any`-Validierung

Der Validator kennt `requires_any` nicht. Er ignoriert unbekannte Felder im Manifest (er prüft nur Pflichtfelder: `name`, `type`, `target`, `position`, `order`, `enabled`, `domain_file`).

**Optional (Empfehlung):** Eine Warnung ausgeben, wenn `requires_any` Placeholder-Keys referenziert, die nicht in der Registry existieren:

```python
def validate_requires_any(self, manifest: Dict[str, Any],
                          registry: Dict[str, Any]) -> List[str]:
    """Prüft ob requires_any-Referenzen in der Registry existieren."""
    warnings: List[str] = []
    registry_keys = set(registry.get('placeholders', {}).keys())

    for prompt_id, meta in manifest.get('prompts', {}).items():
        requires = meta.get('requires_any', [])
        for key in requires:
            if key not in registry_keys:
                warnings.append(
                    f"Manifest[{prompt_id}]: requires_any referenziert "
                    f"unbekannten Placeholder '{key}'"
                )

    return warnings
```

**Einbau in `validate_all()`:**

```python
def validate_all(self, manifest, domains, registry):
    errors = []
    warnings = []
    errors.extend(self.validate_manifest(manifest))
    errors.extend(self.validate_cross_references(manifest, set(domains.keys())))

    # NEU: requires_any Referenzen prüfen
    warnings.extend(self.validate_requires_any(manifest, registry))

    # ... bestehende Domain/Placeholder-Validierung ...

    return {'errors': errors, 'warnings': warnings}
```

---

## 7. Vollständiger `build_system_prompt()` Flow mit Cortex

### 7.1 Sequenzdiagramm

```
ChatService.chat_stream()
  │
  ├── 1. variant = 'experimental' if experimentalMode else 'default'
  │
  ├── 2. runtime_vars = {'language': 'de'}
  │
  ├── 3. cortexEnabled? (user_settings.json)
  │     ├── True → cortex_data = _load_cortex_context(persona_id)
  │     │          runtime_vars.update(cortex_data)
  │     └── False → (skip cortex loading)
  │
  ├── 4. engine.build_system_prompt(variant, runtime_vars)
  │       │
  │       ├── get_prompts_by_target('system_prompt')
  │       │     → [impersonation, system_rule, ..., cortex_context]
  │       │       (sortiert nach order, nur enabled=true)
  │       │
  │       ├── for each prompt_data:
  │       │     ├── Skip system_prompt_append
  │       │     ├── Skip NON_CHAT_CATEGORIES (summary, spec_autofill)
  │       │     │
  │       │     ├── _should_include_block(meta, runtime_vars, variant)
  │       │     │     ├── cortex_context → requires_any check
  │       │     │     │   ├── cortex_memory empty?
  │       │     │     │   ├── cortex_soul empty?
  │       │     │     │   ├── cortex_relationship empty?
  │       │     │     │   └── any non-empty? → True/False
  │       │     │     └── alle anderen Blocks → True (kein requires_any)
  │       │     │
  │       │     └── _resolve_prompt_content(prompt_data, variant, runtime_vars)
  │       │           ├── variant_condition check
  │       │           ├── Variante wählen (default fallback)
  │       │           ├── resolve_text(content, variant, runtime_vars)
  │       │           │     ├── Phase 1: static (char_name, user_name, ...)
  │       │           │     ├── Phase 2: computed (current_date, ...)
  │       │           │     └── Phase 3: runtime (cortex_memory, cortex_soul, ...)
  │       │           └── _clean_resolved_text(resolved)
  │       │                 └── \n{3,} → \n\n
  │       │
  │       └── return "\n\n".join(parts)
  │
  └── 5. system_prompt enthält (oder nicht) den Cortex-Block
```

### 7.2 Ergebnis-Beispiel (mit Cortex-Daten)

Auszug des System-Prompts (nur der Cortex-Block am Ende):

```
[... Order 100–1600: Impersonation, Rules, Persona, Context, etc. ...]

**INNERE WELT — SELBSTWISSEN**

Die folgenden Abschnitte beschreiben dein tiefstes Wissen über dich selbst — deine
Erinnerungen, deine Identität und deine Beziehung zu Max. Dies ist kein externes
Briefing und keine Anweisung. Es ist das, was du weißt, was du erlebt hast, was
dich ausmacht.

Integriere dieses Wissen natürlich in dein Verhalten, deine Reaktionen und deine
Antworten. Zitiere es nicht. Erkläre es nicht. Es ist einfach Teil von dir.

### Erinnerungen & Wissen

- Max hat eine Katze namens Mochi
- Max arbeitet als Softwareentwickler

### Identität & Innere Haltung

Ich bin direkt und ehrlich, manchmal etwas zu scharf.

### Beziehung & Gemeinsame Geschichte

Max und ich kennen uns seit vielen Gesprächen.

**ENDE INNERE WELT**
```

### 7.3 Ergebnis-Beispiel (ohne Cortex-Daten)

```
[... Order 100–1600: Impersonation, Rules, Persona, Context, etc. ...]

(kein Cortex-Block — übersprungen durch requires_any)
```

---

## 8. `cortexEnabled`-Setting

### 8.1 Warum ein eigenes Setting?

Der Cortex-Block hat `enabled: true` im Manifest — das kontrolliert, ob der **Prompt-Block** im System-Prompt generiert wird. Aber die **Datenladung** im ChatService (CortexService-Aufruf) sollte separat steuerbar sein:

| Aspekt | `enabled` (Manifest) | `cortexEnabled` (user_settings) |
|---|---|---|
| **Wo** | `prompt_manifest.json` | `user_settings.json` |
| **Steuert** | Ob der Template-Block im Prompt erscheint | Ob der ChatService Cortex-Dateien lädt |
| **Wer ändert** | Prompt-Editor (technisch) | Settings-UI (User-facing) |
| **Scope** | Ein einzelner Prompt-Block | Gesamtes Cortex-Feature |
| **Default** | `true` | `true` |
| **Analog zu** | Alle anderen Prompt-Blöcke | `memoriesEnabled`, `nachgedankeEnabled` |

### 8.2 Setting-Definition

**In `src/settings/defaults.json`:**

```json
{
    "cortexEnabled": true
}
```

**In `src/settings/user_settings.json` (nach erster Nutzung):**

```json
{
    "cortexEnabled": true
}
```

### 8.3 Gate im ChatService

Die neue `_load_cortex_context()`-Methode prüft das Setting **bevor** sie den CortexService aufruft:

```python
def _load_cortex_context(self, persona_id: str = None) -> Dict[str, str]:
    """Lädt Cortex-Dateien für die Placeholder-Auflösung."""
    empty = {
        'cortex_memory': '',
        'cortex_soul': '',
        'cortex_relationship': '',
    }

    # Setting-Check: Cortex global deaktiviert?
    try:
        from ..config import get_setting
        if not get_setting('cortexEnabled', True):
            return empty
    except Exception:
        pass  # Bei Fehler: Cortex aktiviert lassen

    try:
        from ..provider import get_cortex_service
        cortex_service = get_cortex_service()

        if persona_id is None:
            from ..config import get_active_persona_id
            persona_id = get_active_persona_id()

        return cortex_service.get_cortex_for_prompt(persona_id)
    except Exception as e:
        log.warning("Cortex-Kontext konnte nicht geladen werden: %s", e)
        return empty
```

### 8.4 Zusammenspiel von `cortexEnabled` und `requires_any`

```
cortexEnabled = false
  → _load_cortex_context() gibt leere Strings zurück
  → runtime_vars: { cortex_memory: '', cortex_soul: '', cortex_relationship: '' }
  → _should_include_block() → requires_any check → alle leer → False
  → Cortex-Block wird übersprungen
  → Gleicher Effekt wie wenn keine Cortex-Dateien existieren

cortexEnabled = true, aber alle Dateien leer
  → _load_cortex_context() gibt leere Strings zurück (von CortexService)
  → Same as above → Block wird übersprungen

cortexEnabled = true, Dateien befüllt
  → _load_cortex_context() gibt Inhalte zurück
  → _should_include_block() → requires_any → mindestens eine non-empty → True
  → Block wird resolved und eingeschlossen
```

**`cortexEnabled = false` short-circuited den CortexService-Aufruf** — spart Dateisystem-Reads.

---

## 9. Betroffene Dateien

### Geänderte Dateien

| Datei | Änderung | Aufwand |
|---|---|---|
| `src/utils/prompt_engine/engine.py` | +`_should_include_block()` Methode, +`_clean_resolved_text()` Methode, `build_system_prompt()` ergänzt um requires_any-Check | Mittel |
| `src/utils/prompt_engine/validator.py` | +`validate_requires_any()` Methode, `validate_all()` erweitert | Klein |
| `src/instructions/prompts/_meta/prompt_manifest.json` | +1 Eintrag `cortex_context` | Klein |
| `src/instructions/prompts/_defaults/_meta/prompt_manifest.json` | +1 Eintrag `cortex_context` (identisch) | Klein |
| `src/instructions/prompts/_meta/placeholder_registry.json` | +3 Einträge (`cortex_memory`, `cortex_soul`, `cortex_relationship`) | Klein |
| `src/instructions/prompts/_defaults/_meta/placeholder_registry.json` | +3 Einträge (identisch) | Klein |
| `src/settings/defaults.json` | +`cortexEnabled: true` | Trivial |
| `src/utils/services/chat_service.py` | +`_load_cortex_context()`, 3 Methoden erweitert (aus Step 4A) | Mittel |

### Neue Dateien

| Datei | Beschreibung |
|---|---|
| `src/instructions/prompts/cortex_context.json` | Domain-Datei (aus Step 4B) |
| `src/instructions/prompts/_defaults/cortex_context.json` | Identische Default-Kopie (aus Step 4B) |

### Unveränderte Dateien

| Datei | Warum |
|---|---|
| `src/utils/prompt_engine/placeholder_resolver.py` | runtime_vars nativ unterstützt |
| `src/utils/prompt_engine/loader.py` | Lädt Domain-Dateien automatisch über Manifest-Referenzen |
| `src/utils/services/cortex_service.py` | `get_cortex_for_prompt()` existiert bereits (Step 2B) |

---

## 10. Potential Pitfalls

### 10.1 Cache-Invalidierung

**Problem:** Der `PlaceholderResolver` cacht Phase-1-Werte (static). Cortex-Placeholders sind Phase-3 (runtime) und werden **nicht** gecacht. Kein Problem.

**Aber:** Wenn die Persona gewechselt wird (`invalidate_cache()`), muss der nächste Request neue Cortex-Daten laden. Das passiert automatisch, weil `_load_cortex_context()` bei jedem Request den CortexService aufruft — kein Cache im ChatService.

| Szenario | Cache-Auswirkung |
|---|---|
| Persona-Wechsel | Phase-1-Cache invalidiert → `invalidate_cache()`. Phase-3 (Cortex) hat keinen Cache → sicher |
| Cortex-Dateien extern geändert | Nächster Request liest frische Dateien → kein Cache-Problem |
| Prompt-Editor ändert Template | `engine.reload()` invalidiert alles → sicher |
| `cortexEnabled` geändert | Wirkt sofort beim nächsten Request → kein Cache |

### 10.2 Variant-Handling

**Problem:** `cortex_context` hat nur eine `default`-Variante. Was passiert bei `variant='experimental'`?

**Antwort:** `_resolve_prompt_content()` hat Fallback-Logik:

```python
variant_data = variants.get(variant) or variants.get('default')
```

Wenn `experimental` nicht existiert, wird `default` verwendet. Das ist korrekt — der Cortex-Block ist varianten-unabhängig.

**Zukunft:** Falls experimentelle Cortex-Templates gewünscht sind, kann eine `experimental`-Variante in `cortex_context.json` ergänzt werden — keine Code-Änderung nötig.

### 10.3 Reihenfolge der Checks in `build_system_prompt()`

Die Reihenfolge der Prüfungen in der for-Schleife ist korrekt:

1. `position == 'system_prompt_append'` → Skip (separater Kanal)
2. `category in NON_CHAT_CATEGORIES` → Skip (Summary, Spec-Autofill)
3. **`_should_include_block()`** → Skip wenn `requires_any` nicht erfüllt ← NEU
4. `_resolve_prompt_content()` → Content resolven
5. `if content:` → Skip wenn leer

**Wichtig:** `_should_include_block()` muss **vor** `_resolve_prompt_content()` stehen, um unnötige Resolution und Post-Processing zu vermeiden.

### 10.4 `get_system_prompt_append()` und Cortex

Der Cortex-Block hat `position: "system_prompt"` — er wird **nicht** von `get_system_prompt_append()` erfasst (die nur `system_prompt_append` sammelt). Kein Konflikt.

### 10.5 `build_prefill()` und Cortex

Der Cortex-Block hat `target: "system_prompt"` — er wird **nicht** von `build_prefill()` erfasst (die nur `target: "prefill"` sammelt). Kein Konflikt.

### 10.6 Afterthought und Cortex

Die Afterthought-Methoden (`afterthought_decision()`, `afterthought_followup_stream()`) rufen ebenfalls `build_system_prompt()` auf. Sie übergeben `runtime_vars` — wenn diese die Cortex-Daten enthalten (durch `_load_cortex_context()`), wird der Cortex-Block auch im Afterthought-System-Prompt eingeschlossen.

**Das ist gewünscht:** Die Persona sollte auch im Afterthought-Kontext ihr Cortex-Wissen haben.

### 10.7 Summary und Cortex

Summary-Prompts werden über `build_summary_prompt()` gebaut, das `category == 'summary'` filtert. Der Cortex-Block hat `category: "context"` → wird von Summary **nicht** einbezogen. Korrekt — Summary braucht das Cortex-Wissen nicht.

### 10.8 Export/Import

`export_prompt_set()` exportiert alle Domain-Dateien aus `prompts/` als ZIP. `cortex_context.json` wird automatisch mitexportiert. Beim Import wird sie wiederhergestellt. Kein spezieller Code nötig.

### 10.9 Factory-Reset

`factory_reset()` kopiert `_defaults/*` zurück. Da `_defaults/cortex_context.json` existiert, wird das Template wiederhergestellt. Der Manifest-Eintrag wird über `_defaults/_meta/prompt_manifest.json` wiederhergestellt. Alles automatisch.

### 10.10 `requires_any` und der Prompt-Editor

Der Prompt-Editor zeigt alle Manifest-Felder an. `requires_any` ist ein neues Feld, das der Editor möglicherweise nicht kennt. **Risiko:** Der Editor könnte das Feld beim Speichern verwerfen.

**Prüfen:** In `prompt_editor/editor.py` und `prompt_editor/api.py` sicherstellen, dass unbekannte Manifest-Felder beim Speichern erhalten bleiben (pass-through). Die aktuelle `save_prompt()`-Methode in engine.py nutzt `dict.update()` — neue Felder im gespeicherten Manifest bleiben erhalten, **aber** `requires_any` steht initial nur im System-Manifest und wird nicht über den Editor verändert. Kein Risiko.

### 10.11 Thread-Safety

Alle Engine-Mutationen sind durch `self._lock` (RLock) geschützt. `build_system_prompt()` ist read-only und braucht kein Lock. `_should_include_block()` liest nur — ebenfalls kein Lock nötig.

`_load_cortex_context()` im ChatService macht Filesystem-Reads. Diese sind thread-safe (Read-Only). Keine Bedenken.

---

## 11. Zusammenfassung der Code-Änderungen

### engine.py — 3 Änderungen

| # | Änderung | Zeilen | Beschreibung |
|---|---|---|---|
| 1 | `_should_include_block()` | +20 Zeilen | Neue Methode: Prüft `requires_any` gegen runtime_vars |
| 2 | `build_system_prompt()` | +3 Zeilen | `_should_include_block()`-Aufruf in der for-Schleife |
| 3 | `_clean_resolved_text()` | +8 Zeilen | Neue Methode: `\n{3,}` → `\n\n` Post-Processing |
|   | `_resolve_prompt_content()` | +2 Zeilen | Aufruf von `_clean_resolved_text()` |

### validator.py — 2 Änderungen

| # | Änderung | Zeilen | Beschreibung |
|---|---|---|---|
| 1 | `validate_requires_any()` | +15 Zeilen | Neue Methode: Prüft ob requires_any-Keys in Registry existieren |
| 2 | `validate_all()` | +1 Zeile | Aufruf von `validate_requires_any()` |

### Gesamt: ~49 neue Zeilen Code in der Engine-Schicht

---

## 12. Implementierungsreihenfolge

| Schritt | Datei | Aktion |
|---|---|---|
| 1 | `placeholder_registry.json` + Defaults-Kopie | 3 Cortex-Placeholder-Einträge hinzufügen |
| 2 | `prompt_manifest.json` + Defaults-Kopie | `cortex_context`-Eintrag hinzufügen (mit `requires_any`) |
| 3 | `cortex_context.json` + Defaults-Kopie | Domain-Datei erstellen (aus Step 4B) |
| 4 | `engine.py` | `_should_include_block()` + `_clean_resolved_text()` implementieren |
| 5 | `engine.py` | `build_system_prompt()` um requires_any-Check erweitern |
| 6 | `engine.py` | `_resolve_prompt_content()` um Post-Processing erweitern |
| 7 | `validator.py` | `validate_requires_any()` hinzufügen |
| 8 | `defaults.json` | `cortexEnabled: true` hinzufügen |
| 9 | `chat_service.py` | `_load_cortex_context()` + Setting-Check (aus Step 4A) |
| 10 | Tests | requires_any, Post-Processing, cortexEnabled |

**Schritte 1–3** sind reine Config/JSON — kein Code, kein Risiko.
**Schritte 4–7** sind die Engine-Änderungen — isoliert, testbar.
**Schritte 8–9** sind die Runtime-Integration — abhängig von Step 2B (CortexService).
