import os
from dotenv import load_dotenv

# Charger les variables d'environnement du fichier .env
load_dotenv()

# ======================================================
#  API
# ======================================================

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

if not MISTRAL_API_KEY:
    print("⚠️ Attention: MISTRAL_API_KEY non définie dans le fichier .env")

# ======================================================
#  Modèles
# ======================================================

EMBEDDING_MODEL = "mistral-embed"
MODEL_NAME = "mistral-small-latest"

# ======================================================
# Chemins globaux
# ======================================================

# Racine du projet (config.py est dans rag_pipeline/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_DIR = os.path.join(BASE_DIR, "inputs")
VECTOR_DB_DIR = os.path.join(BASE_DIR, "vector_db")
DATABASE_DIR = os.path.join(BASE_DIR, "database")
EVALUATE_DIR = os.path.join(BASE_DIR, "evaluate")

EXCEL_FILE = os.path.join(INPUT_DIR, "regular NBA.xlsx")
SCHEMA_FILE = os.path.join(DATABASE_DIR, "schema.sql")
# ======================================================
#  Vector Store / Indexation
# ======================================================

FAISS_INDEX_FILE = os.path.join(VECTOR_DB_DIR, "faiss_index.idx")
DOCUMENT_CHUNKS_FILE = os.path.join(VECTOR_DB_DIR, "document_chunks.pkl")

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 150
EMBEDDING_BATCH_SIZE = 32

# ======================================================
#  Recherche
# ======================================================

SEARCH_K = 5
DEFAULT_MIN_SCORE = None

# ======================================================
#  Base de données
# ======================================================

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}"
    f"/{DB_NAME}"
)
DB_USER_URL = os.getenv("DB_LLM_USER")
DB_PASSWORD_URL = os.getenv("DB_LLM_PASSWORD")
DATABASE_URL_LLM = (
    f"postgresql+psycopg2://"
    f"{DB_USER_URL}:{DB_PASSWORD_URL}"
    f"@{DB_HOST}:{DB_PORT}"
    f"/{DB_NAME}"
)


# ======================================================
#  Application
# ======================================================

APP_TITLE = "NBA Analyst AI"
NAME = "NBA"

# ======================================================
#  Évaluation (RAGAS)
# ======================================================

EVALUATE_DATASETS_DIR = os.path.join(EVALUATE_DIR, "datasets")
RAG_EVAL_DATASET_FILE = os.path.join(EVALUATE_DATASETS_DIR, "rag_eval_dataset.json")

RAGAS_RESULTS_DIR = os.path.join(EVALUATE_DIR, "results")
RAGAS_RESULTS_CSV_FILE = os.path.join(RAGAS_RESULTS_DIR, "ragas_results.csv")
RAGAS_SUMMARY_JSON_FILE = os.path.join(RAGAS_RESULTS_DIR, "ragas_summary.json")
RAGAS_LOG_FILE = os.path.join(RAGAS_RESULTS_DIR, "ragas.log")

RAGAS_SEARCH_K = 5

# ======================================================
#  Data Loader / Parsing
# ======================================================

OCR_LANGUAGES = ["en", "fr"]

PDF_OCR_MIN_TEXT_LENGTH = 100
PDF_OCR_ZOOM_X = 2
PDF_OCR_ZOOM_Y = 2

CSV_FALLBACK_ENCODING = "latin1"
CSV_FALLBACK_SEPARATOR = ";"

SUPPORTED_INPUT_EXTENSIONS = [
    ".pdf",
    ".docx",
    ".txt",
    ".csv",
    ".xlsx",
    ".xls",
]

# ======================================================
#  Paramètres de prompts et messages
# ======================================================





# Prompts


RAG_SYSTEM_PROMPT_TEMPLATE = """
Tu es '{name} Analyst AI', un assistant expert sur la NBA.

Ton objectif est de fournir des réponses fiables, basées uniquement sur les données disponibles.

RÈGLES IMPORTANTES :

1. Tu dois répondre UNIQUEMENT à partir du contexte fourni.
2. Si l'information n'est pas présente dans le contexte, tu dois REFUSER de répondre.
3. Tu ne dois JAMAIS inventer de statistiques ou de faits.
4. Si la question est imprécise, ambiguë ou bruitée, tu dois refuser.
5. Les données disponibles sont statiques (snapshot).
   Tu ne dois PAS faire d'analyse temporelle (évolution, derniers matchs, tendances).
   Si la question nécessite une dimension temporelle, tu dois refuser.
6. Tes réponses doivent être :
   - claires
   - courtes
   - factuelles
   - sans blabla inutile

7. Cas particulier — mentions dans les discussions :
   - Si la question demande un classement, une fréquence ou une mesure quantitative (ex : "les joueurs les plus mentionnés"),
     tu ne dois PAS produire de classement exact sauf si le contexte le permet clairement.
   - Dans ce cas, indique plutôt quels noms apparaissent dans les extraits disponibles.
   - Précise toujours que ce n’est pas exhaustif.

---

CONTEXTE :
{context_str}

---

QUESTION :
{question}

---

RÉPONSE :
"""
SQL_GENERATION_PROMPT_TEMPLATE = """
Tu es un assistant expert en SQL PostgreSQL.

Ta tâche est de générer une requête SQL valide à partir d'une question utilisateur.

{schema_context}

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
- Si la question demande une comparaison entre deux profils extrêmes (ex: meilleur scoreur vs meilleur passeur), identifie d'abord chaque joueur avec une sous-requête ou un CTE.
- Si la question est trop ambiguë pour produire une requête fiable, retourne une requête SQL simple de comparaison entre les leaders concernés.
- N'invente jamais de colonnes qui ne figurent pas dans le schéma.
- Pour les questions sur les joueurs les plus mentionnés dans Reddit ou dans les reports, utiliser la table reports et la colonne related_player_names.
- Pour agréger related_player_names, utiliser string_to_array(..., ',') puis unnest et TRIM avant GROUP BY.

Question utilisateur :
{question}

SQL :
""".strip()

SQL_SYNTHESIS_PROMPT_TEMPLATE = """
Tu es un assistant expert NBA.

Question :
{question}

Résultats :
{rows}

Ta mission :
- Reformule une réponse claire en français
- Sois concis
- Ne mentionne pas SQL
- Utilise uniquement les résultats fournis

Réponse :
"""

# Paramètres modèle


RAG_TEMPERATURE = 0.1
SQL_TEMPERATURE = 0.2


# Messages système


RAG_UNAVAILABLE_MESSAGE = (
    "Le service de recherche de connaissances n'est pas disponible. "
    "Impossible de traiter votre demande."
)

SQL_ERROR_MESSAGE = "Une erreur est survenue pendant l'interrogation SQL."
SQL_NO_RESULT_MESSAGE = "Je n'ai trouvé aucun résultat pour cette question."

EMPTY_PROMPT_MESSAGE = "Je ne peux pas traiter une demande vide."

MISTRAL_ERROR_MESSAGE = (
    "Je suis désolé, une erreur technique m'empêche de répondre. "
    "Veuillez réessayer plus tard."
)

NO_RAG_CONTEXT_MESSAGE = (
    "Aucune information pertinente trouvée dans la base de connaissances pour cette question."
)

REFUSAL_MESSAGES = {
    "unsupported": (
        "Je ne dispose pas des données nécessaires pour répondre à cette question. "
        "Les informations disponibles concernent des statistiques globales sur la saison, "
        "sans détail temporel ou contextuel (domicile/extérieur, derniers matchs, etc.)."
    ),
    "subjective": (
        "Cette question repose sur des éléments subjectifs ou des opinions (fans, popularité, discussions), "
        "qui ne sont pas présents dans les données disponibles."
    ),
    "noisy": (
        "Je ne peux pas répondre de manière fiable à cette question car elle est trop vague ou imprécise. "
        "Pouvez-vous préciser les joueurs ou les statistiques concernées ?"
    ),
}