// ── SessionItem Component ──
// Matches legacy session-item: full datetime, optional created date, × delete

import { formatFullDateTime } from '../../../../utils/formatTime';
import styles from './Sidebar.module.css';

export default function SessionItem({ session, isActive, onSelect, onDelete }) {
  const dateStr = formatFullDateTime(session.updated_at || session.created_at);
  const createdStr = formatFullDateTime(session.created_at);
  const showCreated = createdStr && createdStr !== dateStr;

  return (
    <div
      className={`${styles.sessionItem} ${isActive ? styles.sessionActive : ''}`}
      onClick={onSelect}
      role="button"
      tabIndex={0}
    >
      <div className={styles.sessionInfo}>
        <div className={styles.sessionDatePrimary}>{dateStr}</div>
        {showCreated && (
          <div className={styles.sessionDateCreated}>Erstellt: {createdStr}</div>
        )}
      </div>
      <button
        className={styles.sessionDelete}
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        title="Chat löschen"
      >
        ×
      </button>
    </div>
  );
}
