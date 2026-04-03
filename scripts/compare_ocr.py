from pathlib import Path
import logging
import json

from utils.extractors.ocr_docstrange import extract_docstrange_async_json
from utils.extractors.ocr_easy import extract_text_with_easyocr_only
from utils.parsers.reddit_parser import parse_reddit_json
from utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

INPUT_DIR = Path("inputs")
OUTPUT_DIR = Path("ocr_compare_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

PDFS = [
    "Reddit 1.pdf",
    "Reddit 2.pdf",
    "Reddit 3.pdf",
    "Reddit 4.pdf",
]

for pdf_name in PDFS:
    pdf_path = INPUT_DIR / pdf_name

    logger.info("Comparaison OCR pour %s", pdf_name)

    # =========================
    # 1. DOCSTRANGE JSON
    # =========================
    docstrange_data = extract_docstrange_async_json(str(pdf_path))

    docstrange_text = ""
    n_blocks = 0

    if docstrange_data:
        json_path = OUTPUT_DIR / f"{pdf_path.stem}_docstrange.json"

        # sauvegarde JSON brut
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(docstrange_data, f, ensure_ascii=False, indent=2)

        # parsing du JSON DocStrange
        docs = parse_reddit_json(str(json_path))
        n_blocks = len(docs)

        # concat texte reconstruit
        docstrange_text = "\n\n".join(
            d["page_content"] for d in docs if d.get("page_content")
        )

        # sauvegarde texte reconstruit
        (OUTPUT_DIR / f"{pdf_path.stem}_docstrange.txt").write_text(
            docstrange_text,
            encoding="utf-8"
        )
    else:
        logger.warning("DocStrange n'a rien retourné pour %s", pdf_name)

    # =========================
    # 2. EASYOCR
    # =========================
    easyocr_text = extract_text_with_easyocr_only(str(pdf_path))

    if easyocr_text:
        (OUTPUT_DIR / f"{pdf_path.stem}_easyocr.txt").write_text(
            easyocr_text,
            encoding="utf-8"
        )
    else:
        logger.warning("EasyOCR n'a rien extrait pour %s", pdf_name)

    # =========================
    # 3. PRINT COMPARAISON
    # =========================
    print(f"\n📄 {pdf_name}")
    print(f"  DocStrange blocs : {n_blocks}")
    print(f"  DocStrange longueur : {len(docstrange_text)}")
    print(f"  EasyOCR longueur : {len(easyocr_text) if easyocr_text else 0}")

    ratio = 0
    if easyocr_text and docstrange_text:
        ratio = len(docstrange_text) / len(easyocr_text)

    print(f"  Ratio DocStrange/EasyOCR : {round(ratio, 2)}")