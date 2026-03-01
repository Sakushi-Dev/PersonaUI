// ── Mood API Service ──

import { apiGet, apiPost } from './apiClient';

/**
 * Get current mood state with decay applied.
 *
 * @returns {Promise<{enabled: boolean, mood?: object, persona_id?: string}>}
 */
export function getCurrentMood() {
  return apiGet('/api/mood');
}

/**
 * Get mood history for the current persona.
 *
 * @param {number} [limit=50] - Maximum number of history entries
 * @returns {Promise<{enabled: boolean, history?: array, persona_id?: string, limit?: number}>}
 */
export function getMoodHistory(limit = 50) {
  return apiGet(`/api/mood/history?limit=${limit}`);
}

/**
 * Update mood system settings (sensitivity and decay rate).
 *
 * @param {object} settings - Settings to update
 * @param {number} [settings.sensitivity] - Sensitivity value (0.0-1.0)
 * @param {number} [settings.decay_rate] - Decay rate value (>= 0.0)
 * @returns {Promise<{enabled: boolean, settings?: object, persona_id?: string}>}
 */
export function updateMoodSettings(settings) {
  return apiPost('/api/mood/settings', settings);
}

/**
 * Reset mood state to baseline values.
 *
 * @returns {Promise<{enabled: boolean, mood?: object, persona_id?: string, message?: string}>}
 */
export function resetMood() {
  return apiPost('/api/mood/reset');
}