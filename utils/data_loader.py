"""
Module de chargement et parsing de données depuis un répertoire local.

Ce module fournit des fonctions pour télécharger un fichier ZIP depuis une URL, l'extraire,et charger les fichiers extraits en fonction de leur type (PDF, DOCX, TXT, CSV, Excel).

Il utilise des fonctions d'extraction spécifiques pour chaque type de fichier, avec une logique de fallback pour les PDF (standard → DocStrange → EasyOCR).

Fonctions:

- download_and_extract_zip(url: str, output_dir: str) -> bool: Télécharge un fichier ZIP depuis une URL et l'extrait dans un répertoire spécifié.

- load_and_parse_files(input_dir: str) -> List[Dict[str, Any]]: Charge et parse récursivement les fichiers d'un répertoire, retournant une liste de documents avec leur contenu et métadonnées.

Chaque document est représenté par un dictionnaire contenant le texte extrait et des métadonnées telles que la source, le nom de fichier, la catégorie, le chemin complet et la méthode d'extraction utilisée.

Le module gère les erreurs de manière robuste, en loggant les problèmes rencontrés lors du téléchargement, de l'extraction ou du parsing des fichiers, et en continuant le processus pour les autres fichiers.
"""

import io
import logging
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List

import requests

from rag_pipeline.config import (
    PDF_OCR_MIN_TEXT_LENGTH,
    CSV_FALLBACK_ENCODING,
    CSV_FALLBACK_SEPARATOR,
)

from utils.extractors.pdf import extract_text_from_pdf
from utils.extractors.ocr_easy import extract_text_with_easyocr_only
from utils.extractors.ocr_docstrange import extract_docstrange_async_json
from utils.extractors.file_types import (
    extract_text_from_docx,
    extract_text_from_txt,
    extract_text_from_csv,
    extract_text_from_excel,
)
from utils.parsers.reddit_parser import reddit_json_to_documents

logger = logging.getLogger(__name__)


def clean_raw_text(text: str) -> str:
    """Nettoyage léger du texte brut pour limiter le bruit avant chunking.

    Ce nettoyage reste volontairement simple pour ne pas casser le contenu utile.
    """
    if not text:
        return text

    # suppression de quelques balises simples
    text = re.sub(r"<img>.*?</img>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<page_number>.*?</page_number>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<footer>.*?</footer>", " ", text, flags=re.IGNORECASE | re.DOTALL)

    # suppression des URLs brutes
    text = re.sub(r"https?://\S+", " ", text)

    # normalisation des espaces
    text = text.replace("\u2028", " ").replace("\u2029", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def download_and_extract_zip(url: str, output_dir: str) -> bool:
    """Télécharge un fichier ZIP depuis une URL et l'extrait.

     arguments:

     - url: l'URL du fichier ZIP à télécharger

     - output_dir: le répertoire où extraire le contenu du ZIP

     retourne: True si le téléchargement et l'extraction ont réussi, False sinon

     raise: Exception si une erreur de téléchargement ou d'extraction se produit

     """
    if not url:
        logger.warning("Aucune URL fournie pour le téléchargement.")
        return False

    try:
        logger.info("Téléchargement des données depuis %s...", url)
        response = requests.get(url, stream=True)
        response.raise_for_status()

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            logger.info("Extraction du contenu dans %s...", output_dir)
            z.extractall(output_dir)

        logger.info("Téléchargement et extraction terminés.")
        return True

    except requests.exceptions.RequestException as e:
        logger.error("Erreur de téléchargement: %s", e)
        return False
    except zipfile.BadZipFile:
        logger.error("Le fichier téléchargé n'est pas un ZIP valide.")
        return False
    except Exception as e:
        logger.error("Erreur inattendue lors du téléchargement/extraction: %s", e)
        return False


def load_and_parse_files(input_dir: str) -> List[Dict[str, Any]]:
    """
    Charge et parse récursivement les fichiers d'un répertoire.

    Retourne une liste de dictionnaires, chacun représentant un document.

    arguments:
- input_dir: le répertoire à parcourir pour charger les fichiers

    retourne: une liste de documents avec leur contenu et métadonnées

    raise: Exception si une erreur de lecture ou de parsing se produit
    """
    documents: List[Dict[str, Any]] = []
    input_path = Path(input_dir)

    if not input_path.is_dir():
        logger.error("Le répertoire d'entrée '%s' n'existe pas.", input_dir)
        return []

    logger.info("Parcours du répertoire source: %s", input_dir)

    for file_path in input_path.rglob("*.*"):
        if not file_path.is_file():
            continue

        relative_path = file_path.relative_to(input_path)
        source_folder = relative_path.parts[0] if len(relative_path.parts) > 1 else "root"
        ext = file_path.suffix.lower()

        logger.debug(
            "Traitement du fichier: %s (Dossier source: %s)",
            relative_path,
            source_folder,
        )

        extracted_content = None

        # =========================
        # PDF
        # =========================
        if ext == ".pdf":
            relative_path_str = str(relative_path)
            full_path_str = str(file_path.resolve())

            # 👉 Détection simple Reddit
            is_reddit_pdf = "reddit" in file_path.name.lower()

            # =========================
            # 1. Extraction standard
            # =========================
            standard_text = extract_text_from_pdf(str(file_path))

            if standard_text and len(standard_text.strip()) >= PDF_OCR_MIN_TEXT_LENGTH:
                standard_text = clean_raw_text(standard_text)

                documents.append(
                    {
                        "page_content": standard_text,
                        "metadata": {
                            "source": relative_path_str,
                            "filename": file_path.name,
                            "category": source_folder,
                            "full_path": full_path_str,
                            "extraction_method": "standard",
                        },
                    }
                )
                continue

            # =========================
            # 2. DocStrange JSON
            # =========================
            logger.info("Texte insuffisant → tentative DocStrange JSON pour %s", relative_path)

            docstrange_data = extract_docstrange_async_json(str(file_path))

            if docstrange_data and is_reddit_pdf:
                docstrange_docs = reddit_json_to_documents(
                    data=docstrange_data,
                    source_path=relative_path_str,
                    source_folder=source_folder,
                    full_path=full_path_str,
                )

                if docstrange_docs:
                    documents.extend(docstrange_docs)
                    continue

                logger.warning(
                    "DocStrange a retourné un JSON mais aucun document exploitable pour %s",
                    relative_path,
                )

            # =========================
            # 3. EasyOCR (fallback)
            # =========================
            logger.warning(
                "DocStrange insuffisant ou inexploitable → fallback EasyOCR pour %s",
                relative_path,
            )

            ocr_text = extract_text_with_easyocr_only(str(file_path))

            if ocr_text:
                ocr_text = clean_raw_text(ocr_text)

                documents.append(
                    {
                        "page_content": ocr_text,
                        "metadata": {
                            "source": relative_path_str,
                            "filename": file_path.name,
                            "category": source_folder,
                            "full_path": full_path_str,
                            "extraction_method": "easyocr",
                        },
                    }
                )
                continue

            logger.warning("Aucune extraction réussie pour %s", relative_path)
            continue

        # =========================
        # AUTRES FICHIERS
        # =========================
        elif ext == ".docx":
            extracted_content = extract_text_from_docx(str(file_path))

        elif ext == ".txt":
            extracted_content = extract_text_from_txt(str(file_path))

        elif ext == ".csv":
            extracted_content = extract_text_from_csv(
                str(file_path),
                fallback_encoding=CSV_FALLBACK_ENCODING,
                fallback_separator=CSV_FALLBACK_SEPARATOR,
            )

        elif ext in [".xlsx", ".xls"]:
            extracted_content = extract_text_from_excel(str(file_path))

        else:
            logger.warning("Type de fichier non supporté ignoré: %s", relative_path)
            continue

        if not extracted_content:
            logger.warning("Aucun contenu n'a pu être extrait de %s", relative_path)
            continue

        if isinstance(extracted_content, dict):
            for sheet_name, text in extracted_content.items():
                text = clean_raw_text(text)

                documents.append(
                    {
                        "page_content": text,
                        "metadata": {
                            "source": f"{str(relative_path)} (Feuille: {sheet_name})",
                            "filename": file_path.name,
                            "sheet": sheet_name,
                            "category": source_folder,
                            "full_path": str(file_path.resolve()),
                        },
                    }
                )
        else:
            extracted_content = clean_raw_text(extracted_content)

            documents.append(
                {
                    "page_content": extracted_content,
                    "metadata": {
                        "source": str(relative_path),
                        "filename": file_path.name,
                        "category": source_folder,
                        "full_path": str(file_path.resolve()),
                    },
                }
            )

    logger.info("%s documents chargés et parsés.", len(documents))
    return documents