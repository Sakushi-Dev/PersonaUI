// ── MoodIndicator Component ──

import styles from './MoodIndicator.module.css';

export default function MoodIndicator({ mood, className }) {
  // Don't render if no mood data
  if (!mood || typeof mood !== 'object') {
    return null;
  }

  const { emoji, dominant, anger, sadness, affection, arousal, trust } = mood;

  if (!emoji) {
    return null;
  }

  // Get the value for the dominant emotion for the tooltip
  const dominantValue = mood[dominant] || 50;
  const tooltipText = `${dominant}: ${dominantValue}/100`;

  return (
    <div 
      className={`${styles.badge} ${className || ''}`}
      title={tooltipText}
      aria-label={tooltipText}
    >
      {emoji}
    </div>
  );
}