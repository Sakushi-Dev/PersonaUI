-- Mood System SQL Queries
-- Used by MoodService for database operations

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

-- name: get_state
SELECT anger, sadness, affection, arousal, trust, last_updated
FROM mood_state WHERE persona_id = ?;

-- name: init_state
INSERT OR IGNORE INTO mood_state (persona_id) VALUES (?);

-- name: update_state
INSERT OR REPLACE INTO mood_state (persona_id, anger, sadness, affection, arousal, trust, last_updated)
VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);

-- name: insert_history
INSERT INTO mood_history (persona_id, anger, sadness, affection, arousal, trust, trigger_text)
VALUES (?, ?, ?, ?, ?, ?, ?);

-- name: get_history
SELECT anger, sadness, affection, arousal, trust, trigger_text, timestamp
FROM mood_history WHERE persona_id = ? ORDER BY timestamp DESC LIMIT ?;