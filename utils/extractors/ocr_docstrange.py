"""
Module d'extraction de texte depuis des fichiers PDF via l'API DocStrange en mode asynchrone.
Fonctions:
- submit_docstrange_async(file_path: str) -> Optional[str]: Soumet un document à DocStrange en mode async et retourne le record_id.
- poll_docstrange_result(record_id: str, max_wait_sec: int = 300, poll_interval_sec: int = 5) -> Optional[dict]: Poll DocStrange jusqu'à completion et retourne la réponse JSON complète.
- extract_docstrange_async_json(file_path: str) -> Optional[dict]: Soumet un PDF à DocStrange async et retourne la réponse JSON finale.
"""
import logging
import time
from pathlib import Path
from typing import Optional

import requests

from rag_pipeline.config import DOCSTRANGE_API_KEY

logger = logging.getLogger(__name__)


def submit_docstrange_async(file_path: str) -> Optional[str]:
    """Soumet un document à DocStrange en mode async et retourne le record_id.
     arguments:
     - file_path: chemin vers le fichier à extraire
     retourne: le record_id de la tâche async ou None en cas d'erreur
     raise: Exception si une erreur de soumission se produit
     """
    if not DOCSTRANGE_API_KEY:
        logger.warning("DOCSTRANGE_API_KEY non définie.")
        return None

    url = "https://extraction-api.nanonets.com/api/v1/extract/async"
    headers = {"Authorization": f"Bearer {DOCSTRANGE_API_KEY}"}
    payload = {"output_format": "json"}

    try:
        with open(file_path, "rb") as f:
            files = {"file": (Path(file_path).name, f, "application/pdf")}
            response = requests.post(
                url,
                data=payload,
                files=files,
                headers=headers,
                timeout=300,
            )

        if response.status_code not in (200, 202):
            logger.error(
                "Erreur DocStrange async %s pour %s : %s",
                response.status_code,
                file_path,
                response.text,
            )
            return None

        data = response.json()
        record_id = data.get("record_id")

        if not record_id:
            logger.error("Aucun record_id retourné par DocStrange pour %s", file_path)
            return None

        logger.info(
            "DocStrange async soumis avec succès pour %s | record_id=%s",
            file_path,
            record_id,
        )
        return record_id

    except Exception as e:
        logger.error("Erreur soumission async DocStrange pour %s: %s", file_path, e)
        return None


def poll_docstrange_result(
    record_id: str,
    max_wait_sec: int = 300,
    poll_interval_sec: int = 5,
) -> Optional[dict]:
    """Poll DocStrange jusqu'à completion et retourne la réponse JSON complète.
     arguments:
     - record_id: l'identifiant de la tâche async à poller
     - max_wait_sec: temps maximum à attendre avant d'abandonner (en secondes)
     - poll_interval_sec: intervalle entre chaque tentative de polling (en secondes)
     retourne: la réponse JSON finale de DocStrange ou None en cas d'erreur ou timeout
     raise: Exception si une erreur de polling se produit
     """
    url = f"https://extraction-api.nanonets.com/api/v1/extract/results/{record_id}"
    headers = {"Authorization": f"Bearer {DOCSTRANGE_API_KEY}"}

    start = time.time()

    while time.time() - start < max_wait_sec:
        try:
            response = requests.get(url, headers=headers, timeout=600)

            if response.status_code == 504:
                logger.warning(
                    "Timeout temporaire DocStrange (504) | record_id=%s | nouvelle tentative...",
                    record_id,
                )
                time.sleep(poll_interval_sec)
                continue

            if response.status_code != 200:
                logger.error(
                    "Erreur polling DocStrange %s pour %s : %s",
                    response.status_code,
                    record_id,
                    response.text,
                )
                return None

            data = response.json()
            status = data.get("status", "").lower()

            logger.info("Polling DocStrange | record_id=%s | status=%s", record_id, status)

            if status == "completed":
                logger.info("DocStrange async terminé | record_id=%s", record_id)
                return data

            if status in {"failed", "error"}:
                logger.error(
                    "DocStrange async en échec | record_id=%s | payload=%s",
                    record_id,
                    data,
                )
                return None

            time.sleep(poll_interval_sec)

        except Exception as e:
            logger.error("Erreur polling DocStrange pour %s: %s", record_id, e)
            return None

    logger.error("Timeout DocStrange async dépassé | record_id=%s", record_id)
    return None


def extract_docstrange_async_json(file_path: str) -> Optional[dict]:
    """Soumet un PDF à DocStrange async et retourne la réponse JSON finale.
     arguments:
     - file_path: chemin vers le fichier PDF
     retourne: la réponse JSON finale de DocStrange ou None en cas d'erreur
     raise: Exception si une erreur de soumission ou de polling se produit
     """
    record_id = submit_docstrange_async(file_path)
    if not record_id:
        return None

    return poll_docstrange_result(record_id)