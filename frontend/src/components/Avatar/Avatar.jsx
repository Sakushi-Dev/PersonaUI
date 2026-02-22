// ── Avatar Component ──

import styles from './Avatar.module.css';

export default function Avatar({ src, type, name, size = 40, onClick, className = '' }) {
  const letter = name ? name.charAt(0).toUpperCase() : '?';

  // Build avatar URL if a source filename/path is provided
  let avatarSrc = null;
  if (src) {
    if (src.startsWith('http') || src.startsWith('/') || src.startsWith('blob:')) {
      avatarSrc = src;
    } else if (type === 'custom') {
      avatarSrc = `/avatar/costum/${src}`;
    } else {
      // 'gallery', 'default', undefined — all use avatars/ directory
      avatarSrc = `/avatar/${src}`;
    }
  }

  return (
    <div
      className={`${styles.avatar} ${onClick ? styles.clickable : ''} ${className}`}
      style={{ width: size, height: size, fontSize: size * 0.4 }}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {avatarSrc ? (
        <img
          src={avatarSrc}
          alt={name || 'Avatar'}
          className={styles.image}
          onError={(e) => {
            e.target.style.display = 'none';
            e.target.nextSibling.style.display = 'flex';
          }}
        />
      ) : null}
      <span
        className={styles.fallback}
        style={{ display: avatarSrc ? 'none' : 'flex' }}
      >
        {letter}
      </span>
    </div>
  );
}
