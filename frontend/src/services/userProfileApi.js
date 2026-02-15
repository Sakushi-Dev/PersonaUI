// ── User Profile API Service ──

import { apiGet, apiPut, apiUpload } from './apiClient';

export function getUserProfile() {
  return apiGet('/api/user-profile');
}

export function updateUserProfile(data) {
  return apiPut('/api/user-profile', data);
}

export function uploadUserAvatar(formData) {
  return apiUpload('/api/user-profile/avatar', formData);
}
