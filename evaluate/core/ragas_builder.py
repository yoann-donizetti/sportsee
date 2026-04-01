"""Ce module contient des fonctions pour construire les lignes d'évaluation RAGAS en interrogeant le pipeline RAG pour chaque question du dataset.
Pour chaque question, elle récupère la réponse générée par le modèle ainsi que les contextes utilisés pour générer la réponse. Elle construit ensuite une liste de dictionnaires contenant les informations suivantes :
- id : Identifiant unique de la question.
- question : Texte de la question.
- ground_truth : Réponse correcte à la question.
- category : Catégorie de la question.
- answerable : Indique si la question est répondable.
- answer : Réponse générée par le modèle.
- contexts : Liste des contextes récupérés par le pipeline RAG.
- nb_contexts : Nombre de contextes récupérés.
"""
import logging
from typing import Any

from rag_pipeline.rag_pipeline import get_vector_store_manager, poser_question


def build_ragas_rows(samples: list[Any], search_k: int) -> list[dict[str, Any]]:
    """
    Construit les lignes d'évaluation en interrogeant le pipeline RAG pour chaque question du dataset.
    Pour chaque question, elle récupère la réponse générée par le modèle ainsi que les contextes utilisés pour générer la réponse. Elle construit ensuite une liste de dictionnaires contenant les informations suivantes :
- id : Identifiant unique de la question.
- question : Texte de la question.
- ground_truth : Réponse correcte à la question.
- category : Catégorie de la question.
- answerable : Indique si la question est répondable.
- answer : Réponse générée par le modèle.
- contexts : Liste des contextes récupérés par le pipeline RAG.
- nb_contexts : Nombre de contextes récupérés.


    Args:
        samples: Liste des questions d'évaluation.
        search_k: Nombre de contextes à récupérer.

    Returns:
        Liste de dictionnaires contenant question, réponse, contextes, etc.
    Raises:
        RuntimeError: Si le VectorStoreManager n'est pas disponible.
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
            k=search_k,
        )

        retrieved_contexts = [res["text"] for res in result["search_results"]]

        rows.append(
            {
                "id": sample.id,
                "question": sample.question,
                "ground_truth": sample.ground_truth,
                "category": sample.category,
                "answerable": sample.answerable,
                "answer": result["answer"],
                "contexts": retrieved_contexts,
                "nb_contexts": len(retrieved_contexts),
                "route_used": result.get("route_used", "UNKNOWN"),
                "sql_success": result.get("sql_success", False),
            }
        )

    logging.info(f"{len(rows)} lignes construites pour RAGAS.")
    return rows