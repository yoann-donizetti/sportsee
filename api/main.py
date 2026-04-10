import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from fastapi import FastAPI, HTTPException
import logging

from api.schemas import AskRequest, AskResponse

from rag_pipeline.rag_pipeline import poser_question, get_vector_store_manager
from database.load_excel_to_db import main as load_excel_to_db
from database.load_reports import main as load_reports
from indexer import run_indexing
from rag_pipeline.config import INPUT_DIR




logger = logging.getLogger(__name__)

vector_store_manager = None


# =========================================================
# STARTUP
# =========================================================

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store_manager

    logger.info("Chargement du vector store...")
    vector_store_manager = get_vector_store_manager()

    yield

    logger.info("Arrêt de l'application")


app = FastAPI(
    title="NBA Analyst AI API",
    description="API REST pour le système hybride (SQL + RAG + REFUS)",
    version="2.0.0",
    lifespan=lifespan,
)


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():
    return {"status": "ok"}
# =========================================================
# Redirect root to docs
# =========================================================

from fastapi.responses import RedirectResponse

@app.get("/")
def root():
    return RedirectResponse(url="/docs")

# =========================================================
# ASK
# =========================================================

@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    try:
        result = poser_question(
            prompt=payload.question,
            vector_store_manager=vector_store_manager,
        )

        return AskResponse(
            question=result["question"],
            answer=result["answer"],
            route_used=result.get("route_used", ""),
            sql_success=result.get("sql_success", False),
            plot_path=result.get("plot_path", ""),
        )

    except Exception as e:
        logger.error(f"Erreur /ask : {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# DATA RELOAD
# =========================================================

@app.post("/data/reload")
def reload_data():
    try:
        logger.info("Rechargement des données...")

        load_excel_to_db()
        load_reports()

        return {
            "status": "ok",
            "message": "Données rechargées avec succès"
        }

    except Exception as e:
        logger.error(f"Erreur reload data : {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# INDEX REBUILD
# =========================================================

@app.post("/index/rebuild")
def rebuild_faiss():
    try:
        logger.info("Reconstruction de l'index FAISS...")

        run_indexing(input_directory=INPUT_DIR)

        return {
            "status": "ok",
            "message": "Index FAISS reconstruit avec succès"
        }

    except Exception as e:
        logger.error(f"Erreur rebuild index : {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# SYSTEM REBUILD (FULL PIPELINE)
# =========================================================

@app.post("/system/rebuild")
def rebuild_system():
    try:
        logger.info("Rebuild complet du système...")

        load_excel_to_db()
        load_reports()
        run_indexing(input_directory=INPUT_DIR)

        return {
            "status": "ok",
            "message": "Système entièrement reconstruit (data + index)"
        }

    except Exception as e:
        logger.error(f"Erreur system rebuild : {e}")
        raise HTTPException(status_code=500, detail=str(e))