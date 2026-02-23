// ── Server API Service ──

import { apiGet, apiPost } from './apiClient';

export function getServerSettings() {
  return apiGet('/api/get_server_settings');
}

export function saveAndRestartServer(serverMode) {
  return apiPost('/api/save_and_restart_server', { server_mode: serverMode });
}

export function testApiKey(apiKey, apiModel) {
  return apiPost('/api/test_api_key', { api_key: apiKey, api_model: apiModel });
}

export function saveApiKey(apiKey) {
  return apiPost('/api/save_api_key', { api_key: apiKey });
}

export function checkApiStatus() {
  return apiGet('/api/check_api_status');
}

export function getLocalIps() {
  return apiGet('/api/get_local_ips');
}

export function generateQRCode(url) {
  return apiPost('/api/generate_qr_code', { url });
}
