// ── MessageList Component ──

import { useRef, useEffect, useCallback } from 'react';
import { useSession } from '../../../../hooks/useSession';
import MessageBubble from './MessageBubble';
import WelcomeMessage from './WelcomeMessage';
import LoadMoreButton from './LoadMoreButton';
import Spinner from '../../../../components/Spinner/Spinner';
import styles from './MessageList.module.css';

export default function MessageList({
  isStreaming,
  streamingText,
  afterthoughtStreaming,
  afterthoughtText,
  hasMore,
  onLoadMore,
  onNewChat,
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

  // Scroll to bottom on new messages
  useEffect(() => {
    scrollToBottom();
  }, [chatHistory.length, streamingText, afterthoughtText, scrollToBottom]);

  // Track if user has scrolled up
  const handleScroll = () => {
    const container = containerRef.current;
    if (!container) return;
    const { scrollTop, scrollHeight, clientHeight } = container;
    shouldScroll.current = scrollHeight - scrollTop - clientHeight < 100;
  };

  const isEmpty = chatHistory.length === 0 && !isStreaming;

  return (
    <div
      ref={containerRef}
      className={styles.container}
      onScroll={handleScroll}
    >
      {isEmpty ? (
        <WelcomeMessage
          characterName={character?.char_name}
          onNewChat={onNewChat}
        />
      ) : (
        <>
          {hasMore && <LoadMoreButton onClick={onLoadMore} />}

          {chatHistory.map((msg, index) => (
            <MessageBubble
              key={`${msg.timestamp}-${index}`}
              message={msg.message}
              isUser={msg.is_user}
              characterName={msg.character_name}
              timestamp={msg.timestamp}
              stats={msg.stats}
              memorized={!!msg.memorized}
              characterAvatar={character?.avatar}
              characterAvatarType={character?.avatar_type}
            />
          ))}

          {isStreaming && streamingText && (
            <MessageBubble
              message={streamingText}
              isUser={false}
              characterName={character?.char_name}
              isStreaming
              characterAvatar={character?.avatar}
              characterAvatarType={character?.avatar_type}
            />
          )}

          {afterthoughtStreaming && afterthoughtText && (
            <MessageBubble
              message={afterthoughtText}
              isUser={false}
              characterName={character?.char_name}
              isStreaming
              characterAvatar={character?.avatar}
              characterAvatarType={character?.avatar_type}
            />
          )}

          {(isStreaming || afterthoughtStreaming) && !streamingText && !afterthoughtText && (
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
