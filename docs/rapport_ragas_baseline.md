# Rapport d’analyse RAGAS — Évaluation Baseline du Système IA SportSee

**Accès aux ressources**

Ces fichiers permettent de reproduire l’évaluation et d’analyser les résultats détaillés du système RAG.

-  [Résultats détaillés (CSV)](../evaluate/results/ragas_results.csv)
-  [Résumé (JSON)](../evaluate/results/ragas_summary.json)
-  [Script d’évaluation RAGAS](../evaluate/scripts/evaluate_ragas.py)
-  [Jeu de test](../evaluate/datasets/rag_eval_dataset.json)

## Contexte

Ce rapport présente l’évaluation initiale du système d’assistant IA de SportSee.
**L’objectif** est d’identifier ce qui fonctionne, ce qui pose problème et d’orienter les améliorations.
Le système repose sur deux étapes :
- **Retrieval** : récupération d’informations dans la base.
- **Génération** : production d’une réponse par le modèle.
L’évaluation a été réalisée sur 15 questions :
- **12 répondables**
- **3 non répondables** (tests de robustesse)

---

## Architecture technique mise en place

Le système évalué repose sur un pipeline RAG structuré, avec plusieurs composants assurant la fiabilité et la traçabilité :

- **Pipeline RAG** :
  - récupération des documents via un Vector Store (FAISS) ;
  - construction d’un contexte pertinent ;
  - génération de réponse via le modèle Mistral.

- **Validation des données (Pydantic)** :
  - validation du dataset d’évaluation ;
  - validation des sorties du pipeline RAG (format structuré, cohérence des champs).

- **Logging structuré** :
  - suivi des étapes clés (retrieval, génération, erreurs) ;
  - traçabilité des appels au modèle et des résultats.

- **Instrumentation avec Logfire** :
  - observabilité du pipeline en temps réel ;
  - suivi des erreurs et du comportement global du système.

- **Évaluation avec RAGAS** :
  - mesure de la qualité des réponses (fidélité, pertinence, qualité du contexte) ;
  - analyse différenciée selon le type de question.

Cette architecture constitue une **baseline instrumentée**, permettant d’analyser précisément les performances et d’identifier les axes d’amélioration.

---

## Métriques RAGAS
**Question clé** : *la réponse est-elle correcte ET basée sur les données ?*

### Faithfulness (Fidélité)
- **Définition** : la réponse s’appuie-t-elle réellement sur les données disponibles ?
- **Interprétation** :
    - Score élevé → réponse fiable
    - Score faible → risque d’invention

### Answer Relevancy (Pertinence)
- **Définition** : la réponse correspond-elle à la question posée ?
- **Interprétation** :
    - Score élevé → bonne compréhension
    - Score faible → hors sujet

### Context Precision (Précision des contextes)
- **Définition** : les informations récupérées sont-elles utiles ?
- **Interprétation** :
    - Score élevé → peu de bruit
    - Score faible → beaucoup d’informations inutiles

### Context Recall (Couverture)
- **Définition** : toutes les informations nécessaires ont-elles été récupérées ?
- **Interprétation** :
    - Score élevé → rien d’important ne manque
    - Score faible → données manquantes

### Refusal Rate (Capacité à refuser)
- **Définition **: le système sait-il dire “je ne sais pas” quand l’information n’existe pas ?
- **Importance**: critique en production pour éviter les hallucinations.

## Résultats

### Tableau de synthèse

| Indicateur         | Score | Lecture                                 |
|--------------------|-------|------------------------------------------|
| Faithfulness       | 0.53  | Fidélité moyenne → risque d’extrapolation |
| Answer Relevancy   | 0.79  | Bonne compréhension des questions         |
| Context Precision  | 0.30  | Beaucoup de bruit dans les contextes      |
| Context Recall     | 0.49  | Couverture partielle                      |
| Refusal Rate       | 0.00  | Aucun refus → hallucinations              |

Le score de **refusal rate à 0.00** indique que le système n’a correctement refusé aucune des questions non répondables.  
Les 3 questions hors périmètre ont toutes donné lieu à une réponse, ce qui confirme un problème critique d’hallucination.

### Par type de question (moyennes)

| Catégorie         | Faithfulness | Relevancy | Precision | Recall | Lecture                                 |
|-------------------|--------------|-----------|-----------|--------|------------------------------------------|
| Factuel simple    | 0.61         | 0.74      | 0.45      | 0.67   | le plus fiable                         |
| Factuel complexe  | 0.28         | 0.91      | 0.17      | 0.50   | convaincant mais peu fiable            |
| Comparaison       | 0.43         | 0.74      | 0.29      | 0.42   | moyen                                    |
| Subjectif         | 0.64         | 0.85      | 0.00      | 0.00   | fluide mais sans preuve                |


- Quand la question est simple, le système est globalement fiable
- Quand la question devient complexe, il reste convaincant mais fait plus d’erreurs
- Quand il faut comparer, il comprend mais manque de précision
- Quand la question est subjective, il répond bien… mais sans preuve


## Analyse avec exemple

L’analyse ci‑dessous s’appuie directement sur les 15 questions utilisées pour l’évaluation, afin d’illustrer concrètement le comportement du système dans des situations variées.

### Cas réussis — Questions simples
*Exemple : Question 2 :*

**Q :** « Quelle équipe a marqué le plus de points ? »

**Réponse du système :** Oklahoma City Thunder

**Évaluation :**
-  Donnée présente dans le dataset  
-  Réponse correcte  
-  Bonne utilisation des informations récupérées

**Interprétation :**
- Retrieval efficace : les données pertinentes ont été trouvées.
- Génération correcte : la réponse est fidèle et factuelle.
- Le système est fiable sur les questions simples et directes

### Cas partiellement réussis
*Exemple : Question 1 :*

**Q :** « Quel joueur a le meilleur ratio points par match ? »

**Réponse du système :** Shai Gilgeous‑Alexander (SGA)

**Évaluation :**
-  Bonne réponse globale  
-  Réponse trop longue  
-  Ajout de contenu non nécessaire ou non demandé

**Interprétation :**
- Bonne compréhension : le système identifie correctement le joueur concerné.
- Manque de contrôle de la génération : la réponse s’étend inutilement, ajoute des détails non demandés et augmente le risque d’erreur.
- Ce comportement montre que le système comprend, mais ne sait pas encore se restreindre à l’essentiel.


### Cas incorrects (Erreurs factuelles)
*Exemple : Question 10 :*

**Q :** « Quel joueur a pris le plus de rebonds ? »

**Réponse du système :** Shai Gilgeous‑Alexander (SGA)

**Réponse correcte attendue :** Ivica Zubac

**Évaluation :**
-  Mauvaise réponse  
-  Le joueur identifié ne correspond pas aux données du dataset

**Interprétation :**
- Mauvais retrieval : les bonnes informations n’ont pas été récupérées.
- Confusion dans les données : le système semble mélanger les statistiques des joueurs.
- Ce type d’erreur montre que, même sur des questions factuelles, la chaîne retrieval + génération n’est pas encore fiable

### Hallucinations (Questions complexes)
*Exemple : Question 3 :*

**Q :** « Quel joueur est le plus complet ? »

**Réponse du système :** Fournit une réponse détaillée et structurée, avec des statistiques et des arguments.

**Évaluation :**
-  Statistiques inventées  
-  Éléments non présents dans les données  
-  Aucune trace de ces informations dans le contexte récupéré

**Interprétation :**
- La réponse donne une impression de maîtrise grâce à sa structure et son niveau de détail.
- En réalité, elle repose sur des inventions et non sur les données disponibles.
- Ce type de comportement est particulièrement trompeur : la forme est convaincante, mais le fond est faux.

### Mélange données / connaissances générales
*Exemple : Question 11 :*
**Q :** « Qui a le plus de passes décisives ? »

**Réponse du système :** Fournit une réponse basée sur des tendances générales de la NBA.

**Évaluation :**
-  Réponse issue de connaissances générales  
-  Aucune utilisation du dataset fourni  
-  Absence de justification basée sur le contexte

**Interprétation :**
- Le système sort du cadre RAG : il ne se limite plus aux données disponibles.
- Cela entraîne une perte de fiabilité, car la réponse ne reflète pas le dataset mais des connaissances externes.
- Ce comportement est problématique : il donne l’illusion d’une réponse pertinente, alors qu’elle n’est pas fondée sur les sources attendues.

### Questions non répondable
*Exemple : Question 13 :*

**Q :** « % à 3 points sur les 5 derniers matchs »

**Réponse du système :** Fournit un pourcentage inventé.

**Évaluation :**
-  Donnée absente du dataset  
-  Le modèle génère une réponse fictive au lieu de refuser

**Réponse attendue :** *"Information non disponible"*

**Interprétation :**
- Absence totale de gestion du refus : le système ne sait pas reconnaître qu’une information n’existe pas.
- Risque majeur en production : ce type d’hallucination peut induire en erreur l’utilisateur final.
- Ce comportement est l’un des points les plus critiques identifiés dans l’évaluation

## Interprétation globale

Deux tendances fortes se dégagent :

1. Bonne compréhension globale
    - Relevancy toujours élevée (0.74 à 0.91)
    - Le modèle comprend bien les questions
2. Manque de fiabilité dès que la difficulté augmente

    - Chute de la faithfulness (jusqu’à 0.28)
    - Precision faible (jusqu’à 0.17)

Cela signifie que :

- le modèle sait répondre correctement en apparence
- mais il ne s’appuie pas toujours sur les bonnes données



---

## Conclusion de cette analyse

Le système est performant pour des usages simples, mais devient risqué dès que :

- la question nécessite plusieurs informations
- les données doivent être croisées
- ou que la réponse n’est pas directement visible


Cette première évaluation constitue une baseline de référence pour mesurer les améliorations futures du système. 
Elle permet d’identifier précisément les axes d’amélioration à mettre en œuvre pour rendre le système plus fiable, plus robuste et mieux adapté aux besoins métier.


## Amélioration du modèle

À partir de cette première évaluation, plusieurs axes d’amélioration se dégagent.  
Ils répondent directement aux limites observées dans les résultats RAGAS et s’alignent avec les attentes du projet, notamment l’intégration des données Excel, la création d’un outil SQL et la seconde évaluation comparative.

### Mieux gérer les questions chiffrées avec un Tool SQL

L’un des principaux problèmes observés est que le système répond parfois à des questions chiffrées en s’appuyant sur des connaissances générales ou en inventant des valeurs.  
Cela montre que le système actuel, basé uniquement sur du retrieval textuel, n’est pas suffisant pour traiter de manière fiable des questions nécessitant des calculs, des tris ou des agrégations.

**Exemples observés :**
- erreurs sur les rebonds ;
- erreurs sur les passes décisives ;
- incapacité à répondre correctement à des questions du type :
  - meilleur pourcentage à 3 points sur une période donnée ;
  - comparaison domicile / extérieur ;
  - combinaison de plusieurs statistiques.

**Amélioration proposée :**
- intégrer les fichiers Excel dans une base SQL ;
- créer un Tool SQL capable de :
  - générer une requête à partir de la question ;
  - exécuter cette requête ;
  - retourner les résultats au LLM ;
- laisser ensuite le modèle reformuler la réponse en langage naturel.

**Effet attendu :**
- réponses chiffrées plus fiables ;
- moins d’hallucinations ;
- meilleure traçabilité de la source de la réponse.

---

### Renforcer la capacité du système à refuser de répondre

Le score de refus est nul sur les questions non répondables.  
Cela signifie que le système préfère produire une réponse, même incorrecte, plutôt que reconnaître l’absence d’information.

**Problème identifié :**
- le système ne sait pas distinguer :
  - une question réellement couverte par les données ;
  - une question hors périmètre ;
  - une question partiellement couverte.

**Amélioration proposée :**
- ajouter dans le prompt une règle explicite :
  - si l’information n’est pas trouvée dans les données ou si elle est insuffisante, répondre que l’information n’est pas disponible ;
- ajouter un contrôle avant génération :
  - si les contextes sont trop faibles ou non pertinents, déclencher un refus ;
- prévoir des cas de tests dédiés aux questions non répondables.

**Effet attendu :**
- diminution des hallucinations ;
- augmentation de la robustesse ;
- comportement plus sûr en production.

---

### Améliorer la qualité du retrieval textuel

Les scores de context precision et context recall montrent que le système récupère encore trop de bruit et ne couvre pas toujours correctement les informations utiles.

**Problèmes observés :**
- contextes partiellement utiles ;
- informations importantes parfois absentes ;
- réponses trop longues ou trop générales.

**Améliorations proposées :**
- retravailler le chunking :
  - taille des chunks ;
  - chevauchement ;
  - séparation plus propre entre documents ;
- améliorer le nettoyage des données textuelles ;
- ajuster le nombre de contextes récupérés (`top_k`) ;
- envisager un reranking ou un filtrage supplémentaire.

**Effet attendu :**
- contextes plus précis ;
- réduction du bruit ;
- meilleure fidélité des réponses.

---

### Adapter le système au type de question

La première évaluation montre que toutes les questions ne doivent pas être traitées de la même manière.

**Constat :**
- les questions simples sont globalement bien traitées ;
- les questions complexes ou comparatives sont plus risquées ;
- les questions subjectives produisent des réponses fluides mais peu fondées.

**Amélioration proposée :**
- mettre en place une logique d’orientation de la question :
  - question factuelle simple → retrieval textuel ou SQL simple ;
  - question chiffrée / comparative → Tool SQL ;
  - question non couverte → refus ;
  - question subjective → réponse prudente avec reformulation limitée aux sources.

**Effet attendu :**
- réponses mieux adaptées au besoin utilisateur ;
- réduction des erreurs de traitement ;
- meilleure cohérence globale du système.

---

### Validation et traçabilité du pipeline

Afin de sécuriser le pipeline et d’améliorer la capacité d’analyse des erreurs, plusieurs mécanismes ont été mis en place :

- utilisation de **Pydantic** pour valider :
  - les données d’entrée du dataset ;
  - les sorties du pipeline RAG ;
- mise en place d’un **logging structuré** pour suivre :
  - les étapes de retrieval ;
  - la génération de réponse ;
  - les erreurs éventuelles ;
- intégration de **Logfire** pour :
  - observer le comportement du pipeline ;
  - analyser les appels au modèle ;
  - faciliter le debugging.

Ces éléments permettent d’obtenir un système **plus robuste et traçable**, facilitant les phases d’analyse et d’amélioration.

---

### Préparer la seconde évaluation comparative

Cette première évaluation constitue une baseline.  
Elle servira de point de comparaison pour mesurer l’apport des améliorations futures.

**Étape suivante prévue :**
- intégrer la base SQL et le Tool SQL ;
- réexécuter le même protocole RAGAS ;
- comparer les scores avant / après.

**Indicateurs attendus d’amélioration :**
- hausse de la faithfulness ;
- hausse de la context precision sur les questions métier ;
- hausse du refusal rate ;
- baisse des erreurs factuelles sur les questions chiffrées.

---

## Synthèse des améliorations attendues

En résumé, la suite du projet doit permettre de faire évoluer le prototype d’un système “convaincant” vers un système “fiable”.

Les priorités sont les suivantes :
1. intégrer les données Excel dans une base SQL ;
2. utiliser un Tool SQL pour les questions chiffrées ;
3. renforcer la gestion du refus ;
4. améliorer le retrieval textuel ;
5. réévaluer le système avec le même protocole pour mesurer les progrès.