// ── Avatar API Service ──

import { apiGet, apiPost, apiDelete, apiUpload } from './apiClient';

export function getAvailableAvatars() {
  return apiGet('/api/get_available_avatars');
}

export function saveAvatar(personaId, avatarData, avatarType) {
  return apiPost('/api/save_avatar', {
    persona_id: personaId,
    avatar: avatarData,
    avatar_type: avatarType,
  });
}

export function uploadAvatar(formData) {
  return apiUpload('/api/upload_avatar', formData);
}

export function deleteAvatar(filename) {
  return apiDelete(`/api/delete_avatar/${filename}`);
}

export function saveUserAvatar(avatarData, avatarType) {
  return apiPost('/api/save_user_avatar', {
    avatar: avatarData,
    avatar_type: avatarType,
  });
}
