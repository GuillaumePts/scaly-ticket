# Scaly / Pics — contexte de travail

Ce fichier sert de reprise rapide pour un prochain contexte Codex. Le projet actif est le site photographe situé dans :

`scaly-product/pics/`

Le serveur et les données réelles peuvent être servis par une infrastructure située hors de ce sous-dossier. Les fichiers front-end à modifier sont principalement sous `scaly-product/pics/public/`.

## Architecture principale

### Pages et fragments

- `scaly-product/pics/public/views/index.html` : shell principal, header, navigation, `#modal-msg`, chargement des CSS/scripts.
- `scaly-product/pics/public/views/accueil.html` : fragment de la page d’accueil.
- `scaly-product/pics/public/views/contact.html` : formulaire de contact et réseaux sociaux.
- `scaly-product/pics/backoffice.html` : structure du dashboard admin, dont BackTicket et ses modales.

### CSS

- `public/css/style.css` : header, navigation dynamique, `#admin`, boutons globaux et footer.
- `public/css/accueil.css` : blocs profil, news, style et prestations de l’accueil.
- `public/css/forms.css` : formulaires visiteurs : contact, connexion, inscription, réservation et calendrier.
- `public/css/contact.css` : layout de la page contact et image de fond.
- `public/css/back.css` : interface admin, boutons admin, overlays, BackTicket et modales.
- `public/css/portfolio.css`, `client.css`, `lock.css`, `sign.css`, etc. : styles spécialisés.

### JavaScript

- `public/js/app.js` : orchestration SPA, chargement des fragments, designs globaux, navigation et header.
- `public/js/dataLoader.js` : fetch `/getaccueil`, initialise `window.AppData` et `window.design`.
- `public/js/accueil.js` : rendu/animations des quatre blocs de l’accueil.
- `public/js/contact.js` : envoi du formulaire contact et chargement des réseaux.
- `public/js/back.js` : dashboard admin général, réglages globaux, `AdminMenuManager`, sélection des designs.
- `public/js/backAccueil.js` : gestion admin accueil.
- `public/js/backContact.js` : gestion admin contact.
- `public/js/backPortfolio.js` : gestion admin portfolio.
- `public/js/backTicket.js` : gros dashboard de rendez-vous/propositions/livraisons, calendrier et modales.
- `public/js/share.js` : moteur commun des transitions SPA et chargement dynamique du back-office.

## Données et numéros de design

Les données sont stockées dans un `bdd.json` par client côté serveur. La structure de design utilisée est généralement :

```json
{
  "profile": 1,
  "style": 3,
  "news": 3,
  "portfolioCard": 3,
  "presta": 3,
  "head": 4,
  "button": 1,
  "footer": 1,
  "navigation": 1,
  "dashboard": 1
}
```

`dataLoader.js` reçoit cette structure via `/getaccueil` et la place dans `window.design`.

Les classes CSS dynamiques sont basées sur le numéro :

- `body.profile-setup-N`, `body.news-setup-N`, `body.style-setup-N` ou classes équivalentes dans `accueil.js`.
- `body.button-setup-N`.
- `body.footer-setup-N`.
- `body.form-setup-N`.
- `body.navigation-setup-N`.
- `body.admin-setup-N` pour `#admin`, toujours aligné sur la navigation.
- `body.dashboard-setup-N` pour l’interface BackTicket et ses modales.
- `#navigation.navigation-design-N`.
- `#admin.admin-design-N`.

`navigation` et `dashboard` sont deux préférences indépendantes. `navigation` pilote obligatoirement le couple `#navigation + #admin`, qui constitue un seul composant visuel. `dashboard` pilote uniquement l’interface BackTicket et ses modales ; pour les anciennes données, le serveur et `dataLoader.js` reprennent la valeur de `navigation` comme valeur de compatibilité.

Toujours retirer les anciennes classes avant d’ajouter la nouvelle. Ne pas supprimer la logique de fetch, les IDs existants ni les callbacks admin.

## Les cinq familles visuelles

### Design 1 — sobre / monochrome

- Majoritairement `var(--back)` et `var(--color-font)`.
- Contraste noir/blanc, lignes fines, peu d’effets.
- `var(--c-one)` peut servir ponctuellement pour une information importante.
- Formulaires éditoriaux simples et lisibles.
- Navigation pleine largeur, position `top` ou `bottom` selon le réglage utilisateur.
- Boutons admin sobres : fond `var(--color-font)`, bordure `var(--back)`, icônes `var(--c-one)`.

### Design 2 — blobs modernes

- Mélange de blobs nets et flous.
- Répartition cible : environ 40% `--c-one`, 40% thème inversé, 20% `--c-two`.
- Glassmorphisme limité, transparent et peu sombre.
- Les boutons peuvent utiliser `.buttonsvg.premium-glass`, `.electron.cyan`, `.electron.purple` et `.background-button`.
- Éviter les cartes répétées, le blur massif, les overflow qui coupent les blobs et la 3D inutile.
- Certaines maquettes design 2 restent susceptibles d’être retravaillées par l’utilisateur : ne pas réinventer massivement sans demande.

### Design 3 — chromatique / coloré

- Utilise `var(--c-one)` et `var(--c-two)` avec touches néon maîtrisées.
- Style coloré cohérent avec news design 3, footer design 3, boutons design 3 et prestations design 3.
- Animations possibles mais garder la lisibilité et éviter le flou GPU permanent.

### Design 4 — neo-brutaliste professionnel

- Grosses bordures, ombres franches, composition 2D/cartoon maîtrisée.
- Référence visuelle : prestations design 3, footer design 4 et `.button`.
- Utilise principalement `var(--c-one)`, avec `var(--c-two)` plus discret.
- Les grosses shadows et bordures font partie du style : ne pas les supprimer complètement.
- Rester professionnel pour un SaaS destiné aux photographes.

### Design 5 — éditorial / artistique

L’idée holographique/iridium initiale a été abandonnée pour éviter un site trop coloré. Le design 5 actuel est donc éditorial :

- Composition magazine, mode, affiche et direction artistique.
- Environ 50% thème normal / 50% thème inversé.
- Images sans filtre imposé et `border-radius: 0`.
- Beaucoup d’espace et de respiration entre les blocs.
- Lignes fines, grandes typographies, compositions asymétriques mais lisibles.
- Pas de holographisme agressif par défaut.

Le vieux code peut encore contenir des traces d’essais iridium/holographiques, surtout dans `forms.css`, `style.css` et certains scripts. Les blocs éditoriaux placés en fin de fichier ont priorité.

## Transitions entre les pages

`window.ScalyPageTransition`, défini dans `share.js`, est le point d’entrée commun des transitions SPA. Le design est déterminé par `window.design.button`, avec `footer` puis les classes `button-setup-N` comme compatibilité. Les remplacements de DOM doivent être exécutés dans `ScalyPageTransition.run(callback)` afin que le contenu change uniquement lorsque le rideau est fermé.

Les designs 1 à 5 sont implémentés. Le design 1 ferme le viewport comme une feuille photographique sobre, avec un repère fin `SCALY / 01`, puis libère le nouvel écran horizontalement. Le design 2 ouvre un fond inversé organique depuis le centre, croise deux blobs nets `--c-one` / `--c-two` autour d’un repère translucide `02`, puis relâche le nouvel écran par une ouverture verticale souple. Le design 3 utilise un obturateur chromatique de cinq bandes pleines arrivant alternativement du haut et du bas autour d’un repère pilule `SCALY / 03`, puis rétracte les bandes en une ligne fine. Le design 4 utilise deux plaques neo-brutalistes issues de `--c-one`, une traverse `--c-two` et un tampon `SCALY / 04`, avant d’éjecter les plaques dans des directions opposées. Le design 5 referme une double page éditoriale moitié thème normal / moitié inversé, compose asymétriquement `SCALY / ISSUE 05`, puis ouvre une page vers le haut et l’autre vers le bas. La séquence active couvre `loadContent()`, `goClient()`, `goBack()`, `navBack()` et la connexion depuis `lock`. Les appels imbriqués utilisent `{ transition: false }` sous le rideau principal pour éviter une double animation.

Chaque famille globale 1 à 5 possède désormais sa transition dédiée.

Le moteur possède aussi un état de chargement modulaire. `ScalyPageTransition.run(callback, { loading: true, label })` conserve la transition fermée tant que la promesse du callback n’est pas résolue. `ScalyPageTransition.beginLoading({ initial: true, label })` retourne un verrou doté de `finish()` pour les opérations dont la durée est pilotée ailleurs. Sans `loading`, les transitions de navigation restent strictement identiques.

`#charging` n’est plus présent dans `index.html` et ne pilote plus ni l’ouverture du site, ni la connexion depuis `lock`. L’ouverture démarre la transition sélectionnée immédiatement après `<body>`, puis la conserve jusqu’à la disponibilité des données, des scripts, des images nécessaires au head et de la police choisie. La connexion couvre de la même manière le fetch d’authentification, l’injection du client ou l’initialisation réelle du dashboard admin. Les chargements 1 à 5 restent visuellement propres à leur famille : ligne de tirage, pulsations organiques, égaliseur chromatique, blocs neo-brutalistes et ligne éditoriale.

Pour éviter tout flash avant `dataLoader.js`, `routes/serverClientRouter.js` hydrate dans le `<head>` le thème, le design `button/footer`, `--c-one`, `--c-two` et `fontPair` depuis `bdd.json`. La paire de polices sélectionnée commence à charger avant le `<body>` et expose `window.__scalyFontReady`; le rideau initial ne révèle le contenu qu’après cette promesse. `dataLoader.js` reste ensuite la source complète de `window.design`, mais ne détermine plus le premier rendu visible.

## Head / header

Le head est le premier écran vu par le visiteur. Il conserve les éléments stables suivants dans `index.html` :

- `#hero-slider` pour le slider historique ;
- `#grandtitre` pour le titre modifiable ;
- `#slogantitre` pour le sous-titre modifiable ;
- `#svgTouch` pour déclencher le reveal vers le profil.

### Numérotation actuelle

- `head` 1 à 5 : nouvelles familles visuelles globales.
- `head` 6 : ancien design 1, slider classique.
- `head` 7 : ancien design 2, double slider vertical.
- `head` 8 : ancien design 3, scène 3D/parallaxe.
- `head` 9 : ancien design 4, split-screen flou/net avec reveal contrôlé.

Le champ `headSchema: 2` indique la nouvelle numérotation. Pour une ancienne donnée sans ce marqueur, le serveur traduit temporairement les valeurs 1–4 vers 6–9 lors de la lecture. Une sauvegarde individuelle du head ou une application globale persiste le nouveau schéma.

### Implémentation des designs 1 à 5

`initHeaderSystemDesign(design, images)` dans `app.js` construit une structure commune `.head-system-stage` sans modifier les IDs éditables. Les familles changent uniquement la composition et les transitions :

- 1 : sobre et monochrome ;
- 2 : blobs modernes ;
- 3 : chromatique maîtrisé ;
- 4 : neo-brutaliste professionnel ;
- 5 : éditorial et artistique.

`initAdaptiveHeader()` nettoie les classes `header-setup-1` à `header-setup-9`, puis applique uniquement la classe active. `cleanupHeader()` retire aussi les scènes, intervalles et timers propres au head courant.

Ne pas renommer `#grandtitre`, `#slogantitre` ou `#svgTouch` : `back.js` les utilise pour l’édition. Toujours préserver `signalProfileReveal()` et la restauration du scroll après la sortie du header.

Pour éviter tout conflit entre les deux générations, `initAdaptiveHeader()` applique aussi `head-system-active` aux designs 1–5 et `head-legacy-active` aux designs 6–9. Sur les nouveaux designs, `#hero-slider` et les scènes historiques restent dans le DOM pour compatibilité mais sont masqués et désactivés.

Le `#svgTouch` des designs head 1–5 est réservé dans une zone stable au-dessus de la navigation fixe afin de rester visible dans le viewport. Cette correction est uniquement CSS : l’ID, le clic et le reveal ne changent pas.

## Portfolio / galeries

Le portfolio est piloté par `public/js/galeries.js`, `public/css/portfolio.css` et `public/js/backPortfolio.js`.

### Numérotation actuelle

- `portfolioCard` 1 à 5 : nouvelles familles visuelles globales ;
- `portfolioCard` 6 : ancien design 1, panorama plein écran ;
- `portfolioCard` 7 : ancien design 2, cartes holographiques ;
- `portfolioCard` 8 : ancien design 3, pile cinématique.

Le champ `portfolioSchema: 2` marque la nouvelle numérotation. Une donnée ancienne sans marqueur et avec une valeur 1–3 est traduite temporairement vers 6–8 par le serveur. La sauvegarde individuelle ou globale du portfolio persiste le marqueur.

### Structure et compatibilité admin

- `creatFolderClient` rend la liste des galeries. Les designs 1–5 partagent les hooks historiques `.cardPhotos`, `.contentphotocard`, `.ladivcontentcardimg`, `.contentOBJcard`, `.share` et `.profilecard`.
- `afficherPhotosAll` rend le détail et les albums en conservant `.h2seclectall`, `.contentsubclient`, `.subcategoryclient`, `.ladescportfolio` et les classes `selectAll-*`.
- `imgall` rend les photos en conservant `.contentimg`, `.h2outil`, `#galleryContainer`, `.img-wrapper` et `.animphoto`.
- Les classes supplémentaires `portfolio-design-N`, `portfolio-view-*` et `portfolio-*` servent uniquement à la composition visuelle et aux transitions.

Les trois choix `layout-div`, `layout-mansory` et `layout-column` restent indépendants du design. `createLayoutOverlay()` ne remplace que cette classe de layout et conserve le hook `.portfolio-gallery-grid`.

Chaque design 1–5 possède une transition propre entre la liste et le détail. Les photos ne reçoivent aucun filtre colorimétrique imposé. Les titres d’album visibles sont aussi synchronisés par `backPortfolio.js` après renommage.

### Corrections après première validation portfolio

- L’entrée dans une nouvelle galerie doit toujours appeler `window.galerieApp.afficherPhotosAll`, jamais directement la fonction locale : le greffon `backPortfolio.js` enveloppe cette méthode pour réinstaller l’édition de description, l’ajout d’album et les commandes de l’album actif.
- Les transitions 1–5 utilisent `.portfolio-scene-transition`, injecté directement sous `body`. Ce calque conserve la photo sélectionnée pendant que le DOM passe de `creatFolderClient` à `afficherPhotosAll`/`imgall`, puis révèle la nouvelle vue.
- La transition du design 1 est une séquence de tirage photographique : extraction de la carte, développement plein écran avec ligne de scan et repères sobres, puis double obturateur croisé qui masque le remplacement du DOM. Ses timings sont `swap: 880ms` et `end: 820ms`.
- La transition du design 2 est une séquence organique : la photo se décroche de sa carte, se transforme en lentille liquide plein écran avec deux blobs discrets issus de `--c-one` et `--c-two`, puis un iris irrégulier se referme vers le centre pour révéler la galerie depuis les bords. Ses timings sont `swap: 950ms` et `end: 880ms`.
- La transition du design 3 est une séquence de prisme chromatique sans filtre sur la photo : deux échos de cadrage issus de `--c-one` et `--c-two` accompagnent son extraction, l'image devient plein écran, puis elle se resserre en fracture diagonale pendant que deux volets colorés se croisent en sens opposés. Ses timings sont `swap: 880ms` et `end: 820ms`.
- La transition du design 4 est une séquence de montage neo-brutaliste : la photo se décroche avec une bordure et une ombre franches, s'agrandit par impacts mécaniques avec ses repères, puis quatre plaques utilisant le thème, `--c-one` et `--c-two` verrouillent l'écran avant de s'éjecter dans quatre directions. Ses timings sont `swap: 820ms` et `end: 800ms`.
- La transition du design 5 est une séquence éditoriale : la photo devient une couverture sans filtre ni arrondi, le titre et les repères typographiques composent la page dans une alternance de thème normal et inversé, puis une feuille à bord diagonal balaie la scène de droite à gauche et révèle la galerie comme la page suivante. Ses timings sont `swap: 940ms` et `end: 920ms`.
- `.portfolio-system-albums` contient désormais `.portfolio-album-fan` et `.portfolio-album-total` : un petit éventail de couvertures sans nom, accompagné du nombre total d’albums.
- En admin, l’ajout d’album doit cibler `.portfolio-album-list`, pas le premier `.contentsubclient` qui peut être la bande des images de couverture.
- Pendant le changement de design portfolio, `portfolioDesignSwitchActive` empêche le masquage de la navigation et maintient le contexte `design-switch-portfolio` ouvert entre deux rendus.
- Ne plus écrire directement `translateY(0)` sur `#navigation` : le design 5 exige aussi `translateX(-50%)`. Utiliser `portfolio-nav-visible`/`portfolio-nav-hidden` et les règles CSS dédiées.

## Accueil

Les quatre blocs de l’accueil sont :

1. profil ;
2. news ;
3. style ;
4. prestations.

### Profil

Le profil contient nom/prénom, deux images et une description. Le design 1 correspond au profil historique. Les designs 2, 3 et 4 ont été reconstruits ; le design 5 est éditorial. Attention à ne pas casser :

- la révélation déclenchée après `svgTouch` et la fin du header fixe ;
- le calcul dynamique de taille du nom/prénom ;
- les animations d’apparition et classes `is-visible`.

### News

Le news utilise désormais principalement le design 3/4 selon le choix global, avec une animation d’impact. Le bloc peut être scroll-jacké et centré automatiquement au démarrage de son animation. Éviter de réintroduire les anciens designs supprimés sans demande.

### Style

Le style utilise une narration scroll-story / scroll-jacking. Le design éditorial 5 est un book abstrait : couverture avec photo de profil et nom, puis quatre photos avec légendes et animation réaliste de tournage de page. Le scroll naturel doit être bloqué pendant la séquence puis restauré à la fin, y compris sur mobile.

### Prestations

Les cartes prestations sont mobiles-first, donc en colonne sur mobile. Ne pas remettre les cartes en ligne par défaut. Le design 2 doit rester ouvert et blobé : éviter `overflow:hidden` sur chaque carte qui coupe les formes.

La numérotation globale des prestations reste 1 à 5. Le JavaScript traduit uniquement le rendu interne des styles historiques dont l’ordre 3/4 est inversé : choix global 3 → `presta-setup-4`, choix global 4 → `presta-setup-3`. Les styles CSS et le numéro affiché dans le sélecteur ne doivent pas être modifiés.

## Formulaires visiteurs

`forms.css` gère les formulaires visibles par les visiteurs :

- contact dans `contact.html` ;
- connexion dans lock ;
- inscription dans lock et accueil ;
- prise de rendez-vous dans les prestations ;
- calendrier et réglages de réservation.

Ces éléments suivent le numéro du footer via `body.form-setup-N` dans le flux normal. Les fetchs et IDs ne doivent pas être modifiés lors d’un travail visuel.

Le formulaire contact est dans `.content_1_contact > #form`. Le centrage a été corrigé pour éviter l’ancien conflit entre `position:absolute`, `left/top` et le `transform:none !important` du design 5. Le conteneur flex centre maintenant le formulaire ; vérifier avant de réintroduire un positionnement absolu.

La page contact utilise désormais une composition compacte dans `.contact-stage`. Le formulaire `#form` et son HTML restent inchangés et continuent d’être entièrement dessinés par `forms.css`. `#imageaccueil` conserve son ID, sa variable `--bg-image` et les hooks de `contact.js`/`backContact.js`, mais devient une illustration de taille contenue intégrée à proximité du formulaire au lieu d’un panneau de `100vh`. `#contentreseaux` se trouve sous cette composition et `#reseaux` affiche toujours ses éléments sur une seule ligne horizontale, avec défilement latéral sur les petits écrans si nécessaire.

`contact.css` décline cette composition via `body.form-setup-1` à `5` : cadre monochrome, image organique, cadre chromatique, bloc neo-brutaliste et mise en page éditoriale. Aucun filtre colorimétrique n’est imposé à l’illustration. Dans le greffon admin, `#imageaccueil` ne porte que l’action de remplacement d’image et `#contentreseaux` porte séparément la gestion des réseaux.

## Navigation et menu admin

### `#navigation`

- La navigation peut être `top` ou `bottom`.
- `applyNavigationDesign(value)` dans `app.js` retire les classes de navigation 1–5 puis ajoute `navigation-setup-N` et `navigation-design-N`.
- La valeur `window.design.navigation` est indépendante dans la logique actuelle.
- En usage normal, `navigation` reste un choix indépendant. La confirmation explicite « appliquer partout » remplace toutefois sa valeur par le design global demandé.
- Ne pas forcer un design 5 via un sélecteur CSS non scopé.

### `#admin` et `AdminMenuManager`

`window.AdminMenuManager` est défini dans `back.js`.

- `getDesign()` utilise prioritairement `window.design.navigation`, puis les anciennes valeurs de compatibilité. Le skin de `#admin` ne doit jamais dépendre de `dashboard` : il suit toujours le numéro de la navigation.
- `syncDesign()` applique `admin-design-N`, nettoie l’overlay et retire les anciennes classes premium ainsi que les électrons : la navigation 2 utilise maintenant une peau compacte sans blur animé.
- `open()` crée dynamiquement `.nav-overlay-js` et `.nav-item-js` selon le contexte courant.
- `open()` calcule la largeur de `#admin.expanded` avec des dimensions propres aux designs 2, 3 et 5 afin que le menu reste ajusté au nombre réel d’actions.
- La position de `#admin` dépend de `top/bottom` et doit rester séparée de la position de navigation.
- Les boutons du menu admin sont maintenant centrés via une règle finale dans `style.css`.
- Ne pas utiliser `.buttonsvg` pour chaque icône de navigation : ce style est réservé au menu admin ouvert quand nécessaire.

### Révision des navigations 2, 3 et 5

Une couche finale autoritaire nommée `NAVIGATION 2 / 3 / 5 - FINAL COMPACT SYSTEM` est placée à la vraie fin de `style.css`, après toutes les anciennes variantes :

- design 2 : deux pilules modernes compactes, sans grosses masses organiques, sans électrons et avec `#admin` centré dans un pont discret ;
- design 3 : géométrie centrale reprise exactement du design 1 avec un SVG de `100 × 50`, le tracé `.nav-mask-path-default` et un logo admin en `object-fit: cover` sans padding interne ;
- design 5 : pellicule abstraite basse, avec peu de perforations transformées en rectangles longs et arrondis, et `#admin` intégré dans le segment central ;
- les trois designs possèdent des positions fermées et `expanded` explicites pour `top` et `bottom`, ainsi qu’une adaptation sous `560px` ;
- le cas authentifié du design 5 utilise aussi l’attribut `[data-design="5"]` : conserver la surcouche dédiée pour neutraliser les anciennes règles plus spécifiques.

## Modal des réglages globaux

La modal est créée dynamiquement par `createModalSettings()` dans `back.js`.

- Parent : `#modal-setting-global`.
- Panneau : `.modal-content-panel`.
- Vue principale : `.lw-modal-main-view`.
- Réglages généraux : `.lw-modal-toggles-container`.
- Carousel de design, couleurs et polices : second `.lw-modal-toggles-container` nommé ici `designContainer`.
- Bouton retour : `backArrow`.

La modal porte désormais `data-design` avec la valeur de `window.design.button`. `applyDesign()` met cet attribut à jour pendant la prévisualisation : chaque famille visuelle peut donc être isolée sans dépendre du design de la navigation ou du dashboard.

Les trois vues utilisent le moteur commun `showSettingsView()` et les états `.lw-settings-view`, `.is-active`, `.is-entering` et `.is-leaving`. Les anciennes animations inline longues ont été supprimées ; ne pas réintroduire de `transform` sur les carrousels, car leur glissement repose déjà sur la transformation de leur track.

### Refonte design 1

Le design 1 est implémenté dans la couche finale `GLOBAL SETTINGS — DESIGN 1 / MONOCHROME EDITORIAL` de `back.css` :

- ouverture courte par feuille horizontale, ligne de scan et révélation découpée du panneau, sans fond flou instantané ;
- panneau éditorial monochrome, en-tête fixe et transitions latérales entre les vues ;
- stockage intégré dans une carte avec jauge monochrome, sauf état critique rouge ;
- deux entrées explicites pour les réglages généraux et la direction artistique, puis fermeture/déconnexion regroupées dans un pied d’actions ;
- toggles rectangulaires, sections générales en lignes et réglages design recomposés dans la même famille visuelle ;
- comportement réduit sous `prefers-reduced-motion` et composition plein écran sous `620px`.

`updateStorageUsage()` ne fixe plus le gradient en inline : il met à jour la largeur et la classe `.storage-fill-critical`, afin que chaque design puisse définir sa propre jauge.

### Refonte design 2

Le design 2 est implémenté dans la couche finale `GLOBAL SETTINGS — DESIGN 2 / LIVING GLASS` de `back.css` :

- ouverture organique depuis le centre, traversée par une forme composée de `--c-one`, du thème inversé et de `--c-two` ;
- panneau unique en verre léger avec deux blobs d’ambiance qui se déplacent selon la vue active, sans empilement de cartes ni blur massif ;
- stockage, entrées principales et actions recomposés dans des surfaces translucides souples ;
- réglages généraux regroupés dans une membrane continue, avec toggles organiques adaptés ;
- carrousels, palettes, couleurs et typographies harmonisés avec des formes rondes et des lueurs limitées ;
- ouverture, fermeture, transitions internes et version mobile couvertes par `prefers-reduced-motion`.

L’en-tête utilise maintenant `[data-settings-design-number]` afin d’afficher dynamiquement le bon numéro lors du passage à chaud entre les designs.

### Refonte design 3

Le design 3 est implémenté dans la couche finale `GLOBAL SETTINGS — DESIGN 3 / CHROMATIC STUDIO` de `back.css` :

- ouverture par cinq bandes chromatiques alternées venant du haut et du bas, suivie d’une révélation horizontale nette du panneau ;
- panneau solide sans glassmorphisme, en-tête asymétrique et aplats francs `--c-one` / `--c-two` ;
- stockage composé sur un plan coloré, deux accès principaux différenciés par couleur et actions en pilules ;
- réglages généraux regroupés avec repères latéraux alternés et toggles pleins passant de la couleur primaire à la secondaire ;
- carrousels, palettes, couleurs et typographies adaptés avec une géométrie vive et des lueurs limitées aux retours interactifs ;
- transitions internes en wipe chromatique, version mobile et `prefers-reduced-motion` pris en charge.

### Refonte design 4

Le design 4 est implémenté dans la couche finale `GLOBAL SETTINGS — DESIGN 4 / PROFESSIONAL CONTACT SHEET` de `back.css` :

- ouverture mécanique par deux plaques néo-brutalistes issues de `--c-one`, qui se rejoignent puis sont éjectées en sens opposés ;
- panneau type planche-contact avec bordures épaisses, trame pointillée et ombre pleine sans flou ;
- en-tête coloré doté d’une traverse `--c-two` et d’un tampon `04`, stockage rayé et contrôles principaux à retour mécanique ;
- réglages généraux regroupés dans un tableau de contrôle, avec séparations franches et toggles rectangulaires physiques ;
- carrousels, palettes, couleurs et typographies traités comme des épreuves encadrées, avec ombres décalées et labels imprimés ;
- transitions internes crantées, états hover/active, version mobile et `prefers-reduced-motion` pris en charge.

### Refonte design 5

Le design 5 est implémenté dans la couche finale `GLOBAL SETTINGS — DESIGN 5 / EDITORIAL ISSUE` de `back.css` :

- ouverture en double page moitié thème normal / moitié thème inversé, titrée `SCALY / ISSUE 05`, puis éjection d’une page vers le haut et de l’autre vers le bas ;
- panneau sans arrondi, sans holographisme et sans 3D, composé comme un numéro de magazine en deux moitiés ;
- stockage, accès principaux et actions structurés par inversion noir/blanc, lignes fines et grandes typographies ;
- réglages généraux présentés comme un index éditorial avec libellés sur la page claire et toggles sur la page inversée ;
- direction artistique mise en page comme un sommaire asymétrique ; les seules couleurs visibles restent les échantillons réellement configurables ;
- transitions internes en ouverture de page, composition mobile verticale spécifique et `prefers-reduced-motion` pris en charge.

Les cinq designs de `#modal-setting-global` disposent maintenant chacun de leur structure visuelle, de leur ouverture, de leur fermeture et de leurs transitions internes dédiées.

### Correctif de visibilité commun

La révélation de la modal est idempotente via `revealGlobalSettings()`. Elle est déclenchée à la fois par un timer court de sécurité et par le double `requestAnimationFrame` visuel : une frame suspendue ou une erreur d’initialisation de Lucide ne peut donc plus laisser les panneaux des cinq designs à leur état initial `opacity: 0`. L’initialisation des icônes est isolée dans un `try/catch` et intervient après la programmation de la révélation.

`updateStorageUsage(fillElement, textElement, barElement)` reçoit désormais les références locales de la jauge et n’est appelé qu’après l’ajout de la modal au document. Ne plus rechercher la jauge avant le montage de `#modal-setting-global`, car une réponse `/storage-usage` très rapide pouvait cibler un DOM encore absent.

### Sélecteurs indépendants et confirmation de portée

À la fermeture de la modal :

- `designContainer` affiche le carrousel `button/footer`, puis le carrousel `navigation` avec la même interaction de glissement.
- Chaque aperçu de navigation est un vrai modèle réduit isolé dans un `iframe` : il charge `style.css`, reprend la structure exacte de `#navigation`, ses SVG, ses blocs et `#admin`, puis applique `navigation-setup-N`/`navigation-design-N`.
- Le choix du dashboard n’est plus présent dans cette modal : il se fait directement depuis BackTicket afin que l’administrateur voie le résultat sur l’interface complète.
- si seule la couleur/police ou la navigation est modifiée, la sauvegarde se fait directement ;
- si le numéro `button/footer` change, `#modal-msg` demande si ce design doit être appliqué au reste du site ;
- « Non, conserver les autres choix » conserve la valeur choisie pour `navigation` et applique uniquement le périmètre boutons/footer avec les réglages couleur/police ;
- « Oui, appliquer partout » applique le même numéro à `profile`, `style`, `news`, `portfolioCard`, `presta`, `head`, `navigation` et `dashboard`. La navigation et `#admin` sont resynchronisés ensemble immédiatement, comme le dashboard, puis toutes les valeurs sont persistées en une seule requête.

La fonction de persistance est `persistDesign(applyEverywhere)`. La confirmation est construite par `askDesignScope(onChoice)` et réutilise `#modal-msg`, `#lw-p` et `.lw-close-overlay`.

## BackTicket / dashboard

`backoffice.html` contient `#backTicket` et plusieurs modales. `backTicket.js` gère notamment :

- propositions et acomptes ;
- rendez-vous et calendrier ;
- clients ;
- livraisons et validations ;
- suivi de projet ;
- configuration globale des réservations ;
- modales `#modal-client`, `#modal-rdv`, `#modal-project-help`, `#view-photo-delivery`, `#modal-deliver`, `#modal-proposal`, `#modal-project-tracking`.

Les designs BackTicket sont dans `back.css`, scopés par `body.dashboard-setup-N`. Les modales et calendriers utilisent en plus `body.dashboard-page-active` afin que leur skin ne déborde pas sur les autres pages admin. Le design 5 est éditorial et couvre l’affichage, les cartes, les listes, les modales, le calendrier et `#modal-msg`.

`backTicket.js` injecte `#dashboard-design-control` en bas à droite quand le dashboard est actif. Le bouton `#changeDesignDashboard` ouvre un contexte `AdminMenuManager` avec précédent/suivant, applique chaque `dashboard-setup-N` en direct sur BackTicket sans modifier `#admin`, puis sauvegarde `dashboard` via `/update-style-design`. Fermer la validation restaure le design initial ; quitter BackTicket nettoie le bouton et toute prévisualisation active.

### Contrats à préserver et liberté UX du dashboard

- Les quatre domaines métier restent couverts : projets/propositions, shootings/rendez-vous, livraisons et clients. Leurs données, fetchs, routes, sockets, IDs utiles, callbacks et règles métier sont des contrats à préserver.
- Le DOM historique, `.dashboard-grid`, les `.dashboard-section`, le rail horizontal, le scroll-snap, les onglets, les cartes et l’emplacement actuel des boutons ne sont pas des contrats. Ils constituent uniquement l’implémentation actuelle et peuvent être supprimés ou réorganisés.
- `initDashboardHorizontalExperience()` est une solution transitoire à réévaluer, pas une direction UX obligatoire. Une future refonte peut utiliser une navigation latérale, une liste maître/détail, un workspace, une timeline, un pipeline, des panneaux, des drawers ou toute autre composition cohérente avec le design choisi.
- Chaque design doit proposer une véritable architecture d’information et un modèle d’interaction distinct. Changer uniquement les couleurs, rayons, ombres ou typographies ne constitue pas une refonte.
- Le résumé contextuel, les compteurs, les attributs d’état et le padding inférieur peuvent être conservés s’ils servent le produit, mais ne doivent pas imposer une mise en page particulière.
- Les rendus JavaScript peuvent être refactorisés pour produire une nouvelle présentation et un nouvel état d’interface, tant que les données chargées, les actions métier et les contrats backend restent fiables.
- Le footer global peut rester masqué pendant BackTicket et l’espace inférieur doit rester suffisant pour la navigation réellement choisie, sans imposer une valeur ou un dispositif fixe si le nouveau layout n’en a pas besoin.
- Les statuts restent lisibles et fonctionnels. `--c-one` et `--c-two` peuvent mettre en valeur les informations importantes du dashboard sans devenir la palette dominante des designs 1 et 5.

### Refonte visuelle approfondie du dashboard

- La refonte est menée design par design. Le dashboard design 1 doit être validé comme une vraie direction UX avant de décliner les autres designs ; les implémentations actuelles des designs 1, 3, 4 et 5 sont des bases visuelles à réévaluer, pas des références structurelles.
- Le design 1 doit être sobre, monochrome et proche de l’esprit Apple, mais son architecture reste libre : il peut proposer une navigation verticale, un workspace maître/détail, un pipeline, un agenda ou une combinaison plus pertinente. Il ne doit pas reprendre automatiquement les anciennes cards, le rail horizontal, les mêmes listes ou les mêmes positions de boutons.
- Le design 1 utilise `window.theme` en majorité : `var(--back)` reste le fond de toutes les grandes surfaces et `var(--color-font)` reste la couleur du contenu. Il est interdit d’utiliser `var(--color-font)` comme grand fond ou état actif dans ce dashboard ; le reverse theme appartient au design 5. Les variations du design 1 doivent venir de mélanges très légers, de bordures fines et d’ombres discrètes.
- Le fond et toutes les surfaces dérivent directement de `var(--back)` et `var(--color-font)`. `var(--c-one)` et `var(--c-two)` ne servent que d’accents légers : ne jamais réutiliser `--admin-d1-surface` comme fond du dashboard, car cette variable inverse volontairement le thème pour certains boutons admin.
- `backTicket.js` peut modifier la composition du DOM, le modèle de navigation et les états visuels nécessaires à la refonte. Les fetchs, routes, IDs contractuels, données et callbacks métier restent inchangés ; préserver la mécanique ne signifie pas préserver l’affichage historique.
- Les statuts conservent de petits repères colorés fonctionnels. Les étapes du suivi projet reçoivent les classes visuelles `.is-complete`, `.is-current` et `.is-locked` sans modifier le calcul historique du workflow.
- Les parcours métier des modales sont conservés, mais leur composition UX peut être refondue : modal, drawer, panneau latéral, feuille mobile ou écran de travail. `#modal-msg` et `#modal-setting-global` restent explicitement hors périmètre de cette refonte.
- L’aide projet, ses légendes, ses notes et toutes les actions de la timeline sont conservées. Le bouton d’aide du suivi est remplacé à chaque ouverture pour éviter son accumulation dans le DOM.
- Le design 3 sert de premier test de cette liberté UX avec `COMMAND WORKSPACE` : un seul outil métier actif remplace le rail horizontal. La navigation devient une matrice de canaux sur mobile puis une console verticale sur grand écran. Projets, shootings, livraisons et clients utilisent respectivement un pipeline, une frise, une file de transfert et un index de contacts ; leurs actions secondaires passent par des menus contextuels. Le calendrier design 3 devient un planning plein écran et son détail journalier une chronologie. Cette direction reste à valider visuellement avant d’être considérée comme terminée.
- Après les cinq dashboards, le chantier prévu avant le responsive couvre les espaces personnels client, l’affichage de leurs livraisons et la signature électronique pour les designs 1 à 5.

La disparition intermittente de `#navigation` venait du timer de masquage différé du portfolio. `ensureAdminNavigationVisible()` retire `portfolio-nav-hidden`, conserve/ajoute `portfolio-nav-visible`, rétablit les styles nécessaires à l’entrée dans BackTicket et refait un passage après 420 ms pour neutraliser cette course. Pendant que BackTicket est actif, un `MutationObserver` surveille aussi les attributs `class/style` de la navigation et la rétablit si un ancien callback tente encore de la masquer ; la classe de visibilité et l’observer sont nettoyés en quittant la page.

`backTicket.js` dispose aussi de `showMessage(message, type, onConfirm, onCancel)` qui manipule `#modal-msg`. Éviter de supprimer les boutons dynamiques `#lw-confirm-btn` ou les listeners de confirmation.

## Cache-busting actuel

Les versions actuelles importantes sont :

- `index.html` : `/css/style.css?v=modal-msg-design-system-v2` ;
- `index.html` : `/css/portfolio.css?v=portfolio-design-system-v8` ;
- `index.html` : `/css/contact.css?v=contact-composition-v1` ;
- `index.html` : `/css/forms.css?v=public-forms-d5-editorial-v1` ;
- `index.html` : `/js/share.js?v=page-transition-loading-v2` ;
- `index.html` : `/js/dataLoader.js?v=page-transition-loading-v1` ;
- `index.html` : `/js/app.js?v=contact-composition-v1` ;
- `index.html` : `/js/accueil.js?v=page-transition-loading-v1` ;
- `app.js` : `/js/galeries.js?v=portfolio-design-system-v8` ;
- `app.js` : `/js/contact.js?v=contact-composition-v1` ;
 - `share.js` : `/js/back.js?v=settings-modal-content-visible-v3` ;
 - `share.js` : `/css/back.css?v=dashboard-design1-theme-vars-v2`.

La zone de titre interne de `#modal-setting-global` est construite en `<div class="lw-settings-header">`, et non en `<header>`, afin de ne pas être interceptée par les règles et scripts du header principal du site.

La direction artistique de la modal utilise des aperçus plus grands pour le bouton/footer et la navigation (`ITEM_WIDTH` 280px, hauteur 190px, navigation rendue dans une base 500px puis agrandie à l’échelle 0.56). Les aperçus sont eux-mêmes les items visuels du carousel : les cadres, fonds et étiquettes externes ont été retirés. Les numéros décoratifs des titres et de l’en-tête ont été retirés.

`#modal-msg` possède désormais cinq compositions plein écran dans `style.css`. Son attribut `data-design` est synchronisé directement avec `window.design.button` par `applyModalMessageDesign()`, y compris pendant la prévisualisation de `back.js`; le design du dashboard ne peut donc plus décaler la numérotation de cette modal. Les contrats existants restent inchangés : `#lw-p`, le `form`, `.lw-close-overlay`, `#lw-confirm-btn` et `.background-button-modal` sont conservés. Le design 1 est sobre et monochrome, le 2 organique, le 3 chromatique, le 4 néo-brutaliste et le 5 bicolore éditorial.

Après une modification importante de CSS chargé par URL versionnée, incrémenter la version correspondante.

## Règles de travail importantes

- Mobile-first : vérifier les layouts mobiles avant les media queries desktop.
- Ne pas toucher aux fetchs, routes, IDs ou callbacks backend pour un changement visuel.
- Ne pas remplacer les variables dynamiques par des couleurs fixes : utiliser `var(--back)`, `var(--color-font)`, `var(--c-one)`, `var(--c-two)` selon le design.
- Éviter les `overflow:hidden` sur les compositions blobées, sauf si nécessaire pour un masque précis.
- Éviter la 3D et les transformations GPU permanentes : elles peuvent flouter ou ralentir le rendu.
- Conserver le scroll-jacking uniquement quand le bloc le demande et toujours restaurer le scroll naturel à la fin.
- Les fichiers CSS sont volumineux et contiennent des blocs historiques/dupliqués. Les règles placées en fin de fichier ont souvent priorité ; vérifier la cascade avant de réécrire une ancienne règle.
- Utiliser `apply_patch` pour les modifications de fichiers.
- L’utilisateur a demandé de ne pas effectuer de test navigateur pour le moment. Faire des vérifications statiques : `node --check` et équilibrage des accolades CSS.

## Vérifications rapides

```powershell
node --check scaly-product/pics/public/js/app.js
node --check scaly-product/pics/public/js/back.js
node --check scaly-product/pics/public/js/backTicket.js
node --check scaly-product/pics/public/js/accueil.js
node --check scaly-product/pics/public/js/contact.js
```

Pour une CSS modifiée, compter les `{` et `}` dans le fichier concerné. Ne pas utiliser de reset Git destructif : le workspace contient des modifications utilisateur et des travaux précédents à préserver.
