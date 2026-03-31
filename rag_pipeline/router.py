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