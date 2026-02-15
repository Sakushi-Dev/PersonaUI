// ── MessageBubble Component ──

import { useContext, useState } from 'react';
import { UserContext } from '../../../../context/UserContext';
import Avatar from '../../../../components/Avatar/Avatar';
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
}) {
  const { profile } = useContext(UserContext);
  const [showStats, setShowStats] = useState(false);

  const avatarSrc = isUser ? profile?.user_avatar : characterAvatar;
  const avatarType = isUser ? profile?.user_avatar_type : characterAvatarType;
  const avatarName = isUser ? (profile?.user_name || 'Du') : characterName;

  const formattedMessage = formatMessage(message);

  const bubbleClasses = [
    styles.messageBubble,
    isStreaming ? styles.streaming : '',
    memorized ? styles.memorized : '',
  ].filter(Boolean).join(' ');

  return (
    <div className={`${styles.message} ${isUser ? styles.userMessage : styles.botMessage}`}>
      <div className={styles.messageAvatar}>
        <Avatar
          src={avatarSrc}
          type={avatarType}
          name={avatarName}
          size={32}
        />
      </div>
      <div className={styles.messageContent}>
        <div className={styles.messageSender}>
          {isUser ? (profile?.user_name || 'Du') : characterName}
        </div>
        <div
          className={bubbleClasses}
          dangerouslySetInnerHTML={{ __html: formattedMessage }}
        />
        {isStreaming && <span className={styles.streamingCursor}>▌</span>}
        {!isUser && !isStreaming && stats && (
          <button
            className={styles.promptInfoBtn}
            onClick={() => setShowStats(true)}
            title="Prompt Info"
          >
            ℹ️
          </button>
        )}
        {timestamp && !isStreaming && (
          <div className={styles.messageTime}>
            {formatTimestamp(timestamp)}
          </div>
        )}
      </div>

      <PromptInfoOverlay
        open={showStats}
        onClose={() => setShowStats(false)}
        stats={stats}
      />
    </div>
  );
}
