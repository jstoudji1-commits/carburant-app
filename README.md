# carburant-app
## Stockage PostgreSQL

L'application utilise PostgreSQL quand la variable `DATABASE_URL` est configuree. Sans cette variable, elle conserve le stockage JSON historique.

### Migration du schema

Le schema est gere avec Alembic :

```bash
alembic upgrade head
```

Sur Render, cette commande est lancee avant le demarrage de l'application.

### Import des donnees JSON existantes

Apres avoir cree la base PostgreSQL et deploye l'application, lancer une seule fois :

```bash
python migrate_storage.py import-json
```

La commande refuse d'ecraser une base PostgreSQL qui contient deja des donnees. Pour forcer l'import apres sauvegarde :

```bash
python migrate_storage.py import-json --force
```

### Retour arriere vers les fichiers JSON

Avant de retirer `DATABASE_URL`, exporter PostgreSQL vers les fichiers :

```bash
python migrate_storage.py export-json
```

Puis redemarrer l'application sans `DATABASE_URL`.

## Mise a jour des bornes de recharge

Les utilisateurs connectes peuvent proposer ou corriger le tarif d'une borne
depuis sa fiche sur la carte. La proposition est affichee immediatement avec
la mention `En attente de validation par OptiPlein`. L'administration dispose
d'une file de validation ; une proposition acceptee devient un tarif confirme
et une proposition refusee cesse d'etre appliquee.

L'application telecharge automatiquement le fichier statique national IRVE
tous les jours a 06:00, heure de Paris. Le fichier est conserve dans le dossier
configure par `OPTIPLEIN_DATA_DIR` (`/var/data` sur Render) afin que la derniere
copie valide reste disponible apres un redemarrage.

Au premier demarrage, le fichier est aussi telecharge immediatement s'il
n'existe pas encore. La mise a jour peut etre desactivee avec :

```bash
OPTIPLEIN_IRVE_DAILY_UPDATE=false
```

Le fichier dynamique national IRVE, qui contient l'etat et l'occupation des
points de charge, est telecharge au demarrage puis toutes les 5 minutes. Chaque
nouvelle copie est controlee avant de remplacer la derniere version valide.

Cette mise a jour peut etre desactivee avec :

```bash
OPTIPLEIN_IRVE_DYNAMIC_UPDATE=false
```

## Indexation et diffusion AdSense

Le domaine canonique public est `https://www.optiplein.fr`. Les requetes recues
sur `optiplein.fr` sont redirigees vers cette version par l'hebergement, et
l'application ne tente jamais de les renvoyer dans le sens inverse.

Pendant la phase de validation AdSense, le code publicitaire est limite aux
pages editoriales substantielles : accueil, guides, FAQ et observatoire. Il est
desactive sur la carte `/web`, la page testeur `/landing`, l'administration et
les pages utilitaires. La carte et la landing portent aussi une directive
`noindex` et ne figurent pas dans le sitemap editorial.

Les operations manuelles a effectuer dans Google Search Console sont detaillees
dans `SEARCH_CONSOLE_CHECKLIST.md`.

## Stations TotalEnergies participantes

Le fichier `totalenergies_avantage_carburant.json` contient les stations du
localisateur officiel portant le filtre `OpeAvantageCarburant`, rapprochées des
identifiants gouvernementaux utilisés par la carte. Il est généré avec :

```bash
python3 update_totalenergies_avantage_carburant.py
```

Le script refuse de remplacer le fichier si la réponse officielle est
anormalement faible. Les stations qui ne peuvent pas être rapprochées à moins
de 500 mètres restent dans la section `unmatched` pour contrôle manuel et ne
sont pas affichées comme participantes.
