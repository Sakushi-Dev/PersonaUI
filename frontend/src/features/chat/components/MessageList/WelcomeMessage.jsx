// ── WelcomeMessage Component ──

import Button from '../../../../components/Button/Button';
import styles from './MessageList.module.css';

export default function WelcomeMessage({ characterName, onNewChat }) {
  return (
    <div className={styles.welcome}>
      <h2 className={styles.welcomeTitle}>
        Willkommen{characterName ? ` bei ${characterName}` : ''}! 👋
      </h2>
      <p className={styles.welcomeText}>
        Starte eine Unterhaltung, indem du eine Nachricht schreibst.
      </p>
      <Button variant="primary" onClick={onNewChat}>
        Chat starten
      </Button>
    </div>
  );
}
