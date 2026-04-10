"""Script d'indexation pour l'application RAG.
Ce script charge les fichiers depuis un répertoire local (ou après téléchargement/extraction d'un ZIP
depuis une URL), extrait le texte de ces fichiers, et construit un index Faiss pour la recherche.

Fonctions:
- run_indexing(input_directory: str, data_url: Optional[str] = None) -> None: Exécute le processus complet d'indexation.

etapes:
1. Téléchargement et extraction optionnels d'un ZIP depuis une URL.
2. Chargement et parsing des fichiers depuis le répertoire d'entrée.
3. Génération des chunks à partir des documents chargés.
4. Construction de l'index Faiss à partir des chunks générés.

Chaque étape gère les erreurs de manière robuste et fournit des logs détaillés pour faciliter le debugging et le suivi du processus.
"""

import argparse
import logging
from typing import Optional

from rag_pipeline.config import INPUT_DIR
from utils.data_loader import load_and_parse_files, download_and_extract_zip
from utils.chunking.reddit_chunker import chunk_reddit_document

from rag_pipeline.vector_store import VectorStoreManager
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def run_indexing(input_directory: str, data_url: Optional[str] = None) -> None:
    """Exécute le processus complet d'indexation.

    arguments:
    - input_directory: le répertoire contenant les fichiers à indexer
    - data_url: URL optionnelle pour télécharger et extraire un fichier inputs.zip

    retourne: None

    raise: Exception si une erreur critique se produit lors du téléchargement, de l'extraction, du chargement ou de l'indexation
    """
    logger.info("--- Démarrage du processus d'indexation ---")

    # Étape 1 : téléchargement / extraction optionnels
    if data_url:
        logger.info("Tentative de téléchargement depuis l'URL : %s", data_url)
        success = download_and_extract_zip(data_url, input_directory)
        if not success:
            logger.error("Échec du téléchargement ou de l'extraction. Arrêt.")
            return
    else:
        logger.info(
            "Aucune URL fournie. Utilisation des fichiers locaux dans : %s",
            input_directory,
        )

    # Étape 2 : chargement et parsing
    logger.info("Chargement et parsing des fichiers depuis : %s", input_directory)
    documents = load_and_parse_files(input_directory)

    if not documents:
        logger.warning(
            "Aucun document n'a été chargé ou parsé. Vérifiez le contenu du dossier d'entrée."
        )
        logger.info("--- Processus d'indexation terminé (aucun document traité) ---")
        return

    # Étape 3 : génération des chunks
    all_chunks = []

    for doc in documents:
        chunks = chunk_reddit_document(doc)

        # 🔥 CORRECTION : adapter le format pour le vector store
        for chunk in chunks:
            formatted_chunk = {
                "page_content": chunk.get("text", ""),  # clé attendue par vector_store
                "metadata": chunk.get("metadata", {}),
            }
            all_chunks.append(formatted_chunk)

    logger.info("Nombre de chunks générés : %s", len(all_chunks))

    if not all_chunks:
        logger.warning("Aucun chunk n'a été généré. Arrêt avant construction de l'index.")
        return

    # Étape 4 : création / mise à jour de l'index
    logger.info("Initialisation du gestionnaire de Vector Store...")
    vector_store = VectorStoreManager()

    logger.info("Construction de l'index Faiss (cela peut prendre du temps)...")
    vector_store.build_index(all_chunks)

    logger.info("--- Processus d'indexation terminé avec succès ---")
    logger.info("Nombre de documents traités : %s", len(documents))

    if vector_store.index:
        logger.info("Nombre de chunks indexés : %s", vector_store.index.ntotal)
    else:
        logger.warning("L'index final n'a pas pu être créé ou est vide.")


if __name__ == "__main__":
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Script d'indexation pour l'application RAG"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default=INPUT_DIR,
        help=f"Répertoire contenant les fichiers sources (par défaut : {INPUT_DIR})",
    )
    parser.add_argument(
        "--data-url",
        type=str,
        default=None,
        help="URL optionnelle pour télécharger et extraire un fichier inputs.zip",
    )

    args = parser.parse_args()
    run_indexing(input_directory=args.input_dir, data_url=args.data_url)