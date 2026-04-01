# Rapport d’analyse RAGAS — Évaluation Baseline du Système IA SportSee

Cette évaluation constitue la baseline du système avant intégration des données structurées (SQL Tool).


## Vérification et correction du dataset d’évaluation

Lors de l’analyse détaillée des résultats, une vérification manuelle avec les données sources a permis d’identifier plusieurs incohérences dans le dataset d’évaluation initial, notamment sur certaines vérités terrain.

Ces incohérences pouvaient produire des faux négatifs et biaiser l’évaluation du système.

Une vérification manuelle systématique a donc été réalisée en comparant les réponses attendues avec les données sources.

Le dataset a ensuite été corrigé, puis l’évaluation RAGAS relancée afin d’obtenir une baseline fiable et exploitable.


**Accès aux ressources**

Ces fichiers permettent de reproduire l’évaluation et d’analyser les résultats détaillés du système RAG.

-  [Résultats détaillés (CSV)](../evaluate/results/baseline_corrected/ragas_results.csv)
-  [Résumé (JSON)](../evaluate/results/baseline_corrected/ragas_summary.json)
-  [Script d’évaluation RAGAS](../evaluate/scripts/evaluate_ragas.py)
-  [Jeu de test](../evaluate/datasets/archive/rag_eval_dataset_baseline_v2.json)

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

| Indicateur         | Score | Lecture |
|--------------------|-------|---------|
| Faithfulness       | 0.44  | Fidélité moyenne : le système s’appuie partiellement sur les données, mais certaines réponses restent peu fiables |
| Answer Relevancy   | 0.73  | Compréhension correcte des questions dans l’ensemble, malgré plusieurs réponses inadaptées |
| Context Precision  | 0.18  | Beaucoup de bruit dans les contextes récupérés : les informations utiles sont souvent noyées |
| Context Recall     | 0.36  | Couverture partielle : une partie des informations nécessaires est récupérée, mais pas de manière systématique |
| Refusal Rate       | 0.00  | Aucun refus correct : le système hallucine encore sur les questions hors périmètre |

Le score de **refusal rate à 0.00** indique que le système n’a correctement refusé aucune des questions non répondables.  
Les 3 questions hors périmètre ont toutes donné lieu à une réponse, ce qui confirme un problème critique d’hallucination.

### Par type de question (moyennes)

| Catégorie         | Faithfulness | Relevancy | Precision | Recall | Lecture |
|-------------------|--------------|-----------|-----------|--------|---------|
| Factuel simple    | 0.53         | 0.59      | 0.22      | 0.50   | Questions parfois bien traitées, mais avec encore plusieurs erreurs factuelles ou contextes peu utiles |
| Factuel complexe  | 0.29         | 0.91      | 0.17      | 0.00   | Le système comprend bien la question, mais la réponse reste peu fiable et peu ancrée dans les données |
| Comparaison       | 0.10         | 0.82      | 0.25      | 0.67   | Bonne compréhension globale, mais difficultés à produire des comparaisons réellement fondées |
| Subjectif         | 0.69         | 0.86      | 0.00      | 0.00   | Réponses fluides et convaincantes, mais sans véritable appui sur un contexte vérifiable |

Les résultats montrent des comportements différents selon la complexité des questions :

- Les questions factuelles simples sont les mieux traitées
- Les questions complexes ou comparatives entraînent davantage d’erreurs
- Les questions subjectives produisent des réponses fluides mais peu fiables

## Analyse avec exemple

L’analyse ci‑dessous s’appuie directement sur les 15 questions utilisées pour l’évaluation, afin d’illustrer concrètement le comportement du système dans des situations variées.

### Cas réussis — Questions simples
*Exemple : Question 8 :*

**Q :** « Quel joueur a marqué le plus de points sur la saison ? »

**Réponse du système :** Shai Gilgeous-Alexander (2485 points)

**Évaluation :**
- Donnée présente dans le dataset  
- Réponse correcte  
- Bonne utilisation des informations récupérées  
- Scores RAGAS élevés (faithfulness, relevancy, precision, recall)

**Interprétation :**
- Retrieval efficace : les bonnes données ont été récupérées dans le contexte.
- Génération maîtrisée : la réponse est cohérente, justifiée et fidèle aux données.
- Le système est capable de fournir des réponses fiables sur des questions factuelles simples lorsque l’information est clairement présente.

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


### Mélange entre données disponibles et connaissances générales

*Exemple : Question 11 :*

**Q :** « Qui a le plus de passes décisives ? »

**Réponse du système :** Le système explique que l’information n’est pas directement visible dans les feuilles fournies, puis propose une réponse probable à partir de tendances générales de la NBA.

**Évaluation :**
- Réponse non strictement fondée sur le dataset
- Utilisation d’hypothèses externes
- Manque de traçabilité par rapport aux sources réellement fournies

**Interprétation :**
- Le système n’arrive pas à extraire directement la bonne information depuis le contexte disponible.
- Il compense en mobilisant des connaissances générales, ce qui donne une réponse plausible mais non fiable dans le cadre du projet.
- Ce comportement justifie l’ajout ultérieur d’un Tool SQL pour les questions statistiques.


### Questions non répondables
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
   - Relevancy élevée (0.73)
   - Le modèle comprend bien les questions

2. Manque de fiabilité dès que la difficulté augmente
   - Faithfulness faible (0.44)
   - Context precision très faible (0.18)

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


Cette baseline met en évidence un système convaincant mais encore insuffisamment fiable pour un usage métier critique, justifiant l’intégration d’un Tool SQL et l’amélioration du pipeline RAG.


## Transition vers l’amélioration du système

### 1. Cadrer le besoin métier
**Objectif de cette phase :**
- Rendre le système capable de répondre de manière fiable aux questions chiffrées, comparatives et agrégées, là où le RAG textuel seul montre ses limites.

**Constat de départ :**
- le système comprend globalement bien les questions ;
- mais il hallucine sur certaines données numériques ;
- il ne sait pas toujours distinguer une information présente d’une information absente ;
- il reste insuffisant pour les questions nécessitant des calculs, tris ou agrégations.


**Questions typiques à couvrir :**
- meilleur % à 3 points ;
- plus de rebonds ;
- plus de passes ;
- comparaison domicile / extérieur ;
- comparaison sur période ;
- combinaison de statistiques.


**Réponse attendue du système :**
- le LLM ne “devine” plus ;
- il interroge une base de données structurée ;
- il s’appuie sur un résultat SQL traçable ;
- il reformule une réponse fiable en langage naturel.


**Résultat attendu :**
- amélioration de la fiabilité sur les questions numériques ;
- réduction des hallucinations ;
- meilleure robustesse du système sur les cas métier ;
- base de comparaison pour la seconde évaluation avant / après intégration du SQL Tool.