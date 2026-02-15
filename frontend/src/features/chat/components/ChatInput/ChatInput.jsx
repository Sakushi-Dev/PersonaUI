// ── ChatInput ──
// Textarea with auto-resize + send button

import { useState, useRef, useCallback, useEffect } from 'react';
import styles from './ChatInput.module.css';

export default function ChatInput({ onSend, disabled, isStreaming, onCancel, placeholder }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize textarea
  const resize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = '42px';
    el.style.height = Math.min(el.scrollHeight, 150) + 'px';
  }, []);

  useEffect(() => {
    resize();
  }, [text, resize]);

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    console.log('[ChatInput] handleSend called, text:', trimmed, 'disabled:', disabled);
    if (!trimmed || disabled) return;

    onSend(trimmed);
    setText('');

    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = '42px';
    }
  }, [text, disabled, onSend]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (isStreaming) return;
      handleSend();
    }
  }, [handleSend, isStreaming]);

  const handleClick = useCallback(() => {
    if (isStreaming) {
      onCancel?.();
    } else {
      handleSend();
    }
  }, [isStreaming, onCancel, handleSend]);

  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        <textarea
          ref={textareaRef}
          className={styles.input}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || 'Deine Nachricht...'}
          rows={1}
          disabled={disabled}
        />
        <button
          className={`${styles.sendBtn} ${isStreaming ? styles.cancel : ''}`}
          onClick={handleClick}
          disabled={disabled && !isStreaming}
          title={isStreaming ? 'Abbrechen' : 'Nachricht senden'}
          type="button"
        >
          {isStreaming ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M2,2 L22,12 L2,22 L7,12 Z" fill="currentColor" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}
