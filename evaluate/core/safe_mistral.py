"""Module safe_mistral.

Ce module contient une version sécurisée du client `ChatMistralAI`
utilisé par LangChain.

Objectif :
corriger localement un problème de fusion des métadonnées `token_usage`
renvoyées par Mistral lors de l'évaluation RAGAS.

Contexte :
dans certains cas, `token_usage` contient des dictionnaires imbriqués
au lieu de simples valeurs numériques. La méthode standard de LangChain
tente alors de faire une addition directe entre dictionnaires, ce qui
provoque une erreur de type.

Cette implémentation surcharge donc la méthode de fusion pour :
- additionner correctement les valeurs numériques,
- fusionner proprement les dictionnaires imbriqués,
- conserver également le `system_fingerprint` si présent.

Avantage :
la correction est intégrée au projet, versionnée, et reproductible,
sans modification manuelle des librairies installées dans l'environnement.
"""

from typing import Any

from langchain_mistralai.chat_models import ChatMistralAI


class SafeChatMistralAI(ChatMistralAI):
    """
    Version sécurisée de `ChatMistralAI`.

    Cette classe hérite du client standard `ChatMistralAI` fourni
    par `langchain_mistralai` et redéfinit la méthode interne
    `_combine_llm_outputs`.

    Pourquoi cette surcharge :
    la version standard peut échouer lorsqu'elle tente de fusionner
    les informations de consommation (`token_usage`) si certaines
    valeurs sont des dictionnaires imbriqués au lieu de scalaires.

    Cette version :
    - gère correctement les scalaires numériques,
    - fusionne les sous-dictionnaires de manière robuste,
    - évite l'erreur `TypeError: unsupported operand type(s) for +=: 'dict' and 'dict'`.
    """

    def _combine_llm_outputs(
        self,
        llm_outputs: list[dict[str, Any] | None]
    ) -> dict[str, Any]:
        """
        Fusionne les sorties LLM renvoyées par plusieurs appels Mistral.

        Cette méthode est appelée par LangChain pour agréger les métadonnées
        associées à plusieurs générations, notamment :
        - `token_usage`
        - `system_fingerprint`

        Args:
            llm_outputs:
                Liste de dictionnaires représentant les sorties LLM brutes.
                Chaque élément peut être :
                - un dictionnaire contenant les métadonnées d'un appel,
                - ou `None` si aucun résultat n'est disponible.

        Returns:
            Un dictionnaire combiné contenant :
            - `token_usage` fusionné de façon robuste,
            - `system_fingerprint` si disponible.

        Logique :
        - si une valeur de `token_usage` est un scalaire numérique,
          elle est additionnée à la valeur précédente ;
        - si une valeur de `token_usage` est un dictionnaire imbriqué,
          ses sous-clés sont fusionnées une par une ;
        - si une valeur n'est pas numérique, elle est simplement remplacée.
        """

        # Dictionnaire final qui stockera l'agrégation des consommations
        # de tokens renvoyées par les différents appels LLM.
        overall_token_usage: dict[str, Any] = {}

        # Empreinte système éventuellement renvoyée par Mistral.
        # On conserve la dernière valeur non vide rencontrée.
        system_fingerprint = None

        # Parcours de toutes les sorties LLM à fusionner.
        for output in llm_outputs:
            # Si une sortie est absente, on l'ignore simplement.
            if output is None:
                continue

            # Récupère le bloc token_usage s'il existe,
            # sinon utilise un dictionnaire vide par défaut.
            token_usage = output.get("token_usage", {})

            # Si des informations de consommation existent,
            # on les fusionne dans overall_token_usage.
            if token_usage:
                for k, v in token_usage.items():

                    # Cas 1 : la valeur associée à la clé courante
                    # est elle-même un dictionnaire imbriqué.
                    if isinstance(v, dict):

                        # Si la clé n'existe pas encore ou n'est pas un dict,
                        # on initialise un sous-dictionnaire vide.
                        if k not in overall_token_usage or not isinstance(overall_token_usage.get(k), dict):
                            overall_token_usage[k] = {}

                        # Fusion clé par clé du sous-dictionnaire.
                        for sub_k, sub_v in v.items():
                            previous = overall_token_usage[k].get(sub_k, 0)

                            # Si l'ancienne et la nouvelle valeur sont numériques,
                            # on les additionne.
                            if isinstance(previous, (int, float)) and isinstance(sub_v, (int, float)):
                                overall_token_usage[k][sub_k] = previous + sub_v
                            else:
                                # Sinon, on remplace simplement la valeur.
                                overall_token_usage[k][sub_k] = sub_v

                    # Cas 2 : la valeur est un scalaire simple.
                    else:
                        previous = overall_token_usage.get(k, 0)

                        # Si les deux valeurs sont numériques, on cumule.
                        if isinstance(previous, (int, float)) and isinstance(v, (int, float)):
                            overall_token_usage[k] = previous + v
                        else:
                            # Sinon, on remplace.
                            overall_token_usage[k] = v

            # Récupère l'empreinte système si elle existe.
            # On conserve la dernière valeur non vide rencontrée.
            fingerprint = output.get("system_fingerprint")
            if fingerprint:
                system_fingerprint = fingerprint

        # Construction du dictionnaire final renvoyé à LangChain.
        combined: dict[str, Any] = {}

        # N'ajoute token_usage que si des valeurs ont bien été fusionnées.
        if overall_token_usage:
            combined["token_usage"] = overall_token_usage

        # N'ajoute system_fingerprint que s'il est disponible.
        if system_fingerprint:
            combined["system_fingerprint"] = system_fingerprint

        return combined