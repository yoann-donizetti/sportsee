# utils/rag_pipeline.py
"""Ce module contient la logique de la pipeline RAG (Retrieval-Augmented Generation) pour l'application NBA Analyst AI.
Il inclut les fonctions pour interagir avec le Vector Store, construire les prompts pour le LLM, et générer les réponses en appelant l'API Mistral.
Note: Ce module est conçu pour être utilisé dans l'application Streamlit (MistralChat.py) et peut être testé indépendamment.
Il gère également les cas où le Vector Store n'est pas disponible, en fournissant des réponses d'erreur appropriées.
Liste des fonctions principales:
- get_vector_store_manager(): Charge le VectorStoreManager, qui gère l'index Faiss et les chunks de documents.
- generer_reponse(prompt_messages): Génère une réponse en appelant l'API Mistral avec les messages formatés.
- construire_contexte(search_results): Construit une chaîne de contexte à partir des résultats de recherche du Vector Store.
- construire_prompt(question, context_str): Construit le prompt final pour l'API Mistral en utilisant le System Prompt RAG.
- poser_question(prompt, vector_store_manager, k): Exécute la logique RAG complète pour une question, en gérant la recherche, 
  la construction du prompt et la génération de la réponse. Retourne la réponse ainsi que les éléments utiles pour l'évaluation.

"""
import logging
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

from .config import (
    MISTRAL_API_KEY, MODEL_NAME, SEARCH_K, NAME
)
from .vector_store import VectorStoreManager

# --- Configuration du Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

# --- Configuration de l'API Mistral ---
api_key = MISTRAL_API_KEY
model = MODEL_NAME

if not api_key:
    raise ValueError("Erreur : Clé API Mistral non trouvée (MISTRAL_API_KEY). Veuillez la définir dans le fichier .env.")

try:
    client = MistralClient(api_key=api_key)
    logging.info("Client Mistral initialisé.")
except Exception as e:
    logging.exception("Erreur initialisation client Mistral")
    raise RuntimeError(f"Erreur lors de l'initialisation du client Mistral : {e}") from e


# --- Chargement du Vector Store ---
def get_vector_store_manager():
    """Charge le VectorStoreManager, qui gère l'index Faiss et les chunks de documents.
    return: VectorStoreManager ou None en cas d'erreur.
    note: Cette fonction peut être mise en cache dans Streamlit pour éviter de recharger l'index à chaque interaction.
    """
    logging.info("Tentative de chargement du VectorStoreManager...")
    try:
        manager = VectorStoreManager()
        # Vérifie si l'index a bien été chargé par le constructeur
        if manager.index is None or not manager.document_chunks:
            logging.error("Index Faiss ou chunks non trouvés/chargés par VectorStoreManager.")
            return None
        logging.info(f"VectorStoreManager chargé avec succès ({manager.index.ntotal} vecteurs).")
        return manager
    except FileNotFoundError:
        logging.error("FileNotFoundError lors de l'init de VectorStoreManager.")
        return None
    except Exception as e:
        logging.exception("Erreur chargement VectorStoreManager")
        return None


# --- Prompt Système pour RAG ---
SYSTEM_PROMPT = f"""Tu es 'NBA Analyst AI', un assistant expert sur la ligue de basketball NBA.
Ta mission est de répondre aux questions des fans en animant le débat.

---
{{context_str}}
---

QUESTION DU FAN:
{{question}}

RÉPONSE DE L'ANALYSTE NBA:"""


# --- Fonctions ---
def generer_reponse(prompt_messages: list[ChatMessage]) -> str:
    """Génère une réponse en appelant l'API Mistral avec les messages formatés.
    param prompt_messages: Liste de ChatMessage à envoyer à l'API Mistral.
    return: La réponse textuelle générée par le modèle.
    note: Cette fonction est séparée pour faciliter les tests unitaires et l'évaluation.
    """
    if not prompt_messages:
        # Logique de sécurité pour éviter d'appeler l'API avec un prompt vide
        logging.warning("Tentative de génération de réponse avec un prompt vide.")
        return "Je ne peux pas traiter une demande vide."
    try:
        # Log de l'appel à l'API avec des détails sur le prompt (sans révéler de données sensibles)
        logging.info(f"Appel à l'API Mistral modèle '{model}' avec {len(prompt_messages)} message(s).")
        response = client.chat(
            model=model,
            messages=prompt_messages,
            temperature=0.1,#temperature=0.1 pour des réponses plus précises et moins créatives, adapté pour une tâche d'analyse factuelle.
        )
        #Vérifie que la réponse contient des choix valides avant d'essayer d'y accéder
        if response.choices and len(response.choices) > 0:
            logging.info("Réponse reçue de l'API Mistral.")
            return response.choices[0].message.content
        else:
            logging.warning("L'API n'a pas retourné de choix valide.")
            return "Désolé, je n'ai pas pu générer de réponse valide pour le moment."
    except Exception:
        logging.exception("Erreur API Mistral pendant client.chat")
        return "Je suis désolé, une erreur technique m'empêche de répondre. Veuillez réessayer plus tard."


def construire_contexte(search_results: list[dict]) -> str:
    """
    Construit une chaîne de contexte à partir des résultats de recherche du Vector Store.
    Chaque résultat est formaté pour inclure la source, le score de similarité et un extrait du contenu.
    return: Une chaîne de texte formatée pour être incluse dans le prompt du LLM
    param search_results: Liste de résultats de recherche,
    où chaque résultat est un dict contenant au moins 'metadata', 'score' et 'text'.
    """
    context_str = "\n\n---\n\n".join([
        f"Source: {res['metadata'].get('source', 'Inconnue')} (Score: {res['score']:.1f}%)\nContenu: {res['text']}"
        for res in search_results
    ])

    if not search_results:
        context_str = "Aucune information pertinente trouvée dans la base de connaissances pour cette question."

    return context_str


def construire_prompt(question: str, context_str: str) -> str:
    """
    Construit le prompt final pour l'API Mistral en utilisant le System Prompt RAG.
    param question: La question posée par l'utilisateur.
    param context_str: Le contexte formaté à inclure dans le prompt.
    return SYSTEM_PROMPT.format(context_str=context_str, question=question)
    """
    return SYSTEM_PROMPT.format(context_str=context_str, question=question)


def poser_question(prompt: str, vector_store_manager=None, k: int = SEARCH_K) -> dict:
    """
    Exécute la logique RAG complète pour une question.
    param prompt: La question posée par l'utilisateur.
    param vector_store_manager: Instance de VectorStoreManager pour effectuer la recherche. 
    Si None, la fonction tentera de le charger elle-même.
    param k: Le nombre de résultats à récupérer du Vector Store.
    return: Un dict contenant la question, la réponse générée, les résultats de recherche, 
    le contexte formaté, le prompt final pour le LLM et les messages envoyés à l'API.
    note: Cette fonction encapsule toute la logique RAG, 
    ce qui facilite les tests unitaires et la maintenance. 
    Elle gère également les cas où le Vector Store n'est pas disponible.
    """
    if vector_store_manager is None:
        vector_store_manager = get_vector_store_manager()

    if vector_store_manager is None:
        logging.error("VectorStoreManager non disponible pour la recherche.")
        return {
            "question": prompt,
            "answer": "Le service de recherche de connaissances n'est pas disponible. Impossible de traiter votre demande.",
            "search_results": [],
            "context_str": "",
            "final_prompt_for_llm": "",
            "messages_for_api": []
        }

    # 1. Rechercher le contexte dans le Vector Store
    try:
        logging.info(f"Recherche de contexte pour la question: '{prompt}' avec k={k}")
        search_results = vector_store_manager.search(prompt, k=k)
        logging.info(f"{len(search_results)} chunks trouvés dans le Vector Store.")
    except Exception:
        logging.exception(f"Erreur pendant vector_store_manager.search pour la query: {prompt}")
        search_results = []

    # 2. Formater le contexte pour le prompt LLM
    context_str = construire_contexte(search_results)

    if not search_results:
        logging.warning(f"Aucun contexte trouvé pour la query: {prompt}")

    # 3. Construire le prompt final
    final_prompt_for_llm = construire_prompt(prompt, context_str)

    # 4. Créer la liste de messages pour l'API
    messages_for_api = [
        ChatMessage(role="user", content=final_prompt_for_llm)
    ]

    # 5. Générer la réponse
    response_content = generer_reponse(messages_for_api)

    return {
        "question": prompt,
        "answer": response_content,
        "search_results": search_results,
        "context_str": context_str,
        "final_prompt_for_llm": final_prompt_for_llm,
        "messages_for_api": messages_for_api
    }
