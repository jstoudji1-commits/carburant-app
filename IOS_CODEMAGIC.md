# Publication iOS sans Mac

Codemagic construit OptiPlein sur un Mac distant et envoie automatiquement le
fichier signe dans TestFlight. Aucun certificat ni fichier `.p8` ne doit etre
ajoute au depot GitHub.

## Configuration Apple

1. Souscrire a l'Apple Developer Program.
2. Creer l'identifiant explicite `com.optiplein.app` dans Certificates,
   Identifiers & Profiles.
3. Creer l'application OptiPlein dans App Store Connect avec ce Bundle ID et le
   SKU `optiplein-ios`.
4. Dans App Store Connect > Utilisateurs et acces > Integrations, creer une cle
   API avec le role Gestionnaire d'apps. Telecharger le fichier `.p8` une seule
   fois et conserver aussi le Key ID et l'Issuer ID.

## Configuration Codemagic

1. Connecter le depot GitHub a Codemagic.
2. Dans Team settings > Integrations > Developer Portal, ajouter la cle avec le
   nom exact `optiplein_app_store`.
3. Generer ou importer un certificat Apple Distribution et recuperer un profil
   App Store pour `com.optiplein.app`.
4. Selectionner le workflow `OptiPlein iOS - TestFlight`, puis lancer le build.

Le workflow installe Capacitor, synchronise la cible iOS, incremente le numero
de build, applique la signature, construit l'IPA et l'envoie dans TestFlight.
Il ne soumet pas automatiquement l'application a la validation publique.

## Tests sur iPhone

Installer TestFlight et verifier : localisation acceptee et refusee, direction
de la fleche, recalcul d'itineraire, connexion persistante, prochain
ravitaillement, stations TotalEnergies, ouverture de Waze et Google Maps, perte
puis retour du reseau.

## Avant la validation publique

- Ajouter les captures d'ecran, la description et les coordonnees d'assistance.
- Utiliser `https://www.optiplein.fr/confidentialite` comme URL de confidentialite.
- Remplir la fiche de confidentialite selon les donnees reellement collectees.
- Fournir a Apple un compte de demonstration si necessaire.
- Verifier que la suppression du compte est accessible dans l'application.
- Expliquer que la localisation sert aux stations proches, aux detours et au
  guidage.

Chaque push sur `main` declenche un nouveau build TestFlight. Le numero
technique est gere automatiquement par Codemagic.
