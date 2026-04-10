"""Pipeline RAG pour l'application NBA Analyst AI.

Ce module contient la logique Retrieval-Augmented Generation (RAG) :
- chargement du Vector Store ;
- recherche des documents pertinents ;
- construction du contexte ;
- construction du prompt ;
- appel au modèle Mistral pour générer une réponse.

Il est utilisé par l'application principale et peut aussi servir
pour les scripts d'évaluation.

Le pipeline est instrumenté avec :
- logging : suivi technique de l'exécution ;
- Logfire : traçabilité des étapes clés du RAG
  (question, retrieval, contexte, prompt, réponse).
"""

import logging
from typing import Optional

import logfire
from mistralai.models.chat_completion import ChatMessage

from .config import (
    MISTRAL_API_KEY,
    MODEL_NAME,
    NAME,
    SEARCH_K,
    RAG_SYSTEM_PROMPT_TEMPLATE,
    SQL_SYNTHESIS_PROMPT_TEMPLATE,
    RAG_TEMPERATURE,
    SQL_TEMPERATURE,
    RAG_UNAVAILABLE_MESSAGE,
    SQL_ERROR_MESSAGE,
    SQL_NO_RESULT_MESSAGE,
    EMPTY_PROMPT_MESSAGE,
    MISTRAL_ERROR_MESSAGE,
    NO_RAG_CONTEXT_MESSAGE,
)
from .vector_store import VectorStoreManager
from evaluate.core.schemas import RagPipelineOutput
from rag_pipeline.router import (
    is_sql_question,
    is_unsupported_question,
    is_noisy_question,
    is_subjective_question,
    is_reports_question,
    build_refusal_answer,
    is_plot_question,
)

from rag_pipeline.tools.plot_tool import build_plot, PlotToolInput
from rag_pipeline.tools.plot_utils import (
    sql_rows_to_plot_data,
    build_plot_title,
)

from rag_pipeline.tools.sql_tool import (
    sql_tool_with_metadata,
    sql_rows_to_context,
)
from rag_pipeline.llm_utils import ask_mistral

logger = logging.getLogger(__name__)

# Initialisation de Logfire pour tracer les étapes du pipeline RAG
logfire.configure(send_to_logfire=False)







def get_vector_store_manager() -> Optional[VectorStoreManager]:
    """Charge le VectorStoreManager.

    Returns:
        Une instance de VectorStoreManager si le chargement réussit,
        sinon None.

    Notes:
        Cette fonction peut être mise en cache côté application
        pour éviter de recharger l'index à chaque interaction.
    """
    logger.info("Tentative de chargement du VectorStoreManager...")

    try:
        manager = VectorStoreManager()

        if manager.index is None or not manager.document_chunks:
            logger.error("Index Faiss ou chunks non trouvés/chargés par VectorStoreManager.")
            return None

        logger.info(
            "VectorStoreManager chargé avec succès (%s vecteurs).",
            manager.index.ntotal,
        )
        return manager

    except FileNotFoundError:
        logger.error("FileNotFoundError lors de l'initialisation de VectorStoreManager.")
        return None
    except Exception:
        logger.exception("Erreur chargement VectorStoreManager")
        return None


def generer_reponse(prompt_messages: list[ChatMessage]) -> str:
    """Génère une réponse via l'API Mistral."""
    if not prompt_messages:
        logger.warning("Tentative de génération de réponse avec un prompt vide.")
        return EMPTY_PROMPT_MESSAGE

    try:
        logger.info(
            "Appel à l'API Mistral modèle '%s' avec %s message(s).",
            MODEL_NAME,
            len(prompt_messages),
        )

        prompt_text = "\n\n".join(
            f"{msg.role.upper()}:\n{msg.content}" for msg in prompt_messages
        )

        response_text = ask_mistral(
            prompt=prompt_text,
            model=MODEL_NAME,
            temperature=RAG_TEMPERATURE,
        )

        logger.info("Réponse reçue de l'API Mistral.")
        return response_text

    except Exception:
        logger.exception("Erreur API Mistral pendant ask_mistral")
        return MISTRAL_ERROR_MESSAGE


def construire_contexte(search_results: list[dict]) -> str:
    """Construit la chaîne de contexte à partir des résultats de recherche.

    Args:
        search_results: Liste de résultats provenant du Vector Store.

    Returns:
        Une chaîne formatée pour être injectée dans le prompt.
    """
    if not search_results:
        return NO_RAG_CONTEXT_MESSAGE

    context_str = "\n\n---\n\n".join(
        [
            (
                f"Source: {res['metadata'].get('source', 'Inconnue')} "
                f"(Score: {res['score']:.1f}%)\n"
                f"Contenu: {res['text']}"
            )
            for res in search_results
        ]
    )
    return context_str


def construire_prompt(question: str, context_str: str) -> str:
    """Construit le prompt final pour le modèle en injectant la question et le contexte."""
    return RAG_SYSTEM_PROMPT_TEMPLATE.format(
        name=NAME,
        context_str=context_str,
        question=question,
    ).strip()


def synthesize_sql_answer(question: str, rows: list[dict]) -> str:
    if not rows:
        return SQL_NO_RESULT_MESSAGE

    prompt = SQL_SYNTHESIS_PROMPT_TEMPLATE.format(
        question=question,
        rows=rows,
    ).strip()

    return ask_mistral(
        prompt=prompt,
        model=MODEL_NAME,
        temperature=SQL_TEMPERATURE,
    )

def poser_question(
    prompt: str,
    vector_store_manager: Optional[VectorStoreManager] = None,
    k: int = SEARCH_K,
) -> dict:
    """Exécute la logique hybride SQL + RAG pour une question."""
    logfire.info("Question utilisateur", question=prompt)

    # =========================================================
    # Questions à refuser directement
    # =========================================================
    if is_unsupported_question(prompt):
        logger.info("Question non supportée détectée : %s", prompt)

        result = RagPipelineOutput(
            question=prompt,
            answer=build_refusal_answer(prompt),
            search_results=[],
            context_str="",
            final_prompt_for_llm="",
            messages_for_api=[],
            route_used="REFUS",
            sql_success=False,
        )
        logger.info("Route choisie : REFUS_UNSUPPORTED")
        return result.model_dump()

    if is_noisy_question(prompt):
        logger.info("Question bruitée détectée : %s", prompt)

        result = RagPipelineOutput(
            question=prompt,
            answer=build_refusal_answer(prompt),
            search_results=[],
            context_str="",
            final_prompt_for_llm="",
            messages_for_api=[],
            route_used="REFUS",
            sql_success=False,
        )
        logger.info("Route choisie : REFUS_NOISY")
        return result.model_dump()

    # =========================================================
    # Routage SQL (questions statistiques / mesurables)
    # =========================================================
    if is_sql_question(prompt):
        logger.info("Question détectée comme SQL : %s", prompt)

        try:
            payload = sql_tool_with_metadata(prompt)

            sql_results = payload["rows"]
            sql_query = payload["sql_query"]

            # =========================================================
            # Cas SQL + Plot
            # =========================================================
            chart_type = is_plot_question(prompt)
            if chart_type:
                logger.info("Question graphique détectée sur route SQL : %s", prompt)

                plot_data = sql_rows_to_plot_data(sql_results)

                if plot_data:
                    chart_type = is_plot_question(prompt)
                    plot_payload = PlotToolInput(
                        chart_type=chart_type,
                        title=build_plot_title(prompt),
                        x_label="Catégorie",
                        y_label="Valeur",
                        data=plot_data,
                        return_base64=False,
                    )

                    plot_result = build_plot(plot_payload)
                    sql_answer = synthesize_sql_answer(prompt, sql_results)
                    sql_context = sql_rows_to_context(prompt, sql_results)

                    result = RagPipelineOutput(
                        question=prompt,
                        answer=sql_answer,
                        search_results=[],
                        context_str=sql_context,
                        final_prompt_for_llm=sql_query,
                        messages_for_api=[],
                        route_used="SQL",
                        sql_success=True,
                        plot_path=plot_result.get("file_path", ""),
                    )

                    logger.info("Route choisie : SQL + PLOT")
                    return result.model_dump()


            sql_answer = synthesize_sql_answer(prompt, sql_results)
            sql_context = sql_rows_to_context(prompt, sql_results)

            result = RagPipelineOutput(
                question=prompt,
                answer=sql_answer,
                search_results=[],
                context_str=sql_context,
                final_prompt_for_llm=sql_query,
                messages_for_api=[],
                route_used="SQL",
                sql_success=True,
            )

            logger.info("Route choisie : SQL")
            return result.model_dump()

        except Exception:
            logger.exception(
                "Erreur pendant l'exécution du SQL tool pour la question : %s",
                prompt,
            )

            result = RagPipelineOutput(
                question=prompt,
                answer=SQL_ERROR_MESSAGE,
                search_results=[],
                context_str="",
                final_prompt_for_llm="",
                messages_for_api=[],
                route_used="SQL",
                sql_success=False,
            )

            return result.model_dump()

    # =========================================================
    # Chargement du Vector Store pour les routes RAG
    # =========================================================
    if vector_store_manager is None:
        vector_store_manager = get_vector_store_manager()

    if vector_store_manager is None:
        logger.error("VectorStoreManager non disponible pour la recherche.")

        result = RagPipelineOutput(
            question=prompt,
            answer=RAG_UNAVAILABLE_MESSAGE,
            search_results=[],
            context_str="",
            final_prompt_for_llm="",
            messages_for_api=[],
            route_used="RAG",
            sql_success=False,
        )
        return result.model_dump()

    # =========================================================
    # Questions textuelles liées aux reports / Reddit / fans
    # =========================================================
    if is_reports_question(prompt):
        logger.info("Question reports détectée : %s", prompt)

        try:
            logger.info(
                "Recherche de contexte reports pour la question: '%s' avec k=%s",
                prompt,
                k,
            )
            search_results = vector_store_manager.search(prompt, k=k)
            logger.info("%s chunks trouvés dans le Vector Store.", len(search_results))

            logfire.info(
                "Résultats de recherche",
                n_chunks=len(search_results),
            )

        except Exception:
            logger.exception(
                "Erreur pendant vector_store_manager.search pour la query: %s",
                prompt,
            )
            search_results = []

            logfire.info(
                "Résultats de recherche",
                n_chunks=0,
            )

        if not search_results:
            logger.info("Aucun contexte trouvé pour question reports, refus.")

            result = RagPipelineOutput(
                question=prompt,
                answer=build_refusal_answer(prompt),
                search_results=[],
                context_str="",
                final_prompt_for_llm="",
                messages_for_api=[],
                route_used="REFUS",
                sql_success=False,
            )
            logger.info("Route choisie : REFUS_REPORTS")
            return result.model_dump()

        context_str = construire_contexte(search_results)

        logfire.info(
            "Contexte construit",
            longueur=len(context_str),
        )

        final_prompt_for_llm = construire_prompt(prompt, context_str)

        logfire.info(
            "Prompt généré",
            longueur=len(final_prompt_for_llm),
        )

        messages_for_api = [
            ChatMessage(role="user", content=final_prompt_for_llm)
        ]

        response_content = generer_reponse(messages_for_api)

        logfire.info(
            "Réponse générée",
            longueur=len(response_content),
        )
        logger.info("Route choisie : RAG (reports)")

        result = RagPipelineOutput(
            question=prompt,
            answer=response_content,
            search_results=search_results,
            context_str=context_str,
            final_prompt_for_llm=final_prompt_for_llm,
            messages_for_api=[
                {"role": msg.role, "content": msg.content}
                for msg in messages_for_api
            ],
            route_used="RAG",
            sql_success=False,
        )

        return result.model_dump()

    # =========================================================
    # Questions subjectives globales : refus
    # =========================================================
    if is_subjective_question(prompt):
        logger.info("Question subjective globale détectée : %s", prompt)

        result = RagPipelineOutput(
            question=prompt,
            answer=build_refusal_answer(prompt),
            search_results=[],
            context_str="",
            final_prompt_for_llm="",
            messages_for_api=[],
            route_used="REFUS",
            sql_success=False,
        )
        logger.info("Route choisie : REFUS_SUBJECTIVE")
        return result.model_dump()

    # =========================================================
    # Pipeline RAG classique
    # =========================================================
    try:
        logger.info("Recherche de contexte pour la question: '%s' avec k=%s", prompt, k)
        search_results = vector_store_manager.search(prompt, k=k)
        logger.info("%s chunks trouvés dans le Vector Store.", len(search_results))

        logfire.info(
            "Résultats de recherche",
            n_chunks=len(search_results),
        )

    except Exception:
        logger.exception(
            "Erreur pendant vector_store_manager.search pour la query: %s",
            prompt,
        )
        search_results = []

        logfire.info(
            "Résultats de recherche",
            n_chunks=0,
        )

    context_str = construire_contexte(search_results)

    logfire.info(
        "Contexte construit",
        longueur=len(context_str),
    )

    if not search_results:
        logger.warning("Aucun contexte trouvé pour la query: %s", prompt)

    final_prompt_for_llm = construire_prompt(prompt, context_str)

    logfire.info(
        "Prompt généré",
        longueur=len(final_prompt_for_llm),
    )

    messages_for_api = [
        ChatMessage(role="user", content=final_prompt_for_llm)
    ]

    response_content = generer_reponse(messages_for_api)

    logfire.info(
        "Réponse générée",
        longueur=len(response_content),
    )
    logger.info("Route choisie : RAG")

    result = RagPipelineOutput(
        question=prompt,
        answer=response_content,
        search_results=search_results,
        context_str=context_str,
        final_prompt_for_llm=final_prompt_for_llm,
        messages_for_api=[
            {"role": msg.role, "content": msg.content}
            for msg in messages_for_api
        ],
        route_used="RAG",
        sql_success=False,
    )

    return result.model_dump()