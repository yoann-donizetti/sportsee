import streamlit as st
import logging

from utils.config import APP_TITLE, NAME
from utils.rag_pipeline import poser_question, get_vector_store_manager

logger = logging.getLogger(__name__)


# --- Chargement du Vector Store (cache Streamlit) ---
@st.cache_resource
def load_vector_store():
    return get_vector_store_manager()


vector_store_manager = load_vector_store()


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

    # message user
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Vérif vector store
    if vector_store_manager is None:
        st.error("Le système RAG n'est pas disponible.")
        st.stop()

    # Appel pipeline RAG (IMPORTANT)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.text("...")

        result = poser_question(
            prompt=prompt,
            vector_store_manager=vector_store_manager
        )

        response = result["answer"]

        placeholder.write(response)

    # Ajout historique
    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })


st.markdown("---")
st.caption("Powered by Mistral AI & FAISS")