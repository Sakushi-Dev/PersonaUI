// ── Session API Service ──

import { apiGet, apiPost, apiDelete } from './apiClient';

export function getSessions(personaId) {
  return apiGet(`/api/sessions?persona_id=${personaId}`);
}

export function getSession(sessionId, personaId) {
  return apiGet(`/api/sessions/${sessionId}?persona_id=${personaId}`);
}

export function createSession(personaId) {
  return apiPost('/api/sessions/new', { persona_id: personaId });
}

export function deleteSession(sessionId, personaId) {
  return apiDelete(`/api/sessions/${sessionId}?persona_id=${personaId}`);
}

export function isSessionEmpty(sessionId, personaId) {
  return apiGet(`/api/sessions/${sessionId}/is_empty?persona_id=${personaId}`);
}

export function loadMoreMessages(sessionId, offset, personaId, limit = 30) {
  return apiPost(`/api/sessions/${sessionId}/load_more`, {
    offset,
    limit,
    persona_id: personaId,
  });
}

export function getPersonaSummary() {
  return apiGet('/api/sessions/persona_summary');
}
