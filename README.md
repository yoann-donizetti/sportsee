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

Le système s’appuie sur un pipeline RAG structuré en plusieurs étapes :

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

## Modules principaux

### rag_pipeline/vector_store.py

Gère la base vectorielle FAISS et la recherche sémantique :

- chargement et découpage des documents en chunks ;
- génération des embeddings avec Mistral ;
- création et sauvegarde de l’index FAISS ;
- recherche des documents les plus pertinents (similarité cosinus).

---

### rag_pipeline/rag_pipeline.py

Implémente le pipeline RAG complet :

- récupération des documents pertinents (retrieval) ;
- construction du contexte ;
- génération du prompt ;
- appel au modèle Mistral ;
- structuration de la réponse avec Pydantic.

---

### utils/data_loader.py

Gère le chargement et le parsing des données :

- extraction de texte depuis différents formats (PDF, TXT, DOCX, CSV, Excel) ;
- fallback OCR pour les PDF scannés ;
- enrichissement des métadonnées.

---

### evaluate/core/

Contient la logique d’évaluation :

- construction du dataset RAGAS ;
- exécution des métriques (faithfulness, relevancy, etc.) ;
- sauvegarde des résultats ;
- validation des données avec Pydantic.

---

## Paramétrage

L’application est configurable via le fichier `rag_pipeline/config.py`.

Les principaux paramètres modifiables sont :

- **Modèles Mistral**
  - modèle de génération (`MODEL_NAME`)
  - modèle d’embedding (`EMBEDDING_MODEL`)

- **Indexation**
  - taille des chunks (`CHUNK_SIZE`)
  - chevauchement des chunks (`CHUNK_OVERLAP`)
  - taille des batchs pour les embeddings (`EMBEDDING_BATCH_SIZE`)

- **Recherche**
  - nombre de documents retournés (`SEARCH_K`)
  - seuil minimum de similarité (optionnel)

- **Chemins**
  - dossier des données (`INPUT_DIR`)
  - index vectoriel (`VECTOR_DB_DIR`)
  - fichiers FAISS et chunks

- **Évaluation**
  - dataset RAGAS utilisé
  - fichiers de sortie (CSV, JSON)

- **Application**
  - nom de l’assistant (`NAME`)
  - titre de l’application (`APP_TITLE`)

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

## Exécution du projet
### 1. Ajouter des documents

Placez vos documents dans le dossier `inputs/`. Les formats supportés sont :
- PDF
- TXT
- DOCX
- CSV
- Excel (.xlsx, xls)

Les documents peuvent être organisés dans des sous-dossiers pour faciliter le classement des sources.


### 2. Indexer les documents

Exécutez le script d’indexation pour parser les fichiers, créer les chunks, générer les embeddings et construire l’index FAISS :

```bash
python -m indexer
```

Ce script va :
1. Charger les documents depuis le dossier `inputs/`
2. Découper les documents en chunks
3. Générer des embeddings avec Mistral
4. Créer un index FAISS pour la recherche sémantique
5. Sauvegarder l'index et les chunks dans le dossier `vector_db/`

### 3. Lancer l'application

```bash
streamlit run MistralChat.py
```

L'application sera accessible à l'adresse http://localhost:8501 dans votre navigateur.


### 4. Lancer l'évaluation RAGAS 

```bash
python -m evaluate.scripts.evaluate_ragas
```

Les résultats sont générés dans :

- [Résultats détaillés RAGAS (CSV)](evaluate/results/ragas_results.csv)
- [Résumé des scores RAGAS (JSON)](evaluate/results/ragas_summary.json)
- [Rapport d’évaluation RAGAS (baseline)](docs/rapport_ragas_baseline.md)

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
Faire évoluer le système d’un assistant **convaincant** vers un assistant **fiable et robuste**, capable de répondre correctement à des questions métier complexes.