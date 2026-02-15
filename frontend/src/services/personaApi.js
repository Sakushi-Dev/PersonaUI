// ── Persona API Service ──

import { apiGet, apiPost, apiPut, apiDelete } from './apiClient';

export function getPersonas() {
  return apiGet('/api/personas');
}

export function createPersona(data) {
  return apiPost('/api/personas', data);
}

export function updatePersona(id, data) {
  return apiPut(`/api/personas/${id}`, data);
}

export function deletePersona(id) {
  return apiDelete(`/api/personas/${id}`);
}

export function activatePersona(id) {
  return apiPost(`/api/personas/${id}/activate`);
}

export function getCharConfig() {
  return apiGet('/get_char_config');
}

export function getAvailableOptions() {
  return apiGet('/get_available_options');
}

export function backgroundAutofill(data) {
  return apiPost('/api/personas/background-autofill', data);
}

export function restoreDefaultPersona() {
  return apiPost('/api/personas/restore_default');
}
