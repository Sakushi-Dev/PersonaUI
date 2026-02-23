// ── PersonaCard Component ──
// Messenger-style contact item matching legacy sidebar-contact-item

import Avatar from '../../../../components/Avatar/Avatar';
import { formatDateTime } from '../../../../utils/formatTime';
import { useLanguage } from '../../../../hooks/useLanguage';
import styles from './Sidebar.module.css';

export default function PersonaCard({ persona, isActive, onClick }) {
  const { language, t } = useLanguage();
  const s = t('sidebar');

  const sessionCount = persona.session_count || 0;
  const subtitle = sessionCount > 0
    ? `${sessionCount} ${sessionCount === 1 ? 'Chat' : 'Chats'}`
    : s.noChatAvailable;
  const lastActivity = formatDateTime(persona.last_updated, language);

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
          <span className={styles.cardName}>{persona.name || s.unnamed}</span>
          {lastActivity && <span className={styles.cardTime}>{lastActivity}</span>}
        </div>
        <div className={styles.cardSub}>{subtitle}</div>
      </div>
    </div>
  );
}
