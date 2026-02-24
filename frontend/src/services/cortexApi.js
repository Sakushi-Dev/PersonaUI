// ── Cortex API Service ──
//
// Frontend-Anbindung an die Cortex-REST-Endpunkte (src/routes/cortex.py).
// Ersetzt memoryApi.js — das alte Memory-System wird durch Cortex abgelöst.

import { apiGet, apiPost, apiPut } from './apiClient';


// ═════════════════════════════════════════════════════════════════════════════
//  CORTEX FILE OPERATIONS
// ═════════════════════════════════════════════════════════════════════════════


/**
 * Lädt alle 3 Cortex-Dateien (memory.md, soul.md, relationship.md) der Persona.
 *
 * @param {string} personaId - Die Persona-ID (aus SessionContext)
 * @returns {Promise<{success: boolean, files: {memory: string, soul: string, relationship: string}, persona_id: string}>}
 */
export function getCortexFiles(personaId) {
  return apiGet(`/api/cortex/files?persona_id=${personaId}`);
}


/**
 * Lädt den Inhalt einer einzelnen Cortex-Datei.
 *
 * @param {string} personaId - Die Persona-ID (aus SessionContext)
 * @param {string} filename  - Dateiname: 'memory.md', 'soul.md' oder 'relationship.md'
 * @returns {Promise<{success: boolean, filename: string, content: string, persona_id: string}>}
 */
export function getCortexFile(personaId, filename) {
  return apiGet(`/api/cortex/file/${filename}?persona_id=${personaId}`);
}


/**
 * Speichert den Inhalt einer einzelnen Cortex-Datei (User-Editing via CortexOverlay).
 *
 * @param {string} personaId - Die Persona-ID (aus SessionContext)
 * @param {string} filename  - Dateiname: 'memory.md', 'soul.md' oder 'relationship.md'
 * @param {string} content   - Der neue Datei-Inhalt (Markdown)
 * @returns {Promise<{success: boolean, filename: string, persona_id: string}>}
 */
export function saveCortexFile(personaId, filename, content) {
  return apiPut(`/api/cortex/file/${filename}`, {
    content,
    persona_id: personaId,
  });
}


/**
 * Setzt eine einzelne Cortex-Datei auf das Template zurück.
 *
 * @param {string} personaId - Die Persona-ID (aus SessionContext)
 * @param {string} filename  - Dateiname: 'memory.md', 'soul.md' oder 'relationship.md'
 * @returns {Promise<{success: boolean, filename: string, content: string, persona_id: string}>}
 */
export function resetCortexFile(personaId, filename) {
  return apiPost(`/api/cortex/reset/${filename}`, {
    persona_id: personaId,
  });
}


/**
 * Setzt alle 3 Cortex-Dateien der Persona auf die Templates zurück.
 *
 * @param {string} personaId - Die Persona-ID (aus SessionContext)
 * @returns {Promise<{success: boolean, files: {memory: string, soul: string, relationship: string}, persona_id: string}>}
 */
export function resetAllCortexFiles(personaId) {
  return apiPost('/api/cortex/reset', {
    persona_id: personaId,
  });
}


// ═════════════════════════════════════════════════════════════════════════════
//  CORTEX SETTINGS
// ═════════════════════════════════════════════════════════════════════════════


/**
 * Lädt die aktuellen Cortex-Einstellungen (Tiers, enabled).
 *
 * @returns {Promise<{success: boolean, settings: object, defaults: object}>}
 */
export function getCortexSettings() {
  return apiGet('/api/cortex/settings');
}


/**
 * Lädt den aktuellen Cortex-Fortschritt (Progress-Bar Daten).
 *
 * @param {number} sessionId - Aktuelle Session-ID
 * @param {string} [personaId] - Optionale Persona-ID
 * @returns {Promise<{success: boolean, progress: object|null, frequency: string, enabled: boolean}>}
 */
export function getCortexProgress(sessionId, personaId) {
  let url = `/api/cortex/progress?session_id=${sessionId}`;
  if (personaId) url += `&persona_id=${personaId}`;
  return apiGet(url);
}


/**
 * Aktualisiert die Cortex-Einstellungen (Partial Update).
 *
 * @param {object} settings - Teilweise oder vollständige Settings
 * @param {boolean} [settings.enabled] - Cortex global ein/aus
 * @param {object}  [settings.tiers]   - Tier-Konfiguration (partial merge)
 * @returns {Promise<{success: boolean, settings: object, defaults: object}>}
 */
export function saveCortexSettings(settings) {
  return apiPut('/api/cortex/settings', settings);
}
