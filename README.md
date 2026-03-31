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



## Architecture du système

Le projet repose sur une architecture hybride combinant :

1. **Base de données (PostgreSQL)**
   - stockage structuré des données NBA ;
   - support pour les requêtes analytiques (SQL).

2. **Pipeline RAG**
   - récupération de contexte via FAISS ;
   - génération de réponses avec Mistral.

3. **Évaluation automatique**
   - mesure de la qualité via RAGAS.

---

###  Pipeline RAG

Le système s’appuie sur un pipeline structuré en plusieurs étapes :

1. **Retrieval**
   - indexation des documents (FAISS) ;
   - recherche des contenus les plus pertinents.

2. **Context building**
   - sélection et agrégation des chunks ;
   - construction du contexte envoyé au modèle.

3. **Generation**
   - appel au modèle Mistral ;
   - production de la réponse finale.

4. **Validation**
   - structuration des sorties avec Pydantic ;
   - contrôle du format et de la cohérence.

5. **Évaluation**
   - scoring avec RAGAS :
     - faithfulness
     - answer relevancy
     - context precision
     - context recall

---

###  Vision cible

Faire évoluer le système vers une architecture hybride complète :

- **SQL** → réponses fiables, calculs précis, données structurées  
- **RAG** → contexte, explication, enrichissement  

Cette approche permet :
- de réduire les hallucinations ;
- d’améliorer la précision des réponses ;
- d’augmenter la robustesse globale du système.



##  Base de données (PostgreSQL)

Le projet s’appuie également sur une base de données PostgreSQL pour stocker :

- les données structurées (équipes, joueurs, statistiques) ;
- les données textuelles (rapports Reddit / PDF) ;
- les futures données match par match.

### Tables principales

- `teams` : équipes NBA
- `players` : joueurs et affiliation équipe
- `stats` : statistiques agrégées par joueur
- `reports` : contenus textuels (RAG)

### Rôle dans le système

- PostgreSQL permet de répondre à des questions **fiables et chiffrées**
- le RAG permet d’apporter du **contexte et de l’interprétation**

Le système évolue vers une architecture hybride :
- SQL → précision et fiabilité des données
- RAG → enrichissement et compréhension du contexte

### Documentations
- [README](database/README.md)
- [SCHEMA SQL](docs/schema_sql.md)



## SQL Tool (questions chiffrées)

Le système intègre un SQL Tool permettant de répondre aux questions nécessitant des données chiffrées.

Fonctionnement :

- détection des questions chiffrées (routing)
- génération d'une requête SQL via le LLM
- validation de la requête (SELECT uniquement)
- exécution sur PostgreSQL (lecture seule)
- synthèse des résultats en langage naturel

Exemples :

- "Qui sont les meilleurs scoreurs ?"
- "Quel joueur a le plus de rebonds ?"

Ce module permet :

- d'améliorer la précision
- de réduire les hallucinations
- de garantir la fiabilité des données numériques

## Routing des requêtes

Le système utilise un mécanisme de routing simple pour orienter les questions :

- Questions chiffrées → SQL Tool
- Questions textuelles → RAG
- Questions hybrides → limitation actuelle

Ce routing permet d'améliorer la pertinence des réponses en utilisant le bon outil selon le type de question.

## Exemples de questions

- Qui sont les 5 meilleurs scoreurs ?
- Quel joueur a le plus de rebonds ?
- Quelle équipe a le meilleur offensive rating ?
- Pourquoi Indiana impressionne cette saison ?

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

sportsee/
│
├── indexer.py                    # Script principal d’indexation des documents
├── MistralChat.py                # Interface utilisateur Streamlit pour interroger le système
│
├── database/                     # Gestion de la base PostgreSQL
│   ├── init_db.sql               # Initialisation de la base, de l’utilisateur et des droits
│   ├── schema.sql                # Création du schéma SQL (tables, contraintes, index, commentaires)
│   ├── schemas.py                # Schémas Pydantic pour valider les données avant insertion
│   ├── load_excel_to_db.py       # Chargement des données structurées Excel dans PostgreSQL
│   ├── load_reports.py           # Chargement des rapports PDF Reddit dans PostgreSQL
|   ├── db_utils.py               # Fonctions utilitaires pour l'accès et la gestion de la base de données
│   └── README.md                 # Documentation technique dédiée à la base de données
│
├── rag_pipeline/                 # Pipeline RAG principal
│   ├── config.py                 # Configuration globale du projet (modèles, chemins, DB, etc.)
│   ├── rag_pipeline.py           # Logique de retrieval, construction de contexte et génération
│   └── vector_store.py           # Gestion de l’index FAISS et de la recherche sémantique
│
├── evaluate/                     # Évaluation automatique du système avec RAGAS
│   ├── core/                     # Modules internes de préparation et d’évaluation
│   │   ├── cleaning.py           # Nettoyage / préparation des données d’évaluation
│   │   ├── dataset_loader.py     # Chargement du dataset d’évaluation
│   │   ├── ragas_builder.py      # Construction des objets nécessaires à RAGAS
│   │   ├── ragas_runner.py       # Lancement des métriques RAGAS
│   │   ├── safe_mistral.py       # Appels sécurisés au modèle Mistral
│   │   ├── saver.py              # Sauvegarde des résultats d’évaluation
│   │   └── schemas.py            # Validation Pydantic des données d’évaluation
│   │
│   ├── datasets/                 # Jeux de test pour l’évaluation
│   │   └── rag_eval_dataset.json # Dataset de questions métier
│   │
│   ├── results/                  # Résultats générés par les évaluations
│   │   └── baseline/             # Résultats de la baseline initiale
│   │       ├── ragas_results.csv # Résultats détaillés par question
│   │       └── ragas_summary.json# Résumé global des scores
│   │
│   └── scripts/                  # Scripts exécutables d’évaluation
│       └── evaluate_ragas.py     # Script principal de lancement RAGAS
│
├── utils/                        # Fonctions utilitaires partagées
│   ├── data_loader.py            # Chargement et parsing multi-format (PDF, OCR, Excel, TXT, CSV…)
│   └── logging_config.py         # Configuration centralisée du logging
│
├── docs/                         # Documentation et rapports
│   ├── rapport_ragas_baseline.md # Rapport d’analyse de la baseline RAGAS
│   └── schema_sql.md             # Description fonctionnelle du schéma SQL
│
├── inputs/                       # Données sources du projet
│                                 # - fichier Excel NBA
│                                 # - PDF Reddit / rapports
│
├── vector_db/                    # Index vectoriel FAISS généré automatiquement
│   └── faiss_index.idx           # Fichier d’index utilisé pour le retrieval
│
├── requirements.txt              # Dépendances Python du projet
├── README.md                     # Documentation principale du projet
└── .gitignore                    # Fichiers et dossiers ignorés par Git
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

DB_HOST=localhost
DB_PORT=5432
DB_NAME=sportsee
DB_USER=sportsee_user
DB_PASSWORD=your_password

## Exécution du projet
### 1. Initialiser la base de données
```bash
psql -U postgres -f database/init_db.sql
```

### 2. Ajouter des documents

Placez vos documents dans le dossier `inputs/`. Les formats supportés sont :
- PDF
- TXT
- DOCX
- CSV
- Excel (.xlsx, xls)

Les documents peuvent être organisés dans des sous-dossiers pour faciliter le classement des sources.

###  3. Charger les données dans PostgreSQL

Données structurées (Excel)
```bash
python -m database.load_excel_to_db
```

Données textuelles (PDF / Reddit)

```bash
python -m database.load_reports
```


### 4. Indexer les documents

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

### 5. Lancer l'application

```bash
streamlit run MistralChat.py
```

L'application sera accessible à l'adresse http://localhost:8501 dans votre navigateur.


### 6. Lancer l'évaluation RAGAS 

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
- gestion imparfaite des questions hybrides (SQL + RAG)
- dépendance au mapping langage naturel → SQL
- absence de fallback intelligent en cas d'erreur SQL


## Améliorations prévues

- intégration d’un Tool SQL pour les questions chiffrées
- meilleure gestion du refus
- amélioration du retrieval (chunking, reranking)
- seconde évaluation comparative

## Objectif
Faire évoluer le système d’un assistant **convaincant** vers un assistant **fiable et robuste**, capable de répondre correctement à des questions métier complexes.