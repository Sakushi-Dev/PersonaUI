// ── Settings Context ──

import { createContext, useState, useCallback, useRef, useEffect } from 'react';
import { getSettings, updateSettings, resetSettings as resetSettingsApi } from '../services/settingsApi';
import { DEFAULTS } from '../utils/constants';

export const SettingsContext = createContext(null);

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState({});
  const [defaults, setDefaults] = useState(DEFAULTS);
  const [loaded, setLoaded] = useState(false);
  const pendingUpdates = useRef({});
  const flushTimer = useRef(null);

  // Load settings from server on mount
  useEffect(() => {
    console.log('[SettingsContext] Loading settings...');
    getSettings()
      .then((data) => {
        console.log('[SettingsContext] Settings loaded:', data?.success);
        if (data.success) {
          setSettings(data.settings || {});
          setDefaults((prev) => ({ ...prev, ...(data.defaults || {}) }));
        }
      })
      .catch((err) => console.warn('[SettingsContext] Failed to load settings:', err))
      .finally(() => {
        console.log('[SettingsContext] setLoaded(true)');
        setLoaded(true);
      });
  }, []);

  // Debounced flush to server
  const flush = useCallback(() => {
    const updates = { ...pendingUpdates.current };
    if (Object.keys(updates).length === 0) return;
    pendingUpdates.current = {};
    updateSettings(updates).catch((err) => console.warn('Settings save failed:', err));
  }, []);

  const scheduleFlush = useCallback(() => {
    if (flushTimer.current) clearTimeout(flushTimer.current);
    flushTimer.current = setTimeout(flush, 300);
  }, [flush]);

  const get = useCallback(
    (key, defaultValue) => {
      if (key in settings) return settings[key];
      if (key in defaults) return defaults[key];
      return defaultValue;
    },
    [settings, defaults]
  );

  const set = useCallback(
    (key, value) => {
      setSettings((prev) => ({ ...prev, [key]: value }));
      pendingUpdates.current[key] = value;
      scheduleFlush();
    },
    [scheduleFlush]
  );

  const setMany = useCallback(
    (updates) => {
      setSettings((prev) => ({ ...prev, ...updates }));
      Object.assign(pendingUpdates.current, updates);
      scheduleFlush();
    },
    [scheduleFlush]
  );

  const reset = useCallback(async () => {
    try {
      const data = await resetSettingsApi();
      if (data.success) {
        setSettings(data.settings || {});
      }
    } catch (err) {
      console.warn('Settings reset failed:', err);
    }
  }, []);

  // Re-fetch settings from the server (e.g. after onboarding)
  const reload = useCallback(async () => {
    try {
      const data = await getSettings();
      if (data.success) {
        setSettings(data.settings || {});
        setDefaults((prev) => ({ ...prev, ...(data.defaults || {}) }));
      }
    } catch (err) {
      console.warn('Failed to reload settings:', err);
    }
  }, []);

  const value = { settings, defaults, loaded, get, set, setMany, reset, reload };

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}
