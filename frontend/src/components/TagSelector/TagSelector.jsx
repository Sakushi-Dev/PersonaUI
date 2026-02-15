// ── TagSelector Component ──

import styles from './TagSelector.module.css';
import TagButton from './TagButton';

export default function TagSelector({ label, options = [], selected = [], onToggle, maxCount }) {
  return (
    <div className={styles.wrapper}>
      {label && <label className={styles.label}>{label}</label>}
      <div className={styles.tags}>
        {options.map((option) => {
          const value = typeof option === 'string' ? option : option.value;
          const display = typeof option === 'string' ? option : option.label;
          const isSelected = selected.includes(value);
          const isDisabled = maxCount && selected.length >= maxCount && !isSelected;

          return (
            <TagButton
              key={value}
              label={display}
              selected={isSelected}
              disabled={isDisabled}
              onClick={() => onToggle?.(value)}
            />
          );
        })}
      </div>
      {maxCount && (
        <span className={styles.counter}>{selected.length}/{maxCount}</span>
      )}
    </div>
  );
}
