// ── Export API Service ──

import { API_BASE_URL } from '../utils/constants';

/**
 * Exports chat session as file download
 * @param {number} sessionId - Session ID
 * @param {string} format - Format: 'txt' or 'json'
 * @returns {Promise<Blob>} - File blob for download
 */
export async function exportChatSession(sessionId, format = 'txt') {
  const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/export?format=${format}`);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || 'Export failed');
  }
  
  return response.blob();
}

/**
 * Triggers browser download for chat export
 * @param {number} sessionId - Session ID
 * @param {string} format - Format: 'txt' or 'json'
 * @returns {Promise<void>}
 */
export async function downloadChatExport(sessionId, format = 'txt') {
  const blob = await exportChatSession(sessionId, format);
  
  // Generate filename
  const date = new Date().toISOString().split('T')[0];
  const extension = format === 'json' ? 'json' : 'txt';
  const filename = `chat_export_${sessionId}_${date}.${extension}`;
  
  // Create download link
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  
  // Trigger download
  document.body.appendChild(link);
  link.click();
  
  // Cleanup
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
