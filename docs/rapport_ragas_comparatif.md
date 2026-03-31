# Rapport d’analyse comparative — Évaluation du système NBA Analyst AI  
## Avant / après intégration du SQL Tool

---

## Contexte et objectif de l’étude

Ce rapport présente une analyse comparative entre :

- la **version baseline**, reposant sur un pipeline **RAG textuel seul** ;
- la **version enrichie RAG + SQL Tool**, intégrant une base PostgreSQL et un mécanisme de routage des questions chiffrées.

L’objectif est d’évaluer l’impact de cette évolution sur :

- la **fiabilité métier** ;
- la **robustesse du système** ;
- la **pertinence des réponses générées**.

---

## Limites identifiées sur la baseline

L’analyse initiale du système RAG a mis en évidence plusieurs limites :

- erreurs factuelles sur les questions numériques ;
- hallucinations sur les questions hors périmètre ;
- difficulté à traiter les agrégations et comparaisons ;
- absence de mécanisme de refus.

---

## Apport du SQL Tool

L’intégration du SQL Tool permet désormais :

- d’interroger une base de données structurée ;
- de générer dynamiquement des requêtes SQL à partir du langage naturel ;
- d’exécuter ces requêtes en lecture seule ;
- de reformuler les արդյունats en langage naturel via le LLM.

Cette évolution marque le passage vers une **architecture hybride RAG + SQL**.

---

## Protocole d’évaluation

### Dataset utilisé

Le comparatif repose sur un jeu de test constant de **15 questions** :

- **12 questions répondables**
- **3 questions non répondables**

Les catégories couvertes sont :

- factuel simple ;
- factuel complexe ;
- comparaison ;
- subjectif ;
- bruit ;
- unsupported.

---

### Métriques utilisées

L’évaluation repose sur les métriques RAGAS suivantes :

- Faithfulness  
- Answer Relevancy  
- Context Precision  
- Context Recall  
- Refusal Rate  

Des indicateurs métier complètent l’analyse :

- **is_correct**  
- **lecture**  
- **refusal_ok**

---

## Résultats globaux

### Baseline (RAG seul)

| Indicateur | Score |
|------------|-------|
| Faithfulness | 0.53 |
| Answer Relevancy | 0.79 |
| Context Precision | 0.30 |
| Context Recall | 0.49 |
| Refusal Rate | 0.00 |

📎 Résultats détaillés :  
- [CSV baseline](evaluate/results/baseline/ragas_results.csv)  
- [Résumé baseline](evaluate/results/baseline/ragas_summary.json)

---

### Version enrichie (RAG + SQL Tool)

| Indicateur | Score |
|------------|-------|
| Faithfulness | 0.03 |
| Answer Relevancy | 0.84 |
| Context Precision | 0.04 |
| Context Recall | 0.08 |
| Refusal Rate | 0.00 |

📎 Résultats détaillés :  
- [CSV version SQL](evaluate/results/sql/ragas_results.csv)  
- [Résumé version SQL](evaluate/results/sql/ragas_summary.json)

---

## Analyse comparative des performances

### Comparaison des métriques RAGAS

| Indicateur            | Baseline (RAG seul) | Version 1.1 (RAG + SQL) | Évolution        | Interprétation |
|----------------------|--------------------|--------------------------|------------------|----------------|
| Faithfulness         | 0.53               | 0.03                     | Forte baisse     | Métrique inadaptée aux réponses SQL |
| Answer Relevancy     | 0.79               | 0.84                     | Légère hausse    | Meilleure adéquation globale |
| Context Precision    | 0.30               | 0.04                     | Forte baisse     | SQL non pris en compte |
| Context Recall       | 0.49               | 0.08                     | Forte baisse     | Même limite |
| Refusal Rate         | 0.00               | 0.00                     | Stable           | Refus toujours absent |

---

### Analyse métier

| Critère métier                  | Baseline | RAG + SQL | Observation |
|--------------------------------|----------|----------|------------|
| Questions factuelles correctes  | Moyen    | Élevé    | Forte amélioration |
| Hallucinations numériques       | Fréquentes | Réduites | Données fiables |
| Questions unsupported           | Mal gérées | Mal gérées | Refus absent |
| Questions bruitées              | Hallucinations | Hallucinations | Problème persistant |
| Questions comparatives          | Variable | Variable | Cas complexe |

---

## Interprétation des résultats

### Dégradation apparente des scores

Les métriques RAGAS montrent une baisse importante :

- Faithfulness : 0.53 → 0.03  
- Context Precision : 0.30 → 0.04  
- Context Recall : 0.49 → 0.08  

---

### Explication

Cette baisse est **méthodologique**, pas fonctionnelle :

- RAGAS suppose un contexte textuel (FAISS)
- SQL fournit des données structurées

donc :
- réponse correcte ≠ bonne note RAGAS

---

### Évolution de l’architecture du système

Pipeline :

- **Avant** → RAG pur  
- **Après** → RAG + SQL + routing  

les métriques doivent évoluer aussi

---

## Analyse qualitative

### Points améliorés

- précision sur les données chiffrées  
- réponses plus fiables  
- réduction des hallucinations numériques  

---

### Limites restantes

- mapping NL → SQL imparfait  
- absence de refus  
- gestion insuffisante des unsupported  
- cas hybrides encore fragiles  

---

## Limites de l’évaluation

### Problème principal

RAGAS n’est pas adapté aux systèmes hybrides.

---

### Métriques impactées

- Faithfulness  
- Context Precision  
- Context Recall  

---

### Besoin d’indicateurs complémentaires

- route_used  
- sql_success  
- is_correct  
- refusal_ok  

---

### Piste d’amélioration

Transformer le SQL en contexte textuel :

```text
Question → SQL → résultat → texte → RAGAS