from __future__ import annotations

import logging
from typing import List, Dict, Any

from sqlalchemy import create_engine, text

from rag_pipeline.config import MODEL_NAME,DATABASE_URL_LLM,SQL_GENERATION_PROMPT_TEMPLATE
from rag_pipeline.llm_utils import ask_mistral

logger = logging.getLogger(__name__)


# =========================================================
# DB
# =========================================================

def get_engine():
    """Instancie et retourne le moteur SQLAlchemy."""
    return create_engine(DATABASE_URL_LLM)




# =========================================================
# Sécurité
# =========================================================

FORBIDDEN = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]


def validate_sql_query(query: str) -> str:
    """Valide et sécurise une requête SQL."""
    q = query.strip()

    if not q:
        raise ValueError("Requête SQL vide")

    # Autoriser uniquement SELECT ou WITH
    if not (q.upper().startswith("SELECT") or q.upper().startswith("WITH")):
        raise ValueError("Seules les requêtes SELECT ou WITH sont autorisées")

    # Bloquer commentaires SQL
    if "--" in q or "/*" in q or "*/" in q:
        raise ValueError("Commentaires SQL non autorisés")

    # Bloquer mots dangereux
    if any(word in q.upper() for word in FORBIDDEN):
        raise ValueError("Requête SQL non autorisée")

    # Éviter plusieurs requêtes séparées par ;
    q_no_trailing = q.rstrip(";").strip()
    if ";" in q_no_trailing:
        raise ValueError("Une seule requête SQL est autorisée")

    # Ajouter LIMIT si absent
    if "LIMIT" not in q.upper():
        q = q.rstrip(";") + " LIMIT 50"

    return q


# =========================================================
# Exécution SQL
# =========================================================

def run_sql_query(query: str) -> List[Dict[str, Any]]:
    """Exécute une requête SQL sécurisée."""
    safe_query = validate_sql_query(query)

    engine = get_engine()
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

Important pour reports :
- Pour compter les joueurs les plus mentionnés dans les documents textuels, utiliser la colonne related_player_names.
- related_player_names doit être découpé avec string_to_array(related_player_names, ',') puis unnest.
- Toujours nettoyer les noms avec TRIM avant agrégation.
- Pour ce type de question, ne pas analyser report_text directement si related_player_names suffit.

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
    {
    "question": "Quelle est la différence de performance entre les joueurs les plus scoreurs et les meilleurs passeurs ?",
    "sql": """
WITH top_scorer AS (
    SELECT
        p.player_name,
        s.pts,
        s.ast,
        s.reb,
        s.fg_pct,
        s.fg3_pct,
        s.offrtg
    FROM stats s
    JOIN players p ON s.player_id = p.player_id
    ORDER BY s.pts DESC
    LIMIT 1
),
top_passer AS (
    SELECT
        p.player_name,
        s.pts,
        s.ast,
        s.reb,
        s.fg_pct,
        s.fg3_pct,
        s.offrtg
    FROM stats s
    JOIN players p ON s.player_id = p.player_id
    ORDER BY s.ast DESC
    LIMIT 1
)
SELECT
    ts.player_name AS top_scorer_name,
    ts.pts AS top_scorer_pts,
    ts.ast AS top_scorer_ast,
    ts.reb AS top_scorer_reb,
    ts.fg_pct AS top_scorer_fg_pct,
    ts.fg3_pct AS top_scorer_fg3_pct,
    ts.offrtg AS top_scorer_offrtg,
    tp.player_name AS top_passer_name,
    tp.pts AS top_passer_pts,
    tp.ast AS top_passer_ast,
    tp.reb AS top_passer_reb,
    tp.fg_pct AS top_passer_fg_pct,
    tp.fg3_pct AS top_passer_fg3_pct,
    tp.offrtg AS top_passer_offrtg
FROM top_scorer ts
CROSS JOIN top_passer tp
LIMIT 1;
""".strip(),
},
{
    "question": "Quel joueur est le plus complet entre points, rebonds et passes ?",
    "sql": """
SELECT
    p.player_name,
    s.pts,
    s.reb,
    s.ast,
    (s.pts + s.reb + s.ast) AS total_contribution
FROM stats s
JOIN players p ON s.player_id = p.player_id
ORDER BY total_contribution DESC
LIMIT 1;
""".strip(),
},
{
    "question": "Quels joueurs sont les plus mentionnés dans les discussions Reddit ?",
    "sql": """
SELECT
    player_name,
    COUNT(*) AS mention_count
FROM (
    SELECT
        TRIM(unnest(string_to_array(related_player_names, ','))) AS player_name
    FROM reports
    WHERE related_player_names IS NOT NULL
) AS extracted
WHERE player_name <> ''
GROUP BY player_name
ORDER BY mention_count DESC, player_name ASC
LIMIT 10;
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

    return SQL_GENERATION_PROMPT_TEMPLATE.format(
        schema_context=SCHEMA_CONTEXT,
        examples=examples,
        question=question,
    )


def clean_llm_sql_output(text: str) -> str:
    """Nettoie la sortie du LLM pour ne garder que la requête SQL."""
    text = text.strip()
    text = text.replace("```sql", "").replace("```", "").strip()

    lines = text.splitlines()
    sql_lines = []
    started = False

    for line in lines:
        stripped = line.strip()
        upper = stripped.upper()

        if upper.startswith("WITH") or upper.startswith("SELECT"):
            started = True

        if started:
            sql_lines.append(line)

    cleaned = "\n".join(sql_lines).strip()

    # Si le LLM a ajouté du texte après la requête, on coupe au dernier ;
    if ";" in cleaned:
        cleaned = cleaned[: cleaned.rfind(";") + 1]

    return cleaned.strip()

def sql_tool_with_metadata(question: str) -> Dict[str, Any]:
    """Pipeline complet : question → SQL → résultats + métadonnées."""
    logger.info("Question reçue: %s", question)

    sql_query = generate_sql_query(question)
    logger.info("SQL généré: %s", sql_query)

    results = run_sql_query(sql_query)

    return {
        "question": question,
        "sql_query": sql_query,
        "rows": results,
        "n_rows": len(results),
    }


def sql_rows_to_context(question: str, rows: List[Dict[str, Any]]) -> str:
    """Transforme les résultats SQL en pseudo-contexte textuel pour analyse."""
    if not rows:
        return f"Aucun résultat SQL trouvé pour la question : {question}"

    lines = [f"Résultats SQL pour la question : {question}"]

    for i, row in enumerate(rows, start=1):
        parts = [f"{k}={v}" for k, v in row.items()]
        lines.append(f"Ligne {i} : " + ", ".join(parts))

    return "\n".join(lines)

# =========================================================
# Tool principal
# =========================================================

def sql_tool(question: str) -> List[Dict[str, Any]]:
    """Pipeline complet : question → SQL → résultats."""
    payload = sql_tool_with_metadata(question)
    return payload["rows"]