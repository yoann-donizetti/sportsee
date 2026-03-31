# Validation des requêtes SQL métier

Objectif : 
- Valider que la base PostgreSQL permet de répondre correctement aux questions métier avant l’intégration du LLM.
- Ces requêtes servent :
    - de base de test ;
    - de validation du schéma ;
    - de référence pour les few-shot examples.


## 1. Joueur avec le plus de points

```sql
SELECT p.player_name, s.pts
FROM stats s
JOIN players p ON s.player_id = p.player_id
ORDER BY s.pts DESC
LIMIT 1;
```

- Vérifie que la jointure stats → players fonctionne
- Vérifie le tri descendant

## 2. Joueur avec le meilleur pourcentage à 3 points

```sql
SELECT p.player_name, s.fg3_pct
FROM stats s
JOIN players p ON s.player_id = p.player_id
WHERE s.fg3_pct IS NOT NULL
ORDER BY s.fg3_pct DESC
LIMIT 1;
```

- Vérifie la gestion des valeurs NULL
- Vérifie les métriques de pourcentage

3. Joueur avec le plus de rebonds

```sql
SELECT p.player_name, s.reb
FROM stats s
JOIN players p ON s.player_id = p.player_id
ORDER BY s.reb DESC
LIMIT 1;
```

- Vérifie une autre métrique clé

4. Joueur avec le plus de passes


```sql
SELECT p.player_name, s.ast
FROM stats s
JOIN players p ON s.player_id = p.player_id
ORDER BY s.ast DESC
LIMIT 1;
```

- Vérifie une statistique différente

5. Top 5 des scoreurs

```sql
SELECT p.player_name, s.pts
FROM stats s
JOIN players p ON s.player_id = p.player_id
ORDER BY s.pts DESC
LIMIT 5;
```

- Vérifie le LIMIT
- Sert directement de few-shot

6. Combinaison points + passes

```sql
SELECT p.player_name, (s.pts + s.ast) AS pts_ast
FROM stats s
JOIN players p ON s.player_id = p.player_id
ORDER BY pts_ast DESC
LIMIT 5;
```

- Vérifie un calcul métier
- Important pour le LLM (expressions SQL)

7. Moyenne des points par équipe
```sql
SELECT t.team_name, AVG(s.pts) AS avg_pts
FROM stats s
JOIN players p ON s.player_id = p.player_id
JOIN teams t ON p.team_code = t.team_code
GROUP BY t.team_name
ORDER BY avg_pts DESC
LIMIT 10;
```

- Vérifie les agrégations
- Vérifie GROUP BY
- Vérifie double JOIN

8. Équipes les plus mentionnées dans les reports

```sql
SELECT t.team_name, COUNT(*) AS nb_mentions
FROM reports r
JOIN teams t ON r.related_team_code = t.team_code
WHERE r.related_team_code IS NOT NULL
GROUP BY t.team_name
ORDER BY nb_mentions DESC
LIMIT 10;
```


- Vérifie l’utilisation des données textuelles
- Permet de connecter SQL et RAG

## Conclusion

Ces requêtes confirment que :

- le schéma relationnel est exploitable ;
- les jointures sont correctes ;
- les questions métier peuvent être exprimées en SQL.

Elles serviront de base pour :

- les few-shot examples ;
- les tests du SQL tool ;
- la validation du système hybride SQL + RAG.

