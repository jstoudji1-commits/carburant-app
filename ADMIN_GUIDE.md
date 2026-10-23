# Administration : fiches et authentification

## Fiches utilisateurs
Depuis Comptes utilisateurs, cliquer sur une adresse e-mail. Recherche par e-mail.
Consultation : profil, formule, Premium effectif, parrain et filleuls retrouvés dans
les comptes, historiques de parrainage conservés (parfois masqués), économies
synchronisées, véhicules, favoris et informations Apple non sensibles.
Les économies affichées sont les montants enregistrés par les applications, pas
une vérification des achats réels. Les historiques peuvent être limités par la
formule du compte. Aucun historique absent ne peut être reconstruit.

Modification : nom, téléphone, ville, formule, validation e-mail, expiration du
bonus Premium, note interne. Un motif est obligatoire. Une version de fiche
obsolète est refusée. Les modifications de la fiche sont journalisées.
Les notes et le journal sont dans DonneeApplication pour PostgreSQL et dans des
fichiers admin-utilisateur-<hash>.json sinon. Ils ne sont pas dans les données
synchronisées vers les applications. Les mots de passe et jetons ne sont jamais
renvoyés par la fiche. L'adresse e-mail (identifiant) et la facturation Apple ne
se modifient pas dans ce formulaire.

## Authentification
ADMIN_PASSWORD est obligatoire. L'ancien accès direct par X-Admin-Password est
supprimé. Le navigateur n'enregistre plus le mot de passe dans sessionStorage.
Après mot de passe correct, une adresse inconnue doit confirmer un code envoyé
à ADMIN_2FA_EMAIL (contact@optiplein.fr par défaut). Durée du code : 10 minutes,
usage unique, 5 essais maximum. L'envoi et les connexions sont limités.
Le choix « Reconnaître cette adresse IP » expire après 30 jours.
La session expire après 8 heures et est liée à l'identité réseau. Cookie
HttpOnly, SameSite=Strict, Secure en HTTPS/Render. Changer ADMIN_PASSWORD
invalide les sessions, codes et reconnaissances précédents.
Le bouton « Oublier les IP reconnues » ferme toutes les sessions et impose une
nouvelle vérification. La déconnexion révoque la session courante.

## Render et proxys
Ne pas configurer FORWARDED_ALLOW_IPS=* pour cette protection. Si des en-têtes
proxy sont présents, seuls les proxys explicitement approuvés dans
ADMIN_TRUSTED_PROXY_CIDRS (liste CIDR séparée par virgules) peuvent être traversés,
de droite à gauche, pour obtenir l'adresse du client. N'ajouter que des plages
confirmées par l'hébergement, jamais une liste supposée ou 0.0.0.0/0.
En l'absence d'une identification fiable, l'accès reste possible par code à
chaque connexion ; aucune adresse partagée du proxy n'est mémorisée.
Cette configuration doit être vérifiée sur l'environnement Render avant de
promettre la reconnaissance automatique des IP habituelles.

L'état de sécurité est dans OPTIPLEIN_DATA_DIR/admin-security.sqlite3,
transactions SQLite atomiques, compatible avec le disque persistant du service
Render déclaré dans render.yaml. Ne pas répliquer le service sur des machines
avec des disques indépendants sans migrer ce stockage vers un stockage partagé.
Les codes et sessions ne sont pas stockés en clair. Sauvegarder ce fichier comme
une donnée privée ; le supprimer impose de nouvelles connexions et validations.

## Validation avant déploiement
Configurer ADMIN_PASSWORD et vérifier l'envoi Brevo/SMTP à ADMIN_2FA_EMAIL.
Faire une connexion depuis un réseau habituel puis un autre, vérifier le code,
la déconnexion et la révocation. Aucun e-mail réel n'est envoyé par les tests.
Commande tests : venv/Scripts/python.exe -B -m unittest discover -s regression_tests
Les modifications présentes sont locales : aucun déploiement automatique n'a
été déclenché par leur préparation.

## Temporisation des IP inconnues
Après chaque série de trois mots de passe incorrects : blocage de 60 secondes,
puis 120, 240, 480, 960 secondes, etc. Le niveau est conservé dans SQLite entre
les connexions et redémarrages. Les tentatives pendant le blocage sont refusées,
même avec le bon mot de passe, sans allonger le délai ni compter comme un nouvel
échec. La réponse HTTP 429 comporte Retry-After ; l'écran affiche un compte à
rebours. Seule une authentification complète avec le code remet le compteur à
zéro. Les IP reconnues restent soumises à la limitation classique des tentatives.
Les limites globales anti-abus restent également actives.
