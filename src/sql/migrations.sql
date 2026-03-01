-- =============================================
-- PersonaUI Database Migrations
-- Spalten-Erweiterungen für bestehende Tabellen
-- =============================================

-- name: check_mood_state
SELECT 1 FROM mood_state LIMIT 1;

-- name: create_mood_state
CREATE TABLE IF NOT EXISTS mood_state (
    persona_id TEXT PRIMARY KEY,
    anger INTEGER DEFAULT 50,
    sadness INTEGER DEFAULT 50,
    affection INTEGER DEFAULT 50,
    arousal INTEGER DEFAULT 50,
    trust INTEGER DEFAULT 50,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- name: create_mood_history
CREATE TABLE IF NOT EXISTS mood_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id TEXT NOT NULL,
    anger INTEGER NOT NULL,
    sadness INTEGER NOT NULL,
    affection INTEGER NOT NULL,
    arousal INTEGER NOT NULL,
    trust INTEGER NOT NULL,
    trigger_text TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
