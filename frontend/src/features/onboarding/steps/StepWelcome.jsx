// ── Step: Welcome ──

import Button from '../../../components/Button/Button';
import styles from './Steps.module.css';

export default function StepWelcome({ onNext }) {
  return (
    <div className={styles.step}>
      <h1 className={styles.title}>Willkommen bei PersonaUI</h1>
      <p className={styles.subtitle}>Dein persönlicher KI-Chat-Begleiter</p>

      <div className={styles.featureGrid}>
        <div className={styles.featureCard}>
          <span className={styles.featureIcon}>🎭</span>
          <h3>Individuelle Personas</h3>
          <p>Erstelle einzigartige KI-Persönlichkeiten mit eigenen Eigenschaften und Hintergrund.</p>
        </div>
        <div className={styles.featureCard}>
          <span className={styles.featureIcon}>🧠</span>
          <h3>Erinnerungen</h3>
          <p>Deine Gespräche werden durch das Memory-System langfristig bereichert.</p>
        </div>
        <div className={styles.featureCard}>
          <span className={styles.featureIcon}>✨</span>
          <h3>Nachgedanke</h3>
          <p>Die KI kann von sich aus Nachrichten senden — wie echte Gespräche.</p>
        </div>
      </div>

      <div className={styles.footer}>
        <Button variant="primary" size="lg" onClick={onNext}>
          Einrichtung starten
        </Button>
      </div>
    </div>
  );
}
