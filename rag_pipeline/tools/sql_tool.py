from __future__ import annotations

import logging
import re
from typing import List, Dict, Any

from sqlalchemy import create_engine, text

from rag_pipeline.config import MODEL_NAME,DATABASE_URL_LLM
from rag_pipeline.llm_utils import ask_mistral

logger = logging.getLogger(__name__)


# =========================================================
# DB
# =========================================================

engine = create_engine(DATABASE_URL_LLM)




# =========================================================
# Sécurité
# =========================================================

FORBIDDEN = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]


def validate_sql_query(query: str) -> str:
    """Valide et sécurise une requête SQL."""
    q = query.strip()

    # Autoriser uniquement SELECT
    if not q.upper().startswith("SELECT"):
        raise ValueError("Seules les requêtes SELECT sont autorisées")

    # Bloquer mots dangereux
    if any(word in q.upper() for word in FORBIDDEN):
        raise ValueError("Requête SQL non autorisée")

    # Ajouter LIMIT si absent
    if "LIMIT" not in q.upper():
        q += " LIMIT 50"

    return q


# =========================================================
# Exécution SQL
# =========================================================

def run_sql_query(query: str) -> List[Dict[str, Any]]:
    """Exécute une requête SQL sécurisée."""
    safe_query = validate_sql_query(query)

    with engine.begin() as conn:
        result = conn.execute(text(safe_query))
        rows = result.fetchall()

        columns = result.keys()

    return [dict(zip(columns, row)) for row in rows]


# =========================================================
# Génération SQL (simple version)
# =========================================================

SCHEMA_CONTEXT = """
Base PostgreSQL disponible pour répondre à des questions NBA.

Tables disponibles :

teams
- team_code : code unique de l’équipe
- team_name : nom complet de l’équipe

players
- player_id : identifiant unique du joueur
- player_name : nom complet du joueur
- team_code : code de l’équipe du joueur
- age : âge du joueur

stats
- player_id : identifiant du joueur
- gp : nombre de matchs joués
- w : nombre de victoires
- l : nombre de défaites
- minutes_avg : minutes moyennes par match
- pts : total de points du joueur sur la période du dataset
- reb : total de rebonds du joueur sur la période du dataset
- ast : total de passes décisives du joueur sur la période du dataset
- fg_pct : pourcentage de réussite au tir
- fg3_pct : pourcentage de réussite à 3 points
- ft_pct : pourcentage de réussite aux lancers francs
- offrtg : offensive rating
- defrtg : defensive rating
- netrtg : net rating
- pace : rythme de jeu
- pie : Player Impact Estimate
- poss : possessions

Important :
- Les colonnes pts, reb et ast sont des totaux et non des moyennes par match.
- Les calculs doivent utiliser directement les valeurs stockées dans la base.

reports
- report_id : identifiant unique du document
- source_file : nom du fichier source
- title : titre du document
- report_text : contenu textuel nettoyé
- related_team_code : équipe principale détectée
- related_player_name : joueur principal détecté
- related_team_codes : liste des équipes détectées (séparées par des virgules)
- related_player_names : liste des joueurs détectés (séparés par des virgules)

Relations :
- players.team_code = teams.team_code
- stats.player_id = players.player_id
- reports.related_team_code = teams.team_code

Contraintes de génération SQL :
- Utiliser uniquement des requêtes SELECT
- Ne jamais utiliser INSERT, UPDATE, DELETE, DROP, ALTER, CREATE ou TRUNCATE
- Toujours ajouter un LIMIT si la requête peut retourner plusieurs lignes
- Utiliser des JOIN explicites
- Ne pas utiliser SELECT *
- Utiliser uniquement les noms exacts des colonnes et tables ci-dessus
"""

FEW_SHOTS = [
    {
        "question": "Quels sont les 5 joueurs avec le plus de points ?",
        "sql": """
SELECT p.player_name, s.pts
FROM stats s
JOIN players p ON s.player_id = p.player_id
ORDER BY s.pts DESC
LIMIT 5;
""".strip(),
    },
    {
        "question": "Quelles sont les 5 équipes avec la meilleure moyenne de points ?",
        "sql": """
SELECT t.team_name, AVG(s.pts) AS avg_pts
FROM stats s
JOIN players p ON s.player_id = p.player_id
JOIN teams t ON p.team_code = t.team_code
GROUP BY t.team_name
ORDER BY avg_pts DESC
LIMIT 5;
""".strip(),
    },
    {
        "question": "Quels sont les joueurs des Los Angeles Lakers avec le plus de points ?",
        "sql": """
SELECT p.player_name, s.pts
FROM stats s
JOIN players p ON s.player_id = p.player_id
JOIN teams t ON p.team_code = t.team_code
WHERE t.team_name = 'Los Angeles Lakers'
ORDER BY s.pts DESC
LIMIT 10;
""".strip(),
    },
    {
        "question": "Quels joueurs combinent le plus de points et de passes ?",
        "sql": """
SELECT p.player_name, (s.pts + s.ast) AS pts_ast
FROM stats s
JOIN players p ON s.player_id = p.player_id
ORDER BY pts_ast DESC
LIMIT 5;
""".strip(),
    },
]


def generate_sql_query(question: str) -> str:
    """Génère une requête SQL à partir d'une question utilisateur via Mistral."""
    prompt = build_sql_prompt(question)

    sql_query = ask_mistral(prompt, model=MODEL_NAME)
    sql_query = clean_llm_sql_output(sql_query)

    return sql_query


def build_sql_prompt(question: str) -> str:
    """Construit le prompt SQL envoyé au LLM."""
    examples = "\n\n".join(
        f"Question: {ex['question']}\nSQL: {ex['sql']}"
        for ex in FEW_SHOTS
    )

    return f"""
        Tu es un assistant expert en SQL PostgreSQL.

        Ta tâche est de générer une requête SQL valide à partir d'une question utilisateur.

        {SCHEMA_CONTEXT}

        Exemples :
        {examples}

        Contraintes :
        - Génère uniquement du SQL
        - Utilise uniquement SELECT
        - N'utilise jamais INSERT, UPDATE, DELETE, DROP, ALTER, CREATE ou TRUNCATE
        - N'utilise jamais SELECT *
        - Utilise des JOIN explicites si nécessaire
        - Ajoute toujours LIMIT si la requête peut retourner plusieurs lignes
        - Utilise uniquement les tables et colonnes décrites dans le schéma

        Question utilisateur :
        {question}

        SQL :
        """.strip()


def clean_llm_sql_output(text: str) -> str:
    """Nettoie la sortie du LLM pour ne garder que le SQL."""
    text = text.strip()
    text = text.replace("```sql", "").replace("```", "").strip()

    lines = text.splitlines()
    sql_lines = []
    started = False

    for line in lines:
        if line.strip().upper().startswith("SELECT"):
            started = True
        if started:
            sql_lines.append(line)

    return "\n".join(sql_lines).strip()


# =========================================================
# Tool principal
# =========================================================

def sql_tool(question: str) -> List[Dict[str, Any]]:
    """Pipeline complet : question → SQL → résultats"""
    logger.info("Question reçue: %s", question)

    sql_query = generate_sql_query(question)
    logger.info("SQL généré: %s", sql_query)

    results = run_sql_query(sql_query)

    return results

if __name__ == "__main__":
    from utils.logging_config import setup_logging

    setup_logging()

    questions = [
        "Qui sont les 5 meilleurs scoreurs ?",
        "Quelles sont les 5 équipes avec la meilleure moyenne de points ?",
        "Quels sont les joueurs des Los Angeles Lakers avec le plus de points ?",
        "Quels joueurs combinent le plus de points et de passes ?",
        "Quelles équipes sont les plus mentionnées dans les reports ?"
    ]

    for q in questions:
        print("\n" + "="*50)
        print(f"Question: {q}")

        try:
            result = sql_tool(q)
            print("Résultat:")
            print(result)
        except Exception as e:
            print("Erreur:", e)