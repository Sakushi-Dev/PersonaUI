// ── MessageBubble Component ──

import { useContext, useState, useRef, useEffect } from 'react';
import { UserContext } from '../../../../context/UserContext';
import Avatar from '../../../../components/Avatar/Avatar';
import ConfirmDialog from '../../../../components/ConfirmDialog/ConfirmDialog';
import PromptInfoOverlay from './PromptInfoOverlay';
import { formatMessage } from '../../../../utils/formatMessage';
import { formatTimestamp } from '../../../../utils/formatTime';
import styles from './MessageList.module.css';

export default function MessageBubble({
  message,
  isUser,
  characterName,
  timestamp,
  stats,
  isStreaming = false,
  characterAvatar,
  characterAvatarType,
  memorized = false,
  showActions = false,
  onDelete,
  onEdit,
  onRegenerate,
  onResend,
}) {
  const { profile } = useContext(UserContext);
  const [showStats, setShowStats] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState('');
  const [confirmAction, setConfirmAction] = useState(null);
  const editRef = useRef(null);

  const avatarSrc = isUser ? profile?.user_avatar : characterAvatar;
  const avatarType = isUser ? profile?.user_avatar_type : characterAvatarType;
  const avatarName = isUser ? (profile?.user_name || 'Du') : characterName;

  // Streaming text is already formatted by the hook — skip double-formatting
  const formattedMessage = isStreaming ? message : formatMessage(message);

  const bubbleClasses = [
    styles.messageBubble,
    isUser ? styles.userBubble : styles.botBubble,
    isStreaming ? styles.streaming : '',
    memorized ? styles.memorized : '',
  ].filter(Boolean).join(' ');

  // Auto-focus & auto-resize textarea when entering edit mode
  useEffect(() => {
    if (isEditing && editRef.current) {
      editRef.current.focus();
      editRef.current.style.height = 'auto';
      editRef.current.style.height = editRef.current.scrollHeight + 'px';
    }
  }, [isEditing]);

  const handleStartEdit = () => {
    setEditText(message);
    setIsEditing(true);
  };

  const handleSaveEdit = () => {
    const trimmed = editText.trim();
    if (trimmed && trimmed !== message) {
      onEdit?.(trimmed);
    }
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
  };

  const handleEditKeyDown = (e) => {
    if (e.key === 'Escape') {
      handleCancelEdit();
    } else if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSaveEdit();
    }
  };

  return (
    <div className={`${styles.message} ${isUser ? styles.userMessage : styles.botMessage}`}>
      <div className={styles.messageAvatar}>
        <Avatar
          src={avatarSrc}
          type={avatarType}
          name={avatarName}
          size={50}
        />
      </div>
      <div className={styles.messageContent}>
        <div className={styles.messageSenderRow}>
          <div className={styles.messageSender}>
            {isUser ? (profile?.user_name || 'Du') : characterName}
          </div>
          {!isUser && !isStreaming && stats && (
            <button
              className={styles.promptInfoBtn}
              onClick={() => setShowStats(true)}
              title="Token Info"
            >
              Token Info
            </button>
          )}
        </div>
        <div className={bubbleClasses}>
          {isEditing ? (
            <div className={styles.editContainer}>
              <textarea
                ref={editRef}
                className={styles.editTextarea}
                value={editText}
                onChange={(e) => {
                  setEditText(e.target.value);
                  e.target.style.height = 'auto';
                  e.target.style.height = e.target.scrollHeight + 'px';
                }}
                onKeyDown={handleEditKeyDown}
                rows={2}
              />
              <div className={styles.editButtons}>
                <button className={styles.editSaveBtn} onClick={handleSaveEdit}>
                  Speichern
                </button>
                <button className={styles.editCancelBtn} onClick={handleCancelEdit}>
                  Abbrechen
                </button>
              </div>
            </div>
          ) : (
            <>
              <span dangerouslySetInnerHTML={{ __html: formattedMessage }} />
              {isStreaming && <span className={styles.streamingCursor}>▌</span>}
              {timestamp && !isStreaming && (
                <div className={styles.messageTime}>
                  {formatTimestamp(timestamp)}
                </div>
              )}
            </>
          )}
        </div>

        {/* Action bar for last message */}
        {showActions && !isEditing && (
          <div className={`${styles.messageActions} ${isUser ? styles.messageActionsUser : ''}`}>
            <button
              className={styles.actionBtn}
              onClick={() => setConfirmAction({ type: 'delete', message: 'Nachricht wirklich löschen?', handler: onDelete })}
              title="Nachricht löschen"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
              <span>Löschen</span>
            </button>
            <button
              className={styles.actionBtn}
              onClick={handleStartEdit}
              title="Nachricht bearbeiten"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
              <span>Bearbeiten</span>
            </button>
            {!isUser && (
              <button
                className={styles.actionBtn}
                onClick={() => setConfirmAction({ type: 'regenerate', message: 'Antwort wirklich neu generieren?', handler: onRegenerate })}
                title="Antwort neu generieren"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
                </svg>
                <span>Neu generieren</span>
              </button>
            )}
            {isUser && (
              <button
                className={styles.actionBtn}
                onClick={onResend}
                title="Nachricht erneut senden"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
                <span>Erneut senden</span>
              </button>
            )}
          </div>
        )}
      </div>

      <PromptInfoOverlay
        open={showStats}
        onClose={() => setShowStats(false)}
        stats={stats}
      />

      <ConfirmDialog
        open={!!confirmAction}
        message={confirmAction?.message || ''}
        onConfirm={() => { confirmAction?.handler?.(); setConfirmAction(null); }}
        onCancel={() => setConfirmAction(null)}
      />
    </div>
  );
}
