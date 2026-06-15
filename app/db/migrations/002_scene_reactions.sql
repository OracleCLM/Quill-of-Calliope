-- Migration: 002_scene_reactions.sql
-- Crea la tabella scene_reactions per gestire le reazioni dei personaggi ai messaggi della scena.

CREATE TABLE IF NOT EXISTS scene_reactions (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    emoji TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
