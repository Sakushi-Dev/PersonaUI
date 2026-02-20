// ── Step: Kontext (3/6) ──

import styles from './Steps.module.css';

const RANGE_INFO = {
  low:    'Ein niedriges Kontext-Limit hält die Kosten gering. Die Persona vergisst ältere Nachrichten schneller, reagiert aber nur auf das Wesentliche.',
  medium: 'Ein mittleres Limit ist ein guter Kompromiss – die Persona behält genug Gesprächsverlauf, um den Faden nicht zu verlieren, ohne die Kosten stark zu erhöhen.',
  high:   'Ein hohes Kontext-Limit gibt der Persona umfangreichen Zugang zum bisherigen Gespräch. Ideal für tiefgehende Unterhaltungen – aber API-Kosten steigen merklich.',
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
        <h2>📏 Kontext</h2>
        <p className={styles.cardDesc}>Wie viel soll sich deine Persona merken?</p>
      </div>
      <div className={styles.cardBody}>

        {/* Intro */}
        <div className={styles.featureIntro}>
          <p>
            Das <strong>Kontext-Limit</strong> bestimmt, wie viele vergangene Nachrichten die KI bei jeder
            Antwort berücksichtigt. Je höher der Wert, desto mehr Gesprächsverlauf fließt in die
            Antwort ein – aber desto mehr kostet jede Nachricht.
          </p>
          <p>
            Stell dir das wie ein Kurzzeitgedächtnis vor: Ein niedriger Wert bedeutet, die Persona
            konzentriert sich auf das Hier und Jetzt. Ein hoher Wert lässt sie tiefer in eure
            Unterhaltung eintauchen.
          </p>
        </div>

        {/* How it affects things */}
        <div className={styles.featureHighlights}>
          <div className={styles.featureHighlight}>
            <span className={styles.featureHighlightIcon}>💬</span>
            <div>
              <strong>Gesprächstiefe</strong>
              <span>Mehr Kontext = die Persona erinnert sich an weiter zurückliegende Nachrichten</span>
            </div>
          </div>
          <div className={styles.featureHighlight}>
            <span className={styles.featureHighlightIcon}>💰</span>
            <div>
              <strong>API-Kosten</strong>
              <span>Jede Nachricht sendet den gesamten Kontext an die API – mehr Kontext kostet mehr</span>
            </div>
          </div>
          <div className={styles.featureHighlight}>
            <span className={styles.featureHighlightIcon}>🧠</span>
            <div>
              <strong>Cortex-Trigger</strong>
              <span>Die Cortex-Frequenz basiert auf deinem Kontext-Limit – beides hängt zusammen</span>
            </div>
          </div>
        </div>

        {/* Slider */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>
            Kontext-Limit: <strong>{data.contextLimit}</strong> Nachrichten
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
            <span className={styles.sliderRec}>Empfohlen: 200</span>
            <span>400</span>
          </div>

          {/* Dynamic Info based on range */}
          <div className={`${styles.infoBox} ${styles.infoBoxCompact}`}>
            <span className={styles.infoIcon}>💡</span>
            <span>{info}</span>
          </div>
        </div>

        <div className={`${styles.infoBox} ${styles.infoBoxCompact}`}>
          <span className={styles.infoIcon}>⚠️</span>
          <span>
            Die Kostenunterschiede bewegen sich im Bereich von Variationen um ca. 4 Nachkommastellen ($0.000x).
            Du kannst den Wert jederzeit in den Einstellungen anpassen.
          </span>
        </div>

      </div>
      <div className={styles.cardFooter}>
        <button className={styles.btnGhost} onClick={onBack}>Zurück</button>
        <button className={styles.btnPrimary} onClick={onNext}>Weiter</button>
      </div>
    </div>
  );
}
