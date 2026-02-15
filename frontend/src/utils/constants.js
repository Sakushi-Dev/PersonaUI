// ── API Base URL & Defaults ──

export const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const DEFAULTS = {
  bubbleFontSize: 18,
  bubbleFontFamily: "'Ubuntu', 'Roboto', 'Segoe UI', system-ui, -apple-system, sans-serif",
  nonverbalColor: '#e4ba00',
  darkMode: false,
  dynamicBackground: true,
  backgroundColor_light: '#f8f9fa',
  colorGradient1_light: '#66cfff',
  color2_light: '#fd91ee',
  backgroundColor_dark: '#1a2332',
  colorGradient1_dark: '#2a3f5f',
  color2_dark: '#3d4f66',
  apiModel: '',
  apiTemperature: 0.7,
  contextLimit: 30,
  experimentalMode: false,
  nachgedankeEnabled: true,
  notificationSound: false,
};

export const LIMITS = {
  personaNameMax: 30,
  personaBackgroundMax: 2000,
  startMessageMax: 500,
  messageLoadBatch: 30,
};

export const AFTERTHOUGHT_INTERVALS = [10000, 60000, 300000, 900000, 3600000]; // 10s, 1min, 5min, 15min, 1h
