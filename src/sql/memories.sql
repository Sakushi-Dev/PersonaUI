-- =============================================
-- Memory-Management Abfragen
-- =============================================

-- name: insert_memory
-- Speichert eine neue Memory-Zusammenfassung
INSERT INTO memories (session_id, persona_id, content, start_message_id, end_message_id)
VALUES (?, ?, ?, ?, ?);

-- name: get_all_memories
-- Holt alle Memories (aktive und inaktive)
SELECT id, session_id, persona_id, content, created_at, is_active
FROM memories
ORDER BY created_at DESC;

-- name: get_active_memories
-- Holt nur aktive Memories
SELECT id, session_id, persona_id, content, created_at, is_active
FROM memories
WHERE is_active = 1
ORDER BY created_at DESC;

-- name: update_memory_content
-- Aktualisiert den Inhalt einer Memory
UPDATE memories 
SET content = ?
WHERE id = ?;

-- name: get_memory_session_id
-- Holt die Session-ID einer Memory (vor dem Löschen)
SELECT session_id FROM memories WHERE id = ?;

-- name: delete_memory
-- Löscht eine Memory
DELETE FROM memories WHERE id = ?;

-- name: get_max_end_message_id
-- Holt die höchste end_message_id für eine Session (Memory-Marker Neuberechnung)
SELECT MAX(end_message_id) FROM memories 
WHERE session_id = ? AND end_message_id IS NOT NULL;

-- name: update_session_memory_marker
-- Aktualisiert den Memory-Marker einer Session
UPDATE chat_sessions 
SET last_memory_message_id = ?
WHERE id = ?;

-- name: toggle_memory_status
-- Schaltet den Aktiv-Status einer Memory um
UPDATE memories 
SET is_active = NOT is_active
WHERE id = ?;

-- name: set_last_memory_message_id
-- Setzt den Memory-Marker für eine Session
UPDATE chat_sessions 
SET last_memory_message_id = ?
WHERE id = ?;

-- name: get_last_memory_message_id
-- Holt den Memory-Marker einer Session
SELECT last_memory_message_id FROM chat_sessions WHERE id = ?;

-- name: upsert_db_info
-- Setzt einen Wert in der DB-Info Tabelle
INSERT OR REPLACE INTO db_info (key, value) VALUES (?, ?);
