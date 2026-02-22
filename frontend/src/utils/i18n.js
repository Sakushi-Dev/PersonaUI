// ── Global Translation Helper ──
// Central i18n function for the entire UI (including onboarding).
// Loads all per-section JSON files from ../locales/**/ via Vite glob import.

const modules = import.meta.glob('../locales/**/*.json', { eager: true });

// Build merged strings object: { en: { sectionName: {...} }, de: { sectionName: {...} } }
const strings = { en: {}, de: {} };
for (const [path, mod] of Object.entries(modules)) {
  const section = path.split('/').pop().replace('.json', '');
  const data = mod.default || mod;
  if (data.en) strings.en[section] = data.en;
  if (data.de) strings.de[section] = data.de;
}

/**
 * Get translated strings for a UI section.
 * Falls back to English if the language or section is missing.
 *
 * @param {string} language  – 'en' | 'de'
 * @param {string} section   – e.g. 'interfaceSettings', 'chat', 'onboardingWelcome'
 * @returns {object} translated string map
 */
export function t(language, section) {
  const lang = strings[language] ? language : 'en';
  return strings[lang]?.[section] || strings.en?.[section] || {};
}
