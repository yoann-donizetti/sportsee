"""
ce module contient la fonction principale pour exécuter l'évaluation RAGAS en utilisant les lignes d'évaluation construites par le module RAGAS Builder.
Il utilise les fonctions d'évaluation de RAGAS pour calculer les métriques de performance du modèle sur les questions répondables, et vérifie les refus de répondre sur les questions non répondables.
Il retourne un DataFrame détaillé avec les résultats de l'évaluation pour chaque question, ainsi qu'un résumé des métriques globales et par catégorie.
Il gère également les cas où il n'y a pas de questions répondables ou non répondables, en assurant que les résultats sont cohérents et complets même dans ces scénarios.

"""

import logging
from pathlib import Path

from utils.config import (
    RAG_EVAL_DATASET_FILE,
    RAGAS_RESULTS_CSV_FILE,
    RAGAS_SUMMARY_JSON_FILE,
    RAGAS_LOG_FILE,
    RAGAS_SEARCH_K,
    MISTRAL_API_KEY,
    MODEL_NAME,
)

from evaluate.core.dataset_loader import load_eval_dataset
from evaluate.core.ragas_builder import build_ragas_rows
from evaluate.core.ragas_runner import run_ragas
from evaluate.core.saver import save_outputs


# ==============================
# Logging
# ==============================
Path(RAGAS_LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
    handlers=[
        logging.FileHandler(RAGAS_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def main() -> None:
    """
    Fonction principale pour exécuter l'évaluation RAGAS.
    Elle charge le dataset d'évaluation, construit les lignes d'évaluation en interrogeant
    le pipeline RAG, exécute l'évaluation RAGAS pour calculer les métriques de performance,
    et sauvegarde les résultats dans un fichier CSV et un résumé dans un fichier JSON.
     Elle affiche également un résumé des résultats dans la console.
     La fonction gère les cas où il n'y a pas de questions répondables ou non répondables, 
     en assurant que les résultats sont cohérents et complets même dans ces scénarios."""
    logging.info("=== Début du script evaluate_ragas ===")

    samples = load_eval_dataset(RAG_EVAL_DATASET_FILE)
    rows = build_ragas_rows(samples=samples, search_k=RAGAS_SEARCH_K)

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

    save_outputs(
        results_df=results_df,
        summary=summary,
        results_csv_file=RAGAS_RESULTS_CSV_FILE,
        summary_json_file=RAGAS_SUMMARY_JSON_FILE,
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

    logging.info("=== Fin du script evaluate_ragas ===")


if __name__ == "__main__":
    main()