# Schéma SQL — Intégration des données structurées

## Objectif

L’objectif de cette étape est d’intégrer les données Excel dans une base relationnelle afin de permettre au système de répondre de manière fiable aux questions chiffrées.

Le système RAG seul montre ses limites sur les questions nécessitant :
- des agrégations ;
- des comparaisons ;
- des calculs.

L’ajout d’une base SQL permet d’améliorer la fiabilité et de réduire les hallucinations.

---

## Choix technique

Le système repose sur une base **SQLite** :

- simple à mettre en place ;
- environnement local reproductible ;
- suffisant pour le volume de données ;
- adapté à un prototype orienté évaluation.

---

## Modélisation des données

Le schéma est conçu pour être :
- simple à exploiter immédiatement ;
- évolutif pour intégrer des données match par match.

---

### Table `teams`

Contient les informations sur les équipes.

| Colonne     | Type | Description |
|------------|------|------------|
| team_code  | TEXT | Code de l’équipe (clé primaire) |
| team_name  | TEXT | Nom complet de l’équipe |

---

### Table `players`

Contient les informations sur les joueurs.

| Colonne     | Type | Description |
|------------|------|------------|
| player_id  | INTEGER | Identifiant unique |
| player_name| TEXT | Nom du joueur |
| team_code  | TEXT | Équipe associée |
| age        | INTEGER | Âge |

---

### Table `stats`

Contient les statistiques agrégées par joueur.

| Colonne     | Type | Description |
|------------|------|------------|
| stat_id    | INTEGER | Identifiant |
| player_id  | INTEGER | Référence joueur |
| gp         | INTEGER | Nombre de matchs |
| pts        | REAL | Points |
| reb        | REAL | Rebonds |
| ast        | REAL | Passes |
| ...        | ...  | Autres statistiques |

---

### Table `matches` (préparée pour évolution)

Cette table est prévue pour intégrer ultérieurement des données match par match.

Elle n’est pas alimentée dans la version actuelle.

---

### Table `reports` (texte)

Permet de stocker des données textuelles (rapports, Reddit, etc.) pour enrichir le RAG.

---

## Limites du dataset actuel

Le dataset Excel contient uniquement des statistiques agrégées.

Il ne permet pas :
- d’analyser les performances par match ;
- de comparer domicile / extérieur ;
- d’analyser des périodes (ex : 5 derniers matchs).

Ces limitations sont prises en compte dans la conception.

---

## Évolution prévue

Le schéma a été conçu pour permettre :
- l’ajout d’une table `matches` alimentée ;
- l’intégration de données temporelles ;
- une analyse plus fine des performances ;
- une meilleure complémentarité entre SQL et RAG.

---

## Rôle dans l’architecture globale

- SQL → données fiables (chiffrées)
- RAG → contexte (texte)

Cette combinaison permet de construire un système hybride plus robuste.