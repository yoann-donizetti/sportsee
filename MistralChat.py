import streamlit as st
import logging
import requests

from rag_pipeline.config import APP_TITLE, NAME, API_URL
from utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# --- UI ---
st.title(APP_TITLE)
st.caption(f"Assistant virtuel pour {NAME}")

# Historique
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": f"Bonjour ! Je suis votre analyste IA pour la {NAME}. Posez-moi vos questions."
        }
    ]

# Affichage historique
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Input utilisateur
if prompt := st.chat_input(f"Posez votre question sur la {NAME}..."):
    logger.info("Nouvelle question posée (longueur=%s caractères)", len(prompt))

    # message user
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Appel API
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.text("...")

        try:
            payload = {"question": prompt}

            response_api = requests.post(API_URL, json=payload, timeout=120)
            response_api.raise_for_status()

            result = response_api.json()
            response = result["answer"]
            route_used = result.get("route_used", "")
            sql_success = result.get("sql_success", False)

            placeholder.write(response)
            st.caption(f"Route utilisée : {route_used} | SQL success : {sql_success}")

            logger.info("Réponse générée (longueur=%s caractères)", len(response))

        except requests.exceptions.RequestException as e:
            response = "Erreur : impossible de joindre l'API."
            placeholder.error(response)
            logger.error("Erreur appel API : %s", e)

        except Exception as e:
            response = "Erreur inattendue lors du traitement de la réponse."
            placeholder.error(response)
            logger.error("Erreur inattendue Streamlit : %s", e)

    # Ajout historique
    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })

st.markdown("---")
st.caption("Powered by Mistral AI, FastAPI & FAISS")