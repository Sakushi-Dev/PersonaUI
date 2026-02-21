// ── Step: Afterthought (5/6) ──

import styles from './Steps.module.css';

const MODES = [
  { value: 'off',    label: 'Off' },
  { value: 'selten', label: 'Rare' },
  { value: 'mittel', label: 'Medium' },
  { value: 'hoch',   label: 'High' },
];

const MODE_INFO = {
  off: {
    text: 'Your persona only responds when you write. No inner dialogue, no spontaneous messages.',
    extra: null,
  },
  selten: {
    text: 'Every 3rd message triggers an inner dialogue. The persona occasionally reaches out on its own – when something is truly on its mind.',
    extra: 'Low additional API costs. Good for getting started.',
  },
  mittel: {
    text: 'Every 2nd message triggers an inner dialogue. The persona adds its own thoughts, questions, or impulses more frequently.',
    extra: 'Moderate additional API costs. Good balance between liveliness and costs.',
  },
  hoch: {
    text: 'Every message triggers an inner dialogue. The persona fully lives out its inner world – spontaneous, impulsive, and approachable.',
    extra: 'Higher additional API costs. For the most intense experience.',
  },
};

export default function StepAfterthought({ data, onChange, onNext, onBack }) {
  const update = (field, value) => {
    onChange((prev) => ({ ...prev, [field]: value }));
  };

  const currentMode = MODE_INFO[data.nachgedankeMode] || MODE_INFO.off;

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.cardStep}>5 / 6</span>
        <h2>Afterthought</h2>
        <p className={styles.cardDesc}>Spontaneous thoughts from your persona.</p>
      </div>
      <div className={styles.cardBody}>

        {/* Intro */}
        <div className={styles.featureIntro}>
          <p>
            Sometimes after a conversation you have another thought – something that only
            comes to mind afterwards. <strong>Afterthought</strong> gives your personas exactly this ability.
          </p>
          <p>
            After your message, the persona has an inner dialogue with itself.
            If something seems important enough, it writes to you on its own –
            with escalating time intervals, like real pondering.
          </p>
        </div>

        {/* How it works */}
        <div className={styles.featureHighlights}>
          <div className={styles.feature}>
            <span className={styles.featureTag}>01</span>
            <div className={styles.featureText}>
              <strong>Inner Dialogue</strong>
              <span className={styles.featureTyped}>The persona quietly considers whether it wants to say something more</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureTag}>02</span>
            <div className={styles.featureText}>
              <strong>Natural Timing</strong>
              <span className={styles.featureTyped}>Escalating pauses – from short to long, like real pondering</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureTag}>03</span>
            <div className={styles.featureText}>
              <strong>Spontaneous Message</strong>
              <span className={styles.featureTyped}>Only when the persona truly has something to say</span>
            </div>
          </div>
        </div>

        {/* Mode Selector */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Frequency <span className={styles.betaBadge}>Beta</span></label>
          <div className={styles.typeGrid} style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
            {MODES.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`${styles.typeChip} ${data.nachgedankeMode === opt.value ? styles.chipActive : ''}`}
                onClick={() => update('nachgedankeMode', opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* Dynamic Info per Mode */}
          <div className={`${styles.infoBox} ${styles.infoBoxCompact}`}>
            <span className={styles.infoIcon}></span>
            <span>
              {currentMode.text}
              {currentMode.extra && (
                <>
                  <br /><strong>{currentMode.extra}</strong>
                </>
              )}
              {data.nachgedankeMode !== 'off' && (
                <>
                  {' '}Afterthought generates additional API requests in the background.
                </>
              )}
            </span>
          </div>
        </div>

      </div>
      <div className={styles.cardFooter}>
        <button className={styles.btnGhost} onClick={onBack}>Back</button>
        <button className={styles.btnPrimary} onClick={onNext}>Next</button>
      </div>
    </div>
  );
}
