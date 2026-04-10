# Analyse comparative — Focus sur la composante RAG

## Évolution après intégration de DocStrange

L’intégration de DocStrange visait à améliorer la qualité du texte extrait des documents Reddit, afin d’optimiser le retrieval et les performances du module RAG.

Cependant, l’analyse des résultats montre que **les performances du RAG restent globalement inchangées**.

---

## Résultats observés

### Question RAG évaluée (subjective)

- **Question** : “Quel est le meilleur joueur NBA actuellement selon les fans ?”
- **Routing** : RAG
- **Résultat** : REFUS

### Scores associés

- **Answer Relevancy** : 0.0  
- **Context Precision** : 0.0  
- **Context Recall** : 0.0  
- **is_correct** : False  

---

## Interprétation

### Absence d’amélioration du retrieval

Malgré une meilleure qualité d’extraction avec DocStrange :

- aucun contexte pertinent n’a été récupéré ;
- le système n’a pas été capable d’identifier ou de reconstruire un consensus ;
- les métriques RAGAS confirment une absence totale d’exploitation du contexte.

---

### Changement de comportement du modèle

Le système adopte désormais un comportement plus robuste :

- refus propre et justifié ;
- disparition des hallucinations sur ce type de question.

Cependant, cette amélioration concerne la **robustesse**, et non la **performance du RAG**.

---

## Analyse des causes

### 1. Nature de la question

La question posée est :

- subjective ;
- basée sur une synthèse d’opinions ;
- dépendante de multiples sources (commentaires).

Le pipeline RAG actuel est peu adapté à ce type de tâche.

---

### 2. Limites du retrieval

Les limites principales identifiées sont :

- chunks Reddit trop larges ou mal structurés ;
- absence de logique d’agrégation entre plusieurs commentaires ;
- difficulté à faire émerger un consensus à partir de données textuelles fragmentées.

---

### 3. Limites du pipeline RAG

Le système est optimisé pour :

- restituer de l’information explicite.

Mais pas pour :

- agréger des opinions ;
- inférer une tendance globale.

---

## Conclusion

L’ajout de DocStrange :

- n’a **pas amélioré les performances du RAG** ;
- a légèrement amélioré la **propreté du texte** ;
- a contribué à un **meilleur comportement de refus**.

Le RAG reste donc le composant le plus limité du système actuel.

---

## Limites de l’évaluation

- une seule question évaluée via le RAG ;
- absence de cas d’usage variés pour mesurer finement les performances ;
- difficulté d’évaluation sur des questions subjectives.

---

## Axes d’amélioration

### Court terme (sans refonte majeure)

- améliorer le chunking des discussions Reddit ;
- structurer les commentaires (post vs réponses) ;
- adapter le prompt pour favoriser la synthèse.

---

### Moyen terme

- introduire une logique de regroupement des mentions (pseudo-consensus) ;
- améliorer le retrieval via reranking ;
- enrichir les métadonnées des chunks.

---

### Long terme

- adapter le système pour gérer :
  - les questions subjectives ;
  - les analyses multi-documents ;
  - les inférences d’opinion collective.

---

## Synthèse

Le système final est performant sur :

- les questions factuelles (SQL) ;
- la robustesse (refus).

Mais reste limité sur :

- les questions subjectives ;
- l’exploitation avancée du texte via RAG.