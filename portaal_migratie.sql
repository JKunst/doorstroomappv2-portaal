-- ============================================================================
-- Portaal migratie: Doorstroomanalyse-tegel toevoegen
-- Op de VPS draaien tegen schoolapp.db (of bv. via `sqlite3 schoolapp.db < ...`)
-- ============================================================================

-- 1. Nieuwe kolom: tegel is standaard zichtbaar voor alle docenten
--    (idempotent dankzij sqlite3 IF NOT EXISTS, maar SQLite is daar zuinig in;
--     als de kolom al bestaat krijg je een foutmelding en doe je niets)
ALTER TABLE tegels ADD COLUMN is_docent_default INTEGER NOT NULL DEFAULT 0;

-- 2. Doorstroomanalyse-tegel toevoegen
INSERT INTO tegels (naam, url, kleur, icoon, is_docent_default)
VALUES (
    'Doorstroomanalyse',
    'https://doorstroom.bovenbouwsucces.nl/',  -- pas aan naar de echte URL
    '#0D5259',                                   -- Corderius-donkergroen
    '📊',
    1
);
