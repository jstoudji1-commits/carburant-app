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
            {
                "title": "Consommer moins au quotidien",
                "paragraphs": [
                    "Le guide d’écoconduite réunit les gestes utiles avant le départ, au volant et pendant l’entretien. Il indique aussi les fausses bonnes idées à éviter pour que l’économie ne se fasse jamais au détriment de la sécurité ou de la mécanique.",
                ],
                "links": [
                    {"label": "Découvrir tous les conseils d’écoconduite", "url": "/guides/moins-consommer-carburant"},
                ],
            },
            {
                "title": "Pr\u00e9parer un trajet sans mauvaise surprise",
                "paragraphs": [
                    "Autonomie, d\u00e9tour, horaires, solution de secours et marge de s\u00e9curit\u00e9 : le guide de trajet rassemble une m\u00e9thode simple pour les longs parcours en voiture thermique, hybride ou \u00e9lectrique.",
                ],
                "links": [
                    {"label": "Pr\u00e9parer un trajet carburant ou \u00e9lectrique", "url": "/guides/preparer-trajet-ravitaillement"},
                ],
            },
            {
                "title": "Mieux comprendre la recharge rapide",
                "paragraphs": [
                    "Puissance annonc\u00e9e, puissance accept\u00e9e, courbe de charge, temp\u00e9rature et niveau de batterie expliquent pourquoi une borne de 300 kW ne recharge pas toujours trois fois plus vite qu'une borne de 100 kW.",
                ],
                "links": [
                    {"label": "Lire le guide de la recharge rapide", "url": "/guides/recharge-rapide-puissance"},
                    {"label": "Pr\u00e9server la batterie", "url": "/guides/preserver-batterie-electrique"},
                ],
            },
            {
                "title": "R\u00e9gler la localisation et le rayon",
                "paragraphs": [
                    "Une position impr\u00e9cise ou un rayon trop large peut rendre la carte difficile \u00e0 interpr\u00e9ter. Ce guide explique les autorisations, la pr\u00e9cision GPS, les coordonn\u00e9es des stations et le choix du rayon.",
                ],
                "links": [
                    {"label": "Comprendre le GPS et le rayon", "url": "/guides/gps-rayon-coordonnees"},
                ],
            },
            {
                "title": "D\u00e9crypter un tarif communautaire",
                "paragraphs": [
                    "Une contribution utilisateur doit rester tra\u00e7able. Le guide explique les mentions \u00ab d\u00e9clar\u00e9 \u00bb, \u00ab en attente \u00bb et \u00ab confirm\u00e9 par OptiPlein \u00bb, ainsi que les preuves utiles pour contr\u00f4ler un tarif.",
                ],
                "links": [
                    {"label": "Comprendre les contributions tarifaires", "url": "/guides/contribuer-tarif-recharge"},
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
                "title": "Pourquoi les prix diffèrent-ils entre carburants et stations ?",
                "paragraphs": [
                    "Le panneau TTC additionne le coût du produit, sa transformation, son transport et son stockage, les charges de la station, sa marge commerciale, l’accise sur l’énergie puis la TVA. Le pétrole brut compte, mais il n’explique donc jamais seul le prix final ni son évolution quotidienne.",
                    "Les barèmes d’accise diffèrent fortement selon le produit. L’E85 et le GPLc bénéficient notamment d’une fiscalité plus faible que les essences conventionnelles, tandis que l’E85 incorpore une part importante de bioéthanol. Entre deux stations, le volume vendu, la proximité d’un dépôt, les services, les horaires, le modèle automatique ou autoroutier et la concurrence locale peuvent aussi modifier le prix.",
                    "La TVA est proportionnelle et porte sur une base comprenant l’accise. À l’inverse, l’accise est principalement fixée par quantité. Pour suivre tout le chemin du prix, du brut jusqu’à la pompe, consulter le guide consacré aux sources et à la décomposition des carburants.",
                ],
                "links": [
                    {"label": "Comprendre la décomposition complète du prix", "url": "/guides/sources-prix-carburants"},
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
        updated="12 août 2026",
        updated_iso="2026-08-12",
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
                "title": "De quoi se compose un prix à la pompe ?",
                "paragraphs": [
                    "Le prix TTC payé par l’automobiliste peut être lu comme l’addition de plusieurs étages : coût du carburant avant taxes, coûts et marges de raffinage, transport et distribution, accise sur l’énergie — encore souvent appelée TICPE — puis TVA. Ces postes n’évoluent pas tous de la même manière ni au même moment.",
                    "Une présentation simplifiée consiste à écrire : prix TTC = (produit hors taxes + raffinage et logistique + distribution + accise) + TVA. Cette formule aide à comprendre le mécanisme, mais elle ne permet pas de reconstituer exactement la comptabilité d’une station à partir du seul panneau de prix.",
                ],
                "bullets": [
                    "Matière première ou composant énergétique : pétrole brut, produits pétroliers raffinés, éthanol, biocomposants ou GPL selon le carburant.",
                    "Transformation : raffinage, mélange des composants et respect des spécifications saisonnières et réglementaires.",
                    "Logistique : importation éventuelle, transport maritime ou par oléoduc, dépôts, stockage stratégique et livraison aux stations.",
                    "Distribution : exploitation de la station, personnel, énergie, maintenance, moyens de paiement, loyers et marge commerciale.",
                    "Fiscalité : accise fixe par quantité et TVA proportionnelle appliquée au prix hors TVA, accise comprise.",
                ],
            },
            {
                "title": "La matière première et le taux de change",
                "paragraphs": [
                    "Pour l’essence et le gazole, le pétrole brut reste un déterminant important, mais un litre de brut n’est pas un litre directement vendu à la pompe. Le brut doit être transporté, raffiné puis transformé en différents produits. Sa qualité, son origine, les coûts maritimes et la disponibilité mondiale influencent son prix.",
                    "Le pétrole et de nombreux produits raffinés s’échangent en dollars. Une hausse du baril peut être partiellement compensée par un euro plus fort ; inversement, un euro plus faible renchérit l’achat en euros même si le cours en dollars varie peu. C’est pourquoi le panneau de la station ne suit pas mécaniquement le Brent au jour le jour.",
                    "L’E85 incorpore une forte proportion de bioéthanol, variable selon la saison, et le GPLc provient de filières liées au raffinage du pétrole et au traitement du gaz naturel. Leurs coûts de matière première et leur fiscalité ne sont donc pas identiques à ceux du SP95 ou du gazole.",
                ],
            },
            {
                "title": "Raffinage, mélange et saisonnalité",
                "paragraphs": [
                    "La marge de raffinage rémunère la transformation du brut en essence, gazole, kérosène, GPL et autres produits. Elle dépend de l’équilibre entre l’offre des raffineries et la demande pour chaque produit. Une maintenance, une panne, une tension sur les stocks ou une forte demande de gazole peut faire évoluer le prix du produit raffiné indépendamment du baril.",
                    "Les carburants doivent respecter des caractéristiques techniques précises. Les formulations peuvent changer selon la saison, notamment pour le comportement au froid ou la volatilité. Des biocomposants sont incorporés selon les produits : jusqu’à 10 % d’éthanol pour le SP95-E10, tandis que la proportion d’éthanol de l’E85 varie davantage. Ces mélanges ont leur propre coût.",
                    "La “marge de raffinage” n’est pas automatiquement le bénéfice net d’un raffineur. Elle doit aussi couvrir énergie, personnel, maintenance, investissements, arrêts techniques, conformité environnementale et risques industriels.",
                ],
            },
            {
                "title": "Transport, stockage et sécurité d’approvisionnement",
                "paragraphs": [
                    "Après raffinage ou importation, le carburant passe par des terminaux et dépôts avant d’être livré. Il peut voyager par navire, oléoduc, train ou camion-citerne. La distance, le volume livré, l’accès au dépôt et le coût de l’énergie expliquent une partie des écarts géographiques.",
                    "Le stockage représente également un coût : installations classées, contrôles de qualité, sécurité incendie, assurance, immobilisation financière des stocks et obligations de stocks stratégiques. Une petite station livrée en faibles volumes n’a pas nécessairement les mêmes coûts unitaires qu’un hypermarché à fort débit proche d’un dépôt.",
                    "Sur autoroute, les contraintes d’exploitation, les redevances et un environnement concurrentiel différent peuvent contribuer à un prix supérieur. À l’inverse, certaines grandes surfaces utilisent le carburant comme produit d’appel et acceptent une marge de distribution très faible pendant certaines périodes.",
                ],
            },
            {
                "title": "Marge de distribution : ce qu’elle finance réellement",
                "paragraphs": [
                    "La marge brute de transport-distribution est l’écart entre le prix hors taxes de vente et le coût d’approvisionnement du produit. Elle ne correspond pas au bénéfice net conservé par la station. Elle finance la livraison, le stockage local, les pertes techniques, les contrôles, le terminal de paiement, les commissions bancaires, les salaires, le nettoyage, la maintenance et l’investissement.",
                    "Les modèles économiques diffèrent fortement. Une station automatique de grande surface à gros volume, une station indépendante avec boutique et une aire d’autoroute ouverte en permanence n’ont ni les mêmes charges ni les mêmes services. Deux stations achetant un produit proche peuvent donc afficher des prix différents sans qu’un seul poste explique tout l’écart.",
                    "Une remise fidélité, une opération à prix coûtant ou un coupon réduit temporairement le montant payé, mais ne modifie pas nécessairement le prix officiel déclaré de la même façon. OptiPlein doit distinguer le prix accessible à tous des avantages soumis à une carte, un compte ou une durée limitée.",
                ],
            },
            {
                "title": "Accise et TVA : deux mécanismes différents",
                "paragraphs": [
                    "L’accise sur les produits énergétiques, historiquement appelée TICPE pour les carburants pétroliers, est principalement calculée sur la quantité vendue. Elle représente donc un montant par litre, hectolitre, kilogramme ou unité énergétique selon le produit. À barème inchangé, une hausse du prix du pétrole n’augmente pas automatiquement cette part fixe.",
                    "La TVA est au taux normal et se calcule sur le prix hors TVA comprenant le produit, les coûts, les marges et l’accise. Elle augmente donc lorsque le prix hors TVA augmente. On entend parfois que la TVA est appliquée “sur la taxe” : cela décrit le fait que l’accise fait partie de la base soumise à TVA.",
                    "Exemple purement pédagogique : si produit, raffinage, logistique et distribution représentent 0,80 €/L et l’accise 0,60 €/L, la base hors TVA vaut 1,40 €. Une TVA de 20 % représente alors 0,28 €, pour un prix TTC de 1,68 €/L. Cet exemple n’est pas le prix réel d’un carburant ni le barème d’une région donnée.",
                ],
                "bullets": [
                    "L’accise est largement fixe par quantité : elle amortit en proportion une partie des petites variations du produit brut.",
                    "La TVA est proportionnelle : son montant en centimes augmente lorsque sa base augmente.",
                    "Les barèmes peuvent dépendre du produit, de l’année et de dispositions territoriales ou temporaires.",
                    "Une comparaison sérieuse doit toujours préciser la date, le territoire et l’unité du barème cité.",
                ],
            },
            {
                "title": "Pourquoi l’E85 et le GPLc sont souvent moins chers",
                "paragraphs": [
                    "Le prix inférieur de l’E85 ne vient pas seulement de sa matière première. Son niveau d’accise est nettement inférieur à celui des essences conventionnelles. Le GPLc bénéficie lui aussi d’une fiscalité spécifique. Le Guide 2026 sur la fiscalité des énergies montre des barèmes très différents selon SP95/SP98, E10, gazole, E85 et GPLc.",
                    "Un prix au litre inférieur ne garantit toutefois pas le même coût d’usage. L’E85 peut entraîner une consommation volumique supérieure selon le véhicule et la saison. Le GPLc nécessite un véhicule compatible et sa consommation en litres peut différer de celle à l’essence. Il faut comparer coût pour 100 km, compatibilité et usage réel, pas uniquement les centimes au litre.",
                    "OptiPlein conserve donc chaque carburant dans une catégorie séparée. Il ne transforme pas artificiellement un prix E85 en équivalent SP95 et ne recommande jamais un produit incompatible avec le véhicule.",
                ],
            },
            {
                "title": "Pourquoi les baisses et hausses arrivent avec un décalage",
                "paragraphs": [
                    "Une station ne remplit pas nécessairement ses cuves chaque jour. Le carburant vendu aujourd’hui peut avoir été acheté à un prix antérieur. Les contrats d’approvisionnement, rotations de stocks et dates de livraison créent un délai entre marchés de gros et prix de détail.",
                    "La concurrence locale joue aussi : une station peut ajuster rapidement son prix face à un concurrent, attendre une prochaine livraison ou lancer une opération commerciale. Les hausses et les baisses ne se transmettent donc ni instantanément ni de manière uniforme dans toutes les communes.",
                    "Enfin, le fichier public reflète les déclarations des points de vente. La date de téléchargement d’OptiPlein ne signifie pas que chaque prix vient d’être modifié. La date de déclaration de la station et le panneau sur place restent indispensables pour évaluer la fraîcheur réelle.",
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
            {"label": "Ministère de la Transition écologique – chaîne pétrolière", "url": "https://www.ecologie.gouv.fr/politiques-publiques/chaine-petroliere"},
            {"label": "Ministère de la Transition écologique – Guide 2026 sur la fiscalité des énergies", "url": "https://www.ecologie.gouv.fr/sites/default/files/documents/Guide%202026%20sur%20fiscalit%C3%A9%20des%20%C3%A9nergies.pdf"},
            {"label": "Ministère de l’Économie – prix, marges et consommation de carburants", "url": "https://www.economie.gouv.fr/files/rapport-prix-marges-consommation-carburants.pdf"},
            {"label": "Base nationale IRVE", "url": "https://transport.data.gouv.fr/datasets/base-nationale-des-lieux-de-recharge-de-vehicules-electriques"},
            {"label": "Licence Ouverte Etalab 2.0", "url": "https://www.etalab.gouv.fr/licence-ouverte-open-licence/"},
        ],
        related=[
            {"label": "Les six carburants expliqués", "url": "/guides/carburants-disponibles"},
            {"label": "Signaler une information incorrecte", "url": "/guides/signaler-erreur-station"},
            {"label": "Réduire sa consommation de carburant", "url": "/guides/moins-consommer-carburant"},
        ],
        updated="12 août 2026",
        updated_iso="2026-08-12",
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
    "guide_ecoconduite": guide(
        "guides/moins-consommer-carburant",
        "Comment consommer moins de carburant : guide complet | OptiPlein",
        "Plus de 70 conseils pratiques et sûrs pour réduire sa consommation de carburant grâce à l’écoconduite, l’entretien et une meilleure préparation des trajets.",
        "Guide pratique d’écoconduite",
        "Comment consommer moins de carburant",
        "Il n’existe pas de geste magique : les économies viennent d’une somme de bonnes habitudes. Ce guide rassemble les actions les plus utiles, des plus simples aux plus techniques, sans jamais sacrifier la sécurité.",
        [
            {
                "title": "1. Réduire les kilomètres inutiles",
                "paragraphs": [
                    "Le litre le moins cher reste celui qui n’est pas consommé. Avant d’optimiser la conduite, vérifier si le déplacement, l’horaire ou l’itinéraire peuvent être adaptés. Un trajet légèrement plus court ou plus fluide vaut souvent davantage qu’une technique de conduite complexe.",
                ],
                "bullets": [
                    "Regrouper plusieurs courses dans une même sortie plutôt que multiplier les démarrages à froid.",
                    "Préparer l’itinéraire avant de partir pour éviter les erreurs, demi-tours et recherches de station.",
                    "Décaler le départ hors des heures de pointe lorsque l’emploi du temps le permet.",
                    "Comparer la durée et la distance : le parcours le plus rapide n’est pas toujours le plus court ni le moins énergivore.",
                    "Éviter un détour vers une station moins chère lorsque le carburant consommé annule la remise.",
                    "Privilégier la marche, le vélo ou les transports collectifs pour les petits trajets adaptés.",
                    "Partager le véhicule par covoiturage : la consommation de la voiture varie peu, mais elle est répartie entre davantage de voyageurs.",
                    "Téléphoner ou vérifier les horaires avant un déplacement incertain afin d’éviter un aller-retour inutile.",
                ],
            },
            {
                "title": "2. Préparer la voiture avant le départ",
                "paragraphs": [
                    "La résistance au roulement, la masse et l’aérodynamique influencent directement l’effort demandé au moteur. Quelques contrôles rapides évitent une surconsommation permanente et améliorent également la sécurité.",
                ],
                "bullets": [
                    "Contrôler la pression des pneus à froid au moins une fois par mois et avant un long trajet.",
                    "Utiliser la pression recommandée par le constructeur, y compris la valeur prévue pour un véhicule très chargé.",
                    "Ne jamais surgonfler au-delà des préconisations pour chercher une économie : l’adhérence et l’usure peuvent se dégrader.",
                    "Retirer coffre de toit, galerie, porte-skis ou porte-vélos dès qu’ils ne servent plus.",
                    "Vider les objets lourds transportés sans nécessité, tout en conservant les équipements de sécurité obligatoires ou utiles.",
                    "Répartir correctement la charge et respecter les limites de masse du véhicule.",
                    "Fermer complètement le coffre et vérifier qu’aucun élément extérieur ne flotte au vent.",
                    "Nettoyer suffisamment pare-brise, vitres, phares et caméras : économiser ne justifie jamais une visibilité réduite.",
                ],
            },
            {
                "title": "3. Démarrer sans faire chauffer inutilement",
                "paragraphs": [
                    "Un moteur froid consomme davantage. Sur la plupart des véhicules modernes, il est préférable de démarrer puis de rouler doucement plutôt que de laisser chauffer longtemps à l’arrêt. Le manuel du constructeur reste la référence.",
                ],
                "bullets": [
                    "Mettre la ceinture, régler le GPS et préparer l’habitacle avant de démarrer le moteur lorsque c’est possible.",
                    "Après le démarrage, partir calmement sans accélération forte pendant les premiers kilomètres.",
                    "Ne pas faire monter le régime à vide pour accélérer la chauffe.",
                    "Dégivrer et désembuer complètement avant de rouler ; la sécurité prime sur la consommation.",
                    "Éviter d’enchaîner plusieurs très courts déplacements avec refroidissement complet du moteur entre chacun.",
                    "Sur diesel, respecter les recommandations liées au filtre à particules et ne pas interrompre volontairement une régénération signalée.",
                ],
            },
            {
                "title": "4. Accélérer et changer de rapport avec souplesse",
                "paragraphs": [
                    "Les accélérations brutales injectent beaucoup d’énergie qui sera souvent dissipée au freinage suivant. L’objectif n’est pas d’accélérer dangereusement lentement, mais d’atteindre la vitesse utile de façon progressive et adaptée au trafic.",
                ],
                "bullets": [
                    "Appuyer progressivement sur l’accélérateur et éviter les départs pied au plancher.",
                    "Passer les rapports sans pousser inutilement le moteur dans les hauts régimes.",
                    "Suivre l’indicateur de changement de rapport lorsqu’il reste compatible avec la circulation et la pente.",
                    "Ne pas rouler en sous-régime avec vibrations ou manque de reprise : rétrograder si le moteur peine.",
                    "Sur boîte automatique, limiter les demandes brusques qui déclenchent inutilement le kick-down.",
                    "Utiliser le mode Éco s’il convient au trajet, tout en gardant la possibilité d’accélérer franchement lorsqu’une situation de sécurité l’exige.",
                    "Après l’accélération, stabiliser rapidement la vitesse au lieu de continuer à gagner puis perdre quelques kilomètres-heure.",
                ],
            },
            {
                "title": "5. Anticiper pour moins freiner",
                "paragraphs": [
                    "L’anticipation est le cœur de l’écoconduite. Toute vitesse gagnée puis supprimée par les freins correspond à de l’énergie perdue, sauf récupération partielle sur certains hybrides. Une distance de sécurité généreuse permet de lever le pied plus tôt.",
                ],
                "bullets": [
                    "Regarder loin devant pour détecter feu rouge, bouchon, rond-point, limitation ou véhicule lent.",
                    "Conserver une distance de sécurité suffisante afin d’éviter les freinages en cascade.",
                    "Lever l’accélérateur tôt lorsque le ralentissement est certain.",
                    "Rester en prise et utiliser le frein moteur selon les recommandations du véhicule.",
                    "Ne pas descendre une pente au point mort : le contrôle du véhicule diminue et l’économie n’est pas garantie.",
                    "Laisser repartir doucement la circulation plutôt que d’alterner accélérateur et frein dans un bouchon.",
                    "Adapter l’allure avant un virage pour limiter le freinage tardif puis la réaccélération.",
                    "Ne jamais franchir un feu ou une priorité pour éviter de freiner : le Code de la route reste absolu.",
                ],
            },
            {
                "title": "6. Stabiliser et modérer la vitesse",
                "paragraphs": [
                    "À vitesse élevée, la résistance de l’air augmente fortement. L’ADEME indique qu’une réduction de 10 km/h sur autoroute peut économiser entre 1 et 3 litres sur 500 km selon le véhicule, avec un temps de parcours un peu plus long.",
                ],
                "bullets": [
                    "Réduire volontairement l’allure sur autoroute lorsque les conditions et le temps disponible le permettent.",
                    "Respecter les limitations : dépasser la vitesse autorisée augmente à la fois risque, consommation et sanctions.",
                    "Éviter les oscillations permanentes autour de la vitesse choisie.",
                    "Utiliser le régulateur sur terrain régulier et circulation fluide s’il aide à stabiliser l’allure.",
                    "Désactiver ou reprendre la main si le régulateur accélère trop fortement dans une côte ou devient inadapté au trafic.",
                    "Employer le limiteur lorsque cela aide à éviter les accélérations involontaires.",
                    "Accepter une légère baisse de vitesse en montée plutôt que maintenir coûte que coûte une allure élevée, sans gêner dangereusement les autres.",
                    "Rester cohérent avec le flux de circulation : rouler anormalement lentement peut créer un danger et des dépassements.",
                ],
            },
            {
                "title": "7. Gérer arrêts, bouchons et ville",
                "paragraphs": [
                    "La conduite urbaine cumule démarrages, moteur froid et temps au ralenti. La meilleure stratégie consiste à fluidifier le trajet et à couper le moteur lors des attentes réellement prolongées, si le véhicule et la situation le permettent.",
                ],
                "bullets": [
                    "Utiliser le système Stop & Start lorsqu’il fonctionne normalement et que son usage n’est pas déconseillé par le constructeur.",
                    "Couper le moteur pendant une attente prolongée à l’arrêt complet ; l’ADEME indique qu’au-delà d’environ dix secondes, le ralenti peut consommer davantage qu’un redémarrage moderne.",
                    "Ne jamais couper le moteur pendant que le véhicule roule.",
                    "Éviter les longues attentes moteur tournant devant une école, un commerce ou une gare.",
                    "Laisser un espace permettant d’avancer par petites phases fluides dans les embouteillages.",
                    "Choisir une place accessible plutôt que tourner longtemps pour chercher la place la plus proche.",
                    "Respecter les zones à faibles émissions, plans de circulation et voies réservées sans improviser de raccourci interdit.",
                ],
            },
            {
                "title": "8. Utiliser chauffage, climatisation et équipements avec mesure",
                "paragraphs": [
                    "Le confort et la visibilité restent essentiels. Il s’agit de limiter les usages excessifs, pas de conduire dans un habitacle dangereux. L’ADEME estime que la climatisation peut augmenter la consommation selon le climat, le véhicule et l’usage.",
                ],
                "bullets": [
                    "À l’arrêt, ouvrir brièvement les portes ou fenêtres d’un véhicule très chaud avant d’activer la climatisation.",
                    "Choisir une température raisonnable plutôt qu’un écart extrême avec l’extérieur.",
                    "Utiliser le recyclage d’air pendant la phase de refroidissement lorsque le manuel le recommande, puis renouveler l’air si nécessaire.",
                    "À basse vitesse, une ouverture modérée des vitres peut suffire ; à vitesse élevée, les fenêtres grandes ouvertes dégradent l’aérodynamique.",
                    "Stationner à l’ombre ou utiliser un pare-soleil lorsque c’est possible et autorisé.",
                    "Éteindre dégivrage arrière, sièges chauffants et autres gros consommateurs lorsqu’ils ne sont plus nécessaires.",
                    "Ne jamais réduire le désembuage, l’éclairage ou les essuie-glaces nécessaires à la sécurité.",
                    "Entretenir le circuit de climatisation s’il devient inefficace plutôt que le faire fonctionner constamment au maximum.",
                ],
            },
            {
                "title": "9. Entretenir pour éviter la surconsommation",
                "paragraphs": [
                    "Un défaut mécanique peut augmenter la consommation bien avant la panne. L’entretien doit suivre le carnet du constructeur, avec des pièces, fluides et dimensions compatibles.",
                ],
                "bullets": [
                    "Respecter les échéances de vidange et utiliser la viscosité d’huile homologuée pour le moteur.",
                    "Remplacer les filtres selon le plan d’entretien, sans monter de pièce prétendument économique non homologuée.",
                    "Faire contrôler un voyant moteur, une fumée inhabituelle, une perte de puissance ou une hausse soudaine de consommation.",
                    "Vérifier qu’un frein ne reste pas légèrement serré si une roue chauffe ou si la voiture avance moins librement.",
                    "Faire contrôler le parallélisme si le véhicule tire d’un côté ou si les pneus s’usent irrégulièrement.",
                    "Choisir des pneus adaptés, de bonne dimension et correctement étiquetés, sans sacrifier l’adhérence nécessaire à l’usage.",
                    "Respecter le contrôle technique et corriger les défauts qui influencent moteur, freinage ou pneumatiques.",
                    "Surveiller les niveaux et rechercher la cause d’une fuite au lieu de seulement compléter le fluide.",
                    "Conserver à jour les logiciels du véhicule lorsque le constructeur publie une correction pertinente.",
                ],
            },
            {
                "title": "10. Adapter la conduite à la météo et au relief",
                "paragraphs": [
                    "Froid, pluie, vent et dénivelé modifient naturellement la consommation. Il faut ajuster ses attentes plutôt que compenser par une conduite risquée.",
                ],
                "bullets": [
                    "Prévoir davantage de carburant en hiver ou lors d’un trajet très montagneux.",
                    "Réduire l’allure sous la pluie : cela améliore la sécurité et limite l’effort nécessaire pour évacuer l’eau.",
                    "Anticiper un fort vent de face et éviter de chercher à maintenir une vitesse élevée à tout prix.",
                    "Utiliser le rapport adapté en montée sans faire peiner ni hurler le moteur.",
                    "Descendre en prise avec un rapport permettant de contrôler la vitesse sans échauffer les freins.",
                    "Ne jamais suivre un poids lourd de près pour profiter de son aspiration : c’est extrêmement dangereux.",
                    "Déneiger correctement le véhicule avant le départ, sans laisser une masse ou des plaques susceptibles de tomber.",
                    "Avec une remorque, vérifier pression, charge, attelage et vitesse ; la hausse de consommation est normale.",
                ],
            },
            {
                "title": "11. Cas des hybrides et technologies récentes",
                "paragraphs": [
                    "Les véhicules hybrides demandent les mêmes bases de conduite souple, mais la récupération d’énergie et le fonctionnement électrique ajoutent quelques leviers. Les indications du tableau de bord et du constructeur priment.",
                ],
                "bullets": [
                    "Freiner progressivement afin de favoriser la récupération lorsque le véhicule le permet, sans allonger dangereusement la distance d’arrêt.",
                    "Éviter d’accélérer fortement puis de compter sur la régénération : une partie de l’énergie est toujours perdue.",
                    "Utiliser le mode électrique là où il est pertinent plutôt que forcer son activation à vitesse ou charge inadaptée.",
                    "Pour un hybride rechargeable, recharger régulièrement selon les recommandations évite de transporter une batterie peu utilisée.",
                    "Programmer le préchauffage ou le préconditionnement lorsque le véhicule est branché si cette fonction existe.",
                    "Ne pas chercher à reproduire une technique trouvée en ligne si elle contredit le manuel ou les alertes du véhicule.",
                ],
            },
            {
                "title": "12. Mesurer les progrès correctement",
                "paragraphs": [
                    "Une seule valeur au tableau de bord peut être trompeuse. Pour savoir si une habitude fonctionne, comparer plusieurs pleins sur des trajets similaires et tenir compte de la météo, de la charge et du trafic.",
                ],
                "bullets": [
                    "Remettre à zéro un compteur de trajet au début d’une période de mesure.",
                    "Calculer ponctuellement la consommation réelle : litres ajoutés divisés par kilomètres parcourus, puis multipliés par 100.",
                    "Comparer des périodes suffisamment longues plutôt qu’un seul trajet favorable.",
                    "Noter température, autoroute, remorque ou coffre de toit pour expliquer les écarts.",
                    "Surveiller une augmentation persistante : elle peut révéler pression insuffisante, entretien nécessaire ou changement d’usage.",
                    "Se fixer un objectif réaliste, par exemple réduire progressivement la moyenne sans augmenter le temps ou le stress de façon excessive.",
                    "Utiliser l’ordinateur de bord comme tendance, tout en sachant qu’il peut différer légèrement du calcul à la pompe.",
                ],
            },
            {
                "title": "13. Fausses bonnes idées et pratiques dangereuses",
                "paragraphs": [
                    "Certaines techniques de « hypermiling » promettent des records mais exposent le conducteur, les autres usagers ou la mécanique. Elles n’ont pas leur place dans une conduite économique responsable.",
                ],
                "bullets": [
                    "Ne pas couper le moteur en roulant : direction, freinage et aides peuvent être affectés.",
                    "Ne pas rouler au point mort dans une descente.",
                    "Ne pas surgonfler les pneus au-delà de la valeur constructeur.",
                    "Ne pas coller un camion ou un autre véhicule pour réduire la résistance de l’air.",
                    "Ne pas franchir un stop, accélérer à l’orange ou négliger une priorité pour conserver son élan.",
                    "Ne pas éteindre les feux, le désembuage ou les essuie-glaces indispensables.",
                    "Ne pas utiliser un carburant différent sans compatibilité explicite du constructeur.",
                    "Ne pas supposer qu’un carburant premium réduit automatiquement la consommation suffisamment pour compenser son prix.",
                    "Ne pas neutraliser un équipement antipollution ou modifier illégalement la gestion moteur.",
                    "Ne pas manipuler le téléphone ou l’application pour surveiller la consommation pendant la conduite.",
                ],
            },
            {
                "title": "14. La checklist simple avant chaque long trajet",
                "paragraphs": [
                    "Pour retenir l’essentiel, cette vérification rapide concentre les gestes ayant le meilleur rapport entre effort, sécurité et économie.",
                ],
                "bullets": [
                    "Trajet et arrêts préparés, circulation vérifiée avant le départ.",
                    "Pneus contrôlés à froid selon la charge prévue.",
                    "Galerie et poids inutiles retirés.",
                    "Carburant compatible et autonomie suffisante.",
                    "Conduite souple, regard loin devant et distances de sécurité respectées.",
                    "Vitesse stable et modérée, sans gêner la circulation.",
                    "Climatisation raisonnable, visibilité toujours parfaite.",
                    "Pause programmée pour rester attentif : la fatigue augmente les erreurs et détruit les bénéfices d’une conduite préparée.",
                ],
            },
        ],
        sources=[
            {"label": "ADEME – L’écoconduite pour consommer moins", "url": "https://agirpourlatransition.ademe.fr/particuliers/economiser/carburant/ecoconduite-solution-consommer-moins-carburant-limiter-emissions-co2"},
            {"label": "Sécurité routière – Écoconduite en voiture", "url": "https://www.securite-routiere.gouv.fr/chacun-son-mode-de-deplacement/dangers-de-la-route-en-voiture/mieux-conduire-en-voiture/eco"},
            {"label": "Ministère de la Transition écologique – gestes efficaces", "url": "https://www.ecologie.gouv.fr/economie-energie-ete"},
            {"label": "Sécurité routière – entretien de la voiture", "url": "https://www.securite-routiere.gouv.fr/chacun-son-mode-de-deplacement/dangers-de-la-route-en-voiture/entretien-de-la-voiture/conseils-pour"},
        ],
        related=[
            {"label": "Calculer la station la plus rentable", "url": "/guides/calcul-station-rentable"},
            {"label": "Comprendre les carburants", "url": "/guides/carburants-disponibles"},
            {"label": "Ouvrir l’application", "url": "/web"},
        ],
        published="10 août 2026",
        updated="10 août 2026",
        published_iso="2026-08-10",
        updated_iso="2026-08-10",
    ),
    "guide_trajet": guide(
        "guides/preparer-trajet-ravitaillement",
        "Pr\u00e9parer un trajet carburant ou \u00e9lectrique | OptiPlein",
        "M\u00e9thode pratique pour choisir ses arr\u00eats, conserver une marge d'autonomie et pr\u00e9voir une solution de secours avant un long trajet.",
        "Guide de voyage",
        "Pr\u00e9parer un trajet sans mauvaise surprise",
        "Un bon arr\u00eat ne se choisit pas uniquement avec le prix le plus bas. Il doit \u00eatre atteignable, ouvert, compatible, raisonnablement proche du parcours et accompagn\u00e9 d'une solution de secours.",
        [
            {
                "title": "Commencer par les besoins du v\u00e9hicule",
                "paragraphs": [
                    "En carburant, relever le produit compatible, la consommation r\u00e9elle sur route et la capacit\u00e9 utile du r\u00e9servoir. En \u00e9lectrique, noter la capacit\u00e9 utile de batterie, la consommation habituelle, le connecteur et les puissances maximales accept\u00e9es en courant alternatif et continu.",
                    "Une valeur issue de votre usage r\u00e9cent est plus utile qu'une homologation id\u00e9ale. Le froid, la pluie, le vent, l'autoroute, le relief, les bagages ou une remorque peuvent augmenter la consommation.",
                ],
                "bullets": [
                    "S\u00e9lectionner le bon v\u00e9hicule dans OptiPlein avant le calcul.",
                    "V\u00e9rifier le carburant ou le connecteur dans le manuel et sur le v\u00e9hicule.",
                    "Pr\u00e9voir une consommation plus prudente si les conditions sont difficiles.",
                    "Ne jamais planifier jusqu'\u00e0 la derni\u00e8re goutte ou au dernier pour cent de batterie.",
                ],
            },
            {
                "title": "Choisir une marge d'autonomie",
                "paragraphs": [
                    "La marge absorbe une sortie manqu\u00e9e, un bouchon, une station ferm\u00e9e ou une borne indisponible. Elle doit augmenter lorsque le secteur est peu dense, la m\u00e9t\u00e9o d\u00e9favorable ou l'itin\u00e9raire difficile.",
                    "En voiture \u00e9lectrique, arriver avec une batterie relativement basse peut favoriser la puissance de charge, mais seulement si une solution de repli reste accessible. La recherche d'une recharge rapide ne doit jamais transformer le trajet en pari.",
                ],
            },
            {
                "title": "Comparer l'arr\u00eat, pas seulement le panneau",
                "paragraphs": [
                    "Pour une station-service, comparer prix, d\u00e9tour, quantit\u00e9 achet\u00e9e et acc\u00e8s. Pour une borne, ajouter le mode de paiement, la puissance r\u00e9ellement utile, la disponibilit\u00e9, les frais de session ou d'occupation et le temps d'arr\u00eat probable.",
                ],
                "bullets": [
                    "V\u00e9rifier que la station se trouve du bon c\u00f4t\u00e9 de l'autoroute ou qu'elle est accessible sans grand d\u00e9tour.",
                    "Ouvrir la fiche pour lire la date et la provenance du prix.",
                    "En recharge, contr\u00f4ler le tarif du moyen de paiement que vous utiliserez vraiment.",
                    "Pr\u00e9f\u00e9rer un site avec plusieurs points de charge lorsqu'une forte affluence est possible.",
                ],
            },
            {
                "title": "Pr\u00e9voir un plan B",
                "paragraphs": [
                    "Identifier au moins une seconde station ou borne avant de partir. Le plan B doit \u00eatre atteignable avec la marge restante, compatible et ouvert. Une capture d'\u00e9cran ne remplace pas une nouvelle v\u00e9rification, car prix et disponibilit\u00e9 peuvent changer.",
                    "Sur un long trajet \u00e9lectrique, mieux vaut conna\u00eetre plusieurs r\u00e9seaux et disposer d'au moins un moyen de paiement alternatif. Le paiement direct par carte bancaire n'est pas disponible partout et son tarif peut diff\u00e9rer d'un badge ou d'un abonnement.",
                ],
            },
            {
                "title": "La checklist juste avant de partir",
                "paragraphs": ["Une derni\u00e8re v\u00e9rification prend deux minutes et limite les mauvaises surprises."],
                "bullets": [
                    "Destination, arr\u00eat principal et solution de secours enregistr\u00e9s.",
                    "Autonomie suffisante pour atteindre le plan B.",
                    "Horaires et accessibilit\u00e9 contr\u00f4l\u00e9s lorsque l'information est disponible.",
                    "Prix et date de mise \u00e0 jour relus.",
                    "Moyen de paiement, badge ou application pr\u00eats pour la recharge.",
                    "T\u00e9l\u00e9phone charg\u00e9 et itin\u00e9raire lanc\u00e9 avant de conduire.",
                ],
            },
        ],
        related=[
            {"label": "Calculer la station rentable", "url": "/guides/calcul-station-rentable"},
            {"label": "Comprendre les tarifs de recharge", "url": "/guides/tarifs-recharge-electrique"},
        ],
        published="18 ao\u00fbt 2026",
        updated="18 ao\u00fbt 2026",
        published_iso="2026-08-18",
        updated_iso="2026-08-18",
    ),
    "guide_recharge_rapide": guide(
        "guides/recharge-rapide-puissance",
        "Recharge rapide : puissance, dur\u00e9e et courbe de charge | OptiPlein",
        "Comprendre la diff\u00e9rence entre puissance de borne, puissance accept\u00e9e et vitesse r\u00e9elle de recharge d'une voiture \u00e9lectrique.",
        "Guide recharge \u00e9lectrique",
        "Pourquoi la puissance affich\u00e9e n'est pas toujours atteinte",
        "Le nombre inscrit sur la borne est une puissance maximale du mat\u00e9riel. La voiture, la batterie et les conditions de la session d\u00e9cident de la puissance r\u00e9ellement re\u00e7ue.",
        [
            {
                "title": "kW et kWh : deux unit\u00e9s diff\u00e9rentes",
                "paragraphs": [
                    "Le kilowatt, not\u00e9 kW, mesure une puissance instantan\u00e9e. Le kilowattheure, not\u00e9 kWh, mesure une quantit\u00e9 d'\u00e9nergie. Une borne peut d\u00e9livrer 100 kW pendant une partie de la session et ajouter, par exemple, 25 kWh en quinze minutes dans des conditions id\u00e9ales.",
                    "Le tarif au kWh facture l'\u00e9nergie. Un tarif \u00e0 la minute facture le temps, m\u00eame lorsque la puissance diminue. Il faut donc lire l'unit\u00e9 avant de comparer deux offres.",
                ],
            },
            {
                "title": "La limite la plus basse s'impose",
                "paragraphs": [
                    "La puissance r\u00e9elle est limit\u00e9e par le maillon le plus faible : borne, c\u00e2ble, architecture du v\u00e9hicule, batterie, partage de puissance du site ou temp\u00e9rature. Brancher une voiture limit\u00e9e \u00e0 80 kW sur une borne de 300 kW ne la fait pas charger \u00e0 300 kW.",
                ],
                "bullets": [
                    "Puissance maximale accept\u00e9e par le mod\u00e8le de voiture.",
                    "Niveau de batterie au d\u00e9but de la session.",
                    "Temp\u00e9rature et pr\u00e9conditionnement de la batterie.",
                    "Puissance partag\u00e9e avec une autre borne du m\u00eame site.",
                    "Limites temporaires du r\u00e9seau ou du mat\u00e9riel.",
                ],
            },
            {
                "title": "La courbe de charge",
                "paragraphs": [
                    "La puissance n'est pas constante. Elle augmente, atteint un plateau puis diminue g\u00e9n\u00e9ralement lorsque la batterie se remplit afin de la prot\u00e9ger. Le pic publicitaire ne suffit donc pas \u00e0 pr\u00e9dire la dur\u00e9e totale ; la courbe moyenne entre le niveau de d\u00e9part et le niveau vis\u00e9 est plus repr\u00e9sentative.",
                    "Lors d'un trajet, plusieurs arr\u00eats courts dans la plage rapide du v\u00e9hicule peuvent parfois \u00eatre plus efficaces qu'une attente jusqu'\u00e0 100 %. Cette strat\u00e9gie doit rester compatible avec l'autonomie et les solutions de secours.",
                ],
            },
            {
                "title": "Temp\u00e9rature et pr\u00e9conditionnement",
                "paragraphs": [
                    "Une batterie tr\u00e8s froide ou tr\u00e8s chaude peut limiter la puissance. Si le v\u00e9hicule poss\u00e8de un pr\u00e9conditionnement automatique, programmer la borne dans son syst\u00e8me de navigation peut aider \u00e0 placer la batterie dans une plage favorable avant l'arriv\u00e9e.",
                    "Le fonctionnement varie selon les mod\u00e8les. Il faut suivre le manuel et ne pas multiplier des acc\u00e9l\u00e9rations ou manipulations improvis\u00e9es pour chauffer la batterie.",
                ],
            },
            {
                "title": "Choisir une borne coh\u00e9rente",
                "bullets": [
                    "Comparer la puissance de la borne avec celle accept\u00e9e par le v\u00e9hicule.",
                    "Lire le tarif complet et les frais d'occupation apr\u00e8s la charge.",
                    "V\u00e9rifier le connecteur et la pr\u00e9sence d'un c\u00e2ble attach\u00e9 en recharge rapide.",
                    "Pr\u00e9f\u00e9rer le niveau de charge n\u00e9cessaire au prochain arr\u00eat plut\u00f4t qu'un objectif automatique de 100 %.",
                    "Lib\u00e9rer la place une fois la session termin\u00e9e.",
                ],
                "paragraphs": ["La borne la plus puissante n'est donc pas toujours la meilleure : prix, fiabilit\u00e9, emplacement et temps r\u00e9el comptent ensemble."],
            },
        ],
        related=[
            {"label": "Tarifs de recharge", "url": "/guides/tarifs-recharge-electrique"},
            {"label": "Pr\u00e9server la batterie", "url": "/guides/preserver-batterie-electrique"},
        ],
        published="18 ao\u00fbt 2026",
        updated="18 ao\u00fbt 2026",
        published_iso="2026-08-18",
        updated_iso="2026-08-18",
    ),
    "guide_batterie": guide(
        "guides/preserver-batterie-electrique",
        "Pr\u00e9server la batterie d'une voiture \u00e9lectrique | OptiPlein",
        "Conseils prudents sur la recharge quotidienne, la chaleur, le stationnement et les charges rapides pour limiter le vieillissement de la batterie.",
        "Guide batterie",
        "Pr\u00e9server sa batterie sans compliquer chaque trajet",
        "La batterie est con\u00e7ue pour \u00eatre utilis\u00e9e. L'objectif n'est pas d'\u00e9viter toute charge rapide ou tout plein complet, mais d'adopter des habitudes raisonnables compatibles avec les consignes du constructeur.",
        [
            {
                "title": "Le manuel du v\u00e9hicule reste prioritaire",
                "paragraphs": [
                    "Les chimies, syst\u00e8mes de refroidissement et r\u00e9serves cach\u00e9es diff\u00e8rent. Une limite quotidienne pertinente pour un mod\u00e8le peut \u00eatre inutile pour un autre. Utiliser les r\u00e9glages recommand\u00e9s par le constructeur et respecter les campagnes de mise \u00e0 jour.",
                ],
            },
            {
                "title": "Adapter la charge au besoin r\u00e9el",
                "paragraphs": [
                    "Pour les usages quotidiens, programmer une limite laissant une marge suffisante peut \u00e9viter de maintenir la batterie longtemps \u00e0 un niveau tr\u00e8s \u00e9lev\u00e9. Avant un long trajet, charger davantage reste l'usage normal du v\u00e9hicule lorsqu'il est pr\u00e9vu par le constructeur.",
                ],
                "bullets": [
                    "Programmer la fin de charge pr\u00e8s de l'heure de d\u00e9part lorsque la fonction existe.",
                    "Ne pas immobiliser volontairement la voiture plusieurs jours compl\u00e8tement charg\u00e9e ou presque vide sans recommandation adapt\u00e9e.",
                    "Brancher selon les besoins plut\u00f4t que chercher syst\u00e9matiquement une d\u00e9charge profonde.",
                    "Conserver une marge avant d'arriver \u00e0 un niveau critique, surtout par froid.",
                ],
            },
            {
                "title": "Chaleur, froid et stationnement",
                "paragraphs": [
                    "La chaleur acc\u00e9l\u00e8re de nombreux m\u00e9canismes de vieillissement. Lorsque c'est possible, stationner \u00e0 l'ombre ou dans un lieu temp\u00e9r\u00e9 et laisser la gestion thermique fonctionner comme pr\u00e9vu. En hiver, le froid r\u00e9duit temporairement l'autonomie et la puissance sans signifier automatiquement une perte permanente de capacit\u00e9.",
                    "Le pr\u00e9conditionnement de l'habitacle lorsque le v\u00e9hicule est branch\u00e9 peut am\u00e9liorer le confort et pr\u00e9server l'autonomie de d\u00e9part.",
                ],
            },
            {
                "title": "Recharge rapide : utile, mais pas obligatoire au quotidien",
                "paragraphs": [
                    "La recharge rapide est faite pour les trajets et les besoins ponctuels. Une recharge plus lente \u00e0 domicile ou \u00e0 destination peut \u00eatre plus pratique et moins ch\u00e8re lorsqu'elle est disponible. Il n'est toutefois pas n\u00e9cessaire de refuser une charge rapide utile par peur d'endommager imm\u00e9diatement la batterie.",
                ],
            },
            {
                "title": "Surveiller sans s'alarmer",
                "paragraphs": [
                    "L'autonomie affich\u00e9e varie avec la consommation r\u00e9cente, la temp\u00e9rature et le parcours. Elle ne mesure pas directement l'\u00e9tat de sant\u00e9 de la batterie. Une baisse soudaine persistante, un message d'alerte ou une recharge anormalement lente justifie un diagnostic professionnel.",
                ],
                "bullets": [
                    "Comparer sur plusieurs trajets semblables, pas sur une seule journ\u00e9e froide.",
                    "Maintenir les pneus \u00e0 la pression recommand\u00e9e.",
                    "Installer les mises \u00e0 jour officielles utiles.",
                    "Consulter le r\u00e9seau constructeur en cas d'alerte haute tension ou thermique.",
                ],
            },
        ],
        related=[
            {"label": "Comprendre la recharge rapide", "url": "/guides/recharge-rapide-puissance"},
            {"label": "Pr\u00e9parer un trajet", "url": "/guides/preparer-trajet-ravitaillement"},
        ],
        published="18 ao\u00fbt 2026",
        updated="18 ao\u00fbt 2026",
        published_iso="2026-08-18",
        updated_iso="2026-08-18",
    ),
    "guide_gps": guide(
        "guides/gps-rayon-coordonnees",
        "GPS, rayon et coordonn\u00e9es des stations | OptiPlein",
        "Comprendre la localisation du t\u00e9l\u00e9phone, les coordonn\u00e9es ouvertes des stations et le choix du rayon de recherche sur OptiPlein.",
        "Guide carte et localisation",
        "Pourquoi un marqueur ou un itin\u00e9raire peut sembler d\u00e9cal\u00e9",
        "La carte combine la position du t\u00e9l\u00e9phone, les coordonn\u00e9es publi\u00e9es pour la station et le point routier choisi par le service de navigation. Ces trois positions peuvent diff\u00e9rer l\u00e9g\u00e8rement.",
        [
            {
                "title": "Comment le t\u00e9l\u00e9phone estime sa position",
                "paragraphs": [
                    "Le navigateur demande l'autorisation de localisation puis utilise les informations fournies par l'appareil. Le GPS, les r\u00e9seaux Wi-Fi et le r\u00e9seau mobile peuvent contribuer \u00e0 l'estimation. En int\u00e9rieur, dans un parking couvert ou entre de grands immeubles, la pr\u00e9cision peut se d\u00e9grader.",
                ],
                "bullets": [
                    "Autoriser la position pr\u00e9cise pour le site.",
                    "Activer les services de localisation de l'appareil.",
                    "Attendre quelques secondes dans un espace d\u00e9gag\u00e9 si le point est tr\u00e8s impr\u00e9cis.",
                    "Recharger la page ou relancer la localisation apr\u00e8s avoir chang\u00e9 l'autorisation.",
                ],
            },
            {
                "title": "D'o\u00f9 viennent les coordonn\u00e9es des stations",
                "paragraphs": [
                    "Les jeux de donn\u00e9es peuvent placer le point sur la parcelle, le b\u00e2timent, la station ou une entr\u00e9e. Pour les grands parkings, centres commerciaux ou aires d'autoroute, quelques dizaines de m\u00e8tres peuvent s\u00e9parer le marqueur de l'acc\u00e8s r\u00e9el.",
                    "OptiPlein conserve la coordonn\u00e9e source tant qu'aucune correction v\u00e9rifiable n'est disponible. D\u00e9placer automatiquement tous les points vers la route la plus proche risquerait de placer une station du mauvais c\u00f4t\u00e9 d'une voie rapide.",
                ],
            },
            {
                "title": "Pourquoi la navigation choisit un autre point",
                "paragraphs": [
                    "Un moteur d'itin\u00e9raire doit rejoindre une voie praticable. Si le marqueur se trouve au centre d'un parking, il peut choisir l'entr\u00e9e routi\u00e8re la plus proche. Sur une route divis\u00e9e, cette entr\u00e9e peut imposer une boucle pour respecter le sens de circulation.",
                ],
            },
            {
                "title": "Choisir un rayon utile",
                "paragraphs": [
                    "Un petit rayon facilite la lecture et limite les d\u00e9tours. Un rayon plus grand aide dans les zones peu denses ou lorsqu'aucune station compatible n'a de prix. Le r\u00e9sum\u00e9 du prix le plus bas et le calcul doivent uniquement comparer les stations effectivement charg\u00e9es dans le rayon actif.",
                ],
                "bullets": [
                    "Commencer par les stations proches.",
                    "Agrandir progressivement si les r\u00e9sultats sont insuffisants.",
                    "Regarder la distance routi\u00e8re et pas seulement la distance \u00e0 vol d'oiseau.",
                    "Sur autoroute, v\u00e9rifier le sens et l'accessibilit\u00e9 de l'aire.",
                ],
            },
            {
                "title": "Signaler une coordonn\u00e9e incorrecte",
                "paragraphs": [
                    "Indiquer le nom, l'adresse, la coordonn\u00e9e ou l'entr\u00e9e correcte, la date et une preuve publique ou une photo sans donn\u00e9e personnelle. Un lien cartographique peut aider, mais il faut expliquer s'il d\u00e9signe la borne, le parking ou son acc\u00e8s.",
                ],
            },
        ],
        related=[
            {"label": "Signaler une erreur", "url": "/guides/signaler-erreur-station"},
            {"label": "Pr\u00e9parer un trajet", "url": "/guides/preparer-trajet-ravitaillement"},
        ],
        published="18 ao\u00fbt 2026",
        updated="18 ao\u00fbt 2026",
        published_iso="2026-08-18",
        updated_iso="2026-08-18",
    ),
    "guide_contribution_tarif": guide(
        "guides/contribuer-tarif-recharge",
        "D\u00e9clarer et faire valider un tarif de recharge | OptiPlein",
        "Comprendre comment contribuer un prix de recharge, quelles preuves fournir et ce que signifient les statuts de validation OptiPlein.",
        "Guide communautaire",
        "Contribuer un tarif de recharge utile et v\u00e9rifiable",
        "Les tarifs de recharge sont souvent absents des donn\u00e9es ouvertes. Une contribution peut aider imm\u00e9diatement les autres utilisateurs, \u00e0 condition d'indiquer le bon moyen de paiement, la date et les frais associ\u00e9s.",
        [
            {
                "title": "Les informations \u00e0 relever",
                "paragraphs": ["Avant de saisir un prix, identifier exactement le site et lire l'ensemble du bar\u00e8me. Un simple montant sans unit\u00e9 ni condition peut induire en erreur."],
                "bullets": [
                    "R\u00e9seau, nom du site, adresse ou identifiant de la borne.",
                    "Prix au kWh avec taxes comprises si cette pr\u00e9cision est disponible.",
                    "Mode de paiement : carte bancaire, badge, application, carte de fid\u00e9lit\u00e9 ou abonnement.",
                    "Frais fixes de session, facturation \u00e0 la minute ou p\u00e9nalit\u00e9 d'occupation.",
                    "Date d'observation et, si possible, lien officiel, capture ou photographie lisible.",
                ],
            },
            {
                "title": "D\u00e9clar\u00e9, en attente et confirm\u00e9",
                "paragraphs": [
                    "Une valeur saisie par un utilisateur peut \u00eatre affich\u00e9e avec la mention \u00ab d\u00e9clar\u00e9 par \u00bb et sa date. Le statut en attente avertit qu'OptiPlein n'a pas encore contr\u00f4l\u00e9 la preuve ou la coh\u00e9rence du tarif.",
                    "Apr\u00e8s v\u00e9rification, la mention \u00ab confirm\u00e9 par OptiPlein \u00bb et une date peuvent \u00eatre ajout\u00e9es. La confirmation porte sur l'information contr\u00f4l\u00e9e \u00e0 cette date ; elle ne bloque pas les changements commerciaux futurs.",
                ],
            },
            {
                "title": "Saisir plusieurs offres sans les confondre",
                "paragraphs": [
                    "Un r\u00e9seau peut proposer 0,55 \u20ac/kWh par paiement direct, 0,45 \u20ac/kWh avec sa carte et 0,29 \u20ac/kWh avec abonnement. Ces prix doivent rester trois offres distinctes, car l'abonnement ou la carte peuvent avoir un co\u00fbt, des conditions d'acc\u00e8s ou une dur\u00e9e d'engagement.",
                    "Le marqueur peut mettre en avant un tarif de comparaison, tandis que la fiche d\u00e9taille les alternatives sur une ligne courte. L'utilisateur doit pouvoir savoir imm\u00e9diatement quel prix correspond \u00e0 son moyen de paiement.",
                ],
            },
            {
                "title": "Ce qu'il ne faut pas publier",
                "bullets": [
                    "Une estimation personnelle pr\u00e9sent\u00e9e comme un tarif officiel.",
                    "Un prix promotionnel sans date de fin ni condition.",
                    "Une facture contenant nom, plaque, identifiant de compte ou coordonn\u00e9es bancaires.",
                    "Le tarif d'une autre station suppos\u00e9 identique pour tout le r\u00e9seau.",
                    "Un prix hors taxes pr\u00e9sent\u00e9 comme le montant pay\u00e9 par le public.",
                ],
                "paragraphs": ["Les contributions doivent respecter la vie priv\u00e9e et rester factuelles. Une donn\u00e9e douteuse peut \u00eatre rejet\u00e9e ou retir\u00e9e apr\u00e8s signalement."],
            },
            {
                "title": "Quand mettre \u00e0 jour une contribution",
                "paragraphs": [
                    "Contribuer de nouveau lorsqu'un panneau, une application officielle ou une session r\u00e9cente montre un tarif diff\u00e9rent. Ne pas remplacer une offre de fid\u00e9lit\u00e9 par le paiement direct : ajouter ou corriger la bonne cat\u00e9gorie avec sa date.",
                ],
            },
        ],
        related=[
            {"label": "Comprendre tous les tarifs de recharge", "url": "/guides/tarifs-recharge-electrique"},
            {"label": "Signaler une anomalie", "url": "/guides/signaler-erreur-station"},
        ],
        published="18 ao\u00fbt 2026",
        updated="18 ao\u00fbt 2026",
        published_iso="2026-08-18",
        updated_iso="2026-08-18",
    ),
}
