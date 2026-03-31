def is_sql_question(question: str) -> bool:
    q = question.lower()

    keywords = [
        "combien",
        "moyenne",
        "total",
        "top",
        "classement",
        "meilleur",
        "meilleurs",
        "plus de",
        "points",
        "rebonds",
        "passes",
        "stat",
        "statistique",
        "pourcentage",
        "rating",
    ]

    return any(k in q for k in keywords)

def format_sql_result(question: str, rows: list[dict]) -> str:
    if not rows:
        return "Je n'ai trouvé aucun résultat dans la base SQL pour cette question."

    lines = [f"Résultats pour : {question}"]
    for row in rows:
        parts = [f"{k}={v}" for k, v in row.items()]
        lines.append("- " + ", ".join(parts))

    return "\n".join(lines)

def is_unsupported_question(question: str) -> bool:
    q = question.lower()

    patterns = [
        "5 derniers matchs",
        "cinq derniers matchs",
        "derniers matchs",
        "last 5 games",
        "à domicile",
        "a domicile",
        "à l'extérieur",
        "a l'exterieur",
        "home",
        "away",
        "domicile",
        "extérieur",
        "exterieur",
        "par quart-temps",
        "par quart temps",
        "play-by-play",
        "play by play",
        "possession par possession",
        "blessure aujourd'hui",
        "blessure ce soir",
        "ce soir",
        "today",
        "tonight",
    ]

    return any(p in q for p in patterns)

def is_noisy_question(question: str) -> bool:
    q = question.lower().strip()
    words = q.split()

    vague_tokens = {
        "truc", "machin", "chose", "stats", "gagne", "meilleur"
    }

    # trop court ou trop vague
    if len(words) < 5:
        return True

    # beaucoup de mots vagues
    vague_count = sum(1 for w in words if w in vague_tokens)
    if vague_count >= 2:
        return True

    return False