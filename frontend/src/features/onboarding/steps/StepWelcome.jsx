// ── Step: Welcome (Legacy 1:1) ──

import styles from './Steps.module.css';

export default function StepWelcome({ onNext }) {
  return (
    <div className={styles.card}>
      <div className={styles.welcomeCard}>
        <div className={styles.logo}>
          <span className={styles.logoIcon}>✦</span>
        </div>
        <h1 className={styles.welcomeTitle}>Willkommen bei PersonaUI</h1>
        <p className={styles.welcomeSubtitle}>Dein persönlicher Begleiter für KI-Personas</p>

        <div className={styles.welcomeFeatures}>
          <div className={styles.feature}>
            <span className={styles.featureIcon}>🧩</span>
            <div className={styles.featureText}>
              <strong>Modulare Personas</strong>
              <span>Erstelle und kombiniere KI-Persönlichkeiten ganz einfach selbst – ohne kompliziertes Prompting oder stundenlanges Suchen nach Konfigurationsdateien.</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureIcon}>⚡</span>
            <div className={styles.featureText}>
              <strong>Perks mit KI generieren</strong>
              <span>Neue Perks bequem mit KI erzeugen und sofort nutzen – PersonaUI übernimmt die Konfiguration für dich.</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureIcon}>💬</span>
            <div className={styles.featureText}>
              <strong>Sofort loslegen</strong>
              <span>Du richtest nur ein paar Einstellungen ein und kannst direkt losschreiben oder neue Personas erfinden – keine komplizierten Konfigurationen nötig.</span>
            </div>
          </div>
        </div>

        <button className={styles.btnPrimary + ' ' + styles.btnLarge} onClick={onNext}>
          Einrichtung starten
          <span className={styles.btnArrow}>→</span>
        </button>
      </div>
    </div>
  );
}
