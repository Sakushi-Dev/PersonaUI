// ── SessionList Component ──
// Matches legacy sessions view: "Neuer Chat" button at top, sessions below

import { useState, useEffect } from 'react';
import { getSessions } from '../../../../services/sessionApi';
import { useSession } from '../../../../hooks/useSession';
import { useLanguage } from '../../../../hooks/useLanguage';
import SessionItem from './SessionItem';
import styles from './Sidebar.module.css';

export default function SessionList({ personaId, onNewChat, onClose }) {
  const { sessionId: activeSessionId, switchSession, deleteSession, switchPersona } = useSession();
  const { t } = useLanguage();
  const s = t('sidebar');
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
    // If already active session, just close the sidebar
    if (session.id === activeSessionId) {
      onClose?.();
      return;
    }
    await switchPersona(personaId);
    await switchSession(session.id, personaId);
    onClose?.();
  };

  const handleDelete = async (session) => {
    await deleteSession(session.id);
    setSessions((prev) => prev.filter((s) => s.id !== session.id));
  };

  if (loading) {
    return <div className={styles.empty}>{s.noChats}</div>;
  }

  return (
    <>
      {/* New Chat button at top of sessions view (legacy position) */}
      <button className={styles.newChatBtn} onClick={onNewChat}>
        <span className={styles.newChatIcon}>+</span>
        <span>{s.newChat}</span>
      </button>

      {sessions.length === 0 ? (
        <div className={styles.empty}>
          {s.noChats}<br />{s.startChat}
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
