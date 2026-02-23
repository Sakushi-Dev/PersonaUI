-- =============================================
-- Chat-Nachrichten Abfragen
-- =============================================

-- name: get_latest_session_id
-- Holt die neueste Session-ID
SELECT id FROM chat_sessions ORDER BY updated_at DESC LIMIT 1;

-- name: get_chat_history
-- Holt Chat-Nachrichten mit Pagination (neueste zuerst, nach ID sortiert)
SELECT id, message, is_user, timestamp, character_name
FROM chat_messages 
WHERE session_id = ?
ORDER BY id DESC
LIMIT ? OFFSET ?;

-- name: get_message_count
-- Zählt alle Nachrichten einer Session
SELECT COUNT(*)
FROM chat_messages 
WHERE session_id = ?;

-- name: get_conversation_context
-- Holt die letzten N Nachrichten für den API-Kontext (nach ID sortiert)
SELECT message, is_user, timestamp
FROM chat_messages 
WHERE session_id = ?
ORDER BY id DESC
LIMIT ?;

-- name: insert_message
-- Speichert eine neue Nachricht
INSERT INTO chat_messages (session_id, message, is_user, character_name)
VALUES (?, ?, ?, ?);

-- name: update_session_timestamp
-- Aktualisiert den Zeitstempel einer Session
UPDATE chat_sessions 
SET updated_at = CURRENT_TIMESTAMP 
WHERE id = ?;

-- name: delete_all_messages
-- Löscht alle Nachrichten (für clear_chat_history)
DELETE FROM chat_messages;

-- name: delete_all_sessions
-- Löscht alle Sessions (für clear_chat_history)
DELETE FROM chat_sessions;

-- name: get_total_message_count
-- Gesamtanzahl aller Nachrichten über alle Sessions
SELECT COUNT(*) FROM chat_messages;

-- name: get_max_message_id
-- Höchste Nachrichten-ID einer Session
SELECT MAX(id) FROM chat_messages WHERE session_id = ?;

-- name: count_all_user_messages
-- Zählt alle User-Nachrichten einer Session
SELECT COUNT(*) FROM chat_messages 
WHERE session_id = ? AND is_user = 1;

-- name: get_all_messages_count
-- Zählt alle Nachrichten einer Session
SELECT COUNT(*) FROM chat_messages WHERE session_id = ?;


-- name: get_all_messages_limited
-- Holt alle Nachrichten einer Session (neueste zuerst, nach ID sortiert)
SELECT id, message, is_user, timestamp, character_name
FROM chat_messages 
WHERE session_id = ?
ORDER BY id DESC
LIMIT ?;

-- name: get_last_message
-- Holt die letzte Nachricht einer Session
SELECT id, message, is_user, timestamp, character_name
FROM chat_messages WHERE session_id = ? ORDER BY id DESC LIMIT 1;

-- name: delete_last_message
-- Löscht die letzte Nachricht einer Session
DELETE FROM chat_messages WHERE id = (
    SELECT id FROM chat_messages WHERE session_id = ? ORDER BY id DESC LIMIT 1
);

-- name: update_last_message_text
-- Aktualisiert den Text der letzten Nachricht einer Session
UPDATE chat_messages SET message = ? WHERE id = (
    SELECT id FROM chat_messages WHERE session_id = ? ORDER BY id DESC LIMIT 1
);

-- name: upsert_db_info
-- Setzt einen Wert in der DB-Info Tabelle
INSERT OR REPLACE INTO db_info (key, value) VALUES (?, ?);
