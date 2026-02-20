// ── useMessages Hook ──
// Streaming messages are added to chatHistory as placeholders (_streaming: true)
// and updated in-place via updateLastMessage. This avoids bubble recreation
// when the stream completes — the same React element transitions from
// streaming to final state without unmounting/remounting.

import { useState, useCallback, useRef } from 'react';
import { useSession } from '../../../hooks/useSession';
import { useSettings } from '../../../hooks/useSettings';
import { sendChatMessage, deleteLastMessage as apiDeleteLastMessage, editLastMessage as apiEditLastMessage, regenerateMessage } from '../../../services/chatApi';
import { loadMoreMessages } from '../../../services/sessionApi';
import { playNotificationSound } from '../../../utils/audioUtils';
import { formatMessage } from '../../../utils/formatMessage';

export function useMessages() {
  const { sessionId, personaId, character, addMessage, updateLastMessage, removeLastMessage, prependMessages, chatHistory, totalMessageCount } = useSession();
  const { get } = useSettings();

  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingStats, setStreamingStats] = useState(null);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  const hasMore = chatHistory.length < totalMessageCount;

  const sendMessage = useCallback(async (text, extra = {}) => {
    console.log('[useMessages] sendMessage called, text:', text, 'sessionId:', sessionId, 'personaId:', personaId, 'isLoading:', isLoading, 'isStreaming:', isStreaming);
    if (!text.trim() || isLoading || isStreaming) return;

    setIsLoading(true);
    setIsStreaming(true);
    setError(null);

    // Add user message immediately
    const userMessage = {
      message: text,
      is_user: true,
      character_name: null,
      timestamp: new Date().toISOString(),
    };
    addMessage(userMessage);

    // Add streaming placeholder for bot response (same element will be updated in-place)
    addMessage({
      message: '',
      is_user: false,
      character_name: character?.char_name,
      _streaming: true,
      timestamp: new Date().toISOString(),
    });

    let rawText = '';

    abortRef.current = sendChatMessage(text, {
      sessionId,
      personaId,
      apiModel: get('apiModel'),
      apiTemperature: get('apiTemperature'),
      contextLimit: get('contextLimit'),
      experimentalMode: get('experimentalMode'),
      pendingAfterthought: extra.pendingAfterthought || null,
      onChunk: (chunk) => {
        rawText += chunk;
        updateLastMessage({ message: formatMessage(rawText) });
      },
      onDone: (data) => {
        setIsStreaming(false);
        setIsLoading(false);
        setStreamingStats(data.stats || null);

        // Finalize the streaming message — same element, no recreation
        updateLastMessage({
          message: data.response,
          _streaming: false,
          character_name: data.character_name,
          timestamp: new Date().toISOString(),
          stats: data.stats,
        });

        // Cortex-Update Benachrichtigung (aus SSE done-Event)
        if (data.cortex_update?.triggered) {
          window.dispatchEvent(new CustomEvent('cortex-update', {
            detail: { tier: data.cortex_update.tier }
          }));
        }

        // Play notification sound if enabled
        if (get('notificationSound', false)) {
          playNotificationSound();
        }
      },
      onError: (err) => {
        setIsStreaming(false);
        setIsLoading(false);
        removeLastMessage(); // Remove the streaming placeholder
        setError(err);
      },
    });
  }, [sessionId, personaId, isLoading, isStreaming, character, addMessage, updateLastMessage, removeLastMessage, get]);

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
    setIsLoading(false);
    removeLastMessage(); // Remove the streaming placeholder
  }, [removeLastMessage]);

  const loadMore = useCallback(async () => {
    if (!hasMore || isLoading) return;

    try {
      const data = await loadMoreMessages(sessionId, chatHistory.length, personaId);
      if (data.success && data.messages?.length > 0) {
        prependMessages(data.messages);
      }
    } catch (err) {
      console.warn('Failed to load more messages:', err);
    }
  }, [sessionId, personaId, chatHistory.length, hasMore, isLoading, prependMessages]);

  // ── Delete last message ──
  const deleteLastMsg = useCallback(async () => {
    if (isStreaming || isLoading || chatHistory.length === 0) return;

    try {
      const result = await apiDeleteLastMessage(sessionId, personaId);
      if (result.success) {
        removeLastMessage();
      }
    } catch (err) {
      console.error('Failed to delete last message:', err);
    }
  }, [sessionId, personaId, isStreaming, isLoading, chatHistory.length, removeLastMessage]);

  // ── Edit last message ──
  const editLastMsg = useCallback(async (newText) => {
    if (isStreaming || isLoading || !newText?.trim()) return;

    try {
      const result = await apiEditLastMessage(sessionId, personaId, newText.trim());
      if (result.success) {
        updateLastMessage({ message: newText.trim() });
      }
    } catch (err) {
      console.error('Failed to edit last message:', err);
    }
  }, [sessionId, personaId, isStreaming, isLoading, updateLastMessage]);

  // ── Regenerate last bot message ──
  const regenerateLastMsg = useCallback(async () => {
    if (isStreaming || isLoading || chatHistory.length === 0) return;

    const lastMsg = chatHistory[chatHistory.length - 1];
    if (lastMsg.is_user || lastMsg._streaming) return;

    // Remove the old bot message from frontend
    removeLastMessage();

    // Add streaming placeholder
    setIsLoading(true);
    setIsStreaming(true);
    setError(null);

    addMessage({
      message: '',
      is_user: false,
      character_name: character?.char_name,
      _streaming: true,
      timestamp: new Date().toISOString(),
    });

    let rawText = '';

    abortRef.current = regenerateMessage({
      sessionId,
      personaId,
      apiModel: get('apiModel'),
      apiTemperature: get('apiTemperature'),
      contextLimit: get('contextLimit'),
      experimentalMode: get('experimentalMode'),
      onChunk: (chunk) => {
        rawText += chunk;
        updateLastMessage({ message: formatMessage(rawText) });
      },
      onDone: (data) => {
        setIsStreaming(false);
        setIsLoading(false);
        setStreamingStats(data.stats || null);

        updateLastMessage({
          message: data.response,
          _streaming: false,
          character_name: data.character_name,
          timestamp: new Date().toISOString(),
          stats: data.stats,
        });

        if (get('notificationSound', false)) {
          playNotificationSound();
        }
      },
      onError: (err) => {
        setIsStreaming(false);
        setIsLoading(false);
        removeLastMessage();
        setError(err);
      },
    });
  }, [sessionId, personaId, isStreaming, isLoading, chatHistory, character, addMessage, updateLastMessage, removeLastMessage, get]);

  // ── Resend last user message (delete from DB, then send again) ──
  const resendLastMsg = useCallback(async () => {
    if (isStreaming || isLoading || chatHistory.length === 0) return;

    const lastMsg = chatHistory[chatHistory.length - 1];
    if (!lastMsg.is_user || lastMsg._streaming) return;

    const text = lastMsg.message;

    // Delete from DB
    try {
      const result = await apiDeleteLastMessage(sessionId, personaId);
      if (!result.success) return;
    } catch (err) {
      console.error('Failed to delete message before resend:', err);
      return;
    }

    // Remove from frontend state
    removeLastMessage();

    // Send as new input (will add user msg + bot streaming placeholder)
    sendMessage(text);
  }, [sessionId, personaId, isStreaming, isLoading, chatHistory, removeLastMessage, sendMessage]);

  return {
    isLoading,
    isStreaming,
    streamingStats,
    error,
    hasMore,
    sendMessage,
    cancelStream,
    loadMore,
    deleteLastMsg,
    editLastMsg,
    regenerateLastMsg,
    resendLastMsg,
  };
}
