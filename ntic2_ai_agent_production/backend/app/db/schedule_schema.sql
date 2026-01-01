-- Schéma de base de données pour les emplois du temps détaillés

-- Table pour les groupes/classes
CREATE TABLE IF NOT EXISTS groupes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

-- Table pour les formateurs
CREATE TABLE IF NOT EXISTS formateurs (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL UNIQUE
);

-- Table pour les modules/cours
CREATE TABLE IF NOT EXISTS modules (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(255) NOT NULL,
    description TEXT
);

-- Table pour les salles
CREATE TABLE IF NOT EXISTS salles (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    type VARCHAR(50), -- TEAM, SP, SC, LABO, AMPHI, etc.
    description TEXT
);

-- Table principale pour les sessions de cours
CREATE TABLE IF NOT EXISTS sessions_cours (
    id SERIAL PRIMARY KEY,
    groupe_id INTEGER REFERENCES groupes(id) ON DELETE CASCADE,
    formateur_id INTEGER REFERENCES formateurs(id) ON DELETE SET NULL,
    module_id INTEGER REFERENCES modules(id) ON DELETE SET NULL,
    salle_id INTEGER REFERENCES salles(id) ON DELETE SET NULL,
    jour VARCHAR(20) NOT NULL, -- Lundi, Mardi, Mercredi, Jeudi, Vendredi, Samedi
    session_num INTEGER NOT NULL, -- 1, 2, 3, 4
    heure_debut TIME NOT NULL, -- 08:00, 09:00, 10:00, 11:00
    heure_fin TIME NOT NULL, -- 09:00, 10:00, 11:00, 12:00
    couleur_fond VARCHAR(20), -- green, pink, purple, etc. (pour les cellules spéciales)
    notes TEXT -- Pour stocker des informations supplémentaires comme "EFM", "Contrôle", etc.
);

-- Index pour améliorer les performances des requêtes
CREATE INDEX IF NOT EXISTS idx_sessions_groupe ON sessions_cours(groupe_id);
CREATE INDEX IF NOT EXISTS idx_sessions_formateur ON sessions_cours(formateur_id);
CREATE INDEX IF NOT EXISTS idx_sessions_module ON sessions_cours(module_id);
CREATE INDEX IF NOT EXISTS idx_sessions_salle ON sessions_cours(salle_id);
CREATE INDEX IF NOT EXISTS idx_sessions_jour ON sessions_cours(jour);
CREATE INDEX IF NOT EXISTS idx_sessions_heure ON sessions_cours(heure_debut, heure_fin);

-- Vue pour faciliter les requêtes
CREATE OR REPLACE VIEW vue_emploi_temps AS
SELECT 
    s.id,
    g.code AS groupe_code,
    f.nom AS formateur_nom,
    m.nom AS module_nom,
    sa.code AS salle_code,
    sa.type AS salle_type,
    s.jour,
    s.session_num,
    s.heure_debut,
    s.heure_fin,
    s.couleur_fond,
    s.notes
FROM sessions_cours s
LEFT JOIN groupes g ON s.groupe_id = g.id
LEFT JOIN formateurs f ON s.formateur_id = f.id
LEFT JOIN modules m ON s.module_id = m.id
LEFT JOIN salles sa ON s.salle_id = sa.id;

