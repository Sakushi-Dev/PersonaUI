// ── useMessages Hook ──

import { useState, useCallback, useRef } from 'react';
import { useSession } from '../../../hooks/useSession';
import { useSettings } from '../../../hooks/useSettings';
import { sendChatMessage } from '../../../services/chatApi';
import { loadMoreMessages } from '../../../services/sessionApi';
import { playNotificationSound } from '../../../utils/audioUtils';

export function useMessages() {
  const { sessionId, personaId, addMessage, prependMessages, chatHistory, totalMessageCount } = useSession();
  const { get } = useSettings();

  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [streamingStats, setStreamingStats] = useState(null);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);
  const loadedCount = useRef(0);

  const hasMore = chatHistory.length < totalMessageCount;

  const sendMessage = useCallback(async (text) => {
    console.log('[useMessages] sendMessage called, text:', text, 'sessionId:', sessionId, 'personaId:', personaId, 'isLoading:', isLoading, 'isStreaming:', isStreaming);
    if (!text.trim() || isLoading || isStreaming) return;

    setIsLoading(true);
    setIsStreaming(true);
    setStreamingText('');
    setError(null);

    // Add user message immediately
    const userMessage = {
      message: text,
      is_user: true,
      character_name: null,
      timestamp: new Date().toISOString(),
    };
    addMessage(userMessage);

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
        setStreamingText(rawText);
      },
      onDone: (data) => {
        setIsStreaming(false);
        setIsLoading(false);
        setStreamingText('');
        setStreamingStats(data.stats || null);

        const botMessage = {
          message: data.response,
          is_user: false,
          character_name: data.character_name,
          timestamp: new Date().toISOString(),
          stats: data.stats,
        };
        addMessage(botMessage);

        // Play notification sound if enabled
        if (get('notificationSound', false)) {
          playNotificationSound();
        }
      },
      onError: (err) => {
        setIsStreaming(false);
        setIsLoading(false);
        setStreamingText('');
        setError(err);
      },
    });
  }, [sessionId, personaId, isLoading, isStreaming, addMessage, get]);

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
    setIsLoading(false);
    setStreamingText('');
  }, []);

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
    streamingText,
    streamingStats,
    error,
    hasMore,
    sendMessage,
    cancelStream,
    loadMore,
  };
}
