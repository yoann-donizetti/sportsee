"""
Parser spécialisé pour les exports JSON Reddit issus de DocStrange / OCR structuré.

Ce module transforme un JSON Reddit extrait depuis un PDF en document(s) exploitables
par le pipeline RAG et l'indexation vectorielle.

Objectifs :
- récupérer les métadonnées utiles du thread ;
- reconstruire un texte propre orienté retrieval ;
- conserver le post principal, les commentaires et les réponses ;
- exclure autant que possible le bruit d'interface Reddit.

Fonctions principales :
- parse_reddit_json(file_path): lit un fichier JSON et retourne une liste de documents.
- reddit_json_to_documents(data, source_path, source_folder, full_path): transforme
  un JSON déjà chargé en mémoire en liste de documents indexables.
"""

from pathlib import Path
import json
from typing import Any, Dict, List, Optional


def parse_reddit_json(file_path: str) -> List[Dict[str, Any]]:
    """
    Lit un fichier JSON Reddit et retourne une liste de documents prêts à être indexés.

    Arguments :
    - file_path : chemin vers le fichier JSON produit par DocStrange

    Retour :
    - liste de documents au format :
      {
          "page_content": str,
          "metadata": dict
      }

    Remarque :
    - cette fonction lit un fichier sur disque ;
    - pour un JSON déjà chargé en mémoire, utiliser reddit_json_to_documents().
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    source_path = str(file_path)
    source_folder = Path(file_path).parent.name if Path(file_path).parent.name else "root"
    full_path = str(Path(file_path).resolve())

    return reddit_json_to_documents(
        data=data,
        source_path=source_path,
        source_folder=source_folder,
        full_path=full_path,
    )


def reddit_json_to_documents(
    data: Dict[str, Any],
    source_path: str,
    source_folder: str,
    full_path: str,
) -> List[Dict[str, Any]]:
    """
    Transforme un JSON Reddit déjà chargé en mémoire en liste de documents indexables.

    Arguments :
    - data : contenu JSON déjà chargé
    - source_path : chemin source logique du fichier
    - source_folder : dossier/catégorie source
    - full_path : chemin absolu du fichier

    Retour :
    - liste contenant un document prêt pour l'indexation, ou liste vide si rien d'utile
      n'a été extrait
    """
    content = (
        data.get("result", {})
        .get("json", {})
        .get("content", {})
    )

    if not isinstance(content, dict) or not content:
        return []

    metadata = extract_metadata(content)
    text = build_clean_text(content)

    if not text.strip():
        return []

    metadata.update(
        {
            "source": source_path,
            "filename": Path(source_path).name,
            "category": source_folder,
            "full_path": full_path,
            "extraction_method": "docstrange",
        }
    )

    return [
        {
            "page_content": text,
            "metadata": metadata,
        }
    ]


def extract_metadata(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait les métadonnées principales du thread Reddit.

    Champs visés :
    - titre
    - subreddit
    - auteur principal
    - url
    - timestamp
    - upvotes
    - nombre de commentaires
    """
    main_post = get_main_post(content)

    return {
        "title": (
            content.get("title")
            or content.get("thread_title")
            or content.get("page_title")
            or content.get("document_title")
            or content.get("document_metadata", {}).get("title")
            or content.get("document_info", {}).get("title")
            or main_post.get("title")
            or main_post.get("post_title")
        ),
        "subreddit": (
            content.get("subreddit")
            or content.get("header", {}).get("subreddit")
            or main_post.get("subreddit")
        ),
        "author": extract_author(content),
        "url": (
            content.get("url")
            or content.get("source_url")
            or content.get("document_url")
            or content.get("footer_url")
            or content.get("document_metadata", {}).get("source_url")
            or content.get("document_metadata", {}).get("url")
            or content.get("document_info", {}).get("source_url")
            or content.get("document_info", {}).get("url")
        ),
        "timestamp": extract_timestamp(content),
        "upvotes": (
            main_post.get("upvotes")
            or content.get("upvotes")
        ),
        "comments_count": (
            main_post.get("comment_count")
            or main_post.get("comments_count")
            or main_post.get("reply_count")
            or content.get("comments_count")
        ),
        "source": "reddit_json",
    }


def get_main_post(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Récupère le post principal quelle que soit sa structure dans le JSON.

    Cas gérés :
    - content["main_post"]
    - content["post"]
    - content["reddit_post"]
    - content["documents"][...]["main_post"]
    """
    direct_main_post = (
        content.get("main_post")
        or content.get("post")
        or content.get("reddit_post")
    )

    if isinstance(direct_main_post, dict):
        return direct_main_post

    documents = content.get("documents", [])
    if isinstance(documents, list):
        for doc in documents:
            if isinstance(doc, dict) and isinstance(doc.get("main_post"), dict):
                return doc["main_post"]

    return {}


def extract_author(content: Dict[str, Any]) -> Optional[str]:
    """
    Extrait l'auteur du post principal.
    """
    main_post = get_main_post(content)
    return main_post.get("author") or main_post.get("user")


def extract_timestamp(content: Dict[str, Any]) -> Optional[str]:
    """
    Extrait le timestamp principal du document.
    """
    return (
        content.get("timestamp")
        or content.get("date_time")
        or content.get("page_date_time")
        or content.get("document_date")
        or content.get("date")
        or content.get("document_metadata", {}).get("date")
    )


def build_clean_text(content: Dict[str, Any]) -> str:
    """
    Construit un texte nettoyé orienté retrieval.

    On garde :
    - titre / subreddit
    - post principal
    - takeaways
    - player_stats
    - commentaires et réponses

    On exclut implicitement :
    - publicité
    - navigation
    - footer
    - posts liés
    - discussions connexes
    """
    parts: List[str] = []

    # =========================
    # TITRE / SUBREDDIT
    # =========================
    title = (
        content.get("title")
        or content.get("thread_title")
        or content.get("page_title")
        or content.get("document_title")
        or content.get("document_metadata", {}).get("title")
        or content.get("document_info", {}).get("title")
    )

    subreddit = (
        content.get("subreddit")
        or content.get("header", {}).get("subreddit")
        or get_main_post(content).get("subreddit")
    )

    if title:
        parts.append(f"TITLE: {title}")

    if subreddit:
        parts.append(f"SUBREDDIT: {subreddit}")

    # =========================
    # MAIN POST
    # =========================
    main_post = get_main_post(content)

    if isinstance(main_post, dict) and main_post:
        parts.append("MAIN POST:")

        main_title = (
            main_post.get("title")
            or main_post.get("post_title")
        )
        if main_title:
            parts.append(main_title)

        author = (
            main_post.get("author")
            or main_post.get("user")
        )
        if author:
            parts.append(f"AUTHOR: {author}")

        post_content = (
            main_post.get("content")
            or main_post.get("body")
            or main_post.get("text")
            or main_post.get("introduction")
        )
        parts.extend(normalize_text_block(post_content))

        takeaways = main_post.get("takeaways")
        if takeaways:
            parts.append("KEY POINTS:")
            parts.extend(normalize_text_block(takeaways))

        player_stats = main_post.get("player_stats")
        if isinstance(player_stats, list) and player_stats:
            parts.append("PLAYER STATS:")
            for stat in player_stats:
                line = format_player_stat(stat)
                if line:
                    parts.append(line)

    # =========================
    # COMMENTS
    # =========================
    comments: List[Any] = []

    if isinstance(content.get("comments"), list):
        comments.extend(content["comments"])

    if isinstance(content.get("main_comments"), list):
        comments.extend(content["main_comments"])

    if isinstance(content.get("main_thread"), dict):
        thread_comments = content["main_thread"].get("comments", [])
        if isinstance(thread_comments, list):
            comments.extend(thread_comments)

    if isinstance(content.get("discussion_thread"), list):
        comments.extend(content["discussion_thread"])
    elif isinstance(content.get("discussion_thread"), dict):
        thread_comments = content["discussion_thread"].get("comments", [])
        if isinstance(thread_comments, list):
            comments.extend(thread_comments)

    if isinstance(content.get("comments_section"), dict):
        section_comments = content["comments_section"].get("comments", [])
        if isinstance(section_comments, list):
            comments.extend(section_comments)

        main_thread_comments = content["comments_section"].get("main_thread_comments", [])
        if isinstance(main_thread_comments, list):
            comments.extend(main_thread_comments)

    documents = content.get("documents", [])
    if isinstance(documents, list):
        for doc in documents:
            if not isinstance(doc, dict):
                continue

            doc_comments = doc.get("comments", [])
            if isinstance(doc_comments, list):
                comments.extend(doc_comments)

    if isinstance(content.get("pages"), list):
        for page in content["pages"]:
            if not isinstance(page, dict):
                continue

            page_comments = page.get("comments", [])
            if isinstance(page_comments, list):
                comments.extend(page_comments)

    if comments:
        parts.append("COMMENTS:")
        parts.extend(flatten_comments(comments))

    text = "\n".join(
        part for part in parts
        if isinstance(part, str) and part.strip()
    )

    return text.strip()


def normalize_text_block(value: Any) -> List[str]:
    """
    Normalise un bloc texte pouvant être :
    - une chaîne
    - une liste de chaînes
    - une liste imbriquée
    """
    if value is None:
        return []

    if isinstance(value, str):
        return [value] if value.strip() else []

    if isinstance(value, list):
        result: List[str] = []
        for item in value:
            result.extend(normalize_text_block(item))
        return result

    return []


def format_player_stat(stat: Any) -> str:
    """
    Formate une ligne de statistiques joueur pour les tableaux utiles.
    """
    if not isinstance(stat, dict):
        return ""

    player = (
        stat.get("player_name")
        or stat.get("player")
        or "Unknown"
    )
    points = (
        stat.get("total_playoff_points")
        or stat.get("value1")
    )
    rts = (
        stat.get("efficiency_rTS")
        or stat.get("efficiency_relative_to_era")
        or stat.get("value2")
    )

    parts = [str(player)]
    if points is not None:
        parts.append(f"points={points}")
    if rts is not None:
        parts.append(f"rTS={rts}")

    return " | ".join(parts)


def flatten_comments(comments: List[Any]) -> List[str]:
    """
    Aplati récursivement les commentaires et leurs réponses.

    Champs lus selon les variantes JSON :
    - content
    - text
    - replies
    """
    results: List[str] = []

    for c in comments:
        if isinstance(c, dict):
            text_value = c.get("content")
            if text_value is None:
                text_value = c.get("text")

            results.extend(normalize_text_block(text_value))

            replies = c.get("replies", [])
            if isinstance(replies, list):
                results.extend(flatten_comments(replies))

        elif isinstance(c, str):
            if c.strip():
                results.append(c)

    return results