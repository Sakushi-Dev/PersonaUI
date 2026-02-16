// ── useMessages Hook ──
// Streaming messages are added to chatHistory as placeholders (_streaming: true)
// and updated in-place via updateLastMessage. This avoids bubble recreation
// when the stream completes — the same React element transitions from
// streaming to final state without unmounting/remounting.

import { useState, useCallback, useRef } from 'react';
import { useSession } from '../../../hooks/useSession';
import { useSettings } from '../../../hooks/useSettings';
import { sendChatMessage } from '../../../services/chatApi';
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

  const sendMessage = useCallback(async (text) => {
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

  return {
    isLoading,
    isStreaming,
    streamingStats,
    error,
    hasMore,
    sendMessage,
    cancelStream,
    loadMore,
  };
}
