// ── useAfterthought Hook ──
// Nachgedanke v2: message-count triggered with 3-phase random delay escalation.
// Modes: "selten" (every 3rd msg), "mittel" (every 2nd), "hoch" (every msg).
// Phase ranges & frequencies loaded from server (afterthought_settings.json).

import { useState, useCallback, useRef, useEffect } from 'react';
import { useSession } from '../../../hooks/useSession';
import { useSettings } from '../../../hooks/useSettings';
import { sendAfterthought } from '../../../services/chatApi';
import { getAfterthoughtSettings } from '../../../services/settingsApi';
import { AFTERTHOUGHT_PHASES as FALLBACK_PHASES, AFTERTHOUGHT_FREQUENCY as FALLBACK_FREQUENCY } from '../../../utils/constants';
import { playNotificationSound } from '../../../utils/audioUtils';
import { formatMessage } from '../../../utils/formatMessage';

/** Pick a random integer in [min, max]. */
function randomBetween(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

export function useAfterthought() {
  const { sessionId, personaId, character, addMessage, updateLastMessage, removeLastMessage } = useSession();
  const { get } = useSettings();

  const [isThinking, setIsThinking] = useState(false);
  const [timer, setTimer] = useState(null);

  // Server-loaded afterthought config (phases + frequency)
  const phasesRef = useRef(FALLBACK_PHASES);
  const frequencyRef = useRef(FALLBACK_FREQUENCY);
  const configLoadedRef = useRef(false);

  // Phase index within the current afterthought cycle (0 = phase 1, 1 = phase 2, 2+ = phase 3)
  const phaseRef = useRef(0);
  const timerRef = useRef(null);
  const activeRef = useRef(false);
  const lastResponseTimeRef = useRef(null);
  // Count user messages since last afterthought trigger (or session start)
  const msgCountRef = useRef(0);
  // Last inner dialogue from a [i_can_wait] decision — sent with next user message then cleared
  const pendingThoughtRef = useRef(null);

  const mode = get('nachgedankeMode', 'off');
  const enabled = mode !== 'off' && mode !== false && mode !== undefined;

  // ── Load afterthought config from server on mount ──
  useEffect(() => {
    getAfterthoughtSettings()
      .then((data) => {
        if (data?.success && data.settings) {
          const s = data.settings;
          if (Array.isArray(s.phases) && s.phases.length > 0) {
            phasesRef.current = s.phases;
          }
          if (s.frequency && typeof s.frequency === 'object') {
            frequencyRef.current = s.frequency;
          }
          configLoadedRef.current = true;
          console.log('[Afterthought] Config loaded from server:', s);
        }
      })
      .catch((err) => {
        console.warn('[Afterthought] Failed to load config, using fallback:', err);
      });
  }, []);

  /** Return the delay (ms) for the given phase index (0-based). */
  const phaseDelay = useCallback((phaseIndex) => {
    const phases = phasesRef.current;
    const idx = Math.min(phaseIndex, phases.length - 1);
    const [lo, hi] = phases[idx];
    return randomBetween(lo, hi);
  }, []);

  const getElapsedTime = () => {
    if (!lastResponseTimeRef.current) return '10 Sekunden';
    const elapsed = Date.now() - lastResponseTimeRef.current;
    if (elapsed < 60000) return `${Math.round(elapsed / 1000)} Sekunden`;
    if (elapsed < 3600000) return `${Math.round(elapsed / 60000)} Minuten`;
    return `${Math.round(elapsed / 3600000)} Stunden`;
  };

  const stopTimer = useCallback(() => {
    activeRef.current = false;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
    setTimer(null);
    setIsThinking(false);
  }, []);

  /** Pause timer without resetting the cycle (e.g. while AI is responding). */
  const pauseTimer = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
    setTimer(null);
  }, []);

  // ── Core check: decision → optional followup ──
  const executeCheck = useCallback(async () => {
    // Re-check enabled state from settings (guards against stale closure)
    const currentMode = get('nachgedankeMode', 'off');
    if (currentMode === 'off' || currentMode === false || currentMode === undefined) {
      stopTimer();
      return;
    }
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
        // [i_can_wait] — save inner dialogue for next user message
        if (decision.inner_dialogue) {
          pendingThoughtRef.current = decision.inner_dialogue;
        }
        // Advance to next phase and schedule again
        phaseRef.current = Math.min(phaseRef.current + 1, phasesRef.current.length - 1);
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

          if (get('notificationSound', false)) {
            playNotificationSound(get('notificationVolume', 0.5));
          }

          lastResponseTimeRef.current = Date.now();
          // After a successful trigger → restart at phase 3 (index 2)
          phaseRef.current = 2;
          scheduleNext();
        },
        onError: () => {
          setIsThinking(false);
          removeLastMessage();
          phaseRef.current = Math.min(phaseRef.current + 1, phasesRef.current.length - 1);
          scheduleNext();
        },
      });
    } catch {
      setIsThinking(false);
      scheduleNext();
    }
  }, [sessionId, personaId, isThinking, character, addMessage, updateLastMessage, removeLastMessage, get, stopTimer]);

  // ── Schedule next check using phased random delay ──
  const scheduleNext = useCallback(() => {
    if (!activeRef.current || !enabled) return;

    const delay = phaseDelay(phaseRef.current);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => executeCheck(), delay);
    setTimer(delay);
  }, [enabled, executeCheck, phaseDelay]);

  /** Resume timer from current phase (e.g. after AI finished responding). */
  const resumeTimer = useCallback(() => {
    if (!activeRef.current || !enabled || isThinking) return;
    lastResponseTimeRef.current = Date.now();
    scheduleNext();
  }, [enabled, isThinking, scheduleNext]);

  // ── Called after every user message from ChatPage ──
  const onUserMessage = useCallback(() => {
    if (!enabled) return;

    msgCountRef.current += 1;
    const freq = frequencyRef.current[mode] ?? 3;

    if (msgCountRef.current >= freq) {
      // Reset counter, start a new afterthought cycle
      msgCountRef.current = 0;
      activeRef.current = true;
      phaseRef.current = 0; // start at phase 1
      lastResponseTimeRef.current = Date.now();
      // Cancel any existing timer before starting fresh
      if (timerRef.current) clearTimeout(timerRef.current);
      scheduleNext();
    }
  }, [enabled, mode, scheduleNext]);

  /** Return + clear the pending inner dialogue (for passing to next chat request). */
  const consumePendingThought = useCallback(() => {
    const thought = pendingThoughtRef.current;
    pendingThoughtRef.current = null;
    return thought;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  // ── Immediately stop when nachgedankeMode is set to 'off' ──
  useEffect(() => {
    if (!enabled) {
      stopTimer();
      msgCountRef.current = 0;
    }
  }, [enabled, stopTimer]);

  // Stop timer & reset counter when session changes
  useEffect(() => {
    stopTimer();
    msgCountRef.current = 0;
    pendingThoughtRef.current = null;
  }, [sessionId, stopTimer]);

  return {
    isThinking,
    timer,
    onUserMessage,
    stopTimer,
    pauseTimer,
    resumeTimer,
    executeCheck,
    consumePendingThought,
  };
}
