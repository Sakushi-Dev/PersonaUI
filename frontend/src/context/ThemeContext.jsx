// ── Theme Context ──

import { createContext, useState, useEffect, useCallback } from 'react';
import * as storage from '../utils/storage';
import { resolveFontFamily, adjustedFontSize } from '../utils/constants';

export const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [isDark, setIsDark] = useState(() => storage.getItem('darkMode', false));
  const [colors, setColors] = useState(() => ({
    backgroundColorLight: storage.getItem('backgroundColorLight', '#a3baff'),
    gradientColor1Light: storage.getItem('gradientColor1Light', '#66cfff'),
    secondaryColorLight: storage.getItem('secondaryColorLight', '#fd91ee'),
    backgroundColorDark: storage.getItem('backgroundColorDark', '#151a24'),
    gradientColor1Dark: storage.getItem('gradientColor1Dark', '#1f2d47'),
    secondaryColorDark: storage.getItem('secondaryColorDark', '#1a2e2b'),
    nonverbalColor: storage.getItem('nonverbalColor', '#e4ba00'),
  }));
  const [fontKey, setFontKey] = useState(() => storage.getItem('bubbleFontFamily', 'ubuntu'));
  const [fontSize, setFontSize] = useState(() => storage.getItem('bubbleFontSize', 18));
  const [fontFamily, setFontFamily] = useState(() =>
    resolveFontFamily(fontKey)
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
    const suffix = isDark ? 'Dark' : 'Light';
    // --color-white = user's "Hintergrund" setting (dynamic bg container + blob1)
    root.style.setProperty('--color-white', colors[`backgroundColor${suffix}`]);
    root.style.setProperty('--color-gradient1', colors[`gradientColor1${suffix}`]);
    root.style.setProperty('--color-sky', colors[`secondaryColor${suffix}`]);
    root.style.setProperty('--nonverbal-color', colors.nonverbalColor);
    root.style.setProperty('--bubble-font-size', `${adjustedFontSize(fontSize, fontKey)}px`);
    root.style.setProperty('--bubble-font-family', fontFamily);
  }, [isDark, colors, fontSize, fontFamily, fontKey]);

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
    fontKey,
    setFontKey,
    fontFamily,
    setFontFamily,
    dynamicBackground,
    setDynamicBackground,
  };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
