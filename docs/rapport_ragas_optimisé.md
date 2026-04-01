# Rapport d’analyse comparative — Évaluation du système NBA Analyst AI  
## Comparaison des versions : Baseline → SQL → Version optimisée

---

## Contexte et objectif de l’étude

Ce rapport présente une analyse comparative entre :

- la **version baseline**, reposant sur un pipeline RAG seul ;
- la **version intermédiaire SQL v1.1**, intégrant un SQL Tool ;
- la **version optimisée finale**, combinant SQL, RAG et mécanisme de refus.

L’objectif est d’évaluer l’impact des évolutions du système sur :

- la **fiabilité métier** ;
- la **robustesse du système** ;
- la **pertinence des réponses générées** ;
- la capacité à gérer les cas hors périmètre via le refus.

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

## Apports des évolutions du système

Les améliorations apportées au système incluent :

- l’intégration d’un **SQL Tool** pour les questions chiffrées ;
- la mise en place d’un **routing des questions** ;
- l’ajout d’un **mécanisme de refus** ;
- une meilleure exploitation des données textuelles et structurées.

Ces évolutions marquent le passage vers une **architecture hybride SQL + RAG + REFUS, orientée fiabilité métier**.

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


---

## Résultats globaux
Ces résultats montrent une amélioration significative entre chaque version, avec un gain particulièrement marqué sur la version optimisée.
### Comparaison des versions

| Indicateur         | Baseline RAG | SQL v1.1 | Version optimisée | Lecture |
|--------------------|-------------:|---------:|------------------:|---------|
| Faithfulness       | 0.44         | 0.07     | **0.99**          | Chute liée à une limite de RAGAS sur les réponses SQL |
| Answer Relevancy   | 0.73         | 0.86     | **0.92**          | Amélioration progressive de la pertinence métier |
| Context Precision  | 0.18         | 0.04     | **0.75**          | Forte amélioration grâce au meilleur usage du contexte |
| Context Recall     | 0.36         | 0.00     | **0.71**          | Le système récupère bien plus d’informations utiles |
| Refusal Rate       | 0.00         | 0.00     | **1.00**          | Ajout du refus = amélioration critique |

---

## Résultats par type de question

| Catégorie         | Baseline RAG | SQL v1.1 | Version optimisée | Lecture |
|------------------|-------------|----------|------------------|---------|
| Factuel simple   | Correct mais instable | Très bon | Très fiable | Le SQL stabilise totalement les réponses |
| Factuel complexe | Fragile | Bon | Très bon | Les calculs complexes sont bien gérés |
| Comparaison      | Faible | Moyen | Bon | Forte amélioration mais encore perfectible |
| Subjectif        | Moyen | Mauvais | Correct | Meilleure gestion via RAG + reports |
| Bruit / Unsupported | Mauvais (hallucinations) | Mauvais | Excellent (refus) | Gain majeur en robustesse |

---

## Analyse métier

| Critère métier                  | Baseline RAG | SQL v1.1 | Version optimisée | Observation |
|--------------------------------|--------------|----------|-------------------|------------|
| Fiabilité des données chiffrées | Faible       | Très élevée | Très élevée      | Le SQL apporte une forte précision |
| Hallucinations                 | Fréquentes   | Réduites | Très rares        | Le refus élimine les réponses incorrectes |
| Questions unsupported          | Mal gérées   | Mal gérées | Bien gérées      | Ajout du refus = gain clé |
| Questions bruitées             | Mal gérées   | Mal gérées | Bien gérées      | Robustesse fortement améliorée |
| Exploitation des reports       | Limitée      | Limitée | Améliorée         | Meilleure utilisation du RAG + SQL |
| Robustesse globale             | Faible       | Moyenne | Élevée            | Système fiable en production |

## Évolution de l’architecture

| Dimension | Baseline RAG | SQL v1.1 | Version optimisée |
|----------|--------------|----------|-------------------|
| Architecture | RAG seul | RAG + SQL partiel | SQL + RAG + REFUS |
| Questions chiffrées | Fragile | Fiable | Très fiable |
| Questions textuelles | RAG seul | RAG inchangé | RAG mieux ciblé |
| Gestion des erreurs | Aucune | Limitée | Refus structuré |
| Robustesse | Faible | Moyenne | Élevée |

## Résultats détaillés — Version optimisée

- **Faithfulness** : 0.99
- **Answer Relevancy** : 0.92
- **Context Precision** : 0.75
- **Context Recall** : 0.71
- **Refusal Rate** : 1.00

### Routing observé

- SQL : 11 questions (73,3 %)
- REFUS : 3 questions (20,0 %)
- RAG : 1 question (6,7 %)

### Performance SQL

- Nombre d’appels SQL : 11
- Succès SQL : 11
- Taux de succès : 1.00

## Interprétation des résultats

### Évolution des performances

L’analyse montre trois phases distinctes :

- la baseline RAG présente des limites en fiabilité ;
- la version SQL améliore fortement les réponses métier mais est mal évaluée par RAGAS ;
- la version optimisée améliore à la fois les performances métier et les scores.

### Explication

La baisse observée en SQL v1.1 s’explique par une limite de RAGAS :

- les réponses SQL ne reposent pas sur un contexte textuel ;
- RAGAS pénalise ce type de réponse.

La version optimisée corrige ce point en :

- intégrant les résultats SQL dans un pseudo-contexte ;
- améliorant le routing ;
- ajoutant un mécanisme de refus.

Les métriques redeviennent ainsi cohérentes avec la performance réelle du système.
Cela montre l’importance d’adapter le protocole d’évaluation au type d’architecture utilisée.

---

## Analyse qualitative


### Points améliorés

- forte amélioration de la fiabilité des réponses chiffrées ;
- réduction très importante des hallucinations ;
- meilleure gestion des questions hors périmètre ;
- réponses mieux alignées avec les besoins métier.

### Limites restantes

- certaines comparaisons restent perfectibles ;
- certaines questions subjectives dépendent fortement des données disponibles ;
- le mapping langage naturel → SQL peut encore être amélioré ;
- l’évaluation des systèmes hybrides reste imparfaite.

---

## Limites de l’évaluation

### Problème principal

RAGAS présente certaines limites pour évaluer les systèmes hybrides.

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

L’évolution du système montre une transformation majeure :

- la baseline RAG est limitée en fiabilité ;
- l’intégration du SQL améliore fortement les performances métier ;
- la version optimisée combine précision, robustesse et bonne évaluation.

Le système final est capable de :

- répondre de manière fiable aux questions chiffrées via SQL ;
- exploiter le contexte textuel lorsque pertinent via RAG ;
- refuser lorsque l’information n’est pas disponible.

Il s’agit d’un système hybride robuste, mieux aligné avec les besoins métier et adapté à un usage réel.

## Fonctionnement du système final

Le système suit les étapes suivantes :

1. analyse de la question ;
2. routing vers SQL, RAG ou refus ;
3. production de la réponse (requête SQL ou génération RAG) ;
4. validation et évaluation.

Ce fonctionnement permet d’adapter dynamiquement le traitement selon le type de question et d’améliorer la fiabilité globale.