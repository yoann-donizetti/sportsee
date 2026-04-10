from typing import Optional


def sql_rows_to_plot_data(rows: list[dict], max_items: int = 10) -> list[dict]:
    """Transforme des lignes SQL en données simples pour le PlotTool."""
    if not rows:
        return []

    first_row = rows[0]
    keys = list(first_row.keys())

    if len(keys) < 2:
        return []

    label_key = keys[0]
    value_key = keys[1]

    plot_data = []

    for row in rows:
        label = str(row.get(label_key, ""))
        value = row.get(value_key)

        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        plot_data.append(
            {
                "label": label,
                "value": value,
            }
        )

    # Tri décroissant sur la valeur
    plot_data.sort(key=lambda x: x["value"], reverse=True)

    # Limitation du nombre d’éléments affichés
    return plot_data[:max_items]


def build_plot_title(question: str) -> str:
    """Construit un titre simple à partir de la question."""
    return f"Visualisation - {question}"