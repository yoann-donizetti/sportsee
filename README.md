# NBA Analyst AI — Assistant RAG avec Mistral

Ce projet implémente un assistant IA basé sur la technique de **Retrieval-Augmented Generation (RAG)** pour répondre à des questions sur des données NBA.

L’objectif est de construire un système capable de :
- répondre à des questions factuelles et analytiques ;
- s’appuyer sur des données structurées ;
- être évalué de manière rigoureuse (RAGAS).

---

## Fonctionnalités

-  **Recherche sémantique** avec FAISS
-  **Génération de réponses** avec Mistral
-  **Évaluation automatique avec RAGAS**
-  **Dataset de test structuré** (questions simples, complexes, bruitées)
-  **Validation des données avec Pydantic**
-  **Observabilité avec Logfire + logging structuré**

---

##  Architecture

Le système repose sur un pipeline RAG complet :

1. **Retrieval**
   - indexation des données (FAISS)
   - recherche des documents pertinents

2. **Context building**
   - sélection et formatage des chunks

3. **Generation**
   - appel au modèle Mistral
   - production de la réponse

4. **Validation**
   - structuration des sorties avec Pydantic

5. **Évaluation**
   - scoring avec RAGAS :
     - faithfulness
     - answer relevancy
     - context precision
     - context recall

---

##  Résultats (Baseline)

| Metric              | Score |
|--------------------|------|
| Faithfulness       | 0.53 |
| Answer Relevancy   | 0.79 |
| Context Precision  | 0.30 |
| Context Recall     | 0.49 |
| Refusal Rate       | 0.00 |

Le score de refusal rate à 0.00 indique que le système ne sait pas refuser
les questions hors périmètre et génère systématiquement une réponse,
même lorsque l'information n'est pas disponible.

###  Interprétation

- Bonne compréhension globale des questions
- Problèmes de fiabilité (hallucinations)
- Retrieval encore bruité
- Aucune gestion du refus (point critique)

---

##  Structure du projet
```bash

nba-analyst-ai/
├── docs/                         # Documentation, rapports d'analyse
│   └── rapport_ragas_baseline.md
│
├── evaluate/                     # Évaluation automatique du système
│   ├── core/
│   │   ├── cleaning.py
│   │   ├── dataset_loader.py
│   │   ├── ragas_builder.py
│   │   ├── ragas_runner.py
│   │   ├── safe_mistral.py
│   │   ├── saver.py
│   │   └── schemas.py
│   │
│   ├── datasets/
│   │   └── rag_eval_dataset.json
│   │
│   ├── results/
│   │   ├── ragas_results.csv
│   │   └── ragas_summary.json
│   │
│   └── scripts/
│       └── evaluate_ragas.py
│
├── rag_pipeline/                 # Pipeline RAG principal
│   ├── config.py
│   ├── rag_pipeline.py
│   └── vector_store.py
│
├── utils/                        # Fonctions utilitaires
│   ├── data_loader.py
│   └── logging_config.py
│
├── inputs/                       # Données sources à indexer
│
├── vector_db/                    # Index FAISS (non versionné, généré automatiquement)
│   └── faiss_index.idx
│
├── indexer.py                    # Script d'indexation
├── MistralChat.py                # Interface utilisateur (Streamlit)
├── requirements.txt
├── README.md
└── .gitignore
```
---

## Installation

```bash
git clone <repo>
cd <repo>

python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sous Windows

pip install -r requirements.txt
```
## Configuration

Créer un fichier .env :

MISTRAL_API_KEY=your_api_key

## Lancer l’évaluation

```bash
python evaluate/scripts/evaluate_ragas.py
```

## Dataset d’évaluation
Le système est testé sur :
- questions factuelles simples
- questions complexes
- comparaisons
- questions bruitées
- questions non répondables

## Limites actuelles

- hallucinations sur certaines questions
- mauvaise gestion des données absentes
- retrieval perfectible (bruit + manque de précision)


## Améliorations prévues

- intégration d’un Tool SQL pour les questions chiffrées
- meilleure gestion du refus
- amélioration du retrieval (chunking, reranking)
- seconde évaluation comparative

## Objectif
Faire évoluer le système d’un assistant **convaincant** vers un assistant **fiable et robuste**, capable de répondre correctement à des questions métier complexe.