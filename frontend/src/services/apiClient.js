// ── Base API Client ──

import { API_BASE_URL } from '../utils/constants';

async function handleResponse(response) {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const error = new Error(errorData.error || `HTTP ${response.status}`);
    error.status = response.status;
    error.data = errorData;
    throw error;
  }
  return response.json();
}

export async function apiGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  return handleResponse(response);
}

export async function apiPost(path, body = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return handleResponse(response);
}

export async function apiPut(path, body = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return handleResponse(response);
}

export async function apiDelete(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'DELETE',
  });
  return handleResponse(response);
}

export async function apiPatch(path, body = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return handleResponse(response);
}

/**
 * Stream SSE response, calling onChunk for each data event
 * Returns an abort controller so the stream can be cancelled
 */
export function apiStream(path, body, { onChunk, onDone, onError }) {
  const abortController = new AbortController();

  fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: abortController.signal,
  })
    .then(async (response) => {
      const contentType = response.headers.get('content-type') || '';

      // If JSON response (error), handle it
      if (contentType.includes('application/json')) {
        const data = await response.json();
        if (data.error_type === 'api_key_missing') {
          onError?.({ type: 'api_key_missing', message: data.error });
        } else if (data.error_type === 'credit_balance_exhausted') {
          onError?.({ type: 'credit_exhausted', message: data.error });
        } else if (!data.success) {
          onError?.({ type: 'error', message: data.error || 'Unknown error' });
        }
        return;
      }

      // SSE stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop(); // Keep incomplete event in buffer

        for (const event of events) {
          if (!event.trim()) continue;

          for (const line of event.split('\n')) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.type === 'chunk') {
                  onChunk?.(data.text);
                } else if (data.type === 'done') {
                  onDone?.(data);
                } else if (data.type === 'error') {
                  onError?.({ type: data.error_type || 'error', message: data.error });
                }
              } catch (e) {
                // Skip malformed JSON
              }
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError?.({ type: 'network', message: err.message });
      }
    });

  return abortController;
}

/**
 * Upload FormData (for avatar uploads etc.)
 */
export async function apiUpload(path, formData) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    body: formData, // No Content-Type header — browser sets boundary
  });
  return handleResponse(response);
}
