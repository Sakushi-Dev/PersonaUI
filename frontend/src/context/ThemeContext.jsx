// ── Theme Context ──

import { createContext, useState, useEffect, useCallback } from 'react';
import * as storage from '../utils/storage';

export const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [isDark, setIsDark] = useState(() => storage.getItem('darkMode', false));
  const [colors, setColors] = useState(() => ({
    backgroundColor_light: storage.getItem('backgroundColor_light', '#f8f9fa'),
    colorGradient1_light: storage.getItem('colorGradient1_light', '#66cfff'),
    color2_light: storage.getItem('color2_light', '#fd91ee'),
    backgroundColor_dark: storage.getItem('backgroundColor_dark', '#1a2332'),
    colorGradient1_dark: storage.getItem('colorGradient1_dark', '#2a3f5f'),
    color2_dark: storage.getItem('color2_dark', '#3d4f66'),
    nonverbalColor: storage.getItem('nonverbalColor', '#e4ba00'),
  }));
  const [fontSize, setFontSize] = useState(() => storage.getItem('bubbleFontSize', 18));
  const [fontFamily, setFontFamily] = useState(() =>
    storage.getItem('bubbleFontFamily', "'Ubuntu', 'Roboto', 'Segoe UI', system-ui, -apple-system, sans-serif")
  );
  const [dynamicBackground, setDynamicBackground] = useState(() => storage.getItem('dynamicBackground', true));

  // Apply theme to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    document.body.classList.toggle('dark-mode', isDark);
    storage.setItem('darkMode', isDark);
  }, [isDark]);

  // Apply CSS variables
  useEffect(() => {
    const root = document.documentElement;
    const suffix = isDark ? '_dark' : '_light';
    root.style.setProperty('--background-color', colors[`backgroundColor${suffix}`]);
    root.style.setProperty('--color-gradient1', colors[`colorGradient1${suffix}`]);
    root.style.setProperty('--color-sky', colors[`color2${suffix}`]);
    root.style.setProperty('--nonverbal-color', colors.nonverbalColor);
    root.style.setProperty('--bubble-font-size', `${fontSize}px`);
    root.style.setProperty('--bubble-font-family', fontFamily);
  }, [isDark, colors, fontSize, fontFamily]);

  const toggleDark = useCallback(() => setIsDark((prev) => !prev), []);

  const updateColors = useCallback((newColors) => {
    setColors((prev) => {
      const updated = { ...prev, ...newColors };
      Object.entries(newColors).forEach(([key, val]) => storage.setItem(key, val));
      return updated;
    });
  }, []);

  const value = {
    isDark,
    setIsDark,
    toggleDark,
    colors,
    updateColors,
    fontSize,
    setFontSize,
    fontFamily,
    setFontFamily,
    dynamicBackground,
    setDynamicBackground,
  };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
