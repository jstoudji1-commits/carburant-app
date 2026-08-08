"""Contenus éditoriaux originaux d'OptiPlein destinés aux pages publiques."""


PUBLICATION = "8 août 2026"
AUTHOR = "J. Stoudji, éditeur d’OptiPlein"


def guide(slug, title, description, eyebrow, hero_title, lead, sections, **extra):
    page = {
        "slug": slug,
        "title": title,
        "nav_title": hero_title,
        "description": description,
        "eyebrow": eyebrow,
        "hero_title": hero_title,
        "lead": lead,
        "published": PUBLICATION,
        "updated": PUBLICATION,
        "published_iso": "2026-08-08",
        "updated_iso": "2026-08-08",
        "author": AUTHOR,
        "article": True,
        "sections": sections,
    }
    page.update(extra)
    return page


GUIDES_EDITORIAUX = {
    "guides": guide(
        "guides",
        "Guides carburant et recharge électrique | OptiPlein",
        "Guides pratiques OptiPlein pour comprendre les prix des carburants, les tarifs de recharge, les données officielles et le calcul de rentabilité.",
        "Centre de ressources",
        "Guides carburant et recharge",
        "Comprendre un prix est aussi important que le voir sur une carte. Ces guides expliquent les données, les calculs et les limites d’OptiPlein avec des exemples concrets.",
        [
            {
                "title": "À quoi servent ces guides ?",
                "paragraphs": [
                    "OptiPlein affiche des prix et propose une station adaptée au véhicule sélectionné. Pour prendre une décision éclairée, il faut cependant savoir quand le prix a été déclaré, quelle unité est utilisée et combien coûte réellement le détour. Le centre de ressources documente ces points sans masquer les incertitudes.",
                    "Chaque article répond à une question rencontrée dans l’application. Les sources sont indiquées, les formules sont détaillées et les limites sont expliquées. Un prix manquant n’est pas remplacé par une estimation arbitraire : il reste signalé comme non communiqué.",
                ],
            },
            {
                "title": "Comprendre les carburants disponibles",
                "paragraphs": [
                    "Le flux français distingue le Gazole, le SP95, le SP98, l’E10, l’E85 et le GPLc. Ces appellations ne sont pas interchangeables. Le guide consacré aux carburants explique leur composition générale, les vérifications à effectuer dans le manuel du véhicule et la raison pour laquelle l’application conserve un filtre séparé pour chaque produit.",
                ],
                "links": [
                    {"label": "Lire le guide des six carburants", "url": "/guides/carburants-disponibles"},
                ],
            },
            {
                "title": "Vérifier la provenance d’un prix",
                "paragraphs": [
                    "La date de déclaration et la source comptent autant que le montant. Le guide des données décrit le parcours du fichier gouvernemental jusqu’à la carte, les contrôles appliqués et les situations dans lesquelles une station peut disparaître du classement.",
                ],
                "links": [
                    {"label": "Comprendre les sources et les mises à jour", "url": "/guides/sources-prix-carburants"},
                ],
            },
            {
                "title": "Comparer le prix et le coût du détour",
                "paragraphs": [
                    "Une économie de quelques centimes par litre peut être annulée par plusieurs kilomètres supplémentaires. Le guide de rentabilité présente les entrées du calcul, la formule utilisée et un exemple chiffré reproductible.",
                ],
                "links": [
                    {"label": "Voir la méthode de calcul", "url": "/guides/calcul-station-rentable"},
                ],
            },
            {
                "title": "Décoder la recharge électrique",
                "paragraphs": [
                    "Une recharge peut combiner prix au kWh, frais de session, facturation à la minute et pénalité d’occupation. Deux guides distincts expliquent les tarifs et les couleurs de disponibilité afin de ne pas confondre prix, puissance et état du point de charge.",
                ],
                "links": [
                    {"label": "Comprendre les tarifs de recharge", "url": "/guides/tarifs-recharge-electrique"},
                    {"label": "Comprendre la disponibilité IRVE", "url": "/guides/disponibilite-bornes-irve"},
                ],
            },
            {
                "title": "Aider à corriger une information",
                "paragraphs": [
                    "Une station peut modifier son enseigne, déplacer un accès ou déclarer tardivement un prix. Le guide de signalement indique les éléments à transmettre pour qu’une anomalie soit vérifiable, sans demander de donnée personnelle inutile.",
                ],
                "links": [
                    {"label": "Signaler un prix ou une position", "url": "/guides/signaler-erreur-station"},
                ],
            },
        ],
        highlights=[
            {"title": "Données expliquées", "text": "Origine, date, contrôles et limites sont décrits clairement."},
            {"title": "Exemples chiffrés", "text": "Les calculs peuvent être vérifiés étape par étape."},
            {"title": "Décisions prudentes", "text": "Une information inconnue reste inconnue au lieu d’être inventée."},
        ],
    ),
    "guide_carburants": guide(
        "guides/carburants-disponibles",
        "Gazole, SP95, SP98, E10, E85 et GPLc : guide complet | OptiPlein",
        "Comprendre les six carburants suivis par le gouvernement français et choisir uniquement un carburant compatible avec son véhicule.",
        "Guide carburants",
        "Les six carburants du flux officiel",
        "Le prix le plus bas n’a de sens qu’entre produits compatibles. Voici ce que représentent les six catégories affichées par OptiPlein et les précautions à prendre avant de changer de carburant.",
        [
            {
                "title": "Pourquoi six catégories distinctes ?",
                "paragraphs": [
                    "Le fichier officiel des prix des carburants distingue six produits : Gazole, SP95, SP98, E10, E85 et GPLc. Une station peut en vendre seulement une partie. OptiPlein conserve donc une colonne et un filtre propres à chaque carburant ; l’absence de prix pour un produit ne signifie pas que la station est fermée.",
                    "Le choix affiché sur la carte peut être changé pour comparer le marché, mais le calcul de la station la plus rentable reste associé au carburant du véhicule actif. Cette séparation évite de comparer, par exemple, le prix du Gazole d’une station avec les besoins d’un véhicule essence.",
                ],
            },
            {
                "title": "Gazole",
                "paragraphs": [
                    "Le Gazole est destiné aux moteurs diesel. Son prix est exprimé en euros par litre. Les appellations commerciales premium ou additivées ne constituent pas une catégorie séparée dans le flux national : le prix déclaré sous « Gazole » correspond au produit réglementaire transmis par la station.",
                    "Un véhicule essence ne doit jamais recevoir de Gazole, et inversement. L’application utilise le profil diesel pour sélectionner automatiquement cette énergie, tout en laissant l’utilisateur consulter les autres prix à titre informatif.",
                ],
            },
            {
                "title": "SP95 et SP98",
                "paragraphs": [
                    "SP signifie essence sans plomb. Les nombres 95 et 98 correspondent à des indices d’octane différents. Le SP98 n’est pas automatiquement meilleur ou plus économique : la compatibilité et l’intérêt éventuel dépendent du moteur et des préconisations du constructeur.",
                    "Certaines stations ne déclarent plus de SP95 classique mais proposent de l’E10. OptiPlein ne transforme pas un prix SP95 en SP98 ou en E10. Chaque montant reste rattaché au libellé fourni par la source officielle.",
                ],
            },
            {
                "title": "E10",
                "paragraphs": [
                    "Le SP95-E10, affiché E10 dans le flux, contient jusqu’à 10 % d’éthanol en volume. Il est compatible avec la majorité des voitures essence récentes, mais la vérification doit se faire sur la trappe à carburant, le manuel du véhicule ou la documentation du constructeur.",
                    "Dans OptiPlein, un profil essence ou hybride essence utilise E10 comme choix initial prudent lorsque aucun carburant plus précis n’est enregistré. L’utilisateur reste libre d’afficher SP95 ou SP98, sans modifier silencieusement les paramètres du véhicule.",
                ],
            },
            {
                "title": "E85",
                "paragraphs": [
                    "Le superéthanol E85 contient une proportion élevée de bioéthanol, variable selon la saison. Il est réservé aux véhicules FlexFuel ou aux véhicules équipés d’un dispositif homologué et compatible. Son prix au litre est souvent inférieur, mais la consommation volumique peut être plus élevée.",
                    "La rentabilité ne doit donc pas être déduite du seul prix affiché. Le profil E85 d’OptiPlein demande une consommation propre au véhicule afin d’éviter de reprendre automatiquement une consommation essence qui ne correspondrait pas à l’usage réel.",
                ],
            },
            {
                "title": "GPLc",
                "paragraphs": [
                    "GPLc désigne le gaz de pétrole liquéfié carburant. Le prix officiel est exprimé en euros par litre, même si le produit est stocké sous pression. Il nécessite un véhicule GPL ou une installation homologuée. Toutes les stations ne disposent pas de la même accessibilité ni des mêmes horaires pour la distribution de GPLc.",
                    "La carte affiche « GPL » pour rester lisible, tandis que la donnée interne conserve le code GPLc du flux officiel. Une station sans prix GPLc vérifiable est exclue du classement pour ce carburant.",
                ],
            },
            {
                "title": "Comment choisir sans risque ?",
                "paragraphs": [
                    "La première règle est de suivre la documentation du constructeur. Une différence de quelques centimes ne justifie jamais l’utilisation d’un carburant non compatible. En cas de doute, vérifier l’étiquette de la trappe, le manuel ou demander conseil à un professionnel.",
                    "La deuxième règle est de comparer la même unité et le même produit. OptiPlein affiche trois décimales, comme les prix au litre généralement déclarés, mais n’atteste pas qu’un prix est encore visible à la pompe au moment précis de l’arrivée.",
                ],
            },
        ],
        sources=[
            {"label": "Prix des carburants – flux instantané officiel", "url": "https://donnees.roulez-eco.fr/opendata/instantane"},
            {"label": "Service public – compatibilité SP95-E10", "url": "https://www.service-public.fr/particuliers/actualites/A12027"},
        ],
        related=[
            {"label": "D’où viennent les prix ?", "url": "/guides/sources-prix-carburants"},
            {"label": "Comment est calculée la rentabilité ?", "url": "/guides/calcul-station-rentable"},
        ],
    ),
    "guide_sources": guide(
        "guides/sources-prix-carburants",
        "Source et mise à jour des prix carburants | OptiPlein",
        "Découvrez comment OptiPlein récupère, contrôle et affiche les prix officiels des carburants et les données nationales des bornes électriques.",
        "Méthodologie des données",
        "D’où viennent les prix affichés ?",
        "OptiPlein ne fixe pas les prix. L’application transforme des données publiées par des sources identifiées, applique des contrôles puis indique clairement ce qui manque ou reste incertain.",
        [
            {
                "title": "Le flux gouvernemental des carburants",
                "paragraphs": [
                    "Pour les stations-service françaises, OptiPlein utilise le fichier instantané diffusé par le service public des prix des carburants. Chaque enregistrement possède notamment un identifiant de point de vente, une adresse, des coordonnées et les prix déclarés pour les produits disponibles.",
                    "Les prix sont déclarés par les points de vente soumis au dispositif. OptiPlein les restitue sans les recalculer. Une valeur anormalement basse peut donc provenir d’une erreur de déclaration ; elle doit être vérifiée avant d’être considérée comme une bonne affaire certaine.",
                ],
            },
            {
                "title": "Les six prix importés",
                "paragraphs": [
                    "L’import traite Gazole, SP95, SP98, E10, E85 et GPLc. Lorsqu’une station ne publie pas un produit, la cellule reste vide. L’application ne remplace pas une valeur absente par une moyenne nationale et ne copie pas le prix d’un carburant voisin.",
                    "Cette règle évite de fabriquer un classement séduisant mais faux. Une station ne participe au calcul que si son prix pour le carburant du véhicule est numérique, positif et situé dans le rayon choisi.",
                ],
            },
            {
                "title": "Bornes électriques : données statiques et dynamiques",
                "paragraphs": [
                    "Les bornes utilisent la base nationale IRVE. Le fichier statique décrit l’opérateur, l’enseigne, l’adresse, les coordonnées, la puissance et les prises. Le fichier dynamique peut fournir l’état de service et l’occupation de chaque point de charge lorsque l’opérateur les publie correctement.",
                    "Le fichier dynamique n’est pas une base tarifaire nationale. Les conditions de prix présentes dans le statique sont parfois textuelles, variables ou absentes. OptiPlein n’affiche un prix au kWh que lorsqu’une valeur unique et exploitable peut être extraite sans ambiguïté.",
                ],
            },
            {
                "title": "Fréquence et remplacement sécurisé",
                "paragraphs": [
                    "La copie statique IRVE est renouvelée quotidiennement à 6 heures, heure de Paris. La disponibilité dynamique est actualisée au démarrage puis régulièrement. Pour les carburants, le service récupère le fichier officiel selon la tâche configurée sur le serveur.",
                    "Chaque téléchargement est contrôlé avant de remplacer la dernière copie valide. Si un fichier est vide, incomplet ou illisible, l’ancienne version reste utilisée. Ce choix favorise la continuité du service tout en évitant d’effacer des données correctes avec un téléchargement défectueux.",
                ],
            },
            {
                "title": "Contrôles réalisés",
                "paragraphs": [
                    "L’import vérifie un nombre minimal de stations, la présence de coordonnées et l’existence d’un volume suffisant de prix valides. Les prix non numériques, nuls lorsqu’ils signifient une absence, ou égaux à une valeur sentinelle technique sont exclus des comparaisons.",
                    "Les distances sont recalculées à partir de la position de l’utilisateur et des coordonnées de la station. Les données sont ensuite limitées au rayon demandé. Le résumé du prix minimum est recalculé avec cette même liste afin d’éviter qu’une station située à l’autre bout de la France apparaisse comme la moins chère autour de l’utilisateur.",
                ],
            },
            {
                "title": "Ce que la date ne garantit pas",
                "paragraphs": [
                    "Une mise à jour récente du fichier ne prouve pas que chaque ligne a été modifiée le même jour. Certaines stations peuvent conserver un prix ancien ou tarder à déclarer un changement. De même, une borne indiquée libre peut être occupée quelques secondes plus tard.",
                    "OptiPlein affiche ces informations comme une aide à la décision. Le prix visible sur place, les conditions de paiement de l’opérateur et la signalisation routière restent prioritaires.",
                ],
            },
            {
                "title": "Corrections et traçabilité",
                "paragraphs": [
                    "Une correction d’enseigne, d’adresse ou de coordonnée doit rester traçable et ne doit pas masquer une nouvelle valeur officielle devenue plus fiable. Les signalements sont examinés à partir de l’identifiant de station, de l’adresse, de la position et d’un élément vérifiable fourni par l’utilisateur.",
                    "OptiPlein indique la source et la date de mise à jour sur ses pages de méthode. Une information tarifaire provenant à l’avenir d’un partenaire sera distinguée du flux ouvert afin que l’utilisateur sache ce qui est officiel, contractuel ou simplement indisponible.",
                ],
            },
        ],
        sources=[
            {"label": "Flux officiel des prix des carburants", "url": "https://donnees.roulez-eco.fr/opendata/instantane"},
            {"label": "Base nationale IRVE", "url": "https://transport.data.gouv.fr/datasets/base-nationale-des-lieux-de-recharge-de-vehicules-electriques"},
            {"label": "Licence Ouverte Etalab 2.0", "url": "https://www.etalab.gouv.fr/licence-ouverte-open-licence/"},
        ],
        related=[
            {"label": "Les six carburants expliqués", "url": "/guides/carburants-disponibles"},
            {"label": "Signaler une information incorrecte", "url": "/guides/signaler-erreur-station"},
        ],
    ),
    "guide_rentabilite": guide(
        "guides/calcul-station-rentable",
        "Calcul de la station la plus rentable : méthode et exemple | OptiPlein",
        "Formule, hypothèses et exemple détaillé du calcul OptiPlein qui compare prix, quantité achetée, distance, consommation et coût du détour.",
        "Méthode de calcul",
        "Comment OptiPlein choisit une station rentable",
        "Le prix affiché à la pompe n’est qu’une partie du coût. OptiPlein compare le gain sur le plein avec l’énergie consommée et le temps nécessaire pour atteindre la station.",
        [
            {
                "title": "Les informations utilisées",
                "paragraphs": [
                    "Le calcul utilise le carburant ou l’énergie du véhicule actif, sa capacité, sa consommation moyenne, le niveau restant, la position de l’utilisateur et les stations ayant un prix valide dans le rayon choisi. Consulter un autre carburant sur la carte ne change pas silencieusement le calcul du véhicule.",
                    "Pour une voiture thermique, la capacité est exprimée en litres et la consommation en litres pour 100 kilomètres. Pour une voiture électrique, la capacité est exprimée en kWh et la consommation en kWh pour 100 kilomètres. Les deux quantités ne sont jamais mélangées.",
                ],
            },
            {
                "title": "Étape 1 : quantité à compléter",
                "paragraphs": [
                    "La quantité théorique à acheter est calculée par : capacité × (100 − niveau restant) ÷ 100. Avec un réservoir de 50 litres rempli à 30 %, la quantité à compléter est 50 × 70 % = 35 litres.",
                    "Pour une batterie de 60 kWh à 30 %, le même calcul donne 42 kWh. Il s’agit d’une hypothèse de comparaison et non d’une instruction de charger systématiquement à 100 %, ce qui dépend du véhicule, du trajet et des recommandations du constructeur.",
                ],
            },
            {
                "title": "Étape 2 : coût de l’achat",
                "paragraphs": [
                    "Le coût de l’énergie achetée est la quantité à compléter multipliée par le prix de la station. Pour 35 litres à 1,80 €/L, le coût est de 63 €. À 1,76 €/L, il est de 61,60 €, soit 1,40 € d’écart avant prise en compte du trajet.",
                    "Une borne sans prix au kWh fiable n’est pas introduite avec une valeur moyenne. Elle reste hors comparaison, car un prix inventé pourrait désigner à tort la borne comme la moins chère.",
                ],
            },
            {
                "title": "Étape 3 : énergie consommée par le détour",
                "paragraphs": [
                    "Lorsque la station impose un aller-retour spécifique, la consommation du détour est : kilomètres supplémentaires × consommation ÷ 100. Un détour de 8 km avec une consommation de 6,5 L/100 km utilise environ 0,52 litre.",
                    "Si le carburant de référence vaut 1,80 €/L, ce détour représente environ 0,94 €. Le gain brut de 1,40 € tombe donc à 0,46 € avant même de valoriser le temps. La station la moins chère au litre n’est plus nécessairement la meilleure décision.",
                ],
            },
            {
                "title": "Étape 4 : temps supplémentaire",
                "paragraphs": [
                    "OptiPlein peut convertir les minutes supplémentaires en coût indicatif à partir d’une vitesse moyenne de détour et d’une valeur horaire interne. Cette composante ne prétend pas donner une valeur universelle au temps : elle évite seulement qu’un détour important soit présenté comme gratuit.",
                    "L’explication affichée distingue le coût de l’achat, le coût de l’énergie consommée pour le détour et le temps estimé. L’utilisateur peut ainsi comprendre pourquoi une station légèrement plus chère mais beaucoup plus proche est retenue.",
                ],
            },
            {
                "title": "Exemple complet",
                "paragraphs": [
                    "Prenons un réservoir de 50 L, rempli à 30 %, une consommation de 6,5 L/100 km et 35 L à acheter. La station A est sur le trajet à 1,80 €/L : achat 63 €. La station B est à 1,76 €/L : achat 61,60 €, mais elle ajoute 8 km.",
                    "Le détour consomme 0,52 L, soit environ 0,94 € au prix de référence. Le coût énergétique de B atteint donc 62,54 €. Son avantage n’est plus que de 0,46 €, auquel il faut comparer le temps supplémentaire. Selon ce temps, A peut être considérée comme plus rentable malgré son prix au litre supérieur.",
                ],
            },
            {
                "title": "Cas particulier de l’électricité",
                "paragraphs": [
                    "Pour un véhicule électrique, la quantité achetée est en kWh. Le détour consomme également des kWh selon la consommation renseignée. À prix identique, l’algorithme privilégie la borne la plus proche afin de ne pas envoyer l’utilisateur vers une borne équivalente située plusieurs kilomètres plus loin.",
                    "La puissance de charge influence surtout la durée de l’arrêt. Elle ne remplace pas le prix au kWh. Un tarif à la minute ou des frais d’occupation exigent une information supplémentaire et ne peuvent pas être comparés correctement avec un simple prix énergétique.",
                ],
            },
            {
                "title": "Limites et bonnes pratiques",
                "paragraphs": [
                    "La consommation réelle varie avec la vitesse, la météo, le relief, la charge du véhicule et la circulation. La distance routière peut également différer de la distance directe. Le résultat est donc une estimation documentée, pas une garantie d’économie.",
                    "Pour améliorer le résultat, renseigner une consommation observée sur plusieurs trajets, maintenir la jauge à jour et vérifier le prix à l’arrivée. Si une donnée paraît incohérente, le signalement permet de la contrôler.",
                ],
            },
        ],
        related=[
            {"label": "Comprendre la source des prix", "url": "/guides/sources-prix-carburants"},
            {"label": "Décoder un tarif de recharge", "url": "/guides/tarifs-recharge-electrique"},
        ],
    ),
    "guide_tarifs_irve": guide(
        "guides/tarifs-recharge-electrique",
        "Tarifs de recharge électrique : kWh, minute et session | OptiPlein",
        "Guide pour comprendre le prix au kWh, les frais de session, la facturation à la minute, l’occupation et les abonnements aux bornes électriques.",
        "Guide recharge électrique",
        "Lire un tarif de recharge sans se tromper",
        "Le montant final d’une recharge peut combiner plusieurs lignes tarifaires. Un simple nombre en €/kWh ne suffit pas toujours à comparer deux bornes.",
        [
            {
                "title": "Prix au kWh",
                "paragraphs": [
                    "La facturation au kilowattheure mesure l’énergie délivrée. Une recharge de 30 kWh à 0,45 €/kWh coûte 13,50 € avant les autres frais. C’est l’unité la plus directement comparable entre réseaux lorsque les conditions sont identiques.",
                    "La quantité reçue par la batterie peut être légèrement inférieure à l’énergie mesurée au point de charge en raison des pertes. Le tarif applicable reste celui défini par l’opérateur ou le fournisseur de mobilité utilisé pour lancer la session.",
                ],
            },
            {
                "title": "Frais de démarrage ou de session",
                "paragraphs": [
                    "Certains tarifs ajoutent un montant fixe à chaque recharge. Avec 1 € de lancement et 10 kWh à 0,40 €/kWh, le total atteint 5 €, soit un coût effectif de 0,50 €/kWh. Plus la session est petite, plus le frais fixe pèse dans le prix moyen.",
                    "OptiPlein conserve le texte des conditions lorsqu’il est publié. Une station n’est classée sur son seul prix au kWh que si cette valeur est suffisamment claire ; le coût final peut rester supérieur à cause d’un frais fixe.",
                ],
            },
            {
                "title": "Facturation à la minute",
                "paragraphs": [
                    "Un prix à la minute dépend de la durée de connexion, donc de la puissance réellement acceptée par la voiture, de la température et du niveau de batterie. Une borne rapide n’assure pas que le véhicule maintiendra sa puissance maximale pendant toute la session.",
                    "Exemple : 30 minutes à 0,20 €/min coûtent 6 €. Sans connaître l’énergie délivrée, ce montant ne peut pas être transformé honnêtement en €/kWh. C’est pourquoi OptiPlein refuse d’inventer un prix énergétique à partir d’un tarif uniquement temporel.",
                ],
            },
            {
                "title": "Frais d’occupation après la charge",
                "paragraphs": [
                    "Une pénalité peut commencer lorsque la batterie est chargée ou après une durée de grâce. Elle vise à libérer la place. Elle peut être exprimée à la minute ou à l’heure et parfois varier selon l’horaire.",
                    "Ces frais ne représentent pas le prix de l’énergie. Avant de quitter le véhicule, il faut consulter les conditions affichées sur la borne ou dans l’application utilisée et activer les notifications de fin de charge lorsqu’elles existent.",
                ],
            },
            {
                "title": "Paiement direct et abonnement",
                "paragraphs": [
                    "Une même borne peut afficher un tarif direct par carte bancaire, un tarif via QR code et plusieurs tarifs proposés par des fournisseurs de mobilité. La carte d’abonnement peut réduire certains prix mais ajouter un abonnement mensuel ou des frais d’itinérance.",
                    "Le prix transmis par un opérateur n’est donc pas automatiquement celui que chaque conducteur paiera. Une comparaison fiable doit préciser le moyen de paiement et éviter de présenter un tarif réservé aux abonnés comme un prix universel.",
                ],
            },
            {
                "title": "Tarifs variables selon la puissance ou l’heure",
                "paragraphs": [
                    "Certains réseaux distinguent charge normale, rapide et très rapide. D’autres appliquent des plages horaires ou des tarifs locaux. Si plusieurs prix au kWh sont associés à une même station sans règle exploitable, OptiPlein indique « tarif variable ou non exploitable ».",
                    "Choisir arbitrairement le prix minimum rendrait le classement trompeur. Le prix minimum pourrait concerner une puissance non compatible, un abonnement ou une heure différente de celle du trajet.",
                ],
            },
            {
                "title": "Pourquoi « Tarif N/C » apparaît ?",
                "paragraphs": [
                    "N/C signifie non communiqué. La base nationale décrit très bien de nombreuses caractéristiques techniques, mais le champ tarifaire peut être vide, libre ou renvoyer vers une application. Le fichier dynamique décrit surtout l’état et l’occupation, pas le montant payé.",
                    "OptiPlein a supprimé l’ancien prix générique de 0,39 €/kWh, car une estimation identique pour des milliers de bornes pouvait désigner une fausse « moins chère ». Une donnée absente est désormais assumée comme telle.",
                ],
            },
            {
                "title": "Liste de vérification avant de charger",
                "paragraphs": [
                    "Vérifier le connecteur, la puissance acceptée par la voiture, le prix au kWh, les frais fixes, le prix à la minute, la pénalité d’occupation et le moyen de paiement. Regarder également si le prix est TTC et si une préautorisation bancaire est demandée.",
                    "Le tarif affiché sur la borne ou dans le parcours de paiement au moment de la session reste la référence pratique. En cas d’écart, conserver une capture ou un reçu permet de faire un signalement précis.",
                ],
            },
        ],
        sources=[
            {"label": "Base nationale IRVE", "url": "https://transport.data.gouv.fr/datasets/base-nationale-des-lieux-de-recharge-de-vehicules-electriques"},
            {"label": "Règlement européen AFIR", "url": "https://eur-lex.europa.eu/eli/reg/2023/1804/oj"},
        ],
        related=[
            {"label": "Comprendre les états des bornes", "url": "/guides/disponibilite-bornes-irve"},
            {"label": "Méthode de calcul électrique", "url": "/guides/calcul-station-rentable"},
        ],
    ),
    "guide_disponibilite": guide(
        "guides/disponibilite-bornes-irve",
        "Borne disponible, occupée ou hors service : guide IRVE | OptiPlein",
        "Comprendre les couleurs vert, orange, rouge et gris utilisées par OptiPlein pour afficher l’état dynamique des bornes de recharge.",
        "Disponibilité IRVE",
        "Que signifient les couleurs des bornes ?",
        "La disponibilité est une photographie récente, pas une réservation. OptiPlein résume l’état de plusieurs points de charge sans masquer les informations manquantes.",
        [
            {
                "title": "Une station peut contenir plusieurs points",
                "paragraphs": [
                    "Une station IRVE regroupe souvent plusieurs points de charge. Chaque point peut avoir son connecteur, sa puissance, son état de service et son occupation. Le marqueur de la station doit résumer cette pluralité en une couleur lisible.",
                    "OptiPlein regroupe les points grâce à l’identifiant de station, puis compte les points disponibles, occupés, hors service ou inconnus. Le détail indique le nombre de points et les prises déclarées lorsque l’information existe.",
                ],
            },
            {
                "title": "Vert : au moins un point disponible",
                "paragraphs": [
                    "Le vert signifie qu’au moins un point est déclaré en service et libre. Cela ne garantit pas que le connecteur convient au véhicule, que la puissance souhaitée est disponible ou que la place restera libre jusqu’à l’arrivée.",
                    "Avant de se déplacer, vérifier les prises et la puissance. Une station peut être verte grâce à une prise Type 2 alors que le conducteur recherche exclusivement un connecteur Combo CCS rapide.",
                ],
            },
            {
                "title": "Orange : points occupés",
                "paragraphs": [
                    "L’orange indique qu’aucun point libre n’est identifié mais qu’au moins un point en service est déclaré occupé. Une session peut se terminer rapidement ou durer longtemps ; la donnée nationale ne fournit pas toujours une heure de libération prévisionnelle.",
                    "Le filtre « bornes disponibles uniquement » masque ces stations sur la carte, mais il n’efface pas les données reçues. En décochant le filtre, l’utilisateur peut de nouveau consulter les stations occupées.",
                ],
            },
            {
                "title": "Rouge : hors service",
                "paragraphs": [
                    "Le rouge correspond à une station dont les points connus sont déclarés hors service, sans point libre ou occupé utilisable. Une maintenance, une panne ou une indisponibilité de communication peut en être la cause.",
                    "Il reste prudent de consulter l’application de l’opérateur lorsqu’un déplacement important est prévu. L’opérateur peut disposer d’une information plus récente ou plus détaillée que le flux agrégé.",
                ],
            },
            {
                "title": "Gris : information indisponible",
                "paragraphs": [
                    "Le gris ne signifie ni libre ni en panne. Il indique simplement qu’OptiPlein ne dispose pas d’un état dynamique suffisamment clair. La borne peut fonctionner normalement tout en ne publiant pas son occupation dans le flux national.",
                    "Présenter le gris comme du vert créerait de faux espoirs ; le présenter comme du rouge écarterait des bornes utilisables. La neutralité est donc le choix le plus honnête.",
                ],
            },
            {
                "title": "Priorité utilisée pour une station mixte",
                "paragraphs": [
                    "Lorsqu’une station contient plusieurs états, la priorité visuelle est : disponible, puis occupée, puis hors service, puis inconnue. Ainsi, une station avec un point libre et deux points occupés reste verte, car une possibilité de recharge immédiate existe.",
                    "Cette priorité sert uniquement à la lecture rapide. Le détail de la fiche demeure nécessaire pour connaître le nombre de points dans chaque situation.",
                ],
            },
            {
                "title": "Actualisation et décalage possible",
                "paragraphs": [
                    "Le fichier dynamique est récupéré régulièrement et chaque état possède idéalement un horodatage. Entre la borne, l’opérateur, l’agrégateur national et OptiPlein, quelques minutes de décalage peuvent exister.",
                    "Une perte de réseau peut également laisser un état ancien. OptiPlein conserve la dernière copie valide si un téléchargement échoue, mais ne peut pas transformer cette continuité technique en garantie de disponibilité physique.",
                ],
            },
            {
                "title": "Bon réflexe avant un long détour",
                "paragraphs": [
                    "Pour un trajet nécessitant impérativement une recharge, prévoir une solution de repli et éviter d’arriver avec une autonomie nulle. Comparer plusieurs stations proches du parcours réduit le risque lié à une place occupée, une puissance réduite ou un moyen de paiement indisponible.",
                ],
            },
        ],
        sources=[
            {"label": "Schéma national des données IRVE dynamiques", "url": "https://schema.data.gouv.fr/etalab/schema-irve-dynamique/latest.html"},
            {"label": "Base nationale IRVE", "url": "https://transport.data.gouv.fr/datasets/base-nationale-des-lieux-de-recharge-de-vehicules-electriques"},
        ],
        related=[
            {"label": "Comprendre les tarifs", "url": "/guides/tarifs-recharge-electrique"},
            {"label": "Signaler une borne incorrecte", "url": "/guides/signaler-erreur-station"},
        ],
    ),
    "guide_signalement": guide(
        "guides/signaler-erreur-station",
        "Signaler un prix ou une position incorrecte | OptiPlein",
        "Procédure OptiPlein pour signaler un prix, une enseigne, une adresse, une coordonnée ou un état de borne incorrect.",
        "Qualité des données",
        "Comment signaler une information incorrecte",
        "Un bon signalement doit permettre de retrouver la station et de vérifier l’écart. Quelques éléments précis valent mieux qu’un long message sans identifiant ni emplacement.",
        [
            {
                "title": "Ce qui peut être signalé",
                "paragraphs": [
                    "Le signalement peut concerner un prix différent de celui affiché, une station fermée, une enseigne incorrecte, une adresse imprécise, un marqueur mal placé, une borne absente, un connecteur erroné ou un état dynamique incohérent.",
                    "Un tarif électrique peut aussi être signalé lorsqu’il manque des frais de session, une condition d’abonnement ou une pénalité d’occupation. L’objectif est de corriger la description, pas de publier une donnée impossible à confirmer.",
                ],
            },
            {
                "title": "Identifier précisément la station",
                "paragraphs": [
                    "Indiquer l’enseigne, la commune, l’adresse et, si possible, l’identifiant visible dans la fiche. Une capture de la carte avec le marqueur sélectionné facilite la recherche. Pour une borne, le nom de l’opérateur et l’identifiant EVSE sont particulièrement utiles.",
                    "Si le problème concerne la position, préciser si le marqueur désigne la mauvaise rue, le mauvais côté d’une autoroute ou seulement une entrée de parking différente. La précision attendue n’est pas la même selon le cas.",
                ],
            },
            {
                "title": "Documenter un prix",
                "paragraphs": [
                    "Pour un carburant, indiquer le produit exact, le prix observé et la date avec l’heure approximative. Une photo du panneau peut aider si elle est prise à l’arrêt et sans personne identifiable.",
                    "Pour une recharge, préciser le moyen de paiement, le prix au kWh, les frais fixes ou temporels et la puissance concernée. Une capture du récapitulatif tarifaire ou un reçu anonymisé est plus utile qu’un montant final sans quantité d’énergie.",
                ],
            },
            {
                "title": "Protéger les données personnelles",
                "paragraphs": [
                    "Ne pas transmettre de numéro complet de carte bancaire, mot de passe, plaque d’immatriculation, QR code privé ou reçu contenant une adresse personnelle. Les captures doivent être recadrées ou masquées avant l’envoi.",
                    "OptiPlein a seulement besoin des informations permettant de vérifier la station et l’anomalie. Une photographie prise pendant la conduite ne doit jamais être réalisée.",
                ],
            },
            {
                "title": "Comment le signalement est vérifié",
                "paragraphs": [
                    "Le signalement est comparé à la source officielle, aux informations déjà enregistrées et aux éléments fournis. Une correction manuelle doit conserver la source, la date et l’identifiant de station afin de pouvoir être réévaluée lors d’une prochaine mise à jour.",
                    "Une seule observation ne permet pas toujours de modifier immédiatement un prix national. OptiPlein peut signaler l’incertitude, exclure temporairement une valeur manifestement incohérente ou attendre une nouvelle déclaration officielle.",
                ],
            },
            {
                "title": "Écrire à OptiPlein",
                "paragraphs": [
                    "Le formulaire « Signaler un problème » de l’application constitue le chemin le plus direct. Il est également possible d’écrire à optiplein5@gmail.com en indiquant « Signalement station » dans l’objet, puis la ville et le carburant concernés.",
                    "Un signalement clair peut être résumé ainsi : station, adresse, donnée affichée, donnée observée, date, source de vérification et capture facultative. Cette structure accélère le contrôle.",
                ],
            },
        ],
        sources=[
            {"label": "Flux officiel des prix des carburants", "url": "https://donnees.roulez-eco.fr/opendata/instantane"},
            {"label": "API Adresse – documentation", "url": "https://adresse.data.gouv.fr/api-doc/adresse"},
        ],
        related=[
            {"label": "Comprendre les sources", "url": "/guides/sources-prix-carburants"},
            {"label": "Contacter OptiPlein", "url": "/contact"},
        ],
    ),
}
