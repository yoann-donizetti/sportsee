import argparse
import logging
from typing import Optional

from rag_pipeline.config import INPUT_DIR
from utils.data_loader import download_and_extract_zip, load_and_parse_files
from rag_pipeline.vector_store import VectorStoreManager
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def run_indexing(input_directory: str, data_url: Optional[str] = None) -> None:
    """Exécute le processus complet d'indexation.

    Args:
        input_directory: Répertoire contenant les fichiers sources.
        data_url: URL optionnelle d'un fichier ZIP à télécharger et extraire.
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

    # Étape 3 : création / mise à jour de l'index
    logger.info("Initialisation du gestionnaire de Vector Store...")
    vector_store = VectorStoreManager()

    logger.info("Construction de l'index Faiss (cela peut prendre du temps)...")
    vector_store.build_index(documents)

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