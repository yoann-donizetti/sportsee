from __future__ import annotations

from mistralai.client import MistralClient

from rag_pipeline.config import MISTRAL_API_KEY, MODEL_NAME,REFUSAL_MESSAGE


client = MistralClient(api_key=MISTRAL_API_KEY)


def ask_mistral(
    prompt: str,
    model: str = MODEL_NAME,
    temperature: float = 0.1,
) -> str:
    """Envoie un prompt à Mistral et retourne le texte de réponse."""
    response = client.chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=temperature,
    )

    return response.choices[0].message.content.strip()




def build_refusal_answer(question: str) -> str:
    q = question.lower()

    # Cas temporel
    if any(x in q for x in ["dernier", "match", "5 matchs", "last", "recent"]):
        return (
            "Je ne dispose pas de données temporelles (par match ou sur une période). "
            "Les données disponibles correspondent à une saison globale."
        )

    # Cas domicile / extérieur
    if any(x in q for x in ["domicile", "extérieur", "home", "away"]):
        return (
            "Je ne dispose pas de données séparées domicile/extérieur dans les informations disponibles."
        )

    # Cas inconnu / bruit / hors scope
    return REFUSAL_MESSAGE