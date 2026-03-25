import logging

def setup_logging():
    """
    Configure le système de logging global de l'application.

    Cette fonction définit :
    - le niveau de logs (INFO par défaut)
    - le format des messages affichés

    Elle doit être appelée UNE SEULE FOIS au démarrage
    (dans indexer.py, Streamlit ou script d'évaluation).
    """

    # Évite de reconfigurer plusieurs fois le logging (important avec Streamlit)
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,  # Niveau minimal des logs affichés (DEBUG, INFO, WARNING, ERROR)
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
            # Exemple :
            # 2026-03-25 10:12:00 - INFO - utils.data_loader - 120 documents chargés
        )