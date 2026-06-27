-- Migration 006: dedup scene_reactions e aggiunge UNIQUE su (message_id, character_id, emoji)
-- Elimina duplicati tenendo la riga con rowid minimo (inserita per prima)
DELETE FROM scene_reactions
WHERE rowid NOT IN (
    SELECT MIN(rowid)
    FROM scene_reactions
    GROUP BY message_id, character_id, emoji
);

CREATE UNIQUE INDEX IF NOT EXISTS uix_scene_reactions_msg_char_emoji
    ON scene_reactions(message_id, character_id, emoji);
