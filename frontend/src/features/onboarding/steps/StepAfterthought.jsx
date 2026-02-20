// ── Step: Afterthought / Nachgedanke (5/6) ──

import styles from './Steps.module.css';

const MODES = [
  { value: 'off',    label: 'Aus' },
  { value: 'selten', label: 'Selten' },
  { value: 'mittel', label: 'Mittel' },
  { value: 'hoch',   label: 'Hoch' },
];

const MODE_INFO = {
  off: {
    icon: '🔇',
    text: 'Deine Persona antwortet nur, wenn du schreibst. Kein innerer Dialog, keine spontanen Nachrichten.',
    extra: null,
  },
  selten: {
    icon: '💭',
    text: 'Jede 3. Nachricht löst einen inneren Dialog aus. Die Persona meldet sich gelegentlich von selbst – wenn ihr wirklich etwas auf dem Herzen liegt.',
    extra: 'Niedrige zusätzliche API-Kosten. Gut zum Einstieg.',
  },
  mittel: {
    icon: '💬',
    text: 'Jede 2. Nachricht löst einen inneren Dialog aus. Die Persona ergänzt häufiger eigene Gedanken, Fragen oder Impulse.',
    extra: 'Moderate zusätzliche API-Kosten. Guter Kompromiss zwischen Lebendigkeit und Kosten.',
  },
  hoch: {
    icon: '🗣️',
    text: 'Jede Nachricht löst einen inneren Dialog aus. Die Persona lebt ihr Innenleben voll aus – spontan, impulsiv und nahbar.',
    extra: 'Höhere zusätzliche API-Kosten. Für das intensivste Erlebnis.',
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
        <h2>💭 Nachgedanke</h2>
        <p className={styles.cardDesc}>Spontane Gedanken deiner Persona.</p>
      </div>
      <div className={styles.cardBody}>

        {/* Intro */}
        <div className={styles.featureIntro}>
          <p>
            Manchmal hat man nach einem Gespräch noch einen Gedanken – etwas, das einem erst
            danach einfällt. <strong>Nachgedanke</strong> gibt deinen Personas genau diese Fähigkeit.
          </p>
          <p>
            Nach deiner Nachricht führt die Persona einen inneren Dialog mit sich selbst.
            Wenn ihr etwas wichtig genug erscheint, schreibt sie dir von sich aus –
            mit eskalierenden Zeitabständen, wie ein echtes Nachdenken.
          </p>
        </div>

        {/* How it works */}
        <div className={styles.featureHighlights}>
          <div className={styles.featureHighlight}>
            <span className={styles.featureHighlightIcon}>🤔</span>
            <div>
              <strong>Innerer Dialog</strong>
              <span>Die Persona überlegt still, ob sie noch etwas sagen möchte</span>
            </div>
          </div>
          <div className={styles.featureHighlight}>
            <span className={styles.featureHighlightIcon}>⏱️</span>
            <div>
              <strong>Natürliches Timing</strong>
              <span>Eskalierende Pausen – von kurz bis lang, wie echtes Nachdenken</span>
            </div>
          </div>
          <div className={styles.featureHighlight}>
            <span className={styles.featureHighlightIcon}>✉️</span>
            <div>
              <strong>Spontane Nachricht</strong>
              <span>Nur wenn die Persona wirklich etwas zu sagen hat</span>
            </div>
          </div>
        </div>

        {/* Mode Selector */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Häufigkeit <span className={styles.betaBadge}>Beta</span></label>
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
            <span className={styles.infoIcon}>{currentMode.icon}</span>
            <span>
              {currentMode.text}
              {currentMode.extra && (
                <>
                  <br /><strong>{currentMode.extra}</strong>
                </>
              )}
            </span>
          </div>
        </div>

        {data.nachgedankeMode !== 'off' && (
          <div className={`${styles.infoBox} ${styles.infoBoxCompact}`}>
            <span className={styles.infoIcon}>⚠️</span>
            <span>
              Nachgedanke erzeugt zusätzliche API-Anfragen im Hintergrund.
              Die Kosten pro Check bewegen sich im Bereich von ca. 4 Nachkommastellen ($0.000x).
            </span>
          </div>
        )}

      </div>
      <div className={styles.cardFooter}>
        <button className={styles.btnGhost} onClick={onBack}>Zurück</button>
        <button className={styles.btnPrimary} onClick={onNext}>Weiter</button>
      </div>
    </div>
  );
}
