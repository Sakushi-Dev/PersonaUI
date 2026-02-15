// ── ChipSelector Component ──

import styles from './ChipSelector.module.css';

export default function ChipSelector({ options = [], value, onChange, multiple = false, label }) {
  const selected = multiple ? (Array.isArray(value) ? value : []) : value;

  const handleClick = (optionValue) => {
    if (multiple) {
      const arr = Array.isArray(selected) ? selected : [];
      const newVal = arr.includes(optionValue)
        ? arr.filter((v) => v !== optionValue)
        : [...arr, optionValue];
      onChange?.(newVal);
    } else {
      onChange?.(optionValue);
    }
  };

  const isSelected = (optionValue) => {
    if (multiple) return Array.isArray(selected) && selected.includes(optionValue);
    return selected === optionValue;
  };

  return (
    <div className={styles.wrapper}>
      {label && <label className={styles.label}>{label}</label>}
      <div className={styles.chips}>
        {options.map((option) => {
          const val = typeof option === 'string' ? option : option.value;
          const display = typeof option === 'string' ? option : option.label;

          return (
            <button
              key={val}
              type="button"
              className={`${styles.chip} ${isSelected(val) ? styles.chipActive : ''}`}
              onClick={() => handleClick(val)}
            >
              {display}
            </button>
          );
        })}
      </div>
    </div>
  );
}
