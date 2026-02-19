// ── API Base URL & Defaults ──

export const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Map shorthand font keys (stored in settings) → full CSS font-family strings
// Must match legacy SettingsManager.applyBubbleFontFamily exactly
export const FONT_FAMILY_MAP = {
  ubuntu: "'Ubuntu', 'Roboto', 'Segoe UI', system-ui, -apple-system, sans-serif",
  comic: "'Comic Sans MS', 'Comic Sans', cursive",
  times: "'Times New Roman', Times, serif",
  courier: "'Courier New', Courier, monospace",
  pixel: "'Press Start 2P', 'VT323', monospace",
  console: "'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace",
};

/** Resolve a shorthand font key to a CSS font-family string. */
export function resolveFontFamily(key) {
  return FONT_FAMILY_MAP[key] || FONT_FAMILY_MAP.ubuntu;
}

// Per-font size offset in px (some fonts render much larger/smaller)
export const FONT_SIZE_OFFSET = {
  pixel: -7,
};

/** Get the effective font size adjusted for the given font key. */
export function adjustedFontSize(basePx, fontKey) {
  return basePx + (FONT_SIZE_OFFSET[fontKey] || 0);
}

// ── HSL → Hex conversion ──
function hslToHex(h, s, l) {
  h = ((h % 360) + 360) % 360;
  s /= 100;
  l /= 100;
  const a = s * Math.min(l, 1 - l);
  const f = (n) => {
    const k = (n + h / 30) % 12;
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color).toString(16).padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

/**
 * Generate theme colors from a single hue value (0–360).
 * Returns { bg, g1, c2 } as hex strings.
 */
export function hueToColors(hue, isDark) {
  if (isDark) {
    return {
      bg: hslToHex(hue, 30, 15),
      g1: hslToHex(hue, 30, 27),
      c2: hslToHex(hue, 22, 33),
    };
  }
  return {
    bg: hslToHex(hue, 100, 82),
    g1: hslToHex(hue - 30, 100, 70),
    c2: hslToHex(hue + 90, 97, 78),
  };
}

/** Default hue for the blue color scheme */
export const DEFAULT_HUE = 220;

/** Preset choices for nonverbal text color */
export const NONVERBAL_PRESETS = [
  { value: '#e4ba00', label: 'Gold' },
  { value: '#00d4aa', label: 'Cyan' },
  { value: '#ff69b4', label: 'Pink' },
  { value: '#ff6b6b', label: 'Rot' },
  { value: '#4ade80', label: 'Grün' },
  { value: '#a78bfa', label: 'Lila' },
];

export const DEFAULTS = {
  bubbleFontSize: 18,
  bubbleFontFamily: "'Ubuntu', 'Roboto', 'Segoe UI', system-ui, -apple-system, sans-serif",
  nonverbalColor: '#e4ba00',
  darkMode: false,
  dynamicBackground: true,
  colorHue: 220,
  backgroundColor_light: '#a3baff',
  colorGradient1_light: '#66cfff',
  color2_light: '#fd91ee',
  backgroundColor_dark: '#1a2332',
  colorGradient1_dark: '#2a3f5f',
  color2_dark: '#3d4f66',
  apiModel: '',
  apiTemperature: 0.7,
  contextLimit: 30,
  experimentalMode: false,
  nachgedankeMode: 'off',
  notificationSound: true,
};

export const LIMITS = {
  personaNameMax: 30,
  personaBackgroundMax: 2000,
  startMessageMax: 500,
  messageLoadBatch: 30,
};

// ── Afterthought / Nachgedanke Phase Config ──
// Each phase: [minMs, maxMs] — a random delay is picked each time
export const AFTERTHOUGHT_PHASES = [
  [20_000, 45_000],   // Phase 1: 20s – 45s
  [45_000, 60_000],  // Phase 2: 45s – 60s
  [60_000, 120_000],  // Phase 3+: 60s – 120s (repeats)
];

// How many user messages between afterthought triggers
export const AFTERTHOUGHT_FREQUENCY = {
  selten: 3,  // every 3rd message
  mittel: 2,  // every 2nd message
  hoch:   1,  // every message
};
