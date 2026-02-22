// ── Emoji Usage API Service ──

import { apiGet, apiPut } from './apiClient';

export function getEmojiUsage() {
  return apiGet('/api/emoji-usage');
}

export function incrementEmojiUsage(emoji) {
  return apiPut('/api/emoji-usage', { emoji });
}
