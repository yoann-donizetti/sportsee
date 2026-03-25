"""
Ce module contient la fonction principale pour exécuter l'évaluation RAGAS
en utilisant les lignes d'évaluation construites par le module RAGAS Builder.

Il utilise les fonctions d'évaluation de RAGAS pour calculer les métriques
de performance du modèle sur les questions répondables, et vérifie les refus
de répondre sur les questions non répondables.

Il retourne un DataFrame détaillé avec les résultats de l'évaluation pour
chaque question, ainsi qu'un résumé des métriques globales et par catégorie.

Il gère également les cas où il n'y a pas de questions répondables ou non
répondables, en assurant que les résultats sont cohérents et complets même
dans ces scénarios.

Le script est instrumenté avec :
- logging : suivi technique de l'exécution ;
- Logfire : traçabilité des grandes étapes du protocole d'évaluation.
"""

import logging
from pathlib import Path

import logfire

from utils.config import (
    RAG_EVAL_DATASET_FILE,
    RAGAS_RESULTS_CSV_FILE,
    RAGAS_SUMMARY_JSON_FILE,
    RAGAS_LOG_FILE,
    RAGAS_SEARCH_K,
    MISTRAL_API_KEY,
    MODEL_NAME,
)
from utils.logging_config import setup_logging

from evaluate.core.dataset_loader import load_eval_dataset
from evaluate.core.ragas_builder import build_ragas_rows
from evaluate.core.ragas_runner import run_ragas
from evaluate.core.saver import save_outputs

logger = logging.getLogger(__name__)


def setup_ragas_logging() -> None:
    """
    Configure le logging pour le script d'évaluation RAGAS.

    Cette configuration :
    - applique le logging global du projet ;
    - ajoute un fichier de log dédié à l'évaluation RAGAS.

    Le fichier de log permet de conserver une trace exploitable
    de l'exécution du protocole d'évaluation.
    """
    setup_logging()

    Path(RAGAS_LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()

    # Vérifie qu'on n'ajoute pas plusieurs fois le même FileHandler
    file_handler_exists = any(
        isinstance(handler, logging.FileHandler)
        and Path(getattr(handler, "baseFilename", "")).resolve() == Path(RAGAS_LOG_FILE).resolve()
        for handler in root_logger.handlers
    )

    if not file_handler_exists:
        file_handler = logging.FileHandler(RAGAS_LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        )
        root_logger.addHandler(file_handler)


def main() -> None:
    """
    Exécute l'évaluation complète du pipeline RAG avec RAGAS.

    Étapes réalisées :
    - chargement du dataset d'évaluation ;
    - génération des réponses du pipeline RAG ;
    - calcul des métriques RAGAS ;
    - sauvegarde des résultats détaillés et du résumé ;
    - affichage d'un résumé des scores dans la console.
    """
    setup_ragas_logging()
    logfire.configure()

    logger.info("=== Début du script evaluate_ragas ===")

    samples = load_eval_dataset(RAG_EVAL_DATASET_FILE)
    logger.info("Dataset chargé avec %s questions.", len(samples))
    logfire.info("Dataset chargé", n_questions=len(samples))

    rows = build_ragas_rows(samples=samples, search_k=RAGAS_SEARCH_K)
    logger.info("%s lignes d'évaluation construites.", len(rows))
    logfire.info("Construction des lignes RAGAS", n_rows=len(rows), search_k=RAGAS_SEARCH_K)

    results_df, summary = run_ragas(
        rows=rows,
        model_name=MODEL_NAME,
        mistral_api_key=MISTRAL_API_KEY,
        active_metrics=[
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "context_recall",
        ],
    )

    logfire.info(
        "Évaluation RAGAS terminée",
        n_questions=summary["n_questions_total"],
        answerable_true=summary["n_answerable_true"],
        answerable_false=summary["n_answerable_false"],
    )

    save_outputs(
        results_df=results_df,
        summary=summary,
        results_csv_file=RAGAS_RESULTS_CSV_FILE,
        summary_json_file=RAGAS_SUMMARY_JSON_FILE,
    )

    logger.info("Résultats sauvegardés.")
    logfire.info(
        "Résultats sauvegardés",
        results_csv=RAGAS_RESULTS_CSV_FILE,
        summary_json=RAGAS_SUMMARY_JSON_FILE,
    )

    print("\n===== RAGAS =====")
    print(f"Nombre total de questions : {summary['n_questions_total']}")
    print(f"Questions answerable = true : {summary['n_answerable_true']}")
    print(f"Questions answerable = false : {summary['n_answerable_false']}")

    print("\n--- Scores questions answerable = true ---")
    for k, v in summary["answerable_true"]["means"].items():
        print(f"{k}: {v:.4f}")

    print("\n--- Robustesse questions answerable = false ---")
    print(f"refusal_rate: {summary['answerable_false']['refusal_rate']:.4f}")

    logger.info("=== Fin du script evaluate_ragas ===")


if __name__ == "__main__":
    main()