![CI](https://github.com/yoann-donizetti/sportsee/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10-blue)
![Tests](https://img.shields.io/badge/tests-pytest-green)
![Vector Search](https://img.shields.io/badge/vector%20search-FAISS-purple)
![RAG](https://img.shields.io/badge/RAG-LangChain-orange)
![LLM](https://img.shields.io/badge/LLM-Mistral-red)
![API](https://img.shields.io/badge/API-FastAPI-009688)
![Docker](https://img.shields.io/badge/docker-ready-blue)


# NBA Analyst AI — Assistant RAG avec Mistral

## Table des matières

- [Fonctionnalités](#fonctionnalités)
- [Architecture du système](#architecture-du-système)
- [API REST](#api-rest)
- [Base de données (PostgreSQL)](#-base-de-données-postgresql)
- [SQL Tool (questions chiffrées et agrégations structurées)](#sql-tool-questions-chiffrées-et-agrégations-structurées)
- [Routing des requêtes](#routing-des-requêtes)
- [Exemples de questions](#exemples-de-questions)
- [Résultats d’évaluation](#résultats-dévaluation)
- [Structure du projet](#-structure-du-projet)
- [Modules principaux](#modules-principaux)
- [Paramétrage](#paramétrage)
- [Installation](#installation)
- [Configuration](#configuration)
- [Exécution du projet](#exécution-du-projet)
- [Dataset d’évaluation](#dataset-dévaluation)
- [Limites actuelles](#limites-actuelles)
- [Améliorations prévues](#améliorations-prévues)
- [Objectif](#objectif)

Ce projet implémente un assistant IA hybride pour répondre à des questions sur des données NBA, en combinant :

- un **SQL Tool** pour les questions chiffrées et analytiques ;
- un **pipeline RAG** pour les questions textuelles et contextuelles ;
- un **mécanisme de refus** pour les questions hors périmètre, bruitées ou non supportées.

L’objectif est de construire un système capable de :

- répondre à des questions factuelles, analytiques et contextuelles ;
- s’appuyer sur des données structurées et textuelles ;
- limiter les hallucinations ;
- être évalué de manière rigoureuse avec **RAGAS** et des indicateurs métier.

---

## Table des matières



## Fonctionnalités

- **Recherche sémantique** avec FAISS
- **Génération de réponses** avec Mistral
- **Routing des questions** vers SQL, RAG ou refus
- **SQL Tool** pour les questions chiffrées et les agrégations fiables
- **Gestion du refus** sur les questions hors périmètre, bruitées ou non supportées
- **Évaluation automatique avec RAGAS**
- **Dataset de test structuré** (questions simples, complexes, comparatives, bruitées, non répondables)
- **Validation des données avec Pydantic**
- **Observabilité avec Logfire + logging structuré**

---



## Architecture du système

Le projet repose sur une architecture hybride combinant :

1. **Base de données (PostgreSQL)**
   - stockage structuré des données NBA ;
   - support pour les requêtes analytiques ;
   - exploitation de données textuelles structurées via la table `reports`.

2. **Pipeline RAG**
   - récupération de contexte via FAISS ;
   - génération de réponses textuelles avec Mistral.

3. **Routing**
   - orientation automatique des questions vers le bon composant :
     - **SQL** pour les questions chiffrées ;
     - **RAG** pour les questions textuelles ;
     - **REFUS** pour les questions non supportées ou hors périmètre.

4. **Évaluation automatique**
   - mesure de la qualité via RAGAS ;
   - suivi d’indicateurs complémentaires (`route_used`, `sql_success`, `refusal_ok`, `is_correct`).

---

###  Pipeline RAG

Le système s’appuie sur un pipeline structuré en plusieurs étapes :

1. **Routing**
   - détection du type de question ;
   - orientation vers SQL, RAG ou refus.

2. **Retrieval**
   - recherche sémantique dans FAISS pour les questions textuelles.

3. **Context building**
   - sélection et agrégation des chunks pertinents.

4. **Generation / Synthesis**
   - génération d’une réponse avec Mistral ;
   - ou synthèse d’un résultat SQL en langage naturel.

5. **Validation**
   - structuration des sorties avec Pydantic ;
   - contrôle du format et de la cohérence.

6. **Évaluation**
   - scoring avec RAGAS ;
   - suivi des performances métier et des refus.

---

### Vision du système final

Le système final repose sur une architecture hybride complète :

- **SQL** → réponses fiables, calculs précis, agrégations et comparaisons structurées ;
- **RAG** → contexte textuel, synthèse et interprétation ;
- **REFUS** → sécurité sur les questions hors périmètre, bruitées ou non supportées.

Cette approche permet :

- de réduire fortement les hallucinations ;
- d’améliorer la précision des réponses ;
- d’augmenter la robustesse globale du système ;
- de mieux aligner la réponse avec le type réel de question posé.


### Schéma d’architecture

Le système repose sur une architecture hybride combinant plusieurs composants :

```text
                ┌──────────────────────────────┐
                │        Streamlit UI          │
                │   (interface utilisateur)    │
                └──────────────┬───────────────┘
                               │
                               ▼
                ┌──────────────────────────────┐
                │        API FastAPI           │
                │   (routing + orchestration)  │
                └──────────────┬───────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   SQL Tool    │     │   Pipeline RAG    │     │     REFUS        │
│ (PostgreSQL)  │     │ (FAISS + Mistral)│     │ (fallback safe)  │
└──────┬────────┘     └────────┬─────────┘     └────────┬────────┘
       │                        │                        │
       ▼                        ▼                        ▼
┌───────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Base SQL NBA  │     │  Vector Store     │     │  Réponse refus   │
│ (données)     │     │  (documents)      │     │  contrôlé        │
└───────────────┘     └──────────────────┘     └─────────────────┘
```
#### Fonctionnement global
L’utilisateur pose une question via Streamlit
- La requête est envoyée à l’API FastAPI
- Le système analyse la question (routing) :
   - SQL → données structurées (statistiques NBA)
   - RAG → contexte textuel (reports, Reddit)
   - REFUS → si la question est hors périmètre
- Le moteur sélectionné génère la réponse
- L’API renvoie la réponse à Streamlit

#### Avantages de cette architecture
- séparation claire des responsabilités
- meilleure maintenabilité
- réduction des hallucinations
- réponses adaptées au type de question
- système scalable (API réutilisable)

#### Limites actuelles
- routing perfectible (cas hybrides)
- dépendance au mapping NL → SQL
-évaluation RAGAS partiellement adaptée aux systèmes hybrides


## API REST

Le système est exposé via une API REST construite avec **FastAPI**.

Cette API permet :

- d’interroger le système avec une question utilisateur ;
- de vérifier l’état du service ;
- de recharger les données ;
- de reconstruire l’index vectoriel ;
- de relancer le pipeline complet.

### Lancement de l’API

```bash
uvicorn api.main:app --reload
```

Par défaut, l’API est accessible à l’adresse :

```text
http://127.0.0.1:8000
```
Documentation interactive
FastAPI génère automatiquement une documentation Swagger :

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
```

#### Endpoints principaux

**GET /health**
> Vérifie que l’API fonctionne correctement.
>
> **Réponse exemple :**
> ```json
> {
>   "status": "ok"
> }
> ```

**POST /ask**
> Permet de poser une question au système. Le routing interne oriente automatiquement la question vers :
> - SQL pour les questions chiffrées et analytiques
> - RAG pour les questions textuelles et contextuelles
> - REFUS pour les questions hors périmètre ou non supportées
>
> **Requête exemple :**
> ```json
> {
>   "question": "Quel joueur a le plus de rebonds sur la saison ?"
> }
> ```
> **Réponse exemple :**
> ```json
> {
>   "question": "Quel joueur a le plus de rebonds sur la saison ?",
>   "answer": "Le joueur ayant pris le plus de rebonds en une saison est Ivica Zubac, avec 1008 rebonds.",
>   "route_used": "SQL",
>   "sql_success": true
> }
> ```

**POST /data/reload**
> Recharge les données structurées et textuelles dans PostgreSQL (Excel, PDF, etc).
>
> **Réponse exemple :**
> ```json
> {
>   "status": "ok",
>   "message": "Données rechargées avec succès"
> }
> ```

**POST /index/rebuild**
> Reconstruit l’index vectoriel FAISS à partir des documents présents dans `inputs/`.
>
> **Réponse exemple :**
> ```json
> {
>   "status": "ok",
>   "message": "Index FAISS reconstruit avec succès"
> }
> ```

**POST /system/rebuild**
> Exécute le pipeline complet de reconstruction (rechargement des données + reconstruction de l’index).
>
> **Réponse exemple :**
> ```json
> {
>   "status": "ok",
>   "message": "Système entièrement reconstruit (data + index)"
> }
> ```

---

#### Tester l’API avec curl

**Windows PowerShell**
```powershell
curl -X POST "http://127.0.0.1:8000/ask" ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"Quel joueur a le plus de rebonds sur la saison ?\"}"
```

**Linux / macOS**
```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"Quel joueur a le plus de rebonds sur la saison ?"}'
```

---

### Interface Streamlit

### Interface Streamlit

L’interface Streamlit agit comme un client de l’API REST :

- l’utilisateur saisit une question ;
- Streamlit envoie une requête HTTP à l’endpoint `/ask` ;
- l’API analyse la question (routing) ;
- le système sélectionne SQL, RAG ou REFUS ;
- la réponse est renvoyée et affichée dans l’interface.

Cette séparation permet une architecture propre et scalable :
Streamlit → API FastAPI → Pipeline hybride

**Lancement de l’interface :**
```bash
streamlit run MistralChat.py
```
Par défaut, l’interface est accessible à l’adresse : [http://localhost:8501](http://localhost:8501)


```

---

### Procédure complète d’exécution

1. **Lancer l’API**
   ```bash
   uvicorn api.main:app --reload
   ```
2. **Lancer Streamlit**
   ```bash
   streamlit run MistralChat.py
   ```
3. **Tester le système**
   - Quel joueur a le plus de rebonds sur la saison ?
   - Quel joueur combine le plus de points et de passes décisives ?
   - Quels joueurs sont les plus mentionnés dans les discussions Reddit ?
   - Que disent les fans sur Haliburton ?
   - Quel joueur a le meilleur pourcentage à 3 points sur les 5 derniers matchs ?

Ces tests permettent de couvrir :
- une route SQL
- une route RAG
- une route REFUS

---

> La racine `/` redirige vers `/docs` (documentation interactive FastAPI).


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

- PostgreSQL permet de répondre à des questions **fiables, chiffrées et agrégées**
- certaines données textuelles structurées issues des reports peuvent aussi être exploitées via SQL
- le RAG permet d’apporter du **contexte, de l’interprétation et des réponses qualitatives**

Le système final repose sur :

- **SQL** → précision, fiabilité, calculs et agrégations
- **RAG** → enrichissement, synthèse et compréhension du contexte
- **REFUS** → sécurité lorsque les données sont absentes ou insuffisantes

### Documentations
- [README](database/README.md)
- [SCHEMA SQL](docs/schema_sql.md)



## SQL Tool (questions chiffrées et agrégations structurées)

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
- "Quels joueurs sont les plus mentionnés dans les discussions Reddit ?"

Ce module permet :

- d'améliorer la précision ;
- de réduire les hallucinations ;
- de garantir la fiabilité des données numériques ;
- de traiter certaines agrégations simples sur des données textuelles structurées, par exemple via `related_player_names` dans la table `reports`.

## Routing des requêtes

Le système utilise un mécanisme de routing pour orienter automatiquement les questions :

- **Questions chiffrées / analytiques** → SQL Tool
- **Questions textuelles / contextuelles** → RAG
- **Questions hors périmètre, bruitées ou non supportées** → refus
- **Certaines questions issues des reports** peuvent être traitées soit par RAG, soit par SQL lorsqu’une agrégation structurée est possible

Ce routing améliore la pertinence, la robustesse et la fiabilité des réponses en utilisant le bon composant selon le type de question.

## Exemples de questions

- Qui sont les 5 meilleurs scoreurs ?
- Quel joueur a le plus de rebonds ?
- Quel joueur combine le plus de points et de passes décisives ?
- Quels joueurs sont les plus mentionnés dans les discussions Reddit ?
- Que disent les fans sur Haliburton ?
- Quel joueur a le meilleur pourcentage à 3 points sur la saison ?

## Résultats d’évaluation

Le projet a été évalué en trois étapes :

1. **Baseline RAG seule**
2. **Version intermédiaire SQL v1.1**
3. **Version finale optimisée (SQL + routing + refus)**

### Baseline corrigée

| Indicateur | Score |
|------------|------|
| Faithfulness | 0.44 |
| Answer Relevancy | 0.73 |
| Context Precision | 0.18 |
| Context Recall | 0.36 |
| Refusal Rate | 0.00 |

### Version intermédiaire SQL v1.1

| Indicateur | Score |
|------------|------|
| Faithfulness | 0.07 |
| Answer Relevancy | 0.86 |
| Context Precision | 0.04 |
| Context Recall | 0.00 |
| Refusal Rate | 0.00 |

### Version optimisée finale

| Indicateur | Score |
|------------|------|
| Faithfulness | **0.99** |
| Answer Relevancy | **0.92** |
| Context Precision | **0.75** |
| Context Recall | **0.71** |
| Refusal Rate | **1.00** |

### Interprétation

La version finale améliore fortement :

- la fiabilité des réponses ;
- la pertinence métier ;
- la gestion des refus ;
- la robustesse globale du système.

Le système final utilise majoritairement le **SQL Tool** pour les questions structurées, le **RAG** pour les questions textuelles pertinentes, et le **refus** pour les cas hors périmètre.

---

##  Structure du projet
```bash

sportsee/
│
├── indexer.py                    # Script principal d’indexation des documents (création des chunks, embeddings, index FAISS)
├── MistralChat.py                # Interface utilisateur Streamlit pour interroger le système RAG
├── requirements.txt              # Dépendances Python du projet
├── README.md                     # Documentation principale du projet
├── .gitignore                    # Fichiers et dossiers ignorés par Git
├── api/                         # API REST FastAPI (exposition du système, endpoints)
│   ├── main.py                  # Point d'entrée principal de l'API FastAPI
│   ├── schemas.py               # Schémas Pydantic pour validation des requêtes/réponses API
│
├── database/                     # Gestion de la base PostgreSQL
│   ├── create_readonly_user.sql  # Script SQL pour créer un utilisateur en lecture seule
│   ├── db_utils.py               # Fonctions utilitaires pour l'accès et la gestion de la base de données
│   ├── init_db.sql               # Initialisation de la base, de l’utilisateur et des droits
│   ├── load_excel_to_db.py       # Chargement des données structurées Excel dans PostgreSQL
│   ├── load_reports.py           # Chargement des rapports PDF Reddit dans PostgreSQL
│   ├── README.md                 # Documentation technique dédiée à la base de données
│   ├── schema.sql                # Création du schéma SQL (tables, contraintes, index, commentaires)
│   └── schemas.py                # Schémas Pydantic pour valider les données avant insertion
│
├── rag_pipeline/                 # Pipeline RAG principal
│   ├── config.py                 # Configuration globale du projet (modèles, chemins, DB, etc.)
│   ├── llm_utils.py              # Fonctions utilitaires pour l’appel au LLM (Mistral)
│   ├── rag_pipeline.py           # Logique de retrieval, construction de contexte et génération de réponse
│   ├── router.py                 # Routage des questions vers SQL Tool ou RAG
│   ├── vector_store.py           # Gestion de l’index FAISS et de la recherche sémantique
│   └── tools/
│       └── sql_tool.py           # Outil pour générer et exécuter des requêtes SQL via le LLM
│
├── evaluate/                     # Évaluation automatique du système avec RAGAS
│   ├── __init__.py               # Initialisation du module evaluate
│   ├── core/                     # Modules internes de préparation et d’évaluation
│   │   ├── cleaning.py           # Nettoyage / préparation des données d’évaluation
│   │   ├── dataset_loader.py     # Chargement du dataset d’évaluation
│   │   ├── ragas_builder.py      # Construction des objets nécessaires à RAGAS
│   │   ├── ragas_runner.py       # Lancement des métriques RAGAS
│   │   ├── safe_mistral.py       # Appels sécurisés au modèle Mistral
│   │   ├── saver.py              # Sauvegarde des résultats d’évaluation
│   │   └── schemas.py            # Validation Pydantic des données d’évaluation
│   ├── datasets/                 # Jeux de test pour l’évaluation
│   │   ├── rag_eval_dataset.json # Dataset principal de questions métier
│   │   └── archive/
│   │       ├── rag_eval_dataset_baseline_v1.json # Anciennes versions du dataset d’évaluation
│   │       └── rag_eval_dataset_baseline_v2.json # Anciennes versions du dataset d’évaluation
│   ├── results/                  # Résultats générés par les évaluations
│   │   ├── baseline/
│   │   │   ├── ragas.log         # Log d’exécution de l’évaluation baseline
│   │   │   ├── ragas_results.csv # Résultats détaillés par question (baseline)
│   │   │   └── ragas_summary.json# Résumé global des scores (baseline)
│   │   ├── baseline_corrected/
│   │   │   ├── ragas.log         # Log d’exécution de l’évaluation baseline corrigée
│   │   │   ├── ragas_results.csv # Résultats détaillés par question (baseline corrigée)
│   │   │   └── ragas_summary.json# Résumé global des scores (baseline corrigée)
│   │   ├── v1_1_sql/
│   │   │   ├── ragas_results.csv # Résultats détaillés par question (v1_1_sql)
│   │   │   └── ragas_summary.json# Résumé global des scores (v1_1_sql)
│   │   ├── v1_1_sql_corrigé/
│   │   │   ├── ragas.log         # Log d’exécution de l’évaluation v1_1_sql corrigée
│   │   │   ├── ragas_results.csv # Résultats détaillés par question (v1_1_sql corrigée)
│   │   │   └── ragas_summary.json# Résumé global des scores (v1_1_sql corrigée)
│   │   └── version optimisée/
│   │       ├── ragas.log         # Log d’exécution de l’évaluation version optimisée
│   │       ├── ragas_results.csv # Résultats détaillés par question (version optimisée)
│   │       └── ragas_summary.json# Résumé global des scores (version optimisée)
│   └── scripts/
│       └── evaluate_ragas.py     # Script principal de lancement RAGAS
│
├── utils/                        # Fonctions utilitaires partagées
│   ├── data_loader.py            # Chargement et parsing multi-format (PDF, OCR, Excel, TXT, CSV…)
│   └── logging_config.py         # Configuration centralisée du logging
│
├── docs/                         # Documentation et rapports
│   ├── rapport_ragas_baseline.md # Rapport d’analyse de la baseline RAGAS
│   ├── rapport_ragas_comparatif.md # Rapport d’analyse comparative RAGAS
│   ├── rapport_ragas_optimisé.md   # Rapport d’analyse version optimisée RAGAS
│   ├── schema_sql.md             # Description fonctionnelle du schéma SQL
│   └── sql_queries_validation.md # Validation des requêtes SQL utilisées
│
├── inputs/                       # Données sources du projet (Excel NBA, PDF)
│
├── vector_db/                    # Index vectoriel FAISS généré automatiquement
│   ├── document_chunks.pkl       # Chunks de documents indexés (pickle)
│   └── faiss_index.idx           # Fichier d’index utilisé pour le retrieval
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

Implémente le pipeline principal du système :

- détection du type de question (routing) ;
- orientation vers SQL, RAG ou refus ;
- récupération des documents pertinents si nécessaire ;
- construction du contexte ;
- génération d’une réponse ou synthèse SQL ;
- structuration de la sortie avec Pydantic.

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

Les résultats sont générés dans le dossier `evaluate/results/` selon la version évaluée.

Rapports disponibles :

- [Rapport baseline](docs/rapport_ragas_baseline.md)
- [Rapport comparatif](docs/rapport_ragas_comparatif.md)
- [Rapport version optimisée](docs/rapport_ragas_optimisé.md)


## Dataset d’évaluation
Le système est testé sur :
- questions factuelles simples
- questions complexes
- comparaisons
- questions bruitées
- questions non répondables

## Limites actuelles

- certaines comparaisons restent perfectibles ;
- certaines questions subjectives dépendent fortement du contenu réellement disponible dans les reports ;
- la qualité du système dépend encore partiellement du mapping langage naturel → SQL ;
- les questions hybrides très complexes restent plus difficiles à traiter ;
- RAGAS reste imparfait pour évaluer certains comportements d’un système hybride.


## Améliorations prévues

- ajout d’une API REST pour exposer le système ;
- amélioration des comparaisons complexes ;
- ajout éventuel d’un score de confiance ;
- amélioration du routing sur certains cas hybrides ;
- enrichissement de l’évaluation pour les systèmes hybrides.

## Objectif
Le système final vise à fournir des réponses fiables sur des données NBA en combinant :

- **SQL** pour les questions structurées et chiffrées ;
- **RAG** pour les questions textuelles et contextuelles ;
- **REFUS** pour les questions hors périmètre ou non supportées.

L’objectif est de proposer un assistant **fiable, robuste et mieux aligné avec les besoins métier**.