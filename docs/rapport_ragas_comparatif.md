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
## Vérification et correction du dataset d’évaluation

Lors de l’analyse détaillée des résultats, une vérification manuelle avec les données sources a permis d’identifier plusieurs incohérences dans le dataset d’évaluation initial, notamment sur certaines vérités terrain.

Ces incohérences pouvaient produire des faux négatifs et biaiser l’évaluation du système.

Une vérification manuelle systématique a donc été réalisée en comparant les réponses attendues avec les données sources.

Le dataset a ensuite été corrigé, puis l’évaluation RAGAS relancée afin d’obtenir une baseline fiable et exploitable.


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
- de reformuler les résultats en langage naturel via le LLM.

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
| Faithfulness | 0.44 |
| Answer Relevancy | 0.73 |
| Context Precision | 0.18 |
| Context Recall | 0.36 |
| Refusal Rate | 0.00 |

📎 Résultats détaillés :  
- [CSV baseline](evaluate/results/baseline/ragas_results.csv)  
- [Résumé baseline](evaluate/results/baseline/ragas_summary.json)

---

### Version enrichie (RAG + SQL Tool)

| Indicateur | Score |
|------------|-------|
| Faithfulness | 0.07 |
| Answer Relevancy | 0.86 |
| Context Precision | 0.04 |
| Context Recall | 0.00 |
| Refusal Rate | 0.00 |

Résultats détaillés :  
- [CSV version SQL](../evaluate/results/v1_1_sql_corrigé/ragas_results.csv)  
- [Résumé version SQL](../evaluate/results/v1_1_sql_corrigé/ragas_summary.json) 
---

## Analyse comparative des performances



### Comparaison des métriques RAGAS

| Indicateur            | Baseline corrigée | Version SQL corrigée | Évolution        | Interprétation |
|----------------------|------------------|----------------------|------------------|----------------|
| Faithfulness         | 0.44             | 0.07                 | Forte baisse     | RAGAS pénalise les réponses issues du SQL, car elles ne reposent plus sur un contexte textuel classique |
| Answer Relevancy     | 0.73             | 0.86                 | Hausse nette     | Les réponses sont globalement plus adaptées aux questions |
| Context Precision    | 0.18             | 0.04                 | Baisse           | Les contextes FAISS ne sont plus centraux dans les réponses SQL |
| Context Recall       | 0.36             | 0.00                 | Forte baisse     | Même limite méthodologique : les réponses SQL ne s’appuient pas sur les chunks textuels |
| Refusal Rate         | 0.00             | 0.00                 | Stable           | À ce stade, la gestion du refus n’est pas encore améliorée |
---



### Analyse métier

| Critère métier                  | Baseline | RAG + SQL | Observation |
|--------------------------------|----------|-----------|------------|
| Questions factuelles correctes  | Moyen    | Élevé     | Forte amélioration sur les questions chiffrées |
| Hallucinations numériques       | Fréquentes | Réduites | Le SQL améliore la fiabilité des réponses statistiques |
| Questions unsupported           | Mal gérées | Mal gérées | Le refus n’est pas encore pris en charge dans cette version |
| Questions bruitées              | Hallucinations | Hallucinations | Pas d’amélioration notable à ce stade |
| Questions comparatives          | Variable | Variable | Certaines comparaisons restent fragiles ou incomplètes |

---

## Interprétation des résultats

### Dégradation apparente des scores

Les métriques RAGAS montrent une baisse importante sur certaines dimensions :

- Faithfulness : 0.44 → 0.07  
- Context Precision : 0.18 → 0.04  
- Context Recall : 0.36 → 0.00  

En revanche, la pertinence des réponses progresse :

- Answer Relevancy : 0.73 → 0.86 

Une baisse des métriques RAGAS ne signifie pas nécessairement une dégradation du système.

Dans ce cas précis :

- les performances métier s’améliorent
- mais les métriques ne capturent pas correctement le fonctionnement hybride

Il est donc nécessaire de croiser :

- métriques automatiques
- validation métier

---

### Explication

Cette baisse n’indique pas nécessairement une dégradation fonctionnelle du système.

Elle s’explique en grande partie par une limite méthodologique de RAGAS dans le cadre d’une architecture hybride :

- la baseline repose sur des contextes textuels issus du retrieval FAISS ;
- la version enrichie produit une partie de ses réponses à partir de données SQL structurées.

Or, les métriques comme la faithfulness, la context precision et la context recall évaluent la relation entre la réponse et un contexte textuel.

Ainsi, une réponse correcte issue du SQL peut obtenir un score faible, simplement parce qu’elle n’est pas reliée aux chunks textuels récupérés.

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

Malgré l’amélioration observée sur les questions chiffrées, plusieurs limites subsistent :

- absence de mécanisme de refus dans cette version ;
- questions unsupported encore mal gérées ;
- questions bruitées toujours sujettes à hallucination ;
- comparaisons complexes encore fragiles ;
- dépendance à la qualité du mapping langage naturel → SQL.
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
```

## Conclusion comparative

L’intégration du SQL Tool constitue une amélioration importante du système sur les questions chiffrées et statistiques.

Les principaux gains observés sont :

- une meilleure pertinence globale des réponses ;
- une réduction des hallucinations numériques sur plusieurs cas factuels ;
- une meilleure adéquation du système aux besoins métier portant sur les données structurées.

En revanche, cette version ne résout pas encore :

- la gestion du refus ;
- les questions hors périmètre ;
- certaines comparaisons complexes ;
- la limite méthodologique de RAGAS pour évaluer un système hybride.

La version enrichie ne doit donc pas être jugée uniquement à travers les métriques RAGAS classiques.  
Elle marque surtout une progression vers un système plus fiable sur les questions quantitatives, tout en montrant la nécessité d’adapter aussi le protocole d’évaluation.

Le système évolue ainsi d’un modèle principalement génératif vers un système orienté données, plus fiable sur les questions quantitatives.