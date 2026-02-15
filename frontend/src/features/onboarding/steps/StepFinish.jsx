// ── Step: Finish – Legacy 1:1 ──

import styles from './Steps.module.css';

export default function StepFinish({ hasApiKey, onFinish, saving }) {
  return (
    <div className={styles.card}>
      {hasApiKey ? (
        /* Standard Finish (mit API-Key) */
        <div className={styles.finishCard}>
          <div className={styles.finishIconBounce}>🎉</div>
          <h2 className={styles.finishTitle}>Viel Spaß!</h2>
          <p className={styles.finishText}>
            Alles eingerichtet. Du kannst jetzt losschreiben, Personas entdecken oder deine eigenen erfinden.
          </p>
          <p className={styles.finishHint}>Alle Einstellungen lassen sich jederzeit über das Menü anpassen.</p>
          <button
            className={`${styles.btnPrimary} ${styles.btnLarge} ${styles.btnGlow}`}
            onClick={onFinish}
            disabled={saving}
          >
            {saving ? 'Speichere...' : 'PersonaUI starten'}
            <span className={styles.btnArrow}>{saving ? '⏳' : '→'}</span>
          </button>
        </div>
      ) : (
        /* Explore Finish (ohne API-Key) */
        <div className={styles.finishCard}>
          <div className={styles.finishIconBounce}>🔍</div>
          <h2 className={styles.finishTitle}>Viel Spaß beim Erkunden!</h2>
          <p className={styles.finishText}>
            Du kannst dich erst einmal umsehen. Um mit Personas zu chatten, gib deinen API-Key später über das Dropdown-Menü unter <strong>Set API-Key</strong> ein.
          </p>
          <p className={styles.finishHint}>Bei Fragen kannst du dich jederzeit an den Projektleiter wenden:</p>
          <a
            href="https://github.com/Sakushi-Dev"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.githubLink}
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
            </svg>
            Sakushi-Dev auf GitHub
          </a>
          <button
            className={`${styles.btnPrimary} ${styles.btnLarge}`}
            onClick={onFinish}
            disabled={saving}
          >
            {saving ? 'Speichere...' : 'PersonaUI erkunden'}
            <span className={styles.btnArrow}>{saving ? '⏳' : '→'}</span>
          </button>
        </div>
      )}
    </div>
  );
}
