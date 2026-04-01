"""Ce module contient des fonctions pour nettoyer et préparer les résultats RAGAS
pour une analyse plus facile et plus lisible. Il supprime les colonnes dupliquées,
conserve uniquement les colonnes pertinentes, nettoie les réponses textuelles,
convertit les métriques en valeurs numériques arrondies, interprète les résultats
pour une lecture qualitative simple, et détermine si le comportement du modèle est jugé correct."""
from typing import Any
import pandas as pd


def clean_results_for_analysis(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoie le DataFrame des résultats RAGAS afin d'obtenir un fichier
    plus lisible et plus simple à analyser.
    Cette fonction effectue les opérations suivantes :
    - Supprime les colonnes dupliquées.
    - Conserve uniquement les colonnes pertinentes pour l'analyse.
    - Nettoie les réponses textuelles générées par le modèle.
    - Convertit les métriques en valeurs numériques et les arrondit à 3 décimales.
    - Interprète les résultats pour produire une lecture qualitative simple.
    - Détermine si le comportement du modèle est jugé correct.
    args :
      results_df : DataFrame contenant les résultats bruts de l'évaluation RAGAS.
    return :
      DataFrame nettoyé et enrichi avec des interprétations qualitatives et une indication de correction.
    raises :
      ValueError si le DataFrame d'entrée ne contient pas les colonnes nécessaires pour l'analyse.
    """
    df = results_df.loc[:, ~results_df.columns.duplicated()].copy()

    cols_to_keep = [
        "id",
        "category",
        "answerable",
        "question",
        "ground_truth",
        "answer",
        "route_used",
        "sql_success",
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
        "refusal_ok",
    ]

    cols_to_keep = [col for col in cols_to_keep if col in df.columns]
    df = df[cols_to_keep].copy()

    def clean_answer(text: Any) -> Any:
        """
        Nettoie une réponse textuelle générée par le modèle.
        Cette fonction effectue les opérations suivantes :
        - Remplace les sauts de ligne par des espaces.
        - Remplace les points-virgules par des virgules.
        - Supprime les espaces en trop.
         Si l'entrée n'est pas une chaîne de caractères, elle est retournée telle quelle.
         return la réponse nettoyée.
         args :
           text : La réponse textuelle à nettoyer.
        return :
              La réponse nettoyée, ou l'entrée originale si ce n'est pas une chaîne de caractères.
            """
        if not isinstance(text, str):
            return text

        text = text.replace("\n", " ")
        text = text.replace(";", ",")
        text = " ".join(text.split())
        return text

    if "answer" in df.columns:
        df["answer"] = df["answer"].apply(clean_answer)

    metric_cols = [
        col
        for col in [
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "context_recall",
        ]
        if col in df.columns
    ]

    for col in metric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df[col] = df[col].round(3)

    def interpret(row: pd.Series) -> str:
        """
        Interprète les résultats pour produire une lecture qualitative simple.
        Selon les critères suivants :
        - Si la question est non-répondable, le refus est un "Bon refus" 
        si "refusal_ok" est True, sinon c'est une "Hallucination".
        - Si la question est répondable, la lecture est basée sur les métriques "answer_relevancy" et "context_precision" :
          - "Très bon" si answer_relevancy >= 0.8 et context_precision >= 0.8
          - "Correct" si answer_relevancy >= 0.5
          - "Faible" sinon
        Si les métriques ne sont pas calculables, la lecture est "Non calculé".

        args :
          row : Une ligne du DataFrame contenant les résultats d'une question d'évaluation.
        return :
          Une chaîne de caractères représentant l'interprétation qualitative des résultats pour cette question.
        raises :
          KeyError si les colonnes nécessaires pour l'interprétation ne sont pas présentes dans la ligne.
        """
        if row.get("answerable") is False:
            if row.get("refusal_ok") is True:
                return "Bon refus"
            return "Hallucination"

        ar = row.get("answer_relevancy")
        cp = row.get("context_precision")

        if not isinstance(ar, (int, float)) or not isinstance(cp, (int, float)):
            return "Non calculé"

        if ar >= 0.8 and cp >= 0.8:
            return "Très bon"
        elif ar >= 0.5:
            return "Correct"
        else:
            return "Faible"

    def compute_correct(row: pd.Series) -> bool:
        """
        Détermine si le comportement du modèle est jugé correct.
        Selon les critères suivants :
        - Si la question est non-répondable, le refus est correct si "refusal_ok" est True.
        - Si la question est répondable, la réponse est considérée comme correcte si "answer_relevancy" est supérieur ou égal à 0.8.
        return True si le comportement est correct, False sinon.

        """
        if row.get("answerable") is False:
            return bool(row.get("refusal_ok"))

        ar = row.get("answer_relevancy")

        if not isinstance(ar, (int, float)):
            return False

        return ar >= 0.8

    df["lecture"] = df.apply(interpret, axis=1)
    df["is_correct"] = df.apply(compute_correct, axis=1)

    for col in metric_cols:
        df[col] = df[col].apply(lambda x: "non calculé" if pd.isna(x) else x)

    return df