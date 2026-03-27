"""Charge les rapports textuels (PDF Reddit, etc.) dans PostgreSQL.

Ce script :
- charge les fichiers du dossier inputs/ via le data_loader ;
- filtre les documents de type reports (PDF Reddit) ;
- nettoie le texte extrait ;
- enrichit les reports avec les équipes et joueurs détectés depuis la base SQL ;
- insère les données dans la table reports.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from database.db_utils import (
    fetch_players,
    fetch_teams,
    get_engine,
    run_schema,
    truncate_table,
)
from rag_pipeline.config import DATABASE_URL, INPUT_DIR, SCHEMA_FILE
from utils.data_loader import load_and_parse_files
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)




# =========================================================
# Texte
# =========================================================

def clean_report_text(text: str) -> str:
    """Nettoie un texte OCR / PDF pour améliorer le retrieval.
    argument :
        - text : le texte brut extrait du PDF / OCR
    retour :le texte nettoyé, prêt à être inséré dans la base
    fonctionnement :
        - remplace les retours à la ligne par des espaces
        - supprime les caractères invisibles et les puces
        - supprime les URLs
        - supprime les dates / heures OCR
        - supprime les motifs de bruit fréquents (UI Reddit, pagination, etc.)
        - filtre les lignes trop courtes, trop longues, ou avec peu de lettres
        - supprime les phrases répétées

    """
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u200b", " ")
    text = text.replace("•", " ")
    text = text.replace("·", " ")
    text = text.replace("|", " ")

    # Suppression URLs
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"www\.\S+", " ", text)

    # Suppression dates / heures OCR
    text = re.sub(r"\b\d{2}/\d{2}/\d{4}\s+\d{2}[:.]\d{2}\b", " ", text)

    # Suppression pagination
    text = re.sub(r"\b\d+\s*/\s*\d+\b", " ", text)

    # Suppression bruit Reddit / OCR
    noise_patterns = [
        r"Accéder au contenu principal",
        r"Se connecter",
        r"Rechercher dans r/nba",
        r"Rejoindre la conversation",
        r"Trier par",
        r"Meilleurs",
        r"Répondre",
        r"Partager",
        r"Commentaires?",
        r"Règles de Reddit",
        r"Politique de confidentialité",
        r"Contrat d'utilisation",
        r"Tous droits réservés",

        # Reddit / UI
        r"upvotes?",
        r"commentaires?",
        r"Discussions connexes",
        r"Afficher plus de commentaires",
        r"Comm\. du top 1%",
        r"Comm\. du 1%",
        r"Comm; du top 1%",
        r"Comm; du 1%",
        r"r/nba",
        r"rInba",
        r"r/NBATalk",
        r"r/thefinals",

        # OCR bruit fréquent
        r"lcommentsl",
        r"\bilya\s+\d+\s*[mjau]\b",
        r"\bil y a\s+\d+\s*[mjau]\b",

        # URLs / tracking
        r"reddit\.com\S*",
        r"doubleclick\.net\S*",

        # pubs / sponsors
        r"Sponsorisé\(e\)",
        r"En savoir plus",
        r"Télécharger",
        r"Officiel",
        r"Xometry",
        r"IBM",
        r"IONOS",
        r"adidas",
        r"pages xometry",
        r"elderscrollsonline",
    ]

    for pattern in noise_patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    lines = [line.strip() for line in text.split("\n")]

    cleaned_lines = []
    for line in lines:
        if not line:
            continue

        if len(line) < 4:
            continue

        if len(line) > 350:
            continue

        if re.fullmatch(r"[\W_]+", line):
            continue

        letters = sum(c.isalpha() for c in line)
        if letters < 3:
            continue

        cleaned_lines.append(line)

    # filtre qualité OCR
    filtered_lines = []
    for line in cleaned_lines:
        words = line.split()
        if len(words) < 3:
            continue

        alpha_ratio = sum(c.isalpha() for c in line) / max(len(line), 1)
        if alpha_ratio < 0.55:
            continue

        filtered_lines.append(line)

    text = " ".join(filtered_lines)
    text = re.sub(r"\s+", " ", text).strip()

    # suppression des phrases répétées
    sentences = re.split(r"(?<=[.!?])\s+", text)

    seen = set()
    unique_sentences = []
    for sentence in sentences:
        s = sentence.strip()
        if not s:
            continue

        key = s.lower()
        if key in seen:
            continue

        seen.add(key)
        unique_sentences.append(s)

    text = " ".join(unique_sentences)
    text = re.sub(r"\s+", " ", text).strip()

    return text


# =========================================================
# Filtrage
# =========================================================

def is_report_document(doc: dict[str, Any]) -> bool:
    """Détermine si un document doit être inséré dans reports.
    argument :
    - doc : un dictionnaire représentant un document chargé par le data_loader, avec au moins
      les clés "metadata" (contenant "filename" et "source") et "page_content" (le texte extrait)
    retour : True si le document doit être traité comme un report, False sinon
    fonctionnement :
    - vérifie que le filename ou la source suggère un PDF Reddit (ex: contient "reddit" et se termine par .pdf)
    - ignore les fichiers Excel ou autres types non textuels
    """
    metadata = doc.get("metadata", {})
    filename = str(metadata.get("filename", "")).lower()
    source = str(metadata.get("source", "")).lower()

    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        return False

    if filename.endswith(".pdf") and "reddit" in filename:
        return True

    if source.endswith(".pdf") and "reddit" in source:
        return True

    return False


# =========================================================
# Alias
# =========================================================

def build_team_aliases(teams: list[dict[str, str]]) -> dict[str, str]:
    """Construit une table alias -> team_code à partir des équipes SQL.
    argument :
    - teams : une liste de dictionnaires représentant les équipes SQL, avec au moins les clés "team_code" et "team_name"
    retour : un dictionnaire mapping chaque alias vers le code de l'équipe correspondante
    fonctionnement :
    - pour chaque équipe, ajoute le nom complet en alias
    - ajoute les parties du nom (ex: "warriors", "golden") comme alias
    - ajoute des alias manuels pour les équipes NBA (ex: "gsw" -> "warriors", "okc" -> "thunder", etc.)

    """
    alias_map: dict[str, str] = {}

    manual_aliases = {
        "ATL": ["hawks", "atlanta"],
        "BKN": ["nets", "brooklyn"],
        "BOS": ["celtics", "boston"],
        "CHA": ["hornets", "charlotte"],
        "CHI": ["bulls", "chicago"],
        "CLE": ["cavs", "cavaliers", "cleveland"],
        "DAL": ["mavs", "mavericks", "dallas"],
        "DEN": ["nuggets", "denver"],
        "DET": ["pistons", "detroit"],
        "GSW": ["warriors", "golden state"],
        "HOU": ["rockets", "houston"],
        "IND": ["pacers", "indiana"],
        "LAC": ["clippers", "la clippers"],
        "LAL": ["lakers", "la lakers"],
        "MEM": ["grizzlies", "memphis"],
        "MIA": ["heat", "miami"],
        "MIL": ["bucks", "milwaukee"],
        "MIN": ["wolves", "timberwolves", "minnesota"],
        "NOP": ["pelicans", "new orleans"],
        "NYK": ["knicks", "new york"],
        "OKC": ["thunder", "okc", "oklahoma city"],
        "ORL": ["magic", "orlando"],
        "PHI": ["76ers", "sixers", "philadelphia"],
        "PHX": ["suns", "phoenix"],
        "POR": ["blazers", "trail blazers", "portland"],
        "SAC": ["kings", "sacramento"],
        "SAS": ["spurs", "san antonio"],
        "TOR": ["raptors", "toronto"],
        "UTA": ["jazz", "utah"],
        "WAS": ["wizards", "washington"],
    }

    for team in teams:
        team_code = team["team_code"]
        team_name = team["team_name"].lower().strip()

        alias_map[team_name] = team_code

        for part in team_name.split():
            if len(part) > 3:
                alias_map[part] = team_code

        for alias in manual_aliases.get(team_code, []):
            alias_map[alias] = team_code

    return alias_map


def build_player_aliases(players: list[str]) -> dict[str, str]:
    """Construit alias -> nom complet joueur.
    argument :
    - players : une liste de noms complets de joueurs
    retour : un dictionnaire mapping chaque alias vers le nom complet du joueur
    fonctionnement :
    - pour chaque joueur, ajoute le nom complet en alias
    - ajoute le nom de famille comme alias si il a au moins 4 caractères
    """
    alias_map: dict[str, str] = {}

    for full_name in players:
        full_name_clean = full_name.lower().strip()
        alias_map[full_name_clean] = full_name

        parts = full_name_clean.split()
        if len(parts) >= 2:
            last_name = parts[-1]
            if len(last_name) >= 4:
                alias_map[last_name] = full_name

    return alias_map


# =========================================================
# Détection
# =========================================================

def detect_team_codes(
    text_content: str,
    title: str,
    team_aliases: dict[str, str],
) -> tuple[Optional[str], list[str]]:
    """Détecte les équipes mentionnées et retourne :
    - l'équipe principale
    - la liste des équipes détectées
    arguments :
        - text_content : le texte du report à analyser
        - title : le titre du report (ex: le nom du PDF ou la source)
        - team_aliases : un dictionnaire alias -> team_code construit à partir des équipes SQL
    retour :
            - le team_code de l'équipe principale (celle la plus mentionnée dans le texte et le titre
            avec un score pondéré), ou None si aucune équipe détectéee
            - la liste des team_codes détectés, ordonnée par score décroissant
    fonctionnement :
        - pour chaque alias d'équipe, compte le nombre d'occurrences dans le texte
        - ajoute un score pondéré si l'alias est mentionné dans le titre ou dans les 500 premiers caractères du texte
        - retourne l'équipe avec le score le plus élevé comme équipe principale, et la liste des équipes détectées ordonnée par score

    """
    text_lower = text_content.lower()
    title_lower = (title or "").lower()
    first_part = text_lower[:500]

    scores: dict[str, float] = {}

    for alias, team_code in team_aliases.items():
        pattern = rf"\b{re.escape(alias)}\b"
        occurrences = len(re.findall(pattern, text_lower))

        if occurrences == 0:
            continue

        score = float(occurrences)

        if re.search(pattern, title_lower):
            score += 2.0

        if re.search(pattern, first_part):
            score += 1.5

        scores[team_code] = scores.get(team_code, 0.0) + score

    if not scores:
        return None, []

    counts = Counter(scores)
    ordered = [team_code for team_code, _ in counts.most_common()]
    main_team = ordered[0]

    return main_team, ordered


def detect_player_names(
    text_content: str,
    title: str,
    player_aliases: dict[str, str],
) -> tuple[Optional[str], list[str]]:
    """Détecte les joueurs mentionnés et retourne :
    - le joueur principal
    - la liste des joueurs détectés
    arguments :
        - text_content : le texte du report à analyser
        - title : le titre du report (ex: le nom du PDF ou la source)
        - player_aliases : un dictionnaire alias -> nom complet construit à partir des joueurs SQL
    retour :
        - le nom complet du joueur principal (celui la plus mentionné dans le texte et le titre avec un score pondéré), ou None si aucun joueur détecté
        - la liste des noms complets des joueurs détectés, ordonnée par score décroissant
    fonctionnement :
        - pour chaque alias de joueur, compte le nombre d'occurrences dans le texte
        - ajoute un score pondéré si l'alias est mentionné dans le titre ou dans les 500 premiers caractères du texte
        - retourne le joueur avec le score le plus élevé comme joueur principal, et la liste des joueurs détectés ordonnée par score
    """
    text_lower = text_content.lower()
    title_lower = (title or "").lower()
    first_part = text_lower[:500]

    scores: dict[str, float] = {}

    for alias, full_name in player_aliases.items():
        pattern = rf"\b{re.escape(alias)}\b"
        occurrences = len(re.findall(pattern, text_lower))

        if occurrences == 0:
            continue

        score = float(occurrences)

        if re.search(pattern, title_lower):
            score += 2.0

        if re.search(pattern, first_part):
            score += 1.5

        scores[full_name] = scores.get(full_name, 0.0) + score

    if not scores:
        return None, []

    counts = Counter(scores)
    ordered = [player_name for player_name, _ in counts.most_common()]
    main_player = ordered[0]

    return main_player, ordered


# =========================================================
# Construction des enregistrements
# =========================================================

def extract_report_record(
    doc: dict[str, Any],
    team_aliases: dict[str, str],
    player_aliases: dict[str, str],
) -> Optional[dict[str, Any]]:
    """Construit un enregistrement prêt à être inséré dans reports.
    argument :
    - doc : un dictionnaire représentant un document chargé par le data_loader, avec au moins les clés "metadata" (contenant "filename" et "source") et "page_content" (le texte extrait)
    - team_aliases : un dictionnaire alias -> code d'équipe construit à partir des équipes SQL
    - player_aliases : un dictionnaire alias -> nom complet construit à partir des joueurs SQL
    retour :
    - un dictionnaire représentant l'enregistrement à insérer dans reports, ou None si le document est ignoré
    fonctionnement :
    - nettoie le texte extrait du document
    - détecte les équipes et joueurs mentionnés dans le texte
    - construit un dictionnaire avec les champs nécessaires pour l'insertion dans la table reports
    """

    metadata = doc.get("metadata", {})
    filename = str(metadata.get("filename", ""))
    source = str(metadata.get("source", ""))

    raw_content = str(doc.get("page_content", ""))
    content = clean_report_text(raw_content)

    if len(content) < 100:
        logger.warning("Report ignoré car trop court : %s", filename)
        return None

    main_team, all_teams = detect_team_codes(content, source, team_aliases)
    main_player, all_players = detect_player_names(content, source, player_aliases)

    return {
        "source_file": filename,
        "title": source,
        "report_text": content,
        "related_team_code": main_team,
        "related_player_name": main_player,
        "related_match_id": None,
        "related_team_codes": ",".join(all_teams) if all_teams else None,
        "related_player_names": ",".join(all_players) if all_players else None,
    }


# =========================================================
# Insertions
# =========================================================

def insert_reports(engine: Engine, reports: list[dict[str, Any]]) -> None:
    """Insère les reports dans la base.
    argument :
    - engine : une instance SQLAlchemy Engine connectée à la base de données
    - reports : une liste de dictionnaires représentant les reports à insérer
    fonctionnement :
    - si la liste est vide, log un avertissement et retourne sans faire d'insertion
    - sinon, exécute une requête d'insertion en utilisant SQLAlchemy text() pour insérer tous les reports en une seule requête

    """
    if not reports:
        logger.warning("Aucun report à insérer.")
        return

    query = text("""
        INSERT INTO reports (
            source_file,
            title,
            report_text,
            related_team_code,
            related_player_name,
            related_match_id,
            related_team_codes,
            related_player_names
        )
        VALUES (
            :source_file,
            :title,
            :report_text,
            :related_team_code,
            :related_player_name,
            :related_match_id,
            :related_team_codes,
            :related_player_names
        )
    """)

    with engine.begin() as conn:
        conn.execute(query, reports)


# =========================================================
# Main
# =========================================================

def main() -> None:
    """Point d'entrée principal.
    fonctionnement :
    - configure le logging
    - crée une connexion à la base de données
    - crée ou met à jour le schéma SQL
    - charge les équipes et les joueurs depuis la base
    - charge les documents depuis le répertoire d'entrée
    - filtre les documents de type report
    - nettoie la table reports
    - insère les reports dans la base
    """
    setup_logging()

    engine = get_engine(DATABASE_URL)

    logger.info("Création / mise à jour du schéma SQL...")
    run_schema(engine, SCHEMA_FILE)

    logger.info("Chargement des équipes depuis la base...")
    teams = fetch_teams(engine)
    team_aliases = build_team_aliases(teams)

    logger.info("Chargement des joueurs depuis la base...")
    players = fetch_players(engine)
    player_aliases = build_player_aliases(players)

    logger.info("Chargement des documents depuis %s", INPUT_DIR)
    documents = load_and_parse_files(str(INPUT_DIR))

    logger.info("Filtrage des documents de type reports...")
    report_docs = [doc for doc in documents if is_report_document(doc)]

    logger.info("%s document(s) report trouvé(s).", len(report_docs))

    reports: list[dict[str, Any]] = []
    for doc in report_docs:
        report = extract_report_record(doc, team_aliases, player_aliases)
        if report is not None:
            reports.append(report)

    logger.info("Nettoyage de la table reports...")
    truncate_table(engine, "reports")

    logger.info("Insertion des reports...")
    insert_reports(engine, reports)

    logger.info("Chargement des reports terminé avec succès.")


if __name__ == "__main__":
    main()