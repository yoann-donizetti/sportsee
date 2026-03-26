"""Ce module contient des fonctions pour charger le dataset d'évaluation RAGAS à partir d'un fichier JSON.
Il définit une classe EvalSample pour représenter chaque question d'évaluation, 
avec validation des données à l'aide de Pydantic. 
La fonction load_eval_dataset lit le fichier JSON, valide chaque question, 
et retourne une liste d'instances EvalSample prêtes à être utilisées pour l'évaluation."""

import json
import logging
from pydantic import BaseModel, Field, ValidationError
import json
import logging
from pydantic import ValidationError

from evaluate.core.schemas import EvalSample


def load_eval_dataset(dataset_path: str) -> list[EvalSample]:
    """
    Charge le dataset d'évaluation RAGAS à partir d'un fichier JSON.
    Le fichier JSON doit être une liste d'objets,
    chacun représentant une question d'évaluation.
    Chaque objet doit contenir les champs suivants :
    - id : Identifiant unique de la question (entier positif).
    - question : Texte de la question.
    - ground_truth : Réponse correcte à la question.
    - category : Catégorie de la question.
    - answerable : Indique si la question est répondable.
    La fonction valide chaque question à l'aide de Pydantic et retourne une liste d'instances EvalSample.
    Si une question est invalide, une erreur de validation est levée avec des détails sur les erreurs.
    args :
      dataset_path : Chemin vers le fichier JSON contenant le dataset d'évaluation RAGAS.
    return :
      list[EvalSample]
    raises : 
      ValidationError si une question du dataset est invalide.
    
        """
    logging.info(f"Chargement du dataset depuis : {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    samples: list[EvalSample] = []

    for row in raw_data:
        try:
            sample = EvalSample(**row)
            samples.append(sample)
        except ValidationError as e:
            logging.error(f"Ligne invalide dans le dataset : {row}")
            logging.error(e.json())
            raise

    logging.info(f"{len(samples)} questions validées avec Pydantic.")
    return samples