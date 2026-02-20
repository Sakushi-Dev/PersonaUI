// ── Step: Cortex (4/6) ──

import styles from './Steps.module.css';

const FREQUENCY_OPTIONS = [
  { value: 'frequent', label: 'Häufig',  emoji: '🔥', percent: 50 },
  { value: 'medium',   label: 'Mittel',  emoji: '⚡', percent: 75 },
  { value: 'rare',     label: 'Selten',  emoji: '🌙', percent: 95 },
];

const FREQUENCY_INFO = {
  frequent: 'Cortex aktualisiert sich häufig – deine Persona nimmt Veränderungen schnell wahr und reagiert zeitnah auf neue Eindrücke. Ideal, wenn du intensiv mit einer Persona chattest.',
  medium: 'Ein gutes Gleichgewicht – Cortex hält sich auf dem Laufenden, ohne ständig aktiv zu sein. Empfohlen für die meisten Nutzer.',
  rare: 'Cortex fasst nur große Gesprächsabschnitte zusammen – spart API-Kosten, aber die Persona braucht länger, um Veränderungen wahrzunehmen.',
};

export default function StepCortex({ data, onChange, onNext, onBack }) {
  const update = (field, value) => {
    onChange((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.cardStep}>4 / 6</span>
        <h2>🧠 Cortex</h2>
        <p className={styles.cardDesc}>Das Gedächtnis deiner Personas.</p>
      </div>
      <div className={styles.cardBody}>

        {/* Intro Text */}
        <div className={styles.featureIntro}>
          <p>
            Jede Persona entwickelt mit der Zeit ein eigenes Gedächtnis. <strong>Cortex</strong> beobachtet
            eure Gespräche still im Hintergrund und formt daraus Erinnerungen, Eigenheiten und eine
            gemeinsame Geschichte.
          </p>
          <p>
            Je mehr ihr redet, desto tiefer wird die Verbindung. Deine Persona erinnert sich an
            Details, entwickelt sich weiter und baut eine echte Beziehung zu dir auf –
            ganz von selbst.
          </p>
        </div>

        {/* Cortex drei Bereiche */}
        <div className={styles.featureHighlights}>
          <div className={styles.featureHighlight}>
            <span className={styles.featureHighlightIcon}>💾</span>
            <div>
              <strong>Memory</strong>
              <span>Fakten über dich, gemeinsame Erlebnisse, wichtige Details</span>
            </div>
          </div>
          <div className={styles.featureHighlight}>
            <span className={styles.featureHighlightIcon}>💜</span>
            <div>
              <strong>Seele</strong>
              <span>Wie sich die Persona entwickelt – Charakter, Vorlieben, Eigenarten</span>
            </div>
          </div>
          <div className={styles.featureHighlight}>
            <span className={styles.featureHighlightIcon}>💞</span>
            <div>
              <strong>Beziehung</strong>
              <span>Die Dynamik zwischen euch – Vertrauen, Nähe, eure gemeinsame Geschichte</span>
            </div>
          </div>
        </div>

        {/* Enable/Disable */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Cortex aktivieren</label>
          <div className={styles.modeSwitch}>
            <span className={styles.modeLabel}>Aus</span>
            <label className={styles.toggle}>
              <input
                type="checkbox"
                checked={data.cortexEnabled}
                onChange={() => update('cortexEnabled', !data.cortexEnabled)}
              />
              <span className={styles.toggleSlider} />
            </label>
            <span className={styles.modeLabel}>An</span>
          </div>
          {!data.cortexEnabled && (
            <div className={`${styles.infoBox} ${styles.infoBoxCompact}`}>
              <span className={styles.infoIcon}>ℹ️</span>
              <span>Cortex ist deaktiviert. Deine Personas werden sich nicht an eure Gespräche erinnern.</span>
            </div>
          )}
        </div>

        {/* Frequency */}
        {data.cortexEnabled && (
          <div className={styles.fieldGroup}>
            <label className={styles.label}>Update-Frequenz</label>
            <span className={styles.hint} style={{ marginBottom: 10 }}>
              Wie oft soll Cortex sein Gedächtnis aktualisieren? Der Prozentsatz bezieht sich auf dein Kontext-Limit.
            </span>
            <div className={styles.typeGrid} style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
              {FREQUENCY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`${styles.typeChip} ${styles.typeChipTall} ${data.cortexFrequency === opt.value ? styles.chipActive : ''}`}
                  onClick={() => update('cortexFrequency', opt.value)}
                >
                  <span className={styles.chipEmoji}>{opt.emoji}</span>
                  <span>{opt.label}</span>
                  <span className={styles.chipSub}>{opt.percent}%</span>
                </button>
              ))}
            </div>
            <div className={`${styles.infoBox} ${styles.infoBoxCompact}`}>
              <span className={styles.infoIcon}>💡</span>
              <span>{FREQUENCY_INFO[data.cortexFrequency]}</span>
            </div>
          </div>
        )}

        <div className={styles.infoBox}>
          <span className={styles.infoIcon}>✨</span>
          <span>Cortex arbeitet vollautomatisch im Hintergrund. Du musst nichts tun – einfach reden.</span>
        </div>

      </div>
      <div className={styles.cardFooter}>
        <button className={styles.btnGhost} onClick={onBack}>Zurück</button>
        <button className={styles.btnPrimary} onClick={onNext}>Weiter</button>
      </div>
    </div>
  );
}
