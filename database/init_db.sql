-- =========================================================
-- Initialisation base PostgreSQL - SportSee
-- =========================================================

--  À exécuter en tant qu'utilisateur admin PostgreSQL

-- ========================
-- Création base
-- ========================
DO
$$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_database WHERE datname = 'sportsee'
   ) THEN
      CREATE DATABASE sportsee;
   END IF;
END
$$;

-- ========================
-- Création utilisateur
-- ========================
DO
$$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_roles WHERE rolname = 'sportsee_user'
   ) THEN
      CREATE USER sportsee_user WITH PASSWORD 'CHANGE_ME';
   END IF;
END
$$;

-- ========================
-- Droits base
-- ========================
GRANT CONNECT ON DATABASE sportsee TO sportsee_user;

-- ========================
-- Connexion à la base
-- ========================
\c sportsee

-- ========================
-- Droits schéma
-- ========================
GRANT USAGE ON SCHEMA public TO sportsee_user;
GRANT CREATE ON SCHEMA public TO sportsee_user;

-- ========================
-- Important : ownership
-- ========================
ALTER SCHEMA public OWNER TO sportsee_user;

--  Optionnel mais recommandé
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL ON TABLES TO sportsee_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL ON SEQUENCES TO sportsee_user;