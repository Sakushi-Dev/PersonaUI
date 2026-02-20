-- =============================================
-- PersonaUI Database Schema
-- Per-Persona SQLite Datenbank-Schema
-- =============================================

-- DB-Info Tabelle (identifiziert die Persona)
CREATE TABLE IF NOT EXISTS db_info (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Chat-Sitzungen Tabelle
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT DEFAULT 'Neue Konversation',
    persona_id TEXT DEFAULT 'default',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Chat-Nachrichten Tabelle
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    is_user BOOLEAN NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    character_name TEXT DEFAULT 'Assistant',
    FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
);

-- Index für schnellere Nachrichten-Abfragen
CREATE INDEX IF NOT EXISTS idx_session_id 
ON chat_messages(session_id);
