-- =========================================================
-- Création d'un utilisateur lecture seule pour le tool SQL
-- =========================================================

CREATE USER sportsee_llm WITH PASSWORD 'CHANGE_ME';

GRANT CONNECT ON DATABASE sportsee TO sportsee_llm;
GRANT USAGE ON SCHEMA public TO sportsee_llm;

GRANT SELECT ON teams TO sportsee_llm;
GRANT SELECT ON players TO sportsee_llm;
GRANT SELECT ON stats TO sportsee_llm;
GRANT SELECT ON reports TO sportsee_llm;
GRANT SELECT ON matches TO sportsee_llm;