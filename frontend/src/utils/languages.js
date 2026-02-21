// ── Language Configuration ──
// Extensible language registry for the app.
// To add a new language: add an entry to LANGUAGES and provide translations.

export const LANGUAGES = [
  { code: 'en', label: 'EN', name: 'English' },
  { code: 'de', label: 'DE', name: 'Deutsch' },
  // Add more languages here, e.g.:
  // { code: 'fr', label: 'FR', name: 'Français' },
  // { code: 'es', label: 'ES', name: 'Español' },
];

export const DEFAULT_LANGUAGE = 'en';

/**
 * Get a language entry by code.
 * @param {string} code - Language code (e.g. 'en', 'de')
 * @returns {object|undefined}
 */
export function getLanguage(code) {
  return LANGUAGES.find((l) => l.code === code);
}
