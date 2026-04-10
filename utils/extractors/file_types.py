"""Module d'extraction de texte pour différents types de fichiers.
Ce module fournit des fonctions pour extraire du texte de fichiers DOCX, TXT, CSV et Excel. 
Chaque fonction gère les erreurs de manière robuste et utilise des bibliothèques spécifiques 
pour le traitement des fichiers.
Fonctions:
- extract_text_from_docx(file_path: str) -> Optional[str]: Extrait le texte d'un fichier DOCX.
- extract_text_from_txt(file_path: str) -> Optional[str]: Extrait le texte d'un fichier texte brut.
- extract_text_from_csv(file_path: str, fallback_encoding: str, fallback_separator: str) -> Optional[str]: Extrait le texte d'un fichier CSV avec gestion des erreurs de lecture.
- extract_text_from_excel(file_path: str) -> Optional[Union[str, Dict[str, str]]]: Extrait le texte de chaque feuille d'un fichier Excel, retournant un dictionnaire ou une chaîne selon le nombre de feuilles.
Chaque fonction utilise des bibliothèques spécifiques (docx pour DOCX, pandas pour CSV et Excel) et gère les erreurs de manière à fournir des informations utiles en cas de problème.
"""
import logging
from typing import Dict, Optional, Union

logger = logging.getLogger(__name__)


def extract_text_from_docx(file_path: str) -> Optional[str]:
    """Extrait le texte d'un fichier DOCX.
    arguments:
    - file_path: chemin vers le fichier DOCX
    retourne: le texte extrait ou None en cas d'erreur
    raise: ImportError si la bibliothèque docx n'est pas installée
    """
    try:
        import docx

        doc = docx.Document(file_path)
        text = "\n".join(para.text for para in doc.paragraphs if para.text)
        logger.info("Texte extrait de DOCX: %s (%s caractères)", file_path, len(text))
        return text
    except Exception as e:
        logger.error("Erreur extraction DOCX %s: %s", file_path, e)
        return None


def extract_text_from_txt(file_path: str) -> Optional[str]:
    """Extrait le texte d'un fichier texte brut.
     arguments:
    - file_path: chemin vers le fichier TXT
    retourne: le texte extrait ou None en cas d'erreur
     raise: Exception si une erreur de lecture se produit
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        logger.info("Texte extrait de TXT: %s (%s caractères)", file_path, len(text))
        return text
    except Exception as e:
        logger.error("Erreur extraction TXT %s: %s", file_path, e)
        return None


def extract_text_from_csv(
    file_path: str,
    fallback_encoding: str,
    fallback_separator: str,
) -> Optional[str]:
    """Extrait le texte d'un fichier CSV.
    arguments:
    - file_path: chemin vers le fichier CSV
    - fallback_encoding: encodage à utiliser en cas d'erreur de décodage
    - fallback_separator: séparateur à utiliser en cas d'erreur de lecture
    retourne: le texte extrait ou None en cas d'erreur
    raise: ImportError si la bibliothèque pandas n'est pas installée
    """
    try:
        import pandas as pd

        try:
            df = pd.read_csv(file_path)
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding=fallback_encoding)
        except Exception as read_e:
            logger.warning(
                "Erreur lecture CSV %s: %s. Tentative avec séparateur '%s'",
                file_path,
                read_e,
                fallback_separator,
            )
            try:
                df = pd.read_csv(file_path, sep=fallback_separator)
            except UnicodeDecodeError:
                df = pd.read_csv(
                    file_path,
                    sep=fallback_separator,
                    encoding=fallback_encoding,
                )
            except Exception as read_e2:
                logger.error("Impossible de lire le CSV %s: %s", file_path, read_e2)
                return None

        text = df.to_string()
        logger.info("Texte extrait de CSV: %s (%s caractères)", file_path, len(text))
        return text

    except ImportError:
        logger.warning("Pandas non installé. Impossible de lire les fichiers CSV.")
        return None
    except Exception as e:
        logger.error("Erreur extraction CSV %s: %s", file_path, e)
        return None


def extract_text_from_excel(file_path: str) -> Optional[Union[str, Dict[str, str]]]:
    """Extrait le texte de chaque feuille d'un fichier Excel.
    arguments:
    - file_path: chemin vers le fichier Excel
    retourne: un dictionnaire avec le nom de chaque feuille comme clé et son texte comme valeur, ou une chaîne si une seule feuille, ou None en cas d'erreur
    raise: ImportError si la bibliothèque pandas ou openpyxl n'est pas installée
    """
    try:
        import pandas as pd

        excel_file = pd.ExcelFile(file_path)
        sheets_data = {}

        for sheet_name in excel_file.sheet_names:
            df = excel_file.parse(sheet_name)
            sheets_data[sheet_name] = df.to_string()

        logger.info(
            "Texte extrait de %s feuille(s) dans Excel: %s",
            len(sheets_data),
            file_path,
        )

        if len(sheets_data) == 1:
            return list(sheets_data.values())[0]
        return sheets_data

    except ImportError:
        logger.warning(
            "Pandas ou openpyxl non installé. Impossible de lire les fichiers Excel."
        )
        return None
    except Exception as e:
        logger.error("Erreur extraction Excel %s: %s", file_path, e)
        return None