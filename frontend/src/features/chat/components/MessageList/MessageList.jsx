// ── MessageList Component ──
// Streaming messages live inside chatHistory (marked with _streaming: true).
// This means the same React element is used for both streaming and final state,
// preventing bubble recreation when the stream completes.

import { useRef, useEffect, useCallback } from 'react';
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
  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);
  const shouldScroll = useRef(true);

  const scrollToBottom = useCallback((smooth = true) => {
    if (messagesEndRef.current && shouldScroll.current) {
      messagesEndRef.current.scrollIntoView({
        behavior: smooth ? 'smooth' : 'instant',
      });
    }
  }, []);

  // Scroll to bottom on new messages or streaming content updates
  const lastMessage = chatHistory[chatHistory.length - 1];
  useEffect(() => {
    scrollToBottom();
  }, [chatHistory.length, lastMessage?.message, scrollToBottom]);

  // Track if user has scrolled up
  const handleScroll = () => {
    const container = containerRef.current;
    if (!container) return;
    const { scrollTop, scrollHeight, clientHeight } = container;
    shouldScroll.current = scrollHeight - scrollTop - clientHeight < 100;
  };

  return (
    <div
      ref={containerRef}
      className={styles.container}
      onScroll={handleScroll}
    >
      {chatHistory.length === 0 && !isStreaming ? null : (
        <>
          {hasMore && <LoadMoreButton onClick={onLoadMore} />}

          {chatHistory.map((msg, index) => {
            // Streaming placeholder with no text yet → show spinner
            if (msg._streaming && !msg.message) {
              return (
                <div key={`${msg.timestamp}-${index}`} className={styles.thinking}>
                  <Spinner />
                </div>
              );
            }

            const isLast = index === chatHistory.length - 1;
            const showActions = isLast && !msg._streaming && !isStreaming && !afterthoughtStreaming;

            return (
              <MessageBubble
                key={`${msg.timestamp}-${index}`}
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

      <div ref={messagesEndRef} />
    </div>
  );
}
