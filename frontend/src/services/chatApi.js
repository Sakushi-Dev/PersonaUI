// ── Chat API Service ──

import { apiPost, apiStream } from './apiClient';

export function sendChatMessage(message, options = {}) {
  const body = {
    message,
    session_id: options.sessionId,
    persona_id: options.personaId || 'default',
    ...(options.apiModel && { api_model: options.apiModel }),
    ...(options.apiTemperature !== undefined && { api_temperature: options.apiTemperature }),
    ...(options.contextLimit !== undefined && { context_limit: options.contextLimit }),
    ...(options.experimentalMode !== undefined && { experimental_mode: options.experimentalMode }),
  };

  return apiStream('/chat_stream', body, {
    onChunk: options.onChunk,
    onDone: options.onDone,
    onError: options.onError,
  });
}

export function sendAfterthought(options = {}) {
  const body = {
    session_id: options.sessionId,
    elapsed_time: options.elapsedTime,
    phase: options.phase, // 'decision' or 'followup'
    persona_id: options.personaId || 'default',
    ...(options.innerDialogue && { inner_dialogue: options.innerDialogue }),
    ...(options.apiModel && { api_model: options.apiModel }),
    ...(options.apiTemperature !== undefined && { api_temperature: options.apiTemperature }),
    ...(options.contextLimit !== undefined && { context_limit: options.contextLimit }),
    ...(options.experimentalMode !== undefined && { experimental_mode: options.experimentalMode }),
  };

  if (options.phase === 'decision') {
    return apiPost('/afterthought', body);
  }

  // Followup phase uses SSE streaming
  return apiStream('/afterthought', body, {
    onChunk: options.onChunk,
    onDone: options.onDone,
    onError: options.onError,
  });
}

export function clearChat(sessionId) {
  return apiPost('/clear_chat', { session_id: sessionId });
}
