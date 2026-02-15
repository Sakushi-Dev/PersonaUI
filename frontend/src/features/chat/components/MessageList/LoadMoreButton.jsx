// ── LoadMoreButton Component ──

import styles from './MessageList.module.css';

export default function LoadMoreButton({ onClick }) {
  return (
    <div className={styles.loadMore}>
      <button className={styles.loadMoreBtn} onClick={onClick}>
        Ältere Nachrichten laden
      </button>
    </div>
  );
}
