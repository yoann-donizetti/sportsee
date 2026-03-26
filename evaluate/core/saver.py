import csv
import json
import logging
from pathlib import Path
import pandas as pd

from evaluate.core.cleaning import clean_results_for_analysis


def save_outputs(
    results_df: pd.DataFrame,
    summary: dict,
    results_csv_file: str,
    summary_json_file: str,
) -> None:
    """
    Sauvegarde les résultats de l'évaluation dans un fichier CSV et un résumé dans un fichier JSON.
    Args:
    results_df: DataFrame contenant les résultats détaillés de l'évaluation.
    summary: Dictionnaire contenant le résumé des métriques globales et par catégorie.
    results_csv_file: Chemin vers le fichier CSV où les résultats détaillés seront sauvegardés.
    summary_json_file: Chemin vers le fichier JSON où le résumé sera sauvegardé.
    Raises:
    IOError: Si une erreur survient lors de la sauvegarde des fichiers.
    """
    Path(results_csv_file).parent.mkdir(parents=True, exist_ok=True)

    df_clean = clean_results_for_analysis(results_df)

    df_clean.to_csv(
        results_csv_file,
        index=False,
        sep=";",
        encoding="utf-8-sig",
        quoting=csv.QUOTE_ALL,
    )

    logging.info(f"CSV sauvegardé : {results_csv_file}")

    with open(summary_json_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logging.info(f"Résumé sauvegardé : {summary_json_file}")