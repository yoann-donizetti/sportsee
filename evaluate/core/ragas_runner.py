"""Module RAGAS Runner
Ce module contient la fonction principale pour exécuter l'évaluation 
RAGAS en utilisant les lignes d'évaluation construites par le module RAGAS Builder.
Il utilise les fonctions d'évaluation de RAGAS pour calculer les métriques de performance
du modèle sur les questions répondables, et vérifie les refus de répondre sur les questions non répondables.
Il retourne un DataFrame détaillé avec les résultats de l'évaluation pour chaque question,
ainsi qu'un résumé des métriques globales et par catégorie.
Il gère également les cas où il n'y a pas de questions répondables ou non répondables,
en assurant que les résultats sont cohérents et complets même dans ces scénarios."""
import logging
from typing import Any

import pandas as pd
from datasets import Dataset

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings


def get_ragas_llm(model_name: str, mistral_api_key: str) -> LangchainLLMWrapper:
    """
    Instancie le LLM utilisé par RAGAS.
     - model_name : Nom du modèle Mistral à utiliser comme judge.
     - mistral_api_key : Clé API Mistral.
     args :
    - model_name : Nom du modèle Mistral à utiliser comme judge.
     Returns:
        LangchainLLMWrapper encapsulant le modèle Mistral spécifié.
    raises:
    RuntimeError: Si le modèle spécifié n'est pas disponible ou si la clé API est invalide.

    """
    return LangchainLLMWrapper(
        ChatMistralAI(
            model=model_name,
            mistral_api_key=mistral_api_key,
        )
    )


def get_ragas_embeddings(mistral_api_key: str) -> LangchainEmbeddingsWrapper:
    """
    Instancie les embeddings utilisés par RAGAS.
    args :
    - mistral_api_key : Clé API Mistral.
    Returns:
    LangchainEmbeddingsWrapper encapsulant les embeddings Mistral.
    raises:
    RuntimeError: Si les embeddings ne sont pas disponibles ou si la clé API est invalide
    """
    return LangchainEmbeddingsWrapper(
        MistralAIEmbeddings(
            model="mistral-embed",
            mistral_api_key=mistral_api_key,
        )
    )


def is_refusal(answer: str) -> bool:
    """
Détermine si une réponse est un refus de répondre plutôt qu'une réponse informative.
Cette fonction vérifie si la réponse contient des expressions indiquant que le modèle refuse de répondre 
ou ne peut pas fournir une réponse précise.
Args:
    answer: La réponse générée par le modèle à analyser.
Returns:
    True si la réponse est un refus de répondre, False sinon.
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


def run_ragas(
    rows: list[dict[str, Any]],
    model_name: str,
    mistral_api_key: str,
    active_metrics: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Exécute l'évaluation RAGAS et retourne :
    - final_df : résultats détaillés
    - summary : résumé des métriques

    Args:
        rows: Lignes d'évaluation construites depuis le pipeline RAG.
        model_name: Nom du modèle Mistral utilisé comme judge.
        mistral_api_key: Clé API Mistral.
        active_metrics: Liste des métriques à activer.

    Returns:
        Tuple (DataFrame résultats, dictionnaire summary)
    Raises:
        RuntimeError: Si une erreur survient lors de l'évaluation RAGAS.

    """
    logging.info("Lancement RAGAS...")

    if active_metrics is None:
        active_metrics = [
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "context_recall",
        ]

    metric_objects = {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
        "context_recall": context_recall,
    }

    selected_metrics = [metric_objects[name] for name in active_metrics]

    rows_true = [row for row in rows if row["answerable"]]
    rows_false = [row for row in rows if not row["answerable"]]

    if rows_true:
        ragas_dataset = Dataset.from_dict(
            {
                "question": [r["question"] for r in rows_true],
                "ground_truth": [r["ground_truth"] for r in rows_true],
                "answer": [r["answer"] for r in rows_true],
                "contexts": [r["contexts"] for r in rows_true],
            }
        )

        llm = get_ragas_llm(model_name=model_name, mistral_api_key=mistral_api_key)
        embeddings = get_ragas_embeddings(mistral_api_key=mistral_api_key)

        result = evaluate(
            dataset=ragas_dataset,
            metrics=selected_metrics,
            llm=llm,
            embeddings=embeddings,
            raise_exceptions=False,
        )

        ragas_df = result.to_pandas().reset_index(drop=True)
        meta_true_df = pd.DataFrame(rows_true).reset_index(drop=True)

        duplicate_cols = [col for col in ragas_df.columns if col in meta_true_df.columns]
        ragas_df = ragas_df.drop(columns=duplicate_cols, errors="ignore")

        ragas_true_df = pd.concat([meta_true_df, ragas_df], axis=1)
    else:
        ragas_true_df = pd.DataFrame()

    if rows_false:
        false_df = pd.DataFrame(rows_false).reset_index(drop=True).copy()
        for col in active_metrics:
            false_df[col] = None
        false_df["refusal_ok"] = false_df["answer"].apply(is_refusal)
    else:
        false_df = pd.DataFrame()

    final_df = pd.concat(
        [ragas_true_df, false_df],
        ignore_index=True,
        sort=False,
    )

    metric_cols = [col for col in active_metrics if col in final_df.columns]

    for col in metric_cols:
        final_df[col] = pd.to_numeric(final_df[col], errors="coerce")

    summary: dict[str, Any] = {
        "n_questions_total": int(len(final_df)),
        "n_answerable_true": int(len(rows_true)),
        "n_answerable_false": int(len(rows_false)),
        "metric_columns": metric_cols,
    }

    if rows_true and metric_cols:
        true_mask = final_df["answerable"] == True

        summary["global_means"] = {
            col: float(final_df.loc[true_mask, col].mean(skipna=True))
            for col in metric_cols
        }

        summary["by_category_answerable_true"] = (
            final_df.loc[true_mask]
            .groupby("category")[metric_cols]
            .mean(numeric_only=True)
            .round(4)
            .to_dict(orient="index")
        )

        summary["answerable_true"] = {
            "n_questions": int(len(rows_true)),
            "means": {
                col: float(final_df.loc[true_mask, col].mean(skipna=True))
                for col in metric_cols
            },
        }
    else:
        summary["global_means"] = {}
        summary["by_category_answerable_true"] = {}
        summary["answerable_true"] = {
            "n_questions": 0,
            "means": {},
        }

    if rows_false:
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