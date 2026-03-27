"""Charge les données Excel dans PostgreSQL."""

from __future__ import annotations

import datetime
import logging
import re
from pathlib import Path
from typing import Tuple

import pandas as pd
from sqlalchemy import text

from database.db_utils import get_engine, get_player_id_map, run_schema,truncate_table
from database.schemas import PlayerRecord, StatRecord, TeamRecord
from rag_pipeline.config import DATABASE_URL, EXCEL_FILE, SCHEMA_FILE


# =========================================================
# Logging
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# =========================================================
# Excel
# =========================================================

def load_excel_sheets(file_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Charge les feuilles Excel et retourne les DataFrames.
    arguments :
    - file_path : chemin vers le fichier Excel
    retour : un tuple (df_teams, df_stats) contenant les DataFrames des équipes et des statistiques
    fonctionnement :
    - utilise pandas pour lire le fichier Excel
    - lit la feuille "Equipe" dans df_teams
    - lit la feuille "Données NBA" dans df_stats_raw sans header
    - corrige le header de df_stats_raw en utilisant la fonction rebuild_stats_header
    """
    xls = pd.ExcelFile(file_path)

    df_teams = pd.read_excel(xls, sheet_name="Equipe")
    df_stats_raw = pd.read_excel(xls, sheet_name="Données NBA", header=None)

    df_stats = rebuild_stats_header(df_stats_raw)

    return df_teams, df_stats


def rebuild_stats_header(df: pd.DataFrame) -> pd.DataFrame:
    """Corrige le header (ligne 1 = 1..53, ligne 2 = vrais noms).
     arguments :
     - df : DataFrame brut avec header sur 2 lignes
     retour : DataFrame avec header corrigé
     fonctionnement :
     - utilise la deuxième ligne comme noms de colonnes
     - supprime les deux premières lignes originales
    - réinitialise les index du DataFrame
    """
    df.columns = df.iloc[1]
    df = df.iloc[2:].reset_index(drop=True)
    return df


# =========================================================
# Nettoyage
# =========================================================

def normalize_column_name(column: str) -> str:
    """Mappe les noms de colonnes Excel aux noms de champs DB.
    arguments :
    - column : nom de colonne Excel
    retour : nom de colonne normalisé pour la base de données
    fonctionnement :
    - gère le cas spécial de "15:00" qui est interprété comme un objet datetime.time
    - utilise un mapping explicite pour les colonnes connues
    - pour les autres colonnes, convertit en minuscules, remplace les caractères non-alphanumériques par des underscores, et nettoie les underscores redondants
    """
    if isinstance(column, datetime.time) and column == datetime.time(15, 0):
        return "fifteen_min"

    col = str(column).strip()

    mapping = {
        "Player": "player_name",
        "Team": "team_code",
        "Age": "age",
        "GP": "gp",
        "W": "w",
        "L": "l",
        "Min": "minutes_avg",
        "PTS": "pts",
        "FGM": "fgm",
        "FGA": "fga",
        "FG%": "fg_pct",
        "15:00": "fifteen_min",
        "3PA": "fg3a",
        "3P%": "fg3_pct",
        "FTM": "ftm",
        "FTA": "fta",
        "FT%": "ft_pct",
        "OREB": "oreb",
        "DREB": "dreb",
        "REB": "reb",
        "AST": "ast",
        "TOV": "tov",
        "STL": "stl",
        "BLK": "blk",
        "PF": "pf",
        "FP": "fp",
        "DD2": "dd2",
        "TD3": "td3",
        "+/-": "plus_minus",
        "OFFRTG": "offrtg",
        "DEFRTG": "defrtg",
        "NETRTG": "netrtg",
        "AST%": "ast_pct",
        "AST/TO": "ast_to",
        "AST RATIO": "ast_ratio",
        "OREB%": "oreb_pct",
        "DREB%": "dreb_pct",
        "REB%": "reb_pct",
        "TO RATIO": "to_ratio",
        "EFG%": "efg_pct",
        "TS%": "ts_pct",
        "USG%": "usg_pct",
        "PACE": "pace",
        "PIE": "pie",
        "POSS": "poss",
        "Code": "team_code",
        "Nom complet de l'équipe": "team_name",
    }

    if col in mapping:
        return mapping[col]

    col = col.lower()
    col = re.sub(r"[^\w]+", "_", col)
    col = re.sub(r"_+", "_", col).strip("_")
    return col


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie le DataFrame en normalisant les noms de colonnes et en remplaçant les NaN par None.
    arguments :
    - df : DataFrame à nettoyer
    retour : DataFrame nettoyé
    fonctionnement :
    - normalise les noms de colonnes
    - remplace les valeurs NaN par None
    """
    df = df.copy()
    df.columns = [normalize_column_name(col) for col in df.columns]
    df = df.dropna(axis=1, how="all")
    return df.where(pd.notnull(df), None)


def ensure_required_columns(df: pd.DataFrame, required: list[str], name: str) -> None:
    """Vérifie que les colonnes obligatoires sont présentes.
    arguments :
    - df : DataFrame à vérifier
    - required : liste des colonnes obligatoires
    - name : nom du DataFrame pour les messages d'erreur
    fonctionnement :
    - compare les colonnes requises avec celles du DataFrame
    - si des colonnes sont manquantes, lève une ValueError avec les détails
    """
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{name} colonnes manquantes : {missing} | dispo : {df.columns.tolist()}"
        )


# =========================================================
# Extraction
# =========================================================

def extract_teams(df: pd.DataFrame) -> list[dict]:
    """Extrait les équipes du DataFrame.
    arguments :
    - df : DataFrame contenant les informations des équipes
    retour : liste de dictionnaires représentant les équipes
    fonctionnement :
    - itère sur chaque ligne du DataFrame
    - ignore les lignes sans code ou nom d'équipe
    - crée un dictionnaire pour chaque équipe valide
    
    """
    records = []
    for _, row in df.iterrows():
        if not row.get("team_code") or not row.get("team_name"):
            continue
        records.append(TeamRecord(**row).model_dump())
    return records


def extract_players(df: pd.DataFrame) -> list[dict]:
    """Extrait les joueurs du DataFrame.
    arguments :
    - df : DataFrame contenant les informations des joueurs
    retour : liste de dictionnaires représentant les joueurs
    fonctionnement :
    - sélectionne les colonnes pertinentes
    - supprime les doublons
    - crée un dictionnaire pour chaque joueur valide
    """
    players = df[["player_name", "team_code", "age"]].drop_duplicates()
    return [PlayerRecord(**row).model_dump() for _, row in players.iterrows()]


def extract_stats(df: pd.DataFrame) -> list[dict]:
    """Extrait les statistiques du DataFrame.
    arguments :
    - df : DataFrame contenant les statistiques des joueurs
    retour : liste de dictionnaires représentant les statistiques
    fonctionnement :
    - itère sur chaque ligne du DataFrame
    - valide chaque ligne avec StatRecord
    - crée un dictionnaire pour chaque statistique valide
    """
    records = []
    for _, row in df.iterrows():
        validated = StatRecord(**row.to_dict())
        records.append(validated.model_dump())
    return records


# =========================================================
# Insert
# =========================================================

def insert_teams(engine, data: list[dict]) -> None:
    """Insère les équipes dans la base en ignorant les doublons.
    arguments :
    - engine : moteur de base de données
    - data : liste de dictionnaires représentant les équipes
    fonctionnement :
    - insère les équipes dans la table teams
    - ignore les doublons
    """
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO teams (team_code, team_name)
            VALUES (:team_code, :team_name)
            ON CONFLICT DO NOTHING
        """), data)


def insert_players(engine, data: list[dict]) -> None:
    """Insère les joueurs dans la base en ignorant les doublons.
    arguments :
    - engine : moteur de base de données
    - data : liste de dictionnaires représentant les joueurs
    fonctionnement :
    - insère les joueurs dans la table players
    - ignore les doublons
    """
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO players (player_name, team_code, age)
            VALUES (:player_name, :team_code, :age)
            ON CONFLICT DO NOTHING
        """), data)





def insert_stats(engine, stats: list[dict]) -> None:
    """Insère les statistiques dans la base en associant les joueurs par leur nom.
    arguments :
    - engine : moteur de base de données
    - stats : liste de dictionnaires représentant les statistiques
    fonctionnement :
    - récupère l'ID des joueurs à partir de leur nom
    - crée un dictionnaire pour chaque statistique valide
    - insère les statistiques dans la table stats
    """
    player_map = get_player_id_map(engine)

    rows_to_insert = []

    for stat in stats:
        stat = stat.copy()
        player_name = stat.pop("player_name")
        player_id = player_map.get(player_name)

        if player_id is None:
            continue

        stat["player_id"] = player_id
        rows_to_insert.append(stat)

    if not rows_to_insert:
        logger.warning("Aucune statistique à insérer.")
        return

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO stats (
                player_id, gp, w, l, minutes_avg,
                pts, fgm, fga, fg_pct,
                fifteen_min, fg3a, fg3_pct,
                ftm, fta, ft_pct,
                oreb, dreb, reb,
                ast, tov, stl, blk,
                pf, fp, dd2, td3,
                plus_minus,
                offrtg, defrtg, netrtg,
                ast_pct, ast_to, ast_ratio,
                oreb_pct, dreb_pct, reb_pct,
                to_ratio, efg_pct, ts_pct, usg_pct,
                pace, pie, poss
            )
            VALUES (
                :player_id, :gp, :w, :l, :minutes_avg,
                :pts, :fgm, :fga, :fg_pct,
                :fifteen_min, :fg3a, :fg3_pct,
                :ftm, :fta, :ft_pct,
                :oreb, :dreb, :reb,
                :ast, :tov, :stl, :blk,
                :pf, :fp, :dd2, :td3,
                :plus_minus,
                :offrtg, :defrtg, :netrtg,
                :ast_pct, :ast_to, :ast_ratio,
                :oreb_pct, :dreb_pct, :reb_pct,
                :to_ratio, :efg_pct, :ts_pct, :usg_pct,
                :pace, :pie, :poss
            )
        """), rows_to_insert)


# =========================================================
# Main
# =========================================================

def main() -> None:
    """Point d'entrée principal.
    fonctionnement :
    - configure le logging
    - crée une connexion à la base de données
    - crée ou met à jour le schéma SQL
    - charge les équipes et les joueurs depuis le fichier Excel
    - nettoie les DataFrames
    - vérifie que les colonnes obligatoires sont présentes
    - extrait les équipes, les joueurs et les statistiques des DataFrames
    - insère les équipes et les joueurs dans la base
    - vide la table des statistiques
    - insère les statistiques dans la base
    - affiche un message de succès
    """
    engine = get_engine(DATABASE_URL)

    logger.info("Création du schéma")
    run_schema(engine, SCHEMA_FILE)

    logger.info("Lecture Excel")
    df_teams, df_stats = load_excel_sheets(EXCEL_FILE)

    df_teams = clean_dataframe(df_teams)
    df_stats = clean_dataframe(df_stats)

    ensure_required_columns(df_teams, ["team_code", "team_name"], "teams")
    ensure_required_columns(df_stats, ["player_name", "team_code", "age"], "stats")

    teams = extract_teams(df_teams)
    players = extract_players(df_stats)
    stats = extract_stats(df_stats)

    insert_teams(engine, teams)
    insert_players(engine, players)

    truncate_table
    insert_stats(engine, stats)

    logger.info("Chargement terminé")


if __name__ == "__main__":
    main()