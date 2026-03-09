// ── MessageList Component ──
// Streaming messages live inside chatHistory (marked with _streaming: true).
// This means the same React element is used for both streaming and final state,
// preventing bubble recreation when the stream completes.

import { useRef, useEffect } from 'react';
import { useSession } from '../../../../hooks/useSession';
import MessageBubble from './MessageBubble';
import LoadMoreButton from './LoadMoreButton';
import Spinner from '../../../../components/Spinner/Spinner';
import styles from './MessageList.module.css';

export default function MessageList({
  isStreaming,
  afterthoughtStreaming,
  hasMore,
  onLoadMore,
  onDeleteLast,
  onEditLast,
  onRegenerateLast,
  onResendLast,
}) {
  const { chatHistory, character } = useSession();
  const containerRef = useRef(null);
  const prevLengthRef = useRef(chatHistory.length);

  // Scroll bot bubble top to center of viewport
  const scrollToBotBubble = (container, idx) => {
    const attempt = (count = 0) => {
      const el = container.querySelector(`[data-message-index="${idx}"]`);
      if (el && el.offsetHeight > 0) {
        const containerRect = container.getBoundingClientRect();
        const elRect = el.getBoundingClientRect();
        const relativeTop = elRect.top - containerRect.top;
        const center = container.clientHeight / 2;
        container.scrollTo({ top: container.scrollTop + relativeTop - center, behavior: 'smooth' });
        return;
      }
      if (count < 20) setTimeout(() => attempt(count + 1), 100);
    };
    setTimeout(() => attempt(), 80);
  };

  // Scroll to new bubble when message count increases
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const prevLen = prevLengthRef.current;
    if (chatHistory.length <= prevLen) {
      prevLengthRef.current = chatHistory.length;
      return;
    }
    prevLengthRef.current = chatHistory.length;

    // Check if any of the newly added messages is a user message
    const newMessages = chatHistory.slice(prevLen);
    const hasNewUserMsg = newMessages.some(m => m.is_user);
    const hasNewBotMsg = newMessages.some(m => !m.is_user);
    const botIdx = chatHistory.length - 1;

    if (hasNewUserMsg) {
      // User sent a message — scroll to bottom once content renders
      const prevScrollHeight = container.scrollHeight;
      const attemptUser = (count = 0) => {
        if (container.scrollHeight > prevScrollHeight) {
          container.scrollTop = container.scrollHeight;

          // If bot bubble also came with user msg, scroll to it once it renders
          if (hasNewBotMsg) {
            scrollToBotBubble(container, botIdx);
          }
          return;
        }
        if (count < 30) setTimeout(() => attemptUser(count + 1), 50);
      };
      attemptUser();
      return;
    }

    // Bot-only bubble (e.g. afterthought)
    scrollToBotBubble(container, botIdx);
  }, [chatHistory.length]);

  return (
    <div
      ref={containerRef}
      className={styles.container}
    >
      {chatHistory.length === 0 && !isStreaming ? null : (
        <>
          {hasMore && <LoadMoreButton onClick={onLoadMore} />}

          {chatHistory.map((msg, index) => {
            const isLast = index === chatHistory.length - 1;
            const showActions = isLast && !msg._streaming && !isStreaming && !afterthoughtStreaming;

            return (
              <div 
                key={msg._id || `${msg.timestamp}-${index}`}
                data-message-index={index}
              >
                <MessageBubble
                  message={msg.message}
                  isUser={msg.is_user}
                  characterName={msg.character_name}
                  timestamp={msg.timestamp}
                  stats={msg.stats}
                  isStreaming={!!msg._streaming}
                  characterAvatar={character?.avatar}
                  characterAvatarType={character?.avatar_type}
                  showActions={showActions}
                  onDelete={onDeleteLast}
                  onEdit={onEditLast}
                  onRegenerate={onRegenerateLast}
                  onResend={onResendLast}
                />
              </div>
            );
          })}

          {/* Afterthought decision phase spinner (before streaming placeholder is added) */}
          {afterthoughtStreaming && !chatHistory.some(m => m._streaming) && (
            <div className={styles.thinking}>
              <Spinner />
            </div>
          )}
        </>
      )}
    </div>
  );
}
