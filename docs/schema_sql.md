# Schéma SQL — Intégration des données structurées

## Objectif

L’objectif de cette étape est d’intégrer les données Excel dans une base relationnelle afin de permettre au système de répondre de manière fiable aux questions chiffrées.

Le système RAG seul montre ses limites sur les questions nécessitant :
- des agrégations ;
- des comparaisons ;
- des calculs.

L’ajout d’une base SQL permet d’améliorer la fiabilité, de réduire les hallucinations et de fournir des réponses traçables.

---

## Choix technique

Le système repose sur une base **PostgreSQL**.

Ce choix a été retenu pour plusieurs raisons :
- base relationnelle robuste et évolutive ;
- meilleure structuration des données ;
- possibilité de documenter directement les tables et colonnes ;
- plus grande proximité avec un contexte de production ;
- meilleure extensibilité pour intégrer à terme des données match par match.



---

## Sécurité du SQL Tool

L’utilisation d’un LLM pour générer des requêtes SQL introduit un risque d’exécution de requêtes non contrôlées.

Afin de sécuriser le système, plusieurs mécanismes sont prévus :
- limitation aux requêtes de type `SELECT` uniquement ;
- validation des requêtes avant exécution ;
- accès restreint aux seules tables métier utiles ;
- utilisateur base de données avec droits limités ;
- séparation claire entre données structurées (SQL) et données textuelles (RAG).

L’objectif est de garantir que le SQL Tool reste un composant de consultation, sans possibilité de modifier ou supprimer les données.

---

## Modélisation des données

Le schéma a été conçu pour être :
- exploitable immédiatement avec les données Excel actuelles ;
- évolutif pour intégrer ultérieurement des données match par match ;
- compatible avec une architecture hybride SQL + RAG.

---

### Table `teams`

Contient les informations sur les équipes NBA.

| Colonne     | Type      | Description |
|------------|-----------|------------|
| team_code  | VARCHAR   | Code de l’équipe (clé primaire) |
| team_name  | TEXT      | Nom complet de l’équipe |

---

### Table `players`

Contient les informations de référence sur les joueurs.

| Colonne      | Type      | Description |
|-------------|-----------|------------|
| player_id   | SERIAL    | Identifiant unique |
| player_name | TEXT      | Nom du joueur |
| team_code   | VARCHAR   | Équipe associée |
| age         | INTEGER   | Âge du joueur |

---

### Table `stats`

Contient les statistiques agrégées par joueur.

Chaque ligne correspond à un joueur dans le dataset actuel.

| Colonne         | Type    | Description |
|----------------|---------|------------|
| stat_id        | SERIAL  | Identifiant unique |
| player_id      | INTEGER | Référence au joueur |
| gp             | INTEGER | Nombre de matchs joués |
| w              | INTEGER | Victoires |
| l              | INTEGER | Défaites |
| minutes_avg    | REAL    | Minutes moyennes jouées par match |
| pts            | REAL    | Points |
| fgm            | REAL    | Tirs réussis |
| fga            | REAL    | Tirs tentés |
| fg_pct         | REAL    | Pourcentage aux tirs |
| fifteen_min    | REAL    | Minutes jouées après 15:00 |
| fg3a           | REAL    | Tirs à 3 points tentés |
| fg3_pct        | REAL    | Pourcentage à 3 points |
| ftm            | REAL    | Lancers francs réussis |
| fta            | REAL    | Lancers francs tentés |
| ft_pct         | REAL    | Pourcentage aux lancers francs |
| oreb           | REAL    | Rebonds offensifs |
| dreb           | REAL    | Rebonds défensifs |
| reb            | REAL    | Rebonds totaux |
| ast            | REAL    | Passes décisives |
| tov            | REAL    | Balles perdues |
| stl            | REAL    | Interceptions |
| blk            | REAL    | Contres |
| pf             | REAL    | Fautes personnelles |
| fp             | REAL    | Fantasy points |
| dd2            | INTEGER | Double-doubles |
| td3            | INTEGER | Triple-doubles |
| plus_minus     | REAL    | Plus-Minus |
| offrtg         | REAL    | Offensive Rating |
| defrtg         | REAL    | Defensive Rating |
| netrtg         | REAL    | Net Rating |
| ast_pct        | REAL    | Pourcentage d’assists |
| ast_to         | REAL    | Ratio passes / pertes de balle |
| ast_ratio      | REAL    | Ratio d’assists pour 100 possessions |
| oreb_pct       | REAL    | Pourcentage de rebonds offensifs |
| dreb_pct       | REAL    | Pourcentage de rebonds défensifs |
| reb_pct        | REAL    | Pourcentage de rebonds totaux |
| to_ratio       | REAL    | Turnover Ratio |
| efg_pct        | REAL    | Effective Field Goal % |
| ts_pct         | REAL    | True Shooting % |
| usg_pct        | REAL    | Usage Rate |
| pace           | REAL    | Rythme de jeu |
| pie            | REAL    | Player Impact Estimate |
| poss           | REAL    | Possessions jouées |

---

### Table `matches` (préparée pour évolution)

Cette table est prévue pour accueillir ultérieurement des données match par match.

Elle n’est pas alimentée dans la version actuelle si les données sources ne contiennent pas encore :
- date du match ;
- équipe à domicile ;
- équipe à l’extérieur ;
- identifiant de match.

| Colonne         | Type    | Description |
|----------------|---------|------------|
| match_id        | SERIAL  | Identifiant unique |
| match_date      | DATE    | Date du match |
| home_team_code  | VARCHAR | Équipe à domicile |
| away_team_code  | VARCHAR | Équipe à l’extérieur |
| season          | TEXT    | Saison |
| source          | TEXT    | Source des données |

---

### Table `reports`

Permet de stocker des données textuelles pour enrichir le système RAG :
- rapports ;
- commentaires ;
- discussions Reddit ;
- comptes rendus de matchs.

| Colonne            | Type    | Description |
|-------------------|---------|------------|
| report_id          | SERIAL  | Identifiant unique |
| source_file        | TEXT    | Fichier source |
| title              | TEXT    | Titre éventuel |
| report_text        | TEXT    | Contenu textuel |
| related_team_code  | VARCHAR | Équipe associée |
| related_player_name| TEXT    | Joueur associé |
| related_match_id   | INTEGER | Match associé si disponible |

**Note :**
Le système distingue :
- une entité principale (`related_team_code`, `related_player_name`) utilisée pour les requêtes directes ;
- des entités secondaires (`related_team_codes`, `related_player_names`) permettant d’enrichir le contexte et d’améliorer la recherche sémantique.
---

## Limites du dataset actuel

Le dataset Excel actuellement utilisé contient uniquement des statistiques agrégées par joueur.

Il ne permet pas :
- d’analyser les performances par match ;
- de comparer domicile / extérieur ;
- d’analyser une période glissante (ex. : 5 derniers matchs) ;
- de reconstruire une chronologie détaillée des performances.

Ces limites sont prises en compte dans la conception de la base :
- le schéma prévoit déjà des tables `matches` et `reports` ;
- mais seules les tables réellement alimentables sont exploitées dans cette phase.

---

## Évolution prévue

Le schéma a été conçu pour permettre :
- l’ajout d’une table `matches` réellement alimentée ;
- l’intégration de données temporelles ;
- l’enrichissement via des rapports textuels ;
- une analyse plus fine des performances ;
- une meilleure complémentarité entre SQL et RAG.

À terme, cette architecture permettra de traiter :
- des questions purement chiffrées via SQL ;
- des questions contextuelles via RAG ;
- des questions hybrides via SQL + RAG.

---

## Rôle dans l’architecture globale

- **SQL** → données fiables, structurées et traçables ;
- **RAG** → contexte textuel, explication et enrichissement ;
- **LLM** → reformulation en langage naturel.

Cette combinaison permet de construire un système hybride plus robuste, plus fiable et mieux adapté aux besoins métier.