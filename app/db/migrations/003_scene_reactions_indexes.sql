-- Migration: aggiunta indici per la tabella scene_reactions
-- Descrizione: crea gli indici idx_scene_reactions_message_id e idx_scene_reactions_character_id
-- Data: 2026-06-04

BEGIN;

-- Indice sul campo message_id per velocizzare le ricerche per messaggio
CREATE INDEX IF NOT EXISTS idx_scene_reactions_message_id
    ON scene_reactions (message_id);

-- Indice sul campo character_id per velocizzare le ricerche per personaggio
CREATE INDEX IF NOT EXISTS idx_scene_reactions_character_id
    ON scene_reactions (character_id);

COMMIT;
