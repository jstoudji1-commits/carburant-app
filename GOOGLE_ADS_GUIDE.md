# Suivi Google Ads des inscriptions

- Compte : AW-18540838649.
- Action commune Inscription : AW-18540838649/bgDvCM746KsdEPn9-ohF.
- Déclencheurs : validation réussie de l’e-mail du compte et validation réussie de l’e-mail du testeur Android.
- Aucun événement au simple affichage, à la soumission du formulaire, à la connexion ou via un paramètre URL de succès.

## Consentement et portée
Le script public static/google-ads.js charge Google uniquement après acceptation via Mesure publicitaire. Le refus reste possible avec la même visibilité ; le choix dure 180 jours et peut être changé avec le bouton permanent. Le retrait recharge la page pour ne plus charger la balise. La personnalisation publicitaire et Analytics restent refusés.
La mesure est destinée au navigateur Web, pas aux installations App Store/Google Play ni aux sessions natives Capacitor.
Le consentement doit être présent dans le navigateur qui valide le lien e-mail. Un lien ouvert dans un autre navigateur sans consentement ne produit pas de conversion. Les bloqueurs peuvent aussi empêcher la mesure.

## Confirmation et doublons
Après validation et seulement avec consentement, le serveur émet un reçu anonyme signé, HttpOnly, valable 24 heures. Les reçus compte et testeur sont distincts. L’API /api/ads/conversions expose uniquement le type et un identifiant aléatoire ; elle exige aussi le consentement et désactive le cache. L’identifiant devient transaction_id pour la déduplication Google. Un marqueur local évite les renvois après le callback. Le callback ne constitue pas une preuve de comptabilisation dans Google Ads.
Aucune adresse e-mail, aucun jeton de validation et aucune donnée du profil ne sont transmis par cette intégration. Les URL de page et de provenance sont filtrées.

## Vérification après déploiement
Utiliser Tag Assistant sur une page publique : refus = aucun chargement de gtag.js par cette intégration ; acceptation = balise AW-18540838649 et consentement accordé pour la mesure publicitaire uniquement.
Valider chacun des deux parcours avec des comptes de test et consentement préalable. Vérifier send_to et transaction_id ; recharger ne doit pas générer une nouvelle inscription.
Vérifier ensuite le diagnostic de la balise et l’action Inscription dans Google Ads. Le réglage de comptage de cette action reste celui du compte Ads ; il peut limiter les conversions comptabilisées par clic. Les deux parcours alimentent la même action, pas deux actions distinctes.
Les tests automatisés locaux simulent Google et n’envoient aucune conversion réelle. La réception et l’attribution Google ne peuvent être confirmées avant déploiement et vérification dans le compte.
