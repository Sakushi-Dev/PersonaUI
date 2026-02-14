-- =============================================
-- PersonaUI Database Migrations
-- Spalten-Erweiterungen für bestehende Tabellen
-- =============================================

-- name: check_last_memory_message_id
-- Prüft ob die Spalte last_memory_message_id existiert
SELECT last_memory_message_id FROM chat_sessions LIMIT 1;

-- name: add_last_memory_message_id
-- Migration: Memory-Marker Spalte zu Sessions hinzufügen
ALTER TABLE chat_sessions 
ADD COLUMN last_memory_message_id INTEGER DEFAULT NULL;

-- name: check_memory_message_ranges
-- Prüft ob die Spalten start_message_id/end_message_id existieren
SELECT start_message_id FROM memories LIMIT 1;

-- name: add_start_message_id
-- Migration: Start-Message-ID für Memory-Ranges
ALTER TABLE memories 
ADD COLUMN start_message_id INTEGER DEFAULT NULL;

-- name: add_end_message_id
-- Migration: End-Message-ID für Memory-Ranges
ALTER TABLE memories 
ADD COLUMN end_message_id INTEGER DEFAULT NULL;
