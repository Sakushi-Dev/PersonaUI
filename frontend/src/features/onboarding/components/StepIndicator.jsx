// ── StepIndicator ──

import styles from './StepIndicator.module.css';

export default function StepIndicator({ current, total, onGoTo }) {
  return (
    <div className={styles.dots}>
      {Array.from({ length: total }, (_, i) => (
        <button
          key={i}
          className={`${styles.dot} ${i === current ? styles.active : ''} ${i < current ? styles.completed : ''}`}
          onClick={() => onGoTo(i)}
          disabled={i > current}
          aria-label={`Schritt ${i + 1}`}
        />
      ))}
    </div>
  );
}
