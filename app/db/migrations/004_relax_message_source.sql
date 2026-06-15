-- Migration 004: rilassa il CHECK su messages.source (WI-50).
-- Contratto test (father-authored): la route memorizza 'source' in modo OPACO
-- (nessuna validazione del valore). Lo schema 001 aveva
--   CHECK (source IN ('manual','discord_scrape','ai_draft'))
-- che rifiutava valori opachi (es. 'discord','import') → IntegrityError.
-- SQLite non supporta DROP CONSTRAINT via ALTER → ricreazione tabella.
-- Idempotente per fresh-DB (init_schema esegue tutte le migration in ordine):
-- a questo punto 'messages' è creata da 001 (vuota nei test) → copia 0+ righe.

PRAGMA foreign_keys=OFF;

CREATE TABLE IF NOT EXISTS messages_new (
    id                TEXT PRIMARY KEY,
    scene_id          TEXT NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    character_id      TEXT REFERENCES characters(id) ON DELETE SET NULL,
    author_name       TEXT,
    content_original  TEXT,
    content_enhanced  TEXT,
    ts                TEXT NOT NULL,
    source            TEXT NOT NULL DEFAULT 'manual',   -- CHECK rimosso (opaco)
    position_order    INTEGER NOT NULL DEFAULT 0,
    is_summary        INTEGER NOT NULL DEFAULT 0
);

INSERT INTO messages_new (id, scene_id, character_id, author_name,
    content_original, content_enhanced, ts, source, position_order, is_summary)
SELECT id, scene_id, character_id, author_name,
    content_original, content_enhanced, ts, source, position_order, is_summary
FROM messages;

DROP TABLE messages;
ALTER TABLE messages_new RENAME TO messages;

CREATE INDEX IF NOT EXISTS idx_messages_scene_id ON messages(scene_id, position_order);
CREATE INDEX IF NOT EXISTS idx_messages_character ON messages(character_id);
CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(ts);

PRAGMA foreign_keys=ON;
