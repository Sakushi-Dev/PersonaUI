// ── Access Control API Service ──

import { apiGet, apiPost } from './apiClient';

export function requestAccess() {
  return apiPost('/api/access/request');
}

export function pollAccessStatus() {
  return apiGet('/api/access/poll');
}

export function getAccessLists() {
  return apiGet('/api/access/lists');
}

export function getPendingRequests() {
  return apiGet('/api/access/pending');
}

export function approveRequest(ip) {
  return apiPost('/api/access/approve', { ip });
}

export function denyRequest(ip) {
  return apiPost('/api/access/deny', { ip });
}

export function removeFromList(ip, listType) {
  return apiPost('/api/access/remove', { ip, list: listType });
}

export function toggleAccessControl(enabled) {
  return apiPost('/api/access/toggle', { enabled });
}

export function getAccessStatus() {
  return apiGet('/api/access/status');
}
