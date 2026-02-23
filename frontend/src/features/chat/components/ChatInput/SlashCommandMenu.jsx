// ── SlashCommandMenu ──
// Floating popup above the chat input showing matching slash commands.

import { useEffect, useRef } from 'react';
import { useLanguage } from '../../../../hooks/useLanguage';
import styles from './SlashCommandMenu.module.css';

export default function SlashCommandMenu({
  commands,       // filtered list of {name, description}
  selectedIndex,  // currently highlighted index
  onSelect,       // (cmd) => void  – called when user picks a command
  onHover,        // (index) => void – called when mouse enters an item
  visible,        // boolean
}) {
  const listRef = useRef(null);
  const { t } = useLanguage();
  const sc = t('slashCommands');

  // Keep selected item scrolled into view
  useEffect(() => {
    if (!listRef.current) return;
    const active = listRef.current.querySelector(`.${styles.active}`);
    if (active) {
      active.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  if (!visible || commands.length === 0) return null;

  return (
    <div className={styles.menu}>
      <ul ref={listRef} className={styles.list}>
        {commands.map((cmd, i) => (
          <li
            key={cmd.name}
            className={`${styles.item} ${i === selectedIndex ? styles.active : ''}`}
            onMouseDown={(e) => {
              e.preventDefault(); // keep textarea focus
              onSelect(cmd);
            }}
            onMouseEnter={() => onHover?.(i)}
          >
            <span className={styles.commandName}>/{cmd.name}</span>
            <span className={styles.commandDesc}>{sc[cmd.name] || cmd.description}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
