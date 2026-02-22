// ── LoadMoreButton Component ──

import { useLanguage } from '../../../../hooks/useLanguage';
import styles from './MessageList.module.css';

export default function LoadMoreButton({ onClick }) {
  const { t } = useLanguage();
  const s = t('chat');

  return (
    <div className={styles.loadMore}>
      <button className={styles.loadMoreBtn} onClick={onClick}>
        {s.loadMore}
      </button>
    </div>
  );
}
