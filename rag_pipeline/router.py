from rag_pipeline.config import REFUSAL_MESSAGES

def is_sql_question(question: str) -> bool:
    q = question.lower().strip()

    # Cas reports agrégés -> SQL
    if is_reports_aggregation_question(question):
        return True

    # Cas non SQL évidents
    non_sql_patterns = [
        "meilleur joueur selon les fans",
        "meilleur joueur nba actuellement selon les fans",
        "joueur préféré",
        "joueur prefere",
        "préféré des fans",
        "prefere des fans",
        "popularité globale",
        "popularite globale",
        "avis général",
        "avis general",
        "opinion générale",
        "opinion generale",
    ]
    if any(p in q for p in non_sql_patterns):
        return False

    # Cas unsupported évidents
    unsupported_patterns = [
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
        "ce soir",
        "today",
        "tonight",
    ]
    if any(p in q for p in unsupported_patterns):
        return False

    # Indices de métriques mesurables
    metric_keywords = [
            "points",
            "point",
            "rebonds",
            "rebond",
            "passes",
            "passes décisives",
            "passes decisives",
            "pourcentage",
            "fg%",
            "3 points",
            "3pt",
            "reb",
            "ast",
            "pts",
            "rating",
            "offrtg",
            "defrtg",
            "netrtg",
            "efficacité",
            "efficacite",
            "performance",
            "performances",
            "scoreur",
            "scoreurs",
            "marqueur",
            "marqueurs",
            "score",
            "scoring",
        ]

    # Indices d'opérations analytiques
    operation_keywords = [
        "combien",
        "moyenne",
        "total",
        "top",
        "classement",
        "plus de",
        "plus grand",
        "meilleur",
        "meilleurs",
        "moins de",
        "combine",
        "combiné",
        "combinés",
        "combiner",
        "différence",
        "difference",
        "comparaison",
        "compare",
        "comparer",
        "complet",
        "plus complet",
        "top 5",
        "top 10",
        "leader",
        "leaders",
    ]

    # Cas métiers explicites à forcer en SQL
    sql_patterns = [
            "plus complet entre points, rebonds et passes",
            "plus complet entre points rebonds et passes",
            "différence de performance entre les joueurs les plus scoreurs et les meilleurs passeurs",
            "difference de performance entre les joueurs les plus scoreurs et les meilleurs passeurs",
            "joueurs les plus scoreurs et les meilleurs passeurs",
            "combine le plus de points et de passes",
            "combine le plus de points et de passes décisives",
            "combine le plus de points et de passes decisives",
            "top 5 des meilleurs scoreurs",
            "top 10 des meilleurs scoreurs",
            "meilleurs scoreurs",
            "meilleurs marqueurs",
            "top 5 des marqueurs",
            "top 10 des marqueurs",
            "joueurs avec le plus de points",
            "joueurs avec le plus de rebonds",
            "joueurs avec le plus de passes",
            "compare les points de",
            "comparaison des points de",
            "compare les rebonds de",
            "comparaison des rebonds de",
            "compare les passes de",
            "comparaison des passes de",
        ]
    if any(p in q for p in sql_patterns):
        return True

    has_metric = any(k in q for k in metric_keywords)
    has_operation = any(k in q for k in operation_keywords)

    return has_metric and has_operation

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
        "truc", "machin", "chose", "stats", "gagne"
    }

    # trop court ou trop vague
    if len(words) < 5:
        return True

    # beaucoup de mots vagues
    vague_count = sum(1 for w in words if w in vague_tokens)
    if vague_count >= 2:
        return True

    return False



def is_subjective_question(question: str) -> bool:
    q = question.lower().strip()

    patterns = [
        "meilleur joueur selon les fans",
        "meilleur joueur nba actuellement selon les fans",
        "joueur préféré",
        "joueur prefere",
        "préféré des fans",
        "prefere des fans",
        "popularité globale",
        "popularite globale",
        "avis général",
        "avis general",
        "opinion générale",
        "opinion generale",
        "consensus des fans",
    ]

    return any(p in q for p in patterns)

def is_reports_question(question: str) -> bool:
    q = question.lower().strip()

    patterns = [
        "reddit",
        "discussion",
        "discussions",
        "commentaire",
        "commentaires",
        "fans",
        "supporters",
        "que disent",
        "que pensent",
        "que raconte",
        "que racontent",
        "mentionné",
        "mentionnés",
        "mentionnées",
        "plus mentionnés",
        "plus mentionnes",
        "rapport",
        "rapports",
        "report",
        "reports",
    ]

    return any(p in q for p in patterns)


def build_refusal_answer(question: str) -> str:
    if is_unsupported_question(question):
        return REFUSAL_MESSAGES["unsupported"]

    if is_subjective_question(question):
        return REFUSAL_MESSAGES["subjective"]

    if is_noisy_question(question):
        return REFUSAL_MESSAGES["noisy"]

    return REFUSAL_MESSAGES["noisy"]

def is_reports_aggregation_question(question: str) -> bool:
    q = question.lower().strip()

    patterns = [
        "plus mentionnés dans les discussions reddit",
        "plus mentionnes dans les discussions reddit",
        "plus mentionnés sur reddit",
        "plus mentionnes sur reddit",
        "plus cités sur reddit",
        "plus cites sur reddit",
        "joueurs les plus mentionnés",
        "joueurs les plus mentionnes",
        "joueurs les plus cités",
        "joueurs les plus cites",
        "noms reviennent le plus",
        "top joueurs mentionnés",
        "top joueurs mentionnes",
    ]

    return any(p in q for p in patterns)

def is_plot_question(question: str) -> str | None:
    q = question.lower().strip()

    # =========================
    # EVOLUTION → LINE
    # =========================
    if any(p in q for p in [
        "évolution",
        "evolution",
        "progression",
        "au fil du temps",
        "par match",
        "par saison",
    ]):
        return "line"

    # =========================
    # COMPARAISON → BAR
    # =========================
    if any(p in q for p in [
        "compare",
        "comparer",
        "comparaison",
        "vs",
        "entre",
    ]):
        return "bar"

    # =========================
    # CLASSEMENT / TOP → BAR
    # =========================
    if any(p in q for p in [
        "top",
        "classement",
        "meilleurs",
        "plus de",
        "moins de",
        "leaders",
        "scoreurs",
        "scoreur",
        "marqueurs",
        "marqueur",
        "meilleurs scoreurs",
        "meilleurs marqueurs",
    ]):
        return "bar"

    # =========================
    # EXPLICITE → BAR
    # =========================
    if any(p in q for p in [
        "graphique",
        "graphe",
        "courbe",
        "histogramme",
        "camembert",
    ]):
        return "bar"

    return None