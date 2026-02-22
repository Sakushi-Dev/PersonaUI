// ── Avatar API Service ──

import { apiPost, apiDelete, apiUpload } from './apiClient';

/**
 * Lädt die Avatar-Liste direkt aus frontend/public/avatar/index.json.
 * Das Backend hält diese Datei bei Upload/Delete aktuell.
 */
export async function getAvailableAvatars() {
  const res = await fetch('/avatar/index.json', { cache: 'no-store' });
  if (!res.ok) throw new Error('Avatar-Index konnte nicht geladen werden');
  return res.json();
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
