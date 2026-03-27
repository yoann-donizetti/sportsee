# db_utils.py
# Regroupe les fonctions utilitaires pour l'accès à la base de données :
# - création de la connexion (engine SQLAlchemy)
# - exécution du schéma SQL
# - opérations génériques (truncate, fetch)
# - récupération des entités (équipes, joueurs)
# Permet de mutualiser la logique DB entre les scripts du projet
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def get_engine(database_url: str) -> Engine:
    """Crée et retourne l'engine SQLAlchemy."""
    return create_engine(database_url)


def run_schema(engine: Engine, schema_path: str | Path) -> None:
    """Exécute le script SQL de création / mise à jour du schéma PostgreSQL.
   arguments:
    - engine: l'engine SQLAlchemy connecté à la base de données
    - schema_path: chemin vers le fichier SQL contenant les commandes de création / mise à jour du schéma
    fonctions:
    - lit le contenu du fichier SQL
    - exécute les commandes SQL sur la base de données via l'engine
        - gère la connexion et le commit des transactions
        - ferme la connexion après l'exécution
    """
    schema_path = Path(schema_path)
    sql = schema_path.read_text(encoding="utf-8")

    conn = engine.raw_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
    finally:
        conn.close()


def truncate_table(engine: Engine, table_name: str) -> None:
    """Vide une table PostgreSQL avec reset des identifiants."""
    query = text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE")

    with engine.begin() as conn:
        conn.execute(query)


def fetch_teams(engine: Engine) -> list[dict[str, str]]:
    """Récupère les équipes depuis la base.
    arguments:
    - engine: l'engine SQLAlchemy connecté à la base de données
    retourne: une liste de dictionnaires avec les données des équipes
    fonctions:
    - exécute une requête SQL pour récupérer les équipes (team_code, team_name)
    - retourne une liste de dictionnaires avec les données des équipes """
    query = text("""
        SELECT team_code, team_name
        FROM teams
    """)

    with engine.begin() as conn:
        rows = conn.execute(query).fetchall()

    return [
        {
            "team_code": row.team_code,
            "team_name": row.team_name,
        }
        for row in rows
    ]


def fetch_players(engine: Engine) -> list[str]:
    """Récupère les noms de joueurs depuis la base.
    arguments:
    - engine: l'engine SQLAlchemy connecté à la base de données
    retourne: une liste de noms de joueurs
    fonctions:
    - exécute une requête SQL pour récupérer les noms de joueurs (player_name)
    - retourne une liste de noms de joueurs
    """
    query = text("""
        SELECT player_name
        FROM players
    """)

    with engine.begin() as conn:
        rows = conn.execute(query).fetchall()

    return [row.player_name for row in rows]


def get_player_id_map(engine: Engine) -> dict[str, int]:
    """Construit un mapping player_name -> player_id.
    arguments:
    - engine: l'engine SQLAlchemy connecté à la base de données
    retourne: un dictionnaire mapping player_name -> player_id
    fonctions:
    - exécute une requête SQL pour récupérer les identifiants et noms des joueurs
    - construit et retourne un dictionnaire mapping player_name -> player_id
    """
    query = text("""
        SELECT player_id, player_name
        FROM players
    """)

    with engine.begin() as conn:
        rows = conn.execute(query).fetchall()

    return {row.player_name: row.player_id for row in rows}