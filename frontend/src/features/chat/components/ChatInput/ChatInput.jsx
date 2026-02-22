// ── ChatInput ──
// Textarea with auto-resize + send button + slash-command support

import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import styles from './ChatInput.module.css';
import SlashCommandMenu from './SlashCommandMenu';
import { getCommands, findCommand } from '../../slashCommands';

export default function ChatInput({ onSend, disabled, isStreaming, onCancel, placeholder, sessionId }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  // ── Slash-command state ──
  const [cmdMenuOpen, setCmdMenuOpen] = useState(false);
  const [cmdSelectedIdx, setCmdSelectedIdx] = useState(0);

  // Derive the query typed after "/"
  const cmdQuery = useMemo(() => {
    if (!text.startsWith('/')) return null;
    // everything after the leading "/" up to first space (or end)
    const raw = text.slice(1).split(' ')[0];
    return raw;
  }, [text]);

  // Filtered command list
  const filteredCmds = useMemo(() => {
    if (cmdQuery === null) return [];
    return getCommands(cmdQuery);
  }, [cmdQuery]);

  // Open / close the menu reactively
  useEffect(() => {
    if (cmdQuery !== null && filteredCmds.length > 0) {
      setCmdMenuOpen(true);
      setCmdSelectedIdx(0);
    } else {
      setCmdMenuOpen(false);
    }
  }, [cmdQuery, filteredCmds.length]);

  // ── Auto-resize textarea ──
  const resize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = '42px';
    el.style.height = Math.min(el.scrollHeight, 150) + 'px';
  }, []);

  useEffect(() => {
    resize();
  }, [text, resize]);

  // ── Refocus textarea when streaming ends ──
  const wasStreaming = useRef(false);
  useEffect(() => {
    if (isStreaming) {
      wasStreaming.current = true;
    } else if (wasStreaming.current) {
      wasStreaming.current = false;
      // Refocus after SSE completes so user can type immediately
      textareaRef.current?.focus();
    }
  }, [isStreaming]);

  // ── Execute a slash command ──
  const executeCommand = useCallback((cmd) => {
    // args = everything after "/commandName "
    const argsStr = text.slice(1 + cmd.name.length).trim();
    console.log(`[ChatInput] executing /${cmd.name}`, argsStr ? `args: ${argsStr}` : '(no args)');
    cmd.execute({ args: argsStr, sessionId });
    setText('');
    setCmdMenuOpen(false);
    if (textareaRef.current) textareaRef.current.style.height = '42px';
  }, [text, sessionId]);

  // ── Select a command from the menu (click or Enter) ──
  const selectCommand = useCallback((cmd) => {
    // If the user just typed "/" or a partial match, fill in the command name and execute
    executeCommand(cmd);
  }, [executeCommand]);

  // ── Send normal message ──
  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    console.log('[ChatInput] handleSend called, text:', trimmed, 'disabled:', disabled, 'isStreaming:', isStreaming);
    if (!trimmed || disabled || isStreaming) return;

    // Check if it's a complete slash command
    if (trimmed.startsWith('/')) {
      const parts = trimmed.slice(1).split(' ');
      const cmd = findCommand(parts[0]);
      if (cmd) {
        executeCommand(cmd);
        return;
      }
    }

    onSend(trimmed);
    setText('');

    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = '42px';
    }
  }, [text, disabled, isStreaming, onSend, executeCommand]);

  // ── Keyboard handling ──
  const handleKeyDown = useCallback((e) => {
    // When command menu is open, arrow keys & Enter navigate/select
    if (cmdMenuOpen && filteredCmds.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setCmdSelectedIdx((prev) => (prev + 1) % filteredCmds.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setCmdSelectedIdx((prev) => (prev - 1 + filteredCmds.length) % filteredCmds.length);
        return;
      }
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        selectCommand(filteredCmds[cmdSelectedIdx]);
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setCmdMenuOpen(false);
        return;
      }
      if (e.key === 'Tab') {
        // Tab-complete: fill the command name into the input
        e.preventDefault();
        const cmd = filteredCmds[cmdSelectedIdx];
        setText('/' + cmd.name + ' ');
        return;
      }
    }

    // Normal Enter → send
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (isStreaming) return;
      handleSend();
    }
  }, [cmdMenuOpen, filteredCmds, cmdSelectedIdx, handleSend, isStreaming, selectCommand]);

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
        <SlashCommandMenu
          commands={filteredCmds}
          selectedIndex={cmdSelectedIdx}
          onSelect={selectCommand}
          onHover={setCmdSelectedIdx}
          visible={cmdMenuOpen}
        />
        <textarea
          ref={textareaRef}
          className={`${styles.input} ${isStreaming ? styles.inputStreaming : ''}`}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isStreaming ? 'Antwort wird generiert...' : (placeholder || 'Deine Nachricht...')}
          rows={1}
          disabled={disabled}
        />
        <button
          className={`${styles.sendBtn} ${isStreaming ? styles.cancel : ''}`}
          onClick={handleClick}
          disabled={disabled}
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
