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
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_memory_message_id INTEGER DEFAULT NULL
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

-- Memory-Tabelle für Erinnerungen
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    persona_id TEXT DEFAULT 'default',
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    start_message_id INTEGER DEFAULT NULL,
    end_message_id INTEGER DEFAULT NULL
);

-- Indizes für Memory-Abfragen
CREATE INDEX IF NOT EXISTS idx_memory_session 
ON memories(session_id);

CREATE INDEX IF NOT EXISTS idx_memory_active 
ON memories(is_active);

CREATE INDEX IF NOT EXISTS idx_memory_persona 
ON memories(persona_id);
