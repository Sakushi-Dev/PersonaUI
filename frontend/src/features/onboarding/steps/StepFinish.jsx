// ── Step: Finish ──

import Button from '../../../components/Button/Button';
import styles from './Steps.module.css';

export default function StepFinish({ hasApiKey, onFinish, saving }) {
  return (
    <div className={styles.step}>
      <div className={styles.finishIcon}>🎉</div>

      {hasApiKey ? (
        <>
          <h2 className={styles.title}>Viel Spaß!</h2>
          <p className={styles.subtitle}>
            Alles ist eingerichtet. Deine KI wartet auf dich.
          </p>
        </>
      ) : (
        <>
          <h2 className={styles.title}>Viel Spaß beim Erkunden!</h2>
          <p className={styles.subtitle}>
            Du kannst PersonaUI erkunden, aber für die Chat-Funktion
            wird ein API-Key benötigt. Diesen kannst du jederzeit in
            den Einstellungen hinterlegen.
          </p>
        </>
      )}

      <div className={styles.footer}>
        <Button variant="primary" size="lg" onClick={onFinish} disabled={saving}>
          {saving ? 'Wird eingerichtet...' : (hasApiKey ? 'PersonaUI starten' : 'PersonaUI erkunden')}
        </Button>
      </div>

      {!hasApiKey && (
        <p className={styles.hint}>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer">
            → PersonaUI auf GitHub
          </a>
        </p>
      )}
    </div>
  );
}
