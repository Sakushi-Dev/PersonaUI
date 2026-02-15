// ── PersonaCard Component ──
// Messenger-style contact item matching legacy sidebar-contact-item

import Avatar from '../../../../components/Avatar/Avatar';
import { formatDateTime } from '../../../../utils/formatTime';
import styles from './Sidebar.module.css';

export default function PersonaCard({ persona, isActive, onClick }) {
  const sessionCount = persona.session_count || 0;
  const subtitle = sessionCount > 0
    ? `${sessionCount} ${sessionCount === 1 ? 'Chat' : 'Chats'}`
    : 'Kein Chat vorhanden';
  const lastActivity = formatDateTime(persona.last_updated);

  return (
    <div
      className={`${styles.card} ${isActive ? styles.cardActive : ''}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
    >
      <div className={styles.avatarWrapper}>
        <Avatar
          src={persona.avatar}
          type={persona.avatar_type}
          name={persona.name}
          size={46}
        />
        {isActive && <span className={styles.onlineDot} />}
      </div>
      <div className={styles.cardInfo}>
        <div className={styles.cardNameRow}>
          <span className={styles.cardName}>{persona.name || 'Unbenannt'}</span>
          {lastActivity && <span className={styles.cardTime}>{lastActivity}</span>}
        </div>
        <div className={styles.cardSub}>{subtitle}</div>
      </div>
    </div>
  );
}
