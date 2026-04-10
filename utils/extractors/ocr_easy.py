import logging
import os
from typing import Optional

import numpy as np
from tqdm import tqdm

from rag_pipeline.config import OCR_LANGUAGES, PDF_OCR_ZOOM_X, PDF_OCR_ZOOM_Y

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    from PIL import Image
    import easyocr

    logger.info("Initialisation du lecteur EasyOCR...")
    reader = easyocr.Reader(OCR_LANGUAGES)
    logger.info("Lecteur EasyOCR initialisé.")

except ImportError as e:
    logger.warning(
        "Modules OCR (PyMuPDF, Pillow, easyocr) non installés ou erreur: %s. "
        "L'OCR EasyOCR ne sera pas disponible.",
        e,
    )
    fitz = None
    Image = None
    easyocr = None
    reader = None

except Exception as e:
    logger.error("Erreur inattendue lors du chargement EasyOCR: %s", e)
    fitz = None
    Image = None
    easyocr = None
    reader = None


def extract_text_with_easyocr_only(file_path: str) -> Optional[str]:
    """Extrait le texte d'un PDF uniquement avec EasyOCR."""
    if not fitz or not reader:
        logger.warning("Modules/Modèle OCR non disponibles. Impossible d'effectuer l'OCR.")
        return None

    text_content = []

    try:
        doc = fitz.open(file_path)

        for page_num in tqdm(range(len(doc)), desc=f"EasyOCR de {os.path.basename(file_path)}"):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(
                matrix=fitz.Matrix(PDF_OCR_ZOOM_X, PDF_OCR_ZOOM_Y)
            )
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            try:
                img_np = np.array(img)
                results = reader.readtext(img_np)
                page_text = "\n".join([res[1] for res in results])
                text_content.append(page_text)
            except Exception as ocr_e:
                logger.error(
                    "Erreur lors de l'OCR de la page %s de %s avec EasyOCR: %s",
                    page_num + 1,
                    file_path,
                    ocr_e,
                )
                continue

        doc.close()
        full_text = "\n".join(text_content).strip()

        if full_text:
            logger.info(
                "Texte extrait via EasyOCR: %s (%s caractères)",
                file_path,
                len(full_text),
            )
            return full_text

        logger.warning("Aucun texte significatif extrait via EasyOCR pour %s", file_path)
        return None

    except Exception as e:
        logger.error("Erreur EasyOCR pour %s: %s", file_path, e)
        return None