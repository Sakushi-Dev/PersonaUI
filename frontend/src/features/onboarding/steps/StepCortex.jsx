// ── Step: Cortex (4/6) ──

import styles from './Steps.module.css';

const FREQUENCY_OPTIONS = [
  { value: 'frequent', label: 'Frequent',  percent: 50 },
  { value: 'medium',   label: 'Medium',    percent: 75 },
  { value: 'rare',     label: 'Rare',      percent: 95 },
];

const FREQUENCY_INFO = {
  frequent: 'Cortex updates frequently – your persona picks up on changes quickly and responds promptly to new impressions. Ideal if you chat intensively with a persona.',
  medium: 'A good balance – Cortex stays up to date without being constantly active. Recommended for most users.',
  rare: 'Cortex only summarizes large conversation sections – saves API costs, but the persona takes longer to notice changes.',
};

export default function StepCortex({ data, onChange, onNext, onBack }) {
  const update = (field, value) => {
    onChange((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.cardStep}>4 / 6</span>
        <h2>Cortex</h2>
        <p className={styles.cardDesc}>Your personas' memory system.</p>
      </div>
      <div className={styles.cardBody}>

        {/* Intro Text */}
        <div className={styles.featureIntro}>
          <p>
            Each persona develops its own memory over time. <strong>Cortex</strong> silently observes
            your conversations in the background and shapes them into memories, quirks, and a
            shared history.
          </p>
          <p>
            The more you talk, the deeper the connection. Your persona remembers
            details, evolves, and builds a genuine relationship with you –
            all on its own.
          </p>
        </div>

        {/* Cortex drei Bereiche */}
        <div className={styles.featureHighlights}>
          <div className={styles.feature}>
            <span className={styles.featureTag}>01</span>
            <div className={styles.featureText}>
              <strong>Memory</strong>
              <span className={styles.featureTyped}>Facts about you, shared experiences, important details</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureTag}>02</span>
            <div className={styles.featureText}>
              <strong>Soul</strong>
              <span className={styles.featureTyped}>How the persona evolves – character, preferences, quirks</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureTag}>03</span>
            <div className={styles.featureText}>
              <strong>Relationship</strong>
              <span className={styles.featureTyped}>The dynamic between you – trust, closeness, your shared history</span>
            </div>
          </div>
        </div>

        {/* Enable/Disable */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Enable Cortex</label>
          <div className={styles.modeSwitch}>
            <span className={styles.modeLabel}>Off</span>
            <label className={styles.toggle}>
              <input
                type="checkbox"
                checked={data.cortexEnabled}
                onChange={() => update('cortexEnabled', !data.cortexEnabled)}
              />
              <span className={styles.toggleSlider} />
            </label>
            <span className={styles.modeLabel}>On</span>
          </div>
          {!data.cortexEnabled && (
            <div className={`${styles.infoBox} ${styles.infoBoxCompact}`}>
              <span className={styles.infoIcon}></span>
              <span>Cortex is disabled. Your personas will not remember your conversations.</span>
            </div>
          )}
        </div>

        {/* Frequency */}
        {data.cortexEnabled && (
          <div className={styles.fieldGroup}>
            <label className={styles.label}>Update Frequency</label>
            <span className={styles.hint} style={{ marginBottom: 10 }}>
              How often should Cortex update its memory? The percentage refers to your context limit.
            </span>
            <div className={styles.typeGrid} style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
              {FREQUENCY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`${styles.typeChip} ${styles.typeChipTall} ${data.cortexFrequency === opt.value ? styles.chipActive : ''}`}
                  onClick={() => update('cortexFrequency', opt.value)}
                >
                  <span>{opt.label}</span>
                  <span className={styles.chipSub}>{opt.percent}%</span>
                </button>
              ))}
            </div>
            <div className={`${styles.infoBox} ${styles.infoBoxCompact}`}>
              <span className={styles.infoIcon}></span>
              <span>
                {FREQUENCY_INFO[data.cortexFrequency]}
                {' '}Cortex works fully automatically in the background. You don't need to do anything – just talk.
              </span>
            </div>
          </div>
        )}

      </div>
      <div className={styles.cardFooter}>
        <button className={styles.btnGhost} onClick={onBack}>Back</button>
        <button className={styles.btnPrimary} onClick={onNext}>Next</button>
      </div>
    </div>
  );
}
