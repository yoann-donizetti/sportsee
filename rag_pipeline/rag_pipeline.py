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
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

from .config import MISTRAL_API_KEY, MODEL_NAME, NAME, SEARCH_K
from .vector_store import VectorStoreManager
from evaluate.core.schemas import RagPipelineOutput
from rag_pipeline.router import is_sql_question, format_sql_result
from rag_pipeline.tools.sql_tool import sql_tool
from rag_pipeline.llm_utils import ask_mistral

logger = logging.getLogger(__name__)

# Initialisation de Logfire pour tracer les étapes du pipeline RAG
logfire.configure(send_to_logfire=False)

# --- Configuration de l'API Mistral ---
if not MISTRAL_API_KEY:
    raise ValueError(
        "Erreur : Clé API Mistral non trouvée (MISTRAL_API_KEY). "
        "Veuillez la définir dans le fichier .env."
    )

try:
    client = MistralClient(api_key=MISTRAL_API_KEY)
    logger.info("Client Mistral initialisé.")
except Exception as e:
    logger.exception("Erreur initialisation client Mistral")
    raise RuntimeError(
        f"Erreur lors de l'initialisation du client Mistral : {e}"
    ) from e


# --- Prompt système ---
SYSTEM_PROMPT = f"""Tu es '{NAME} Analyst AI', un assistant expert sur la ligue de basketball NBA.
Ta mission est de répondre aux questions des fans en animant le débat.

---
{{context_str}}
---

QUESTION DU FAN:
{{question}}

RÉPONSE DE L'ANALYSTE NBA:"""


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
    """Génère une réponse via l'API Mistral.

    Args:
        prompt_messages: Liste de messages à envoyer au modèle.

    Returns:
        La réponse texte générée par le modèle, ou un message d'erreur.
    """
    if not prompt_messages:
        logger.warning("Tentative de génération de réponse avec un prompt vide.")
        return "Je ne peux pas traiter une demande vide."

    try:
        logger.info(
            "Appel à l'API Mistral modèle '%s' avec %s message(s).",
            MODEL_NAME,
            len(prompt_messages),
        )

        response = client.chat(
            model=MODEL_NAME,
            messages=prompt_messages,
            temperature=0.1,
        )

        if response.choices and len(response.choices) > 0:
            logger.info("Réponse reçue de l'API Mistral.")
            return response.choices[0].message.content

        logger.warning("L'API n'a pas retourné de choix valide.")
        return "Désolé, je n'ai pas pu générer de réponse valide pour le moment."

    except Exception:
        logger.exception("Erreur API Mistral pendant client.chat")
        return (
            "Je suis désolé, une erreur technique m'empêche de répondre. "
            "Veuillez réessayer plus tard."
        )


def construire_contexte(search_results: list[dict]) -> str:
    """Construit la chaîne de contexte à partir des résultats de recherche.

    Args:
        search_results: Liste de résultats provenant du Vector Store.

    Returns:
        Une chaîne formatée pour être injectée dans le prompt.
    """
    if not search_results:
        return "Aucune information pertinente trouvée dans la base de connaissances pour cette question."

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
    """Construit le prompt final pour le modèle.

    Args:
        question: Question utilisateur.
        context_str: Contexte récupéré depuis le Vector Store.

    Returns:
        Le prompt final formaté.
    """
    return SYSTEM_PROMPT.format(context_str=context_str, question=question)

def synthesize_sql_answer(question: str, rows: list[dict]) -> str:
    """Reformule les résultats SQL en réponse naturelle."""
    if not rows:
        return "Je n'ai trouvé aucun résultat pour cette question."

    prompt = f"""
Tu es un assistant expert NBA.

Question :
{question}

Résultats SQL :
{rows}

Ta mission :
- Reformule une réponse claire en français
- Sois naturel et concis
- Si plusieurs lignes, fais une phrase fluide
- Ne mentionne pas SQL
- Utilise uniquement les résultats fournis

Réponse :
""".strip()

    return ask_mistral(prompt, model=MODEL_NAME)


def poser_question(
    prompt: str,
    vector_store_manager: Optional[VectorStoreManager] = None,
    k: int = SEARCH_K,
) -> dict:
    """Exécute la logique hybride SQL + RAG pour une question."""
    logfire.info("Question utilisateur", question=prompt)

    # =========================================================
    # Routage SQL
    # =========================================================
    if is_sql_question(prompt):
        logger.info("Question détectée comme SQL : %s", prompt)

        try:
            sql_results = sql_tool(prompt)
            sql_answer = synthesize_sql_answer(prompt, sql_results)

            result = RagPipelineOutput(
                question=prompt,
                answer=sql_answer,
                search_results=[],
                context_str="",
                final_prompt_for_llm="",
                messages_for_api=[],
            )
            logger.info("Route choisie : SQL")
            return result.model_dump()

        except Exception:
            logger.exception("Erreur pendant l'exécution du SQL tool pour la question : %s", prompt)

            result = RagPipelineOutput(
                question=prompt,
                answer="Une erreur est survenue pendant l'interrogation SQL.",
                search_results=[],
                context_str="",
                final_prompt_for_llm="",
                messages_for_api=[],
            )
            return result.model_dump()

    # =========================================================
    # Pipeline RAG actuel
    # =========================================================
    if vector_store_manager is None:
        vector_store_manager = get_vector_store_manager()

    if vector_store_manager is None:
        logger.error("VectorStoreManager non disponible pour la recherche.")

        result = RagPipelineOutput(
            question=prompt,
            answer=(
                "Le service de recherche de connaissances n'est pas disponible. "
                "Impossible de traiter votre demande."
            ),
            search_results=[],
            context_str="",
            final_prompt_for_llm="",
            messages_for_api=[],
        )
        return result.model_dump()

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
    )

    return result.model_dump()