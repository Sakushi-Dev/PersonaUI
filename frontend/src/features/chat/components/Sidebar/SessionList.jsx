// ── SessionList Component ──
// Matches legacy sessions view: "Neuer Chat" button at top, sessions below

import { useState, useEffect } from 'react';
import { getSessions } from '../../../../services/sessionApi';
import { useSession } from '../../../../hooks/useSession';
import SessionItem from './SessionItem';
import styles from './Sidebar.module.css';

export default function SessionList({ personaId, onNewChat }) {
  const { sessionId: activeSessionId, switchSession, deleteSession, switchPersona } = useSession();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!personaId) return;
    setLoading(true);
    getSessions(personaId)
      .then((data) => {
        if (data.success) setSessions(data.sessions || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [personaId]);

  const handleSelect = async (session) => {
    await switchPersona(personaId);
    await switchSession(session.id, personaId);
  };

  const handleDelete = async (session) => {
    await deleteSession(session.id);
    setSessions((prev) => prev.filter((s) => s.id !== session.id));
  };

  if (loading) {
    return <div className={styles.empty}>Laden...</div>;
  }

  return (
    <>
      {/* New Chat button at top of sessions view (legacy position) */}
      <button className={styles.newChatBtn} onClick={onNewChat}>
        <span className={styles.newChatIcon}>+</span>
        <span>Neuer Chat</span>
      </button>

      {sessions.length === 0 ? (
        <div className={styles.empty}>
          Noch keine Chats.<br />Starte einen neuen Chat!
        </div>
      ) : (
        <div className={styles.sessionsList}>
          {sessions.map((session) => (
            <SessionItem
              key={session.id}
              session={session}
              isActive={session.id === activeSessionId}
              onSelect={() => handleSelect(session)}
              onDelete={() => handleDelete(session)}
            />
          ))}
        </div>
      )}
    </>
  );
}
