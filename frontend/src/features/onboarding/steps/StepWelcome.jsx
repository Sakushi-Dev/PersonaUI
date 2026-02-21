// ── Step: Welcome ──

import styles from './Steps.module.css';

export default function StepWelcome({ onNext }) {
  return (
    <div className={styles.card}>
      <div className={styles.welcomeCard}>
        <div className={styles.logo}>
          <div className={styles.logoInner}>
            <img src="/persona_ui.ico" alt="PersonaUI" className={styles.logoIcon} />
          </div>
        </div>
        <h1 className={styles.welcomeTitle}>Welcome to PersonaUI</h1>
        <p className={styles.welcomeSubtitle}>
          Create AI characters with their own personality, memories, and quirks –
          local, private, and entirely on your machine.
        </p>

        <div className={styles.welcomeFeatures}>
          <div className={styles.feature}>
            <span className={styles.featureTag}>01</span>
            <div className={styles.featureText}>
              <strong>Living Personas</strong>
              <span className={styles.featureTyped}>Each persona has unique character traits, knowledge areas, and an individual expression style. You decide who you talk to.</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureTag}>02</span>
            <div className={styles.featureText}>
              <strong>Cortex – Real Memory</strong>
              <span className={styles.featureTyped}>Your personas remember your conversations, evolve over time, and build a genuine relationship with you.</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureTag}>03</span>
            <div className={styles.featureText}>
              <strong>Afterthought</strong>
              <span className={styles.featureTyped}>Sometimes your persona reaches out on its own when something comes to mind – just like a real conversation partner.</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureTag}>04</span>
            <div className={styles.featureText}>
              <strong>100% Local & Private</strong>
              <span className={styles.featureTyped}>No cloud, no tracking. All data stays on your machine – only the API communication goes out.</span>
            </div>
          </div>
        </div>

        <p className={styles.welcomeHint}>
          6 quick steps to set everything up – takes just a few minutes.
        </p>

        <button className={styles.btnPrimary + ' ' + styles.btnLarge} onClick={onNext}>
          Start Setup
        </button>
      </div>
    </div>
  );
}
