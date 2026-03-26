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

DATABASE_FILE = os.path.join(DATABASE_DIR, "interactions.db")
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

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