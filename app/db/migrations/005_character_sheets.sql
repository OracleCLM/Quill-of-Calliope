CREATE TABLE IF NOT EXISTS character_sheets (
    id TEXT PRIMARY KEY,
    character_name TEXT NOT NULL,
    character_id TEXT REFERENCES characters(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    ts TEXT,
    position_order INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_char_sheets_name ON character_sheets(character_name);
