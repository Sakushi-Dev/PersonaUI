// ── Memory API Service ──

import { apiGet, apiPost, apiPut, apiDelete, apiPatch } from './apiClient';

export function getMemories() {
  return apiGet('/api/memory/list');
}

export function createMemory(data) {
  return apiPost('/api/memory/create', data);
}

export function previewMemory(data) {
  return apiPost('/api/memory/preview', data);
}

export function updateMemory(id, data) {
  return apiPut(`/api/memory/${id}`, data);
}

export function deleteMemory(id) {
  return apiDelete(`/api/memory/${id}`);
}

export function toggleMemory(id) {
  return apiPatch(`/api/memory/${id}/toggle`);
}

export function checkMemoryAvailability(sessionId) {
  return apiGet(`/api/memory/check-availability/${sessionId}`);
}

export function getMemoryStats() {
  return apiGet('/api/memory/stats');
}
