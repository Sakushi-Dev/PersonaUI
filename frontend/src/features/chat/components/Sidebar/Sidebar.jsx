// ── Sidebar Component ──
// Matches legacy _sidebar.html + SessionManager.js layout

import { createPortal } from 'react-dom';
import { useSession } from '../../../../hooks/useSession';
import PersonaList from './PersonaList';
import SessionList from './SessionList';
import styles from './Sidebar.module.css';

export default function Sidebar({
  isOpen,
  view,
  selectedPersonaId,
  onClose,
  onShowPersonas,
  onSelectPersona,
  onNewChat,
}) {
  const { personas, personaId: activePersonaId } = useSession();

  const selectedPersona = personas.find((p) => p.id === selectedPersonaId);

  return createPortal(
    <>
      {isOpen && <div className={styles.backdrop} onClick={onClose} />}
      <aside className={`${styles.sidebar} ${isOpen ? styles.open : ''}`}>
        {/* Header: back btn (sessions only) + title + close btn */}
        <div className={styles.header}>
          {view === 'sessions' && (
            <button className={styles.backBtn} onClick={onShowPersonas} title="Zurück zur Persona-Übersicht">
              <span>◀</span>
            </button>
          )}
          <span className={styles.title}>
            {view === 'sessions' ? (selectedPersona?.name || 'Sessions') : 'Chats'}
          </span>
          <button className={styles.closeBtn} onClick={onClose} title="Sidebar ausblenden">
            <span>◀</span>
          </button>
        </div>

        {/* Content: persona list or sessions (with new-chat button inside) */}
        <div className={styles.content}>
          {view === 'personas' ? (
            <PersonaList
              personas={personas}
              activePersonaId={activePersonaId}
              onSelectPersona={onSelectPersona}
            />
          ) : (
            <SessionList
              personaId={selectedPersonaId}
              onNewChat={onNewChat}
            />
          )}
        </div>
      </aside>
    </>,
    document.body
  );
}
