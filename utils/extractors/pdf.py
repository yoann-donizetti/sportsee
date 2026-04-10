"""
Module d'extraction de texte depuis des fichiers PDF.
Utilise PyPDF2 pour une extraction simple sans OCR.
Fonctions:
- extract_text_from_pdf(file_path: str) -> Optional[str]: Extrait le texte d'un fichier PDF, retourne None en cas d'erreur.

"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> Optional[str]:
    """Extraction simple de texte depuis un PDF (sans OCR).
    arguments:
    - file_path: chemin vers le fichier PDF
    retourne: le texte extrait ou None en cas d'erreur
    raise: ImportError si la bibliothèque PyPDF2 n'est pas installée
    """
    try:
        from PyPDF2 import PdfReader

        pdf_reader = PdfReader(file_path)
        text = "".join(
            page.extract_text() + "\n"
            for page in pdf_reader.pages
            if page.extract_text()
        ).strip()

        logger.info(
            "Extraction standard PDF: %s (%s caractères)",
            file_path,
            len(text),
        )
        return text if text else None

    except Exception as e:
        logger.error("Erreur extraction PDF %s: %s", file_path, e)
        return None