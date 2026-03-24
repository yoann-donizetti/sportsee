"""Script d'évaluation RAGAS pour un pipeline RAG utilisant MistralAI.
Ce script réalise les étapes suivantes :
1. Chargement et validation du dataset d'évaluation à partir d'un fichier JSON.
2. Pour chaque question du dataset, pose la question au pipeline RAG et construit une ligne d'évaluation.
3. Exécution de l'évaluation RAGAS en calculant les métriques pour les questions answerable = True et en vérifiant les refus pour les questions answerable = False.
4. Sauvegarde des résultats détaillés dans un fichier CSV et du résumé dans un fichier JSON.
5. Affichage d'un résumé des scores et de la robustesse dans la console.
Le script utilise les bibliothèques suivantes :
- json : pour la manipulation de fichiers JSON.
- logging : pour la gestion des logs d'exécution.
- pathlib : pour la gestion des chemins de fichiers.
- typing : pour les annotations de type.
- pandas : pour la manipulation de DataFrames.
- datasets : pour la gestion des datasets d'évaluation.
- pydantic : pour la validation des données d'entrée.
- ragas : pour l'évaluation RAGAS et les métriques associées.
- langchain_mistralai : pour l'intégration du modèle MistralAI en tant que LLM et pour les embeddings.
- utils.config : pour la gestion des configurations et des chemins de fichiers.
- utils.rag_pipeline : pour l'interaction avec le pipeline RAG et la gestion du vector store.
"""
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
from datasets import Dataset
from pydantic import BaseModel, Field, ValidationError

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings

from utils.config import (
    RAG_EVAL_DATASET_FILE,
    RAGAS_RESULTS_CSV_FILE,
    RAGAS_SUMMARY_JSON_FILE,
    RAGAS_LOG_FILE,
    RAGAS_SEARCH_K,
    MISTRAL_API_KEY,
    MODEL_NAME,
)
from utils.rag_pipeline import get_vector_store_manager, poser_question


# ==============================
# Logging
# ==============================
# Assure que le dossier de logs existe
Path(RAGAS_LOG_FILE).parent.mkdir(parents=True, exist_ok=True) 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
    handlers=[
        logging.FileHandler(RAGAS_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)


# ==============================
# Validation dataset
# ==============================
class EvalSample(BaseModel):
    """Représente un échantillon de question pour l'évaluation RAGAS.
    id: Identifiant unique de la question (entier positif).
    question: Texte de la question posée au modèle.
    ground_truth: Réponse attendue (texte) pour la question.
    category: Catégorie de la question
    answerable: Indique si la question est censée être answerable (True) ou non (False).

    """
    id: int = Field(..., ge=1)
    question: str = Field(..., min_length=3)
    ground_truth: str = Field(..., min_length=3)
    category: str = Field(..., min_length=2)
    answerable: bool


# ==============================
# Chargement dataset
# ==============================
def load_eval_dataset(dataset_path: str) -> list[EvalSample]:

    """Charge et valide le dataset d'évaluation RAGAS à partir d'un fichier JSON.
    Le fichier JSON doit être une liste d'objets, chacun représentant une question d'évaluation avec les champs suivants :
- id (int) : Identifiant unique de la question (doit être un entier positif).
- question (str) : Texte de la question posée au modèle (doit être une chaîne de caractères d'au moins 3 caractères).
- ground_truth (str) : Réponse attendue pour la question (doit être une chaîne de caractères d'au moins 3 caractères).
- category (str) : Catégorie de la question (doit être une chaîne de caractères d'au moins 2 caractères).
- answerable (bool) : Indique si la question est censée être answerable (True) ou non (False).

    Args:
        dataset_path (str): Chemin vers le fichier JSON du dataset d'évaluation.
    Returns:
        list[EvalSample]: Liste d'échantillons validés pour l'évaluation RAGAS.
    Raises:
        ValidationError: Si une ligne du dataset est invalide.
    """
    logging.info(f"Chargement du dataset depuis : {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    samples: list[EvalSample] = []
    for row in raw_data:
        try:
            sample = EvalSample(**row)
            samples.append(sample)
        except ValidationError as e:
            logging.error(f"Ligne invalide dans le dataset : {row}")
            logging.error(e.json())
            raise

    logging.info(f"{len(samples)} questions validées avec Pydantic.")
    return samples


# ==============================
# Génération réponses RAG
# ==============================
def build_ragas_rows(samples: list[EvalSample]) -> list[dict[str, Any]]:
    """Pour chaque question du dataset, pose la question au pipeline RAG et construit une ligne d'évaluation contenant :
        - id : Identifiant de la question
        - question : Texte de la question
        - ground_truth : Réponse attendue
        - category : Catégorie de la question
        - answerable : Indique si la question est censée être answerable
        - answer : Réponse générée par le modèle
        - contexts : Contextes récupérés par le modèle
        - nb_contexts : Nombre de contextes récupérés
    Args:
        samples (list[EvalSample]): Liste d'échantillons d'évaluation.
    Returns:
        list[dict[str, Any]]: Liste de lignes d'évaluation construites pour chaque question.
    """

    logging.info("Construction des lignes d'évaluation...")

    vector_store_manager = get_vector_store_manager()
    if vector_store_manager is None:
        raise RuntimeError("VectorStoreManager non disponible")

    rows: list[dict[str, Any]] = []

    for sample in samples:
        logging.info(f"Question id={sample.id}")

        result = poser_question(
            prompt=sample.question,
            vector_store_manager=vector_store_manager,
            k=RAGAS_SEARCH_K
        )

        retrieved_contexts = [res["text"] for res in result["search_results"]]

        rows.append({
            "id": sample.id,
            "question": sample.question,
            "ground_truth": sample.ground_truth,
            "category": sample.category,
            "answerable": sample.answerable,
            "answer": result["answer"],
            "contexts": retrieved_contexts,
            "nb_contexts": len(retrieved_contexts),
        })

    logging.info(f"{len(rows)} lignes construites pour RAGAS.")
    return rows


# ==============================
# LLM + Embeddings Mistral
# ==============================
def get_ragas_llm():
    """
    Crée une instance de LangchainLLMWrapper utilisant le modèle ChatMistralAI pour l'évaluation RAGAS.
    Le modèle utilisé est défini par la variable MODEL_NAME et nécessite une clé API MISTRAL_API_KEY pour fonctionner.
    Returns: LangchainLLMWrapper: Instance de LangchainLLMWrapper utilisant ChatMistralAI.
    """
    return LangchainLLMWrapper(
        ChatMistralAI(
            model=MODEL_NAME,
            mistral_api_key=MISTRAL_API_KEY
        )
    )


def get_ragas_embeddings():
    """Crée une instance de LangchainEmbeddingsWrapper utilisant MistralAIEmbeddings pour l'évaluation RAGAS.
    Le modèle d'embeddings utilisé est "mistral-embed" et nécessite une clé API MISTRAL_API_KEY pour fonctionner.
    Returns: LangchainEmbeddingsWrapper: Instance de LangchainEmbeddingsWrapper utilisant MistralAIEmbeddings.
    """
    return LangchainEmbeddingsWrapper(
        MistralAIEmbeddings(
            model="mistral-embed",
            mistral_api_key=MISTRAL_API_KEY
        )
    )


# ==============================
# Robustesse : refus correct
# ==============================
def is_refusal(answer: str) -> bool:
    """Détermine si la réponse du modèle est un refus correct de répondre à une question non answerable.
    La fonction vérifie si la réponse contient des expressions indiquant que le modèle ne peut pas répondre 
    en raison d'un manque d'information ou d'une impossibilité de déterminer la réponse.
    Args:        answer (str): Réponse générée par le modèle.
    Returns: bool: True si la réponse est un refus correct, False sinon.
    """
    if not isinstance(answer, str):
        return False

    refusal_keywords = [
        "je ne sais pas",
        "impossible de déterminer",
        "pas d'information",
        "données insuffisantes",
        "je n'ai pas assez d'informations",
        "je ne peux pas déterminer",
        "non évaluable",
        "information non disponible",
    ]

    answer_lower = answer.lower()
    return any(keyword in answer_lower for keyword in refusal_keywords)


# ==============================
# Évaluation RAGAS
# ==============================
def run_ragas(rows: list[dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Exécute l'évaluation RAGAS sur les lignes construites à partir du dataset d'évaluation.
    La fonction sépare les questions en deux groupes : celles avec answerable = True 
    et celles avec answerable = False. 
    Pour les questions answerable = True, elle utilise la fonction evaluate de RAGAS pour calculer 
    les métriques de faithfulness, answer_relevancy, context_precision et context_recall. 
    Pour les questions answerable = False, elle vérifie si le modèle a correctement refusé de répondre. Enfin, elle fusionne les résultats et construit un résumé des scores et de la robustesse.
    Args:        rows (list[dict[str, Any]]): Liste de lignes d'évaluation construites pour chaque question.
    Returns: tuple[pd.DataFrame, dict[str, Any]]: Un DataFrame contenant les résultats détaillés de l'évaluation pour chaque question,
    et un dictionnaire résumant les scores moyens et la robustesse.
    """
    logging.info("Lancement RAGAS...")

    rows_true = [row for row in rows if row["answerable"]]
    rows_false = [row for row in rows if not row["answerable"]]

    # ------------------------------
    # Partie RAGAS : answerable = True
    # ------------------------------
    if rows_true:
        ragas_dataset = Dataset.from_dict({
            "question": [r["question"] for r in rows_true],
            "ground_truth": [r["ground_truth"] for r in rows_true],
            "answer": [r["answer"] for r in rows_true],
            "contexts": [r["contexts"] for r in rows_true],
        })

        llm = get_ragas_llm()
        embeddings = get_ragas_embeddings()

        result = evaluate(
            dataset=ragas_dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            ],
            llm=llm,
            embeddings=embeddings,
            raise_exceptions=False,
        )

        ragas_df = result.to_pandas().reset_index(drop=True)
        meta_true_df = pd.DataFrame(rows_true).reset_index(drop=True)

        # On enlève les colonnes déjà présentes dans meta_true_df
        duplicate_cols = [col for col in ragas_df.columns if col in meta_true_df.columns]
        ragas_df = ragas_df.drop(columns=duplicate_cols, errors="ignore")

        ragas_true_df = pd.concat([meta_true_df, ragas_df], axis=1)
    else:
        ragas_true_df = pd.DataFrame()

    # ------------------------------
    # Partie robustesse : answerable = False
    # ------------------------------
    if rows_false:
        false_df = pd.DataFrame(rows_false).reset_index(drop=True).copy()
        false_df["faithfulness"] = None
        false_df["answer_relevancy"] = None
        false_df["context_precision"] = None
        false_df["context_recall"] = None
        false_df["refusal_ok"] = false_df["answer"].apply(is_refusal)
    else:
        false_df = pd.DataFrame()

    # ------------------------------
    # Fusion finale
    # ------------------------------
    final_df = pd.concat(
        [ragas_true_df, false_df],
        ignore_index=True,
        sort=False
    )

    metric_cols = [
        col for col in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
        if col in final_df.columns
    ]

    summary = {
        "n_questions_total": int(len(final_df)),
        "n_answerable_true": int(len(rows_true)),
        "n_answerable_false": int(len(rows_false)),
        "metric_columns": metric_cols,
    }

    # Scores answerable = true
    if not ragas_true_df.empty and metric_cols:
        summary["global_means"] = {
            col: float(ragas_true_df[col].mean(skipna=True))
            for col in metric_cols
        }

        summary["by_category_answerable_true"] = (
            ragas_true_df.groupby("category")[metric_cols]
            .mean(numeric_only=True)
            .round(4)
            .to_dict(orient="index")
        )

        summary["answerable_true"] = {
            "n_questions": int(len(rows_true)),
            "means": {
                col: float(ragas_true_df[col].mean(skipna=True))
                for col in metric_cols
            }
        }
    else:
        summary["global_means"] = {}
        summary["by_category_answerable_true"] = {}
        summary["answerable_true"] = {
            "n_questions": 0,
            "means": {}
        }

    # Robustesse answerable = false
    if not false_df.empty:
        refusal_rate = float(false_df["refusal_ok"].mean()) if len(false_df) > 0 else 0.0

        summary["answerable_false"] = {
            "n_questions": int(len(rows_false)),
            "refusal_rate": refusal_rate,
            "n_refusal_ok": int(false_df["refusal_ok"].sum()),
            "n_refusal_ko": int((~false_df["refusal_ok"]).sum()),
        }
    else:
        summary["answerable_false"] = {
            "n_questions": 0,
            "refusal_rate": 0.0,
            "n_refusal_ok": 0,
            "n_refusal_ko": 0,
        }

    logging.info("Évaluation RAGAS terminée.")
    return final_df, summary


# ==============================
# Nettoyage des résultats
# ==============================
def clean_results_for_analysis(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoie le DataFrame des résultats RAGAS afin d'obtenir un fichier de sortie
    plus lisible et plus simple à analyser.

    Objectifs :
    - supprimer les éventuelles colonnes dupliquées issues des fusions précédentes,
    - conserver uniquement les colonnes utiles à l'analyse,
    - nettoyer le format de la réponse générée,
    - arrondir les métriques pour améliorer la lisibilité,
    - ajouter une lecture qualitative du résultat,
    - ajouter un indicateur booléen de correction.

    Args:
        results_df (pd.DataFrame):
            DataFrame brut contenant les résultats détaillés de l'évaluation.

    Returns:
        pd.DataFrame:
            DataFrame nettoyé, prêt à être exporté en CSV pour analyse.
    """

    # Supprime les colonnes dupliquées en conservant la première occurrence.
    # Cela évite les problèmes générés par certaines concaténations de DataFrames.
    df = results_df.loc[:, ~results_df.columns.duplicated()].copy()

    # Liste des colonnes que l'on souhaite conserver dans le fichier final.
    # On garde uniquement les informations réellement utiles pour l'analyse métier.
    cols_to_keep = [
        "id",
        "category",
        "answerable",
        "question",
        "ground_truth",
        "answer",
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
        "refusal_ok",
    ]

    # Filtre la liste précédente pour ne garder que les colonnes réellement présentes.
    # Cela rend la fonction plus robuste si certaines colonnes n'existent pas.
    cols_to_keep = [col for col in cols_to_keep if col in df.columns]
    df = df[cols_to_keep].copy()

    def clean_answer(text):
        """
        Nettoie une réponse textuelle générée par le modèle.

        Traitements réalisés :
        - si la valeur n'est pas une chaîne, elle est renvoyée telle quelle,
        - suppression des retours à la ligne,
        - réduction des espaces multiples en un seul espace,
        - conservation de la réponse complète (pas de troncature).

        Args:
            text:
                Texte de la réponse à nettoyer.

        Returns:
            str | Any:
                Réponse nettoyée.
        """
        if not isinstance(text, str):
            return text

        # Remplace les retours à la ligne par des espaces
        # afin d'obtenir une réponse lisible sur une seule ligne dans le CSV.
        text = text.replace("\n", " ")

        # Réduit les espaces multiples à un seul espace.
        text = " ".join(text.split())

        return text

    # Applique le nettoyage aux réponses si la colonne existe.
    if "answer" in df.columns:
        df["answer"] = df["answer"].apply(clean_answer)

    # Liste des colonnes de métriques numériques.
    metric_cols = [
        col for col in [
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "context_recall",
        ]
        if col in df.columns
    ]

    # Arrondit les métriques à 3 décimales pour faciliter la lecture.
    if metric_cols:
        df[metric_cols] = df[metric_cols].round(3)

    def interpret(row):
        """
        Produit une lecture qualitative du résultat pour une ligne donnée.

        Règles :
        - si la question est non answerable :
            - "Bon refus" si le modèle a correctement refusé,
            - "Hallucination" sinon.
        - si la question est answerable :
            - "Très bon" si answer_relevancy >= 0.8 et context_precision >= 0.8
            - "Correct" si answer_relevancy >= 0.5
            - "Faible" sinon

        Args:
            row (pd.Series):
                Ligne du DataFrame.

        Returns:
            str:
                Libellé qualitatif de la performance.
        """
        if row.get("answerable") is False:
            if row.get("refusal_ok") is True:
                return "Bon refus"
            return "Hallucination"

        ar = row.get("answer_relevancy")
        cp = row.get("context_precision")

        if pd.notna(ar) and pd.notna(cp) and ar >= 0.8 and cp >= 0.8:
            return "Très bon"
        elif pd.notna(ar) and ar >= 0.5:
            return "Correct"
        else:
            return "Faible"

    # Ajoute une colonne de lecture qualitative.
    df["lecture"] = df.apply(interpret, axis=1)

    def compute_correct(row):
        """
        Détermine si le comportement du modèle peut être considéré comme correct.

        Règles :
        - pour une question non answerable :
            le résultat est correct si refusal_ok vaut True.
        - pour une question answerable :
            le résultat est considéré correct si answer_relevancy >= 0.8.

        Args:
            row (pd.Series):
                Ligne du DataFrame.

        Returns:
            bool:
                True si le comportement est jugé correct, False sinon.
        """
        if row.get("answerable") is False:
            return bool(row.get("refusal_ok"))

        ar = row.get("answer_relevancy")
        return pd.notna(ar) and ar >= 0.8

    # Ajoute une colonne booléenne indiquant si le résultat est jugé correct.
    df["is_correct"] = df.apply(compute_correct, axis=1)

    return df


# ==============================
# Sauvegarde
# ==============================
def save_outputs(results_df: pd.DataFrame, summary: dict[str, Any]) -> None:
    """Sauvegarde les résultats détaillés de l'évaluation RAGAS dans un fichier CSV et le résumé dans un fichier JSON.
    La fonction s'assure que les dossiers de destination existent avant d'écrire les fichiers.
    Args:
        results_df (pd.DataFrame): DataFrame contenant les résultats détaillés de l'évaluation pour chaque question.
        summary (dict[str, Any]): Dictionnaire résumant les scores moyens et la robustesse."""
    Path(RAGAS_RESULTS_CSV_FILE).parent.mkdir(parents=True, exist_ok=True)

    # CSV final lisible
    clean_df = clean_results_for_analysis(results_df)
    clean_df.to_csv(RAGAS_RESULTS_CSV_FILE, index=False, encoding="utf-8")
    logging.info(f"Résultats RAGAS sauvegardés : {RAGAS_RESULTS_CSV_FILE}")

    # JSON summary
    with open(RAGAS_SUMMARY_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logging.info(f"Résumé sauvegardé : {RAGAS_SUMMARY_JSON_FILE}")


# ==============================
# Main
# ==============================
def main() -> None:
    """Point d'entrée du script d'évaluation RAGAS.
    La fonction réalise les étapes suivantes :
    1. Charge et valide le dataset d'évaluation à partir d'un fichier JSON.
    2. Pour chaque question du dataset, pose la question au pipeline RAG et construit une ligne d'évaluation.
    3. Exécute l'évaluation RAGAS en calculant les métriques pour les questions answerable = True et en vérifiant les refus pour les questions answerable = False.
    4. Sauvegarde les résultats détaillés dans un fichier CSV et le résumé dans un fichier JSON.
    5. Affiche un résumé des scores et de la robustesse dans la console.
    """
    logging.info("=== Début du script evaluate_ragas ===")

    samples = load_eval_dataset(RAG_EVAL_DATASET_FILE)
    rows = build_ragas_rows(samples)
    results_df, summary = run_ragas(rows)
    save_outputs(results_df, summary)

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