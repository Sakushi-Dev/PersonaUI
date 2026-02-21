// ── Step: Context (3/6) ──

import styles from './Steps.module.css';

const RANGE_INFO = {
  low:    'A low context limit keeps costs down. The persona forgets older messages faster but focuses only on what matters.',
  medium: 'A medium limit is a good compromise – the persona retains enough conversation history to stay on track without significantly increasing costs.',
  high:   'A high context limit gives the persona extensive access to the conversation so far. Ideal for deep conversations – but API costs increase noticeably.',
};

function getRange(value) {
  const n = parseInt(value, 10);
  if (n <= 125) return 'low';
  if (n <= 275) return 'medium';
  return 'high';
}

export default function StepContext({ data, onChange, onNext, onBack }) {
  const update = (field, value) => {
    onChange((prev) => ({ ...prev, [field]: value }));
  };

  const range = getRange(data.contextLimit);
  const info = RANGE_INFO[range];

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.cardStep}>3 / 6</span>
        <h2>Context</h2>
        <p className={styles.cardDesc}>How much should your persona remember?</p>
      </div>
      <div className={styles.cardBody}>

        {/* Intro */}
        <div className={styles.featureIntro}>
          <p>
            The <strong>context limit</strong> determines how many past messages the AI considers
            for each response. The higher the value, the more conversation history flows into
            the response – but each message costs more.
          </p>
          <p>
            Think of it as short-term memory: A low value means the persona focuses on
            the here and now. A high value lets it dive deeper into your conversation.
          </p>
        </div>

        {/* How it affects things */}
        <div className={styles.featureHighlights}>
          <div className={styles.feature}>
            <span className={styles.featureTag}>01</span>
            <div className={styles.featureText}>
              <strong>Conversation Depth</strong>
              <span className={styles.featureTyped}>More context = the persona remembers messages further back</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureTag}>02</span>
            <div className={styles.featureText}>
              <strong>API Costs</strong>
              <span className={styles.featureTyped}>Each message sends the entire context to the API – more context costs more</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureTag}>03</span>
            <div className={styles.featureText}>
              <strong>Cortex Trigger</strong>
              <span className={styles.featureTyped}>The Cortex frequency is based on your context limit – both are linked</span>
            </div>
          </div>
        </div>

        {/* Slider */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>
            Context Limit: <strong>{data.contextLimit}</strong> messages
          </label>
          <input
            type="range"
            className={styles.slider}
            min={50}
            max={400}
            step={5}
            value={parseInt(data.contextLimit, 10)}
            onChange={(e) => update('contextLimit', e.target.value)}
          />
          <div className={styles.sliderLabels}>
            <span>50</span>
            <span className={styles.sliderRec}>Recommended: 200</span>
            <span>400</span>
          </div>

          {/* Dynamic Info based on range */}
          <div className={`${styles.infoBox} ${styles.infoBoxCompact}`}>
            <span className={styles.infoIcon}></span>
            <span>
              {info}
              {' '}You can adjust this value anytime in the settings.
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
