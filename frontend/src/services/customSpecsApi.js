// ── Custom Specs API Service ──

import { apiGet, apiPost, apiDelete } from './apiClient';

export function getCustomSpecs() {
  return apiGet('/api/custom-specs');
}

export function createCustomSpec(category, data) {
  return apiPost(`/api/custom-specs/${category}`, data);
}

export function deleteCustomSpec(category, id) {
  return apiDelete(`/api/custom-specs/${category}/${id}`);
}

export function autofillCustomSpec(category, data) {
  return apiPost('/api/custom-specs/autofill', data);
}
