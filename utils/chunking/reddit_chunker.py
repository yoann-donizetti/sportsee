from typing import List, Dict, Any
import re


def clean_reddit_block(text: str) -> str:
    """Nettoyage léger d'un bloc Reddit avant chunking."""
    if not text:
        return text

    lines = []
    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        # bruit UI évident
        if line.lower() in {
            "accéder au contenu principal",
            "se connecter",
            "répondre ...",
            "afficher plus de commentaires",
            "discussions connexes",
        }:
            continue

        # lignes ultra courtes / sans valeur
        if len(line) <= 2:
            continue

        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def split_comments_into_blocks(comments_text: str, max_chars: int = 1200) -> List[str]:
    """Découpe les commentaires Reddit en blocs plus petits.

    On essaie de couper sur les doubles sauts de ligne pour garder une structure lisible.
    """
    if not comments_text.strip():
        return []

    raw_parts = re.split(r"\n{2,}", comments_text)
    raw_parts = [part.strip() for part in raw_parts if part.strip()]

    blocks = []
    current_block = ""

    for part in raw_parts:
        candidate = f"{current_block}\n\n{part}".strip() if current_block else part

        if len(candidate) <= max_chars:
            current_block = candidate
        else:
            if current_block:
                blocks.append(current_block)
            # si un part seul est déjà trop grand, on le garde tel quel
            current_block = part

    if current_block:
        blocks.append(current_block)

    return blocks


def chunk_reddit_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    text = doc.get("page_content", "")
    metadata = doc.get("metadata", {})

    chunks = []

    main_part = ""
    comments_part = ""

    if "COMMENTS:" in text:
        parts = text.split("COMMENTS:", maxsplit=1)
        main_part = parts[0]
        comments_part = parts[1]
    else:
        main_part = text

    # nettoyage léger
    main_part = clean_reddit_block(main_part)
    comments_part = clean_reddit_block(comments_part)

    # MAIN POST
    if main_part.strip():
        chunks.append({
            "text": main_part.strip(),  # 🔥 correction ici
            "metadata": {
                **metadata,
                "chunk_type": "main_post"
            }
        })

    # COMMENTS
    if comments_part.strip():
        comment_blocks = split_comments_into_blocks(comments_part, max_chars=1200)

        for i, block in enumerate(comment_blocks):
            chunks.append({
                "text": block.strip(),  # 🔥 correction ici
                "metadata": {
                    **metadata,
                    "chunk_type": "comments",
                    "comment_block_id": i
                }
            })

    return chunks