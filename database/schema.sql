-- =========================================================
-- Schéma SQL - SportSee (PostgreSQL)
-- =========================================================

-- ======================
-- Table : teams
-- ======================
CREATE TABLE IF NOT EXISTS teams (
    team_code VARCHAR PRIMARY KEY,
    team_name TEXT NOT NULL
);

COMMENT ON TABLE teams IS 'Équipes NBA';
COMMENT ON COLUMN teams.team_code IS 'Code de l’équipe (3 lettres)';
COMMENT ON COLUMN teams.team_name IS 'Nom complet de l’équipe';

-- ======================
-- Table : players
-- ======================
CREATE TABLE IF NOT EXISTS players (
    player_id SERIAL PRIMARY KEY,
    player_name TEXT NOT NULL UNIQUE,
    team_code VARCHAR NOT NULL,
    age INTEGER,
    FOREIGN KEY (team_code) REFERENCES teams(team_code)
);

COMMENT ON TABLE players IS 'Informations des joueurs NBA';
COMMENT ON COLUMN players.player_name IS 'Nom du joueur';
COMMENT ON COLUMN players.team_code IS 'Code équipe';
COMMENT ON COLUMN players.age IS 'Âge du joueur';

-- ======================
-- Table : stats
-- ======================
CREATE TABLE IF NOT EXISTS stats (
    stat_id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL,

    gp INTEGER,
    w INTEGER,
    l INTEGER,
    minutes_avg REAL,

    pts REAL,

    fgm REAL,
    fga REAL,
    fg_pct REAL,

    fifteen_min REAL,

    fg3a REAL,
    fg3_pct REAL,

    ftm REAL,
    fta REAL,
    ft_pct REAL,

    oreb REAL,
    dreb REAL,
    reb REAL,

    ast REAL,
    tov REAL,
    stl REAL,
    blk REAL,

    pf REAL,
    fp REAL,
    dd2 INTEGER,
    td3 INTEGER,

    plus_minus REAL,

    offrtg REAL,
    defrtg REAL,
    netrtg REAL,

    ast_pct REAL,
    ast_to REAL,
    ast_ratio REAL,

    oreb_pct REAL,
    dreb_pct REAL,
    reb_pct REAL,

    to_ratio REAL,
    efg_pct REAL,
    ts_pct REAL,
    usg_pct REAL,
    pace REAL,
    pie REAL,
    poss REAL,

    FOREIGN KEY (player_id) REFERENCES players(player_id)
);

COMMENT ON TABLE stats IS 'Statistiques agrégées par joueur';

COMMENT ON COLUMN stats.gp IS 'Nombre de matchs joués';
COMMENT ON COLUMN stats.w IS 'Victoires';
COMMENT ON COLUMN stats.l IS 'Défaites';
COMMENT ON COLUMN stats.minutes_avg IS 'Minutes moyennes par match';
COMMENT ON COLUMN stats.pts IS 'Points par match';

COMMENT ON COLUMN stats.fgm IS 'Tirs réussis';
COMMENT ON COLUMN stats.fga IS 'Tirs tentés';
COMMENT ON COLUMN stats.fg_pct IS 'Pourcentage de réussite aux tirs';

COMMENT ON COLUMN stats.fifteen_min IS 'Minutes jouées après 15:00';

COMMENT ON COLUMN stats.fg3a IS 'Tirs à 3 points tentés';
COMMENT ON COLUMN stats.fg3_pct IS 'Pourcentage à 3 points';

COMMENT ON COLUMN stats.ftm IS 'Lancers francs réussis';
COMMENT ON COLUMN stats.fta IS 'Lancers francs tentés';
COMMENT ON COLUMN stats.ft_pct IS 'Pourcentage aux lancers francs';

COMMENT ON COLUMN stats.oreb IS 'Rebonds offensifs';
COMMENT ON COLUMN stats.dreb IS 'Rebonds défensifs';
COMMENT ON COLUMN stats.reb IS 'Rebonds totaux';

COMMENT ON COLUMN stats.ast IS 'Passes décisives';
COMMENT ON COLUMN stats.tov IS 'Balles perdues';
COMMENT ON COLUMN stats.stl IS 'Interceptions';
COMMENT ON COLUMN stats.blk IS 'Contres';

COMMENT ON COLUMN stats.pf IS 'Fautes personnelles';
COMMENT ON COLUMN stats.fp IS 'Fantasy points';
COMMENT ON COLUMN stats.dd2 IS 'Double-doubles';
COMMENT ON COLUMN stats.td3 IS 'Triple-doubles';

COMMENT ON COLUMN stats.plus_minus IS 'Plus-Minus';

COMMENT ON COLUMN stats.offrtg IS 'Offensive Rating';
COMMENT ON COLUMN stats.defrtg IS 'Defensive Rating';
COMMENT ON COLUMN stats.netrtg IS 'Net Rating';

COMMENT ON COLUMN stats.ast_pct IS 'Pourcentage d’assists';
COMMENT ON COLUMN stats.ast_to IS 'Ratio assists / turnovers';
COMMENT ON COLUMN stats.ast_ratio IS 'Assists pour 100 possessions';

COMMENT ON COLUMN stats.oreb_pct IS 'Pourcentage rebonds offensifs';
COMMENT ON COLUMN stats.dreb_pct IS 'Pourcentage rebonds défensifs';
COMMENT ON COLUMN stats.reb_pct IS 'Pourcentage rebonds totaux';

COMMENT ON COLUMN stats.to_ratio IS 'Turnover ratio';
COMMENT ON COLUMN stats.efg_pct IS 'Effective Field Goal %';
COMMENT ON COLUMN stats.ts_pct IS 'True Shooting %';
COMMENT ON COLUMN stats.usg_pct IS 'Usage Rate';
COMMENT ON COLUMN stats.pace IS 'Rythme de jeu';
COMMENT ON COLUMN stats.pie IS 'Player Impact Estimate';
COMMENT ON COLUMN stats.poss IS 'Nombre de possessions';

-- ======================
-- Table : matches
-- ======================
CREATE TABLE IF NOT EXISTS matches (
    match_id SERIAL PRIMARY KEY,
    match_date DATE,
    home_team_code VARCHAR,
    away_team_code VARCHAR,
    season TEXT,
    source TEXT,
    FOREIGN KEY (home_team_code) REFERENCES teams(team_code),
    FOREIGN KEY (away_team_code) REFERENCES teams(team_code)
);

COMMENT ON TABLE matches IS 'Données match par match (future extension)';

-- ======================
-- Table : reports
-- ======================
CREATE TABLE IF NOT EXISTS reports (
    report_id SERIAL PRIMARY KEY,

    source_file TEXT NOT NULL,
    title TEXT,
    report_text TEXT NOT NULL,

    -- Entité principale (simple)
    related_team_code VARCHAR,
    related_player_name TEXT,
    related_match_id INTEGER,

    -- Nouvelles colonnes (multi-entités + confiance)
    related_team_codes TEXT,
    related_player_names TEXT,


    -- Relations
    FOREIGN KEY (related_team_code) REFERENCES teams(team_code),
    FOREIGN KEY (related_match_id) REFERENCES matches(match_id)
);

COMMENT ON TABLE reports IS 'Données textuelles (rapports, Reddit, etc.)';

-- ======================
-- Index
-- ======================
CREATE INDEX IF NOT EXISTS idx_players_team_code
ON players(team_code);

CREATE INDEX IF NOT EXISTS idx_stats_player_id
ON stats(player_id);

CREATE INDEX IF NOT EXISTS idx_reports_team_code
ON reports(related_team_code);

CREATE INDEX IF NOT EXISTS idx_matches_home_team
ON matches(home_team_code);

CREATE INDEX IF NOT EXISTS idx_matches_away_team
ON matches(away_team_code);

