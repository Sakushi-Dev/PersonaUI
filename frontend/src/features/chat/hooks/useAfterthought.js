// ── useAfterthought Hook ──

import { useState, useCallback, useRef, useEffect } from 'react';
import { useSession } from '../../../hooks/useSession';
import { useSettings } from '../../../hooks/useSettings';
import { sendAfterthought } from '../../../services/chatApi';
import { AFTERTHOUGHT_INTERVALS } from '../../../utils/constants';
import { playNotificationSound } from '../../../utils/audioUtils';
import { formatMessage } from '../../../utils/formatMessage';

export function useAfterthought() {
  const { sessionId, personaId, character, addMessage, updateLastMessage, removeLastMessage } = useSession();
  const { get } = useSettings();

  const [isThinking, setIsThinking] = useState(false);
  const [timer, setTimer] = useState(null);

  const stageRef = useRef(0);
  const timerRef = useRef(null);
  const activeRef = useRef(false);
  const lastResponseTimeRef = useRef(null);

  const enabled = get('nachgedankeEnabled', true);

  const getElapsedTime = () => {
    if (!lastResponseTimeRef.current) return '10 Sekunden';
    const elapsed = Date.now() - lastResponseTimeRef.current;
    if (elapsed < 60000) return `${Math.round(elapsed / 1000)} Sekunden`;
    if (elapsed < 3600000) return `${Math.round(elapsed / 60000)} Minuten`;
    return `${Math.round(elapsed / 3600000)} Stunden`;
  };

  const executeCheck = useCallback(async () => {
    if (!sessionId || isThinking) return;

    try {
      setIsThinking(true);

      // Decision phase
      const decision = await sendAfterthought({
        sessionId,
        personaId,
        elapsedTime: getElapsedTime(),
        phase: 'decision',
        apiModel: get('apiModel'),
        apiTemperature: get('apiTemperature'),
        contextLimit: get('contextLimit'),
        experimentalMode: get('experimentalMode'),
      });

      if (!decision.success || !decision.decision) {
        setIsThinking(false);
        // Advance to next stage
        stageRef.current = Math.min(stageRef.current + 1, AFTERTHOUGHT_INTERVALS.length - 1);
        scheduleNext();
        return;
      }

      // Followup phase (streaming) — add placeholder to chatHistory
      let rawText = '';

      addMessage({
        message: '',
        is_user: false,
        character_name: character?.char_name,
        _streaming: true,
        timestamp: new Date().toISOString(),
      });

      sendAfterthought({
        sessionId,
        personaId,
        elapsedTime: getElapsedTime(),
        phase: 'followup',
        innerDialogue: decision.inner_dialogue,
        apiModel: get('apiModel'),
        apiTemperature: get('apiTemperature'),
        contextLimit: get('contextLimit'),
        experimentalMode: get('experimentalMode'),
        onChunk: (chunk) => {
          rawText += chunk;
          updateLastMessage({ message: formatMessage(rawText) });
        },
        onDone: (data) => {
          setIsThinking(false);

          // Finalize the streaming message in-place
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

          lastResponseTimeRef.current = Date.now();
          // Reset to stage 2 (5min) after successful followup
          stageRef.current = 2;
          scheduleNext();
        },
        onError: () => {
          setIsThinking(false);
          removeLastMessage(); // Remove the streaming placeholder
          stageRef.current = Math.min(stageRef.current + 1, AFTERTHOUGHT_INTERVALS.length - 1);
          scheduleNext();
        },
      });
    } catch {
      setIsThinking(false);
      scheduleNext();
    }
  }, [sessionId, personaId, isThinking, character, addMessage, updateLastMessage, removeLastMessage, get]);

  const scheduleNext = useCallback(() => {
    if (!activeRef.current || !enabled) return;
    if (stageRef.current >= AFTERTHOUGHT_INTERVALS.length) return;

    const interval = AFTERTHOUGHT_INTERVALS[stageRef.current];
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => executeCheck(), interval);
    setTimer(interval);
  }, [enabled, executeCheck]);

  const startTimer = useCallback((fromUserMessage = true) => {
    if (!enabled) return;
    activeRef.current = true;
    stageRef.current = fromUserMessage ? 0 : 2;
    lastResponseTimeRef.current = Date.now();
    scheduleNext();
  }, [enabled, scheduleNext]);

  const stopTimer = useCallback(() => {
    activeRef.current = false;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
    setTimer(null);
    setIsThinking(false);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  // Stop timer when session changes
  useEffect(() => {
    stopTimer();
  }, [sessionId, stopTimer]);

  return {
    isThinking,
    timer,
    startTimer,
    stopTimer,
    executeCheck,
  };
}
