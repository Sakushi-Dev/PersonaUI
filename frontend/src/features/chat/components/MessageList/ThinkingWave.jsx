// ── ThinkingWave Component ──
// Animated wave text that cycles through thinking phrases.

import { useState, useEffect, useMemo } from 'react';
import styles from './ThinkingWave.module.css';

export default function ThinkingWave({ phrases = [] }) {
  const [phraseIndex, setPhraseIndex] = useState(0);

  // Cycle through phrases every 3 seconds
  useEffect(() => {
    if (phrases.length <= 1) return;
    const interval = setInterval(() => {
      setPhraseIndex((prev) => (prev + 1) % phrases.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [phrases.length]);

  const currentPhrase = phrases[phraseIndex] || '';

  // Split phrase into individual characters with unique keys
  const letters = useMemo(() => {
    const chars = currentPhrase.split('');
    // Append three animated dots
    return [...chars, '.', '.', '.'];
  }, [currentPhrase]);

  return (
    <span className={styles.thinkingWave} aria-label={currentPhrase}>
      {letters.map((char, i) => (
        <span
          key={`${phraseIndex}-${i}`}
          className={char === ' ' ? styles.waveSpace : styles.waveLetter}
          style={{ animationDelay: `${i * 0.07}s` }}
        >
          {char === ' ' ? '\u00A0' : char}
        </span>
      ))}
    </span>
  );
}
