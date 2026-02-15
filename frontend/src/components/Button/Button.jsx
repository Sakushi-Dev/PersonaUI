// ── Button Component ──

import styles from './Button.module.css';

export default function Button({
  variant = 'primary',
  size = 'md',
  hidden = false,
  disabled = false,
  className = '',
  onClick,
  children,
  type = 'button',
  ...props
}) {
  if (hidden) return null;

  return (
    <button
      type={type}
      className={`${styles.button} ${styles[variant]} ${styles[size]} ${className}`}
      disabled={disabled}
      onClick={onClick}
      {...props}
    >
      {children}
    </button>
  );
}
