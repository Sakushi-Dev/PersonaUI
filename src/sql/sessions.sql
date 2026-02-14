-- =============================================
-- Session-Management Abfragen
-- =============================================

-- name: create_session
-- Erstellt eine neue Chat-Session
INSERT INTO chat_sessions (title, persona_id)
VALUES (?, ?);

-- name: get_all_sessions
-- Holt alle Sessions, sortiert nach Aktualisierung
SELECT id, title, created_at, updated_at, persona_id
FROM chat_sessions
ORDER BY updated_at DESC;

-- name: get_session_by_id
-- Holt eine spezifische Session
SELECT id, title, created_at, updated_at, persona_id
FROM chat_sessions
WHERE id = ?;

-- name: get_session_persona_id
-- Holt die Persona-ID einer Session
SELECT persona_id FROM chat_sessions WHERE id = ?;

-- name: update_session_title
-- Aktualisiert den Titel einer Session
UPDATE chat_sessions 
SET title = ?, updated_at = CURRENT_TIMESTAMP
WHERE id = ?;

-- name: delete_session
-- Löscht eine Session (Nachrichten werden per CASCADE gelöscht)
DELETE FROM chat_sessions WHERE id = ?;

-- name: get_current_session_id
-- Holt die neueste Session-ID
SELECT id FROM chat_sessions ORDER BY updated_at DESC LIMIT 1;

-- name: check_session_exists
-- Prüft ob eine Session existiert
SELECT id FROM chat_sessions WHERE id = ?;

-- name: get_session_count_summary
-- Zusammenfassung: Sessions pro Persona
SELECT COUNT(*) as session_count, MAX(updated_at) as last_updated
FROM chat_sessions;
