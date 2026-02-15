// ── Session Context ──

import { createContext, useState, useCallback, useEffect, useRef } from 'react';
import * as sessionApi from '../services/sessionApi';
import * as personaApi from '../services/personaApi';

export const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const [sessionId, setSessionId] = useState(null);
  const [personaId, setPersonaId] = useState('default');
  const [character, setCharacter] = useState(null);
  const [personas, setPersonas] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  const [totalMessageCount, setTotalMessageCount] = useState(0);
  const [lastMemoryMessageId, setLastMemoryMessageId] = useState(null);
  const [loading, setLoading] = useState(true);
  const initialized = useRef(false);

  // Load personas
  const loadPersonas = useCallback(async () => {
    try {
      const data = await personaApi.getPersonas();
      if (data.success) {
        setPersonas(data.personas || []);
        return data.personas || [];
      }
    } catch (err) {
      console.warn('Failed to load personas:', err);
    }
    return [];
  }, []);

  // ── Core initialization logic (reusable) ──
  const initSession = useCallback(async () => {
    console.log('[SessionContext] initSession starting...');
    setLoading(true);
    try {
      // 1. Load personas list
      const personasList = await loadPersonas();
      console.log('[SessionContext] Loaded personas:', personasList?.length);

      // 2. Get active persona
      let activePid = 'default';
      const active = personasList.find((p) => p.is_active);
      if (active) activePid = active.id || 'default';

      // 3. Check URL params for session/persona
      const params = new URLSearchParams(window.location.search);
      const urlSession = params.get('session');
      const urlPersona = params.get('persona_id');
      if (urlPersona) activePid = urlPersona;

      setPersonaId(activePid);

      // 4. If URL has a session, load it directly
      if (urlSession) {
        try {
          const sessionData = await sessionApi.getSession(parseInt(urlSession, 10), activePid);
          if (sessionData.success !== false) {
            setSessionId(parseInt(urlSession, 10));
            setPersonaId(sessionData.persona_id || activePid);
            setCharacter(sessionData.character);
            setChatHistory(sessionData.chat_history || []);
            setTotalMessageCount(sessionData.total_message_count || 0);
            setLastMemoryMessageId(sessionData.last_memory_message_id || null);
            return;
          }
        } catch { /* fallthrough to load latest */ }
      }

      // 5. Load sessions for active persona, pick the latest
      const sessionsData = await sessionApi.getSessions(activePid);
      if (sessionsData.success && sessionsData.sessions?.length > 0) {
        const latestId = sessionsData.sessions[0].id;
        const sessionData = await sessionApi.getSession(latestId, activePid);
        if (sessionData.success !== false) {
          setSessionId(latestId);
          setPersonaId(sessionData.persona_id || activePid);
          setCharacter(sessionData.character);
          setChatHistory(sessionData.chat_history || []);
          setTotalMessageCount(sessionData.total_message_count || 0);
          setLastMemoryMessageId(sessionData.last_memory_message_id || null);
          updateUrl(latestId, sessionData.persona_id || activePid);
          return;
        }
      }

      // 6. No sessions exist → create a new one
      const newSession = await sessionApi.createSession(activePid);
      if (newSession.success) {
        setSessionId(newSession.session_id);
        setPersonaId(newSession.persona_id || activePid);
        setCharacter(newSession.character);
        setChatHistory(newSession.chat_history || []);
        setTotalMessageCount(newSession.total_message_count || 0);
        updateUrl(newSession.session_id, newSession.persona_id || activePid);
      } else {
        // Last resort: just load character config
        try {
          const charData = await personaApi.getCharConfig();
          if (charData.success !== false) {
            setCharacter(charData.config || charData);
          }
        } catch { /* give up */ }
      }
    } catch (err) {
      console.error('[SessionContext] Failed to initialize session:', err);
    } finally {
      console.log('[SessionContext] initSession done, setLoading(false)');
      setLoading(false);
    }
  }, [loadPersonas]);

  // ── Initial data loading on mount ──
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    initSession();
  }, [initSession]);

  // ── Re-initialize (called after onboarding etc.) ──
  const reinitialize = useCallback(() => {
    return initSession();
  }, [initSession]);

  // Switch to a persona (load their latest session)
  const switchPersona = useCallback(async (newPersonaId) => {
    try {
      // Activate the persona
      await personaApi.activatePersona(newPersonaId);

      // Get sessions for this persona
      const sessionsData = await sessionApi.getSessions(newPersonaId);
      let targetSessionId;

      if (sessionsData.success && sessionsData.sessions?.length > 0) {
        targetSessionId = sessionsData.sessions[0].id;
      } else {
        // Create new session
        const newSession = await sessionApi.createSession(newPersonaId);
        if (newSession.success) {
          targetSessionId = newSession.session_id;
          setCharacter(newSession.character);
          setChatHistory(newSession.chat_history || []);
          setTotalMessageCount(newSession.total_message_count || 0);
          setSessionId(targetSessionId);
          setPersonaId(newPersonaId);
          updateUrl(targetSessionId, newPersonaId);
          return;
        }
      }

      // Load the session
      if (targetSessionId) {
        await switchSession(targetSessionId, newPersonaId);
      }
    } catch (err) {
      console.warn('Failed to switch persona:', err);
    }
  }, []);

  // Switch to a specific session
  const switchSession = useCallback(async (newSessionId, newPersonaId) => {
    try {
      const pid = newPersonaId || personaId;
      const data = await sessionApi.getSession(newSessionId, pid);
      if (data.success !== false) {
        setSessionId(newSessionId);
        setPersonaId(data.persona_id || pid);
        setCharacter(data.character);
        setChatHistory(data.chat_history || []);
        setTotalMessageCount(data.total_message_count || 0);
        setLastMemoryMessageId(data.last_memory_message_id || null);
        updateUrl(newSessionId, data.persona_id || pid);
      }
    } catch (err) {
      console.warn('Failed to switch session:', err);
    }
  }, [personaId]);

  // Create new session for current persona
  const createSession = useCallback(async (forPersonaId) => {
    try {
      const pid = forPersonaId || personaId;

      // Check if current session is empty → delete it first
      if (sessionId) {
        const emptyCheck = await sessionApi.isSessionEmpty(sessionId, pid);
        if (emptyCheck.success && emptyCheck.is_empty) {
          await sessionApi.deleteSession(sessionId, pid);
        }
      }

      const data = await sessionApi.createSession(pid);
      if (data.success) {
        setSessionId(data.session_id);
        setPersonaId(data.persona_id || pid);
        setCharacter(data.character);
        setChatHistory(data.chat_history || []);
        setTotalMessageCount(data.total_message_count || 0);
        updateUrl(data.session_id, data.persona_id || pid);
        return data;
      }
    } catch (err) {
      console.warn('Failed to create session:', err);
    }
    return null;
  }, [personaId, sessionId]);

  // Delete a session
  const deleteSession = useCallback(async (deleteSessionId) => {
    try {
      await sessionApi.deleteSession(deleteSessionId, personaId);

      if (deleteSessionId === sessionId) {
        // Load another session or create new
        const sessionsData = await sessionApi.getSessions(personaId);
        if (sessionsData.success && sessionsData.sessions?.length > 0) {
          await switchSession(sessionsData.sessions[0].id, personaId);
        } else {
          await createSession();
        }
      }
    } catch (err) {
      console.warn('Failed to delete session:', err);
    }
  }, [personaId, sessionId, switchSession, createSession]);

  const updateUrl = (sid, pid) => {
    const url = `/?session=${sid}&persona_id=${pid}`;
    window.history.replaceState({}, '', url);
  };

  // Append a message to chat history
  const addMessage = useCallback((message) => {
    setChatHistory((prev) => [...prev, message]);
    setTotalMessageCount((prev) => prev + 1);
  }, []);

  // Prepend older messages (load more)
  const prependMessages = useCallback((messages) => {
    setChatHistory((prev) => [...messages, ...prev]);
  }, []);

  const value = {
    sessionId,
    personaId,
    character,
    personas,
    chatHistory,
    totalMessageCount,
    lastMemoryMessageId,
    loading,
    setLoading,
    setCharacter,
    setPersonas,
    setChatHistory,
    setTotalMessageCount,
    switchPersona,
    switchSession,
    createSession,
    deleteSession,
    loadPersonas,
    addMessage,
    prependMessages,
    reinitialize,
  };

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
