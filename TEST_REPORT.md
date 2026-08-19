# Rapport de validation OptiPlein

Date : 19 août 2026

## Corrections appliquées

- Création d'un véhicule sans supprimer le véhicule actuellement actif.
- Distinction fiable entre la création d'un nouveau véhicule et la modification du véhicule actif.
- Sauvegarde immédiate du changement de véhicule avant le rechargement lié à son énergie.
- Réparation automatique d'un identifiant de véhicule actif devenu invalide.
- Conservation correcte d'une jauge à 0 %, côté navigateur et côté serveur.
- Limitation de la jauge entre 0 et 100 %.
- Masquage, pour tous les carburants, des stations sans prix exploitable pour le produit sélectionné.
- Réparation de deux fichiers JSON tronqués utilisés par l'enrichissement et la mise à jour des prix.

## Tests automatisés

- Compilation et analyse syntaxique de tous les fichiers Python racine.
- Validation de tous les fichiers JSON racine.
- Recherche d'identifiants HTML dupliqués dans les modèles.
- Contrôle des routes publiques essentielles.
- Validation de toutes les coordonnées du fichier `stations.csv`.
- Scénarios de création, modification et changement de véhicule.
- Pages publiques : accueil, carte, guides, FAQ et observatoire.
- Chargement de la carte avec coordonnées GPS vides.
- Fichiers Search Console, robots, sitemap et ads.txt.
- Rejet des coordonnées API invalides.
- API des six carburants gouvernementaux autour de Marignane.
- Absence de station sans prix dans chaque résultat carburant.
- Validité des coordonnées renvoyées par l'API.
- Nettoyage, calcul d'autonomie et bornage de la jauge des véhicules.

Commandes :

```bash
python3 tests/run_checks.py
node tests/check_vehicle_state.js
python3 -m unittest -v tests/test_backend.py
```

Les tests HTTP nécessitent les dépendances de `requirements.txt` et `httpx`.
