// ── Server API Service ──

import { apiGet, apiPost } from './apiClient';

export function getServerSettings() {
  return apiGet('/api/get_server_settings');
}

export function saveAndRestartServer(serverMode, port) {
  return apiPost('/api/save_and_restart_server', { server_mode: serverMode, port: parseInt(port, 10) || 5000 });
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

export function getQRCode() {
  return apiGet('/api/qr_code');
}

export function getNetworkInfo() {
  return apiGet('/api/network_info');
}
