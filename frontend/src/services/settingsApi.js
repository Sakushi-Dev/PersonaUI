// ── Settings API Service ──

import { apiGet, apiPut, apiPost } from './apiClient';

export function getSettings() {
  return apiGet('/api/user-settings');
}

export function updateSettings(settings) {
  return apiPut('/api/user-settings', settings);
}

export function resetSettings() {
  return apiPost('/api/user-settings/reset');
}
