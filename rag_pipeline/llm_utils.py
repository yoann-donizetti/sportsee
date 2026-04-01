from __future__ import annotations

from mistralai.client import MistralClient

from rag_pipeline.config import MISTRAL_API_KEY, MODEL_NAME


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


