// ── Onboarding Translation Helper ──
// Returns the translation strings for a given language and section.

import strings from './onboardingStrings.json';

/**
 * Get translated strings for a specific onboarding section.
 * Falls back to English if the language or key is missing.
 *
 * @param {string} language  – 'en' | 'de'
 * @param {string} section   – e.g. 'welcome', 'profile', 'common'
 * @returns {object} translated string map
 */
export function t(language, section) {
  const lang = strings[language] ? language : 'en';
  return strings[lang][section] || strings.en[section] || {};
}
