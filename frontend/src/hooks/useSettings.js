// ── useSettings Hook ──

import { useContext } from 'react';
import { SettingsContext } from '../context/SettingsContext';

export function useSettings() {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}
