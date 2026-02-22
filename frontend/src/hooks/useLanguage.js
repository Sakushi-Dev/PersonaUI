// ── useLanguage Hook ──
// Provides the current language and a translation helper from SettingsContext.
// Usage:
//   const { language, t } = useLanguage();
//   const s = t('interfaceSettings');
//   // → s.title, s.designMode, etc.

import { useSettings } from './useSettings';
import { t as translate } from '../utils/i18n';

/**
 * Hook for accessing the current language + section-based translator.
 * @returns {{ language: string, t: (section: string) => object }}
 */
export function useLanguage() {
  const { get } = useSettings();
  const language = get('language', 'en');

  const t = (section) => translate(language, section);

  return { language, t };
}
