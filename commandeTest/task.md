# Scaly — feuille de route globale

## Objectif général

Terminer le SaaS dans sa globalité — fonctionnalités, système de designs, UX et responsive — avant de lancer un chantier sécurité complet.

Le système actuel couvre environ 70 % du site. L’administrateur peut choisir un design global ou modifier les designs bloc par bloc.

## Ordre de travail

### 1. Réorganiser les designs existants du head et du portfolio

- [x] Identifier les 4 designs actuels du head.
- [x] Identifier les 3 designs actuels du portfolio.
- [x] Conserver les 4 designs du head sans les supprimer.
- [x] Conserver les 3 designs du portfolio sans les supprimer.
- [x] Déplacer les 3 designs historiques du portfolio vers les numéros 6, 7 et 8.
- [x] Déplacer les 4 designs historiques du head vers les designs 6, 7, 8 et 9.
- [x] Libérer les numéros 1 à 5 du head pour les designs correspondant au système global.
- [x] Libérer les numéros 1 à 5 du portfolio pour les designs correspondant au système global.
- [x] Vérifier statiquement la compatibilité du head avec le choix global et le choix bloc par bloc.
- [x] Mettre en place la persistance et la migration des numéros de design du head.
- [ ] Vérifier en test navigateur le rendu du head après rechargement.

### 2. Créer les 5 designs du head

- [x] Travailler sur le header, qui est le premier élément vu par le visiteur.
- [x] Prendre en compte le titre, le sous-titre, les images choisies par l’utilisateur et le bouton de reveal.
- [x] Préserver le reveal : le header part pour laisser découvrir la partie profil de l’accueil.
- [x] Créer le design head 1, cohérent avec le design global 1.
- [x] Créer le design head 2, cohérent avec le design global 2.
- [x] Créer le design head 3, cohérent avec le design global 3.
- [x] Créer le design head 4, cohérent avec le design global 4.
- [x] Créer le design head 5, cohérent avec le design global 5.
- [x] Vérifier statiquement le choix individuel du head.
- [x] Vérifier statiquement l’application du design head via le choix global.
- [x] Vérifier statiquement la coexistence des designs head 1–5 et 6–9.
- [x] Corriger le positionnement de `#svgTouch` des designs head 1–5 pour le maintenir dans le viewport, au-dessus de la navigation.

### 3. Créer les 5 designs du portfolio

État au 8 août 2026 : implémentation terminée et vérifications statiques validées. La validation visuelle navigateur par l’utilisateur reste volontairement à faire avant les corrections de détail et le responsive.

#### Corrections issues de la première validation

- [x] Corriger le décentrage horizontal de la navigation design 5 dans le mode admin portfolio.
- [x] Maintenir la navigation et le menu de changement ouverts pendant le parcours des designs 1–8.
- [x] Séparer le choix du design de `#navigation + #admin` de celui de l’interface dashboard BackTicket.
- [x] Ajouter le sélecteur navigation sous le choix `.button/footer`, avec la même interaction de carrousel.
- [x] Remplacer les aperçus abstraits de navigation par de vrais modèles réduits des cinq navigations.
- [x] Retirer le choix dashboard de la modal globale.
- [x] Ajouter dans BackTicket un bouton flottant `changeDesign` qui prévisualise les cinq dashboards directement sur l’interface.
- [x] Persister séparément les champs `navigation` et `dashboard`.
- [x] Corriger la disparition intermittente de la navigation à l’entrée dans BackTicket.
- [x] Historique : transformer les quatre blocs BackTicket en vues horizontales plein écran avec scroll-snap.
- [x] Historique : agrandir verticalement chaque bloc tout en conservant le scroll interne des listes.
- [ ] Réévaluer et, si nécessaire, supprimer cette architecture horizontale avant la refonte UX finale du dashboard.
- [x] Remplacer la phrase fixe du dashboard par un résumé dynamique et amical lié au bloc visible.
- [x] Préserver les fetchs, IDs, modales, rendus et actions existants du dashboard.
- [x] Masquer le footer global pendant BackTicket et garantir au moins 100 px d’espace inférieur sous le dashboard.
- [x] Réintroduire des couleurs de repère pour les statuts des designs dashboard 1 et 5.
- [x] Rétablir le scroll vertical naturel au-dessus des sections et éviter la coupure haute des onglets du dashboard.
- [x] Découpler les classes CSS du dashboard de celles de `#admin` afin que chaque sélecteur de design reste dans son périmètre.
- [x] Remplacer les anciennes miniatures d’albums des cartes par un éventail compact et un compteur d’albums.
- [x] Faire survivre les transitions au remplacement du DOM entre la liste et la galerie.
- [x] Créer une scène animée et distincte pour chacune des transitions 1–5.
- [x] Reprendre individuellement la transition 1 avec un tirage photographique et un double obturateur synchronisé au changement de DOM.
- [x] Valider visuellement la nouvelle transition du portfolio design 1.
- [x] Reprendre individuellement la transition 2 avec une extraction organique, une lentille liquide et un iris synchronisé au changement de DOM.
- [x] Valider visuellement la nouvelle transition du portfolio design 2.
- [x] Reprendre individuellement la transition 3 avec des échos de cadrage, un prisme chromatique et une fracture diagonale synchronisée au changement de DOM.
- [x] Valider visuellement la nouvelle transition du portfolio design 3.
- [x] Reprendre individuellement la transition 4 avec un montage neo-brutaliste, des impacts mécaniques et quatre plaques synchronisées au changement de DOM.
- [x] Valider visuellement la nouvelle transition du portfolio design 4.
- [x] Reprendre individuellement la transition 5 avec une composition de couverture et un passage de page diagonal synchronisé au changement de DOM.
- [x] Valider visuellement la nouvelle transition du portfolio design 5.
- [x] Refondre entièrement la navigation design 2 dans un format moderne et compact, sans grosses masses ni électrons.
- [x] Corriger le SVG central de la navigation design 3 avec les dimensions et le tracé validés du design 1.
- [x] Faire occuper au logo de `#admin` toute la surface disponible dans la navigation design 3.
- [x] Recomposer la navigation design 5 comme une pellicule abstraite, basse, avec des perforations longues et arrondies.
- [x] Intégrer visuellement `#admin` aux navigations 2, 3 et 5.
- [x] Ajuster statiquement les dimensions et positions `top`/`bottom` de `#admin.expanded` pour les designs 2, 3 et 5.
- [ ] Valider visuellement dans le navigateur les navigations 2, 3 et 5, fermées puis ouvertes, en position haute et basse.
- [x] Rétablir le passage par les wrappers `backPortfolio.js` à l’ouverture d’une galerie.
- [x] Rétablir l’édition de description, l’ajout d’album et l’ouverture des commandes via l’engrenage.
- [x] Aligner côté JavaScript la numérotation globale des designs prestations avec l’ordre réel des styles 3 et 4.
- [ ] Valider visuellement ces corrections dans le navigateur.

- [x] Travailler principalement dans `galeries.js`, `portfolio.css` et `backPortfolio.js`.
- [x] Respecter la décomposition actuelle de `galeries.js` :
  - [x] `creatFolderClient` : afficher la liste des galeries de l’utilisateur.
  - [x] `afficherPhotoAll` : entrer dans la galerie choisie, afficher les albums et préparer l’affichage des photos.
  - [x] `imagAll` : fonctionner avec `afficherPhotoAll` pour afficher les photos.
- [x] Étendre le changement de design actuellement appliqué à `creatFolderClient` à `afficherPhotoAll` et `imagAll`.
- [x] Faire du rendu actuel de `afficherPhotoAll` et `imagAll` la référence du design portfolio 1, sobre.
- [x] Créer le design portfolio 1, cohérent avec le design global 1.
- [x] Créer le design portfolio 2, cohérent avec le design global 2.
- [x] Créer le design portfolio 3, cohérent avec le design global 3.
- [x] Créer le design portfolio 4, cohérent avec le design global 4.
- [x] Créer le design portfolio 5, cohérent avec le design global 5.
- [x] Préserver les 3 layouts d’affichage actuellement disponibles.
- [x] Vérifier statiquement que chaque design respecte le layout choisi par l’utilisateur, sans imposer une présentation différente.
- [x] Mettre les photos au premier plan : le design ne doit jamais prendre le dessus sur les images.
- [ ] Garantir un affichage fluide des photos, des albums et des changements de galerie.
- [x] Créer une transition unique entre `creatFolderClient` et le couple `afficherPhotoAll`/`imagAll` pour chaque design.
- [ ] Vérifier que les transitions restent fluides et utilisables sur les trois layouts.
- [x] Conserver les éléments modifiables attendus par `backPortfolio.js`.
- [x] Ne pas renommer les classes utilisées par `backPortfolio.js` sans mettre en place une couche de compatibilité.
- [x] Si une nouvelle structure HTML est nécessaire, conserver des hooks stables — classes, IDs ou attributs dédiés — pour les fonctionnalités admin.
- [x] Vérifier statiquement le choix individuel du portfolio.
- [x] Vérifier statiquement l’application du design portfolio via le choix global.
- [x] Vérifier statiquement la coexistence des designs portfolio 1–5 et 6–8.
- [x] Mettre en place la persistance et la migration des numéros de design du portfolio.

#### Règles visuelles strictes du portfolio

- [x] Toujours donner la priorité aux photos du photographe.
- [x] Éviter les décorations, animations ou compositions qui détournent l’attention des images.
- [x] Ne pas casser le ratio, le cadrage ou la lisibilité des photos.
- [x] Ne pas remplacer le layout choisi par l’utilisateur par une logique propre au design.
- [ ] Vérifier les galeries vides, les galeries avec albums et les galeries avec beaucoup de photos.
- [ ] Vérifier les états de chargement, d’erreur, de retour et de changement de galerie.

### 4. Corriger les détails de chaque design

Pour chaque design global 1 à 5, puis pour les designs historiques conservés :

#### Transitions cohérentes entre les pages

- [x] Créer la transition légère et unique du design 1 et l’utiliser sur toutes les navigations SPA ainsi qu’à la connexion depuis `lock`.
- [x] Créer la transition organique légère et unique du design 2 et l’utiliser sur toutes les navigations SPA ainsi qu’à la connexion depuis `lock`.
- [x] Créer la transition chromatique légère et unique du design 3 et l’utiliser sur toutes les navigations SPA ainsi qu’à la connexion depuis `lock`.
- [x] Créer la transition neo-brutaliste du design 4 et l’utiliser sur toutes les navigations SPA ainsi qu’à la connexion depuis `lock`.
- [x] Créer la transition éditoriale légère et unique du design 5 et l’utiliser sur toutes les navigations SPA ainsi qu’à la connexion depuis `lock`.
- [x] Empêcher les doubles transitions pendant les remplacements imbriqués `lock` → admin/client.
- [x] Maintenir le nouveau contenu masqué jusqu’à la fin de son injection afin d’éviter les flashs visuels.
- [x] Faire inclure `navigation` + `#admin` et `dashboard` dans la confirmation explicite « Oui, appliquer partout », sans casser leurs sélecteurs indépendants.
- [x] Rendre les cinq transitions modulaires avec un état `loading` qui conserve le rideau fermé pendant les opérations longues.
- [x] Remplacer `#charging` à l’ouverture du site et pendant la connexion depuis `lock` par la transition du design actif.
- [x] Créer un indicateur de chargement propre à chacun des designs 1 à 5 sans modifier leurs transitions SPA normales.
- [x] Attendre les vrais signaux de disponibilité du client et du dashboard admin au lieu d’un délai visuel arbitraire.
- [x] Hydrater côté serveur le thème, le design, les couleurs et la paire de polices avant `dataLoader.js` afin d’éviter le flash initial.
- [x] Attendre le chargement de la police choisie sous le rideau initial avant de révéler le head.
- [x] Supprimer les panneaux contact/image de `100vh` sans modifier le formulaire ni sa logique.
- [x] Réduire l’illustration contact et l’intégrer comme élément décoratif autour du formulaire pour les designs 1 à 5.
- [x] Afficher les réseaux sociaux en rangée horizontale sous la composition contact.
- [x] Séparer dans `backContact.js` les zones administrables de l’illustration et des réseaux sociaux.
- [x] Refondre la structure de `#modal-setting-global` sans modifier ses fetchs, IDs ni callbacks de sauvegarde.
- [x] Créer l’ouverture courte et éditoriale propre au design 1, avec fermeture animée et prise en charge de `prefers-reduced-motion`.
- [x] Recomposer pour le design 1 la jauge de stockage, les entrées Réglages/Direction artistique et les actions Fermer/Déconnexion.
- [x] Adapter au design 1 les toggles, carrousels, palettes, sélecteurs de couleurs et choix typographiques.
- [x] Remplacer les animations inline des sous-vues par un moteur de transition commun sans transformer les carrousels.
- [x] Valider visuellement la modal globale design 1 avant de passer au design 2.
- [x] Décliner la refonte complète de la modal globale pour le design 2 Living Glass.
- [x] Adapter dynamiquement le numéro de l’en-tête pendant la prévisualisation des designs.
- [x] Valider visuellement la modal globale design 2 avant de passer au design 3.
- [x] Décliner la refonte complète de la modal globale pour le design 3 Chromatic Studio.
- [x] Valider visuellement la modal globale design 3 avant de passer au design 4.
- [x] Décliner la refonte complète de la modal globale pour le design 4 Professional Contact Sheet.
- [x] Valider visuellement la modal globale design 4 avant de passer au design 5.
- [x] Décliner la dernière refonte de la modal globale pour le design 5 Editorial Issue.
- [x] Couvrir les ouvertures, fermetures, sous-vues, jauges, toggles et réglages de direction artistique des designs 1 à 5.
- [x] Corriger la modal globale vide sur les cinq designs en sécurisant la révélation commune et le montage de la jauge de stockage.
 - [x] Corriger le nettoyage de l'édition des titres (`initialValue`) et empêcher son double déclenchement par blur/fermeture.
 - [x] Remplacer le faux header de la modal globale par une `div` pour éviter les conflits avec le header principal.
 - [x] Agrandir les aperçus de direction artistique du bouton/footer et de la navigation.
 - [x] Retirer les numéros utilisés uniquement comme décoration dans la modal globale.
 - [x] Transformer les aperçus `.button` et `#navigation` en items visuels directs, sans cartes ni étiquettes externes.
 - [x] Refaire `#modal-msg` en plein écran pour les designs 1 à 5, avec une animation et une composition propres à chaque design.
 - [x] Corriger le mapping de `#modal-msg` pour que les designs 1 à 5 correspondent directement au numéro choisi, indépendamment du design du dashboard.
- [ ] Valider visuellement la modal globale design 5 et effectuer une passe comparative finale sur les cinq designs.

- [ ] Corriger les problèmes visuels et les incohérences de cascade CSS.
- [ ] Corriger les espacements, tailles, alignements et hiérarchies typographiques.
- [ ] Corriger les états actifs, hover, focus, disabled et erreurs.
- [ ] Corriger les overlays, modales, boutons et messages de confirmation.
- [ ] Vérifier les interactions entre header, navigation, footer et formulaires.
- [ ] Vérifier les changements de design global et bloc par bloc.
- [ ] Vérifier que les anciennes classes de design sont toujours retirées.
- [ ] Vérifier que les variables dynamiques du thème sont conservées.
- [ ] Vérifier les animations, le scroll-jacking et la restauration du scroll naturel.
- [ ] Vérifier les images, blobs, ombres, bordures et débordements propres à chaque design.
- [ ] Vérifier les pages visiteur, l’espace client et le back-office.

### 4 bis. Refonte UX et visuelle du dashboard et des espaces client

- [ ] Refaire pleinement le dashboard pour les designs 1 à 5, un design après l’autre, sans imposer de rail horizontal, de grille de cards, de liste verticale ou de position de bouton héritée.
- [ ] Reprendre le design 1 comme une véritable direction UX sobre et monochrome, avec une architecture d’information, une hiérarchie et des interactions nouvelles avant toute déclinaison graphique.
- [ ] Remplacer l’aspect historique des cards par une composition UX propre à chaque design sans modifier les fetchs, les routes, les IDs contractuels, les événements ni la logique métier.
- [ ] Repenser séparément les vues projets, shootings, livraisons et clients : chacune peut avoir son propre modèle de navigation, de densité, d’action et de représentation.
- [x] Construire le prototype UX du design 3 `COMMAND WORKSPACE` sans rail horizontal : matrice/console de canaux, outil métier actif, actions contextuelles et planning plein écran.
- [ ] Valider visuellement et fonctionnellement le prototype design 3 sur mobile, tablette et grand écran avant de figer cette direction.
- [ ] Recomposer pour chaque design les modales métier du dashboard : client, rendez-vous, livraison, aperçu, proposition, suivi de projet et aide. Le parcours et les callbacks restent fiables, mais le pattern d’interface est libre.
- [ ] Préserver intégralement `#modal-msg` et `#modal-setting-global` pendant cette refonte.
- [ ] Vérifier avec une attention particulière le suivi de projet complexe, ses étapes, ses actions et toute la partie aide.
- [ ] Refaire les espaces personnels des clients pour les designs 1 à 5.
- [ ] Refaire l’affichage des livraisons côté client pour les designs 1 à 5.
- [ ] Refaire le parcours de signature électronique côté client pour les designs 1 à 5.
- [ ] Valider chaque famille visuelle avant d’engager la passe responsive globale.

### 5. Responsive et mobile-first

- [ ] Revoir les layouts mobiles de l’accueil.
- [ ] Revoir le head et le portfolio sur mobile.
- [ ] Revoir les formulaires, calendriers et prises de rendez-vous.
- [ ] Revoir la navigation et le menu admin.
- [ ] Revoir les modales et BackTicket.
- [ ] Vérifier les interactions tactiles et les animations sur mobile.
- [ ] Vérifier les tablettes et les largeurs intermédiaires.
- [ ] Vérifier les grands écrans après validation mobile.
- [ ] Corriger les débordements horizontaux et les problèmes de hauteur viewport.
- [ ] Vérifier que le scroll naturel est restauré après chaque séquence animée.

### 6. Test complet du SaaS et corrections fonctionnelles

- [ ] Tester l’inscription et la connexion administrateur.
- [ ] Tester la création et le chargement d’un site client.
- [ ] Tester le choix global des designs.
- [ ] Tester le choix des designs bloc par bloc.
- [ ] Tester l’accueil : profil, news, style et prestations.
- [ ] Tester le head et le portfolio avec les designs 1 à 5 et leurs designs historiques conservés.
- [ ] Tester le contact et les réseaux sociaux.
- [ ] Tester les formulaires visiteurs et les réservations.
- [ ] Tester le calendrier et les disponibilités.
- [ ] Tester les clients, rendez-vous, propositions, acomptes et livraisons.
- [ ] Tester l’espace client et les téléchargements.
- [ ] Tester les galeries et leurs protections d’accès.
- [ ] Tester les paiements et les retours de paiement.
- [ ] Tester les uploads, suppressions, recadrages et limites de stockage.
- [ ] Tester les notifications, sockets et mises à jour dynamiques.
- [ ] Tester les erreurs réseau, sessions expirées et rechargements de page.
- [ ] Corriger toutes les erreurs rencontrées.
- [ ] Rejouer les tests après chaque correction importante.

### 7. Grand chantier sécurité final

À démarrer uniquement après la finalisation fonctionnelle, visuelle, responsive et les tests complets.

#### SaaS / `scaly-product`

- [ ] Auditer l’authentification et les sessions.
- [ ] Auditer les rôles administrateur/client et les permissions.
- [ ] Auditer les routes et les fichiers statiques exposés.
- [ ] Auditer les tenants, domaines et séparations de données.
- [ ] Auditer les uploads, téléchargements, PDFs et archives.
- [ ] Auditer les paiements, webhooks et signatures.
- [ ] Auditer les cookies, CORS, CSRF, headers et rate limits.
- [ ] Auditer les secrets, fichiers de configuration et variables d’environnement.
- [ ] Auditer les injections, validations et contrôles de chemins.
- [ ] Auditer les logs, erreurs et informations sensibles.
- [ ] Corriger, tester et documenter chaque vulnérabilité.

#### Site mère de vente

- [ ] Auditer l’authentification et les comptes.
- [ ] Auditer les routes commerciales et administratives.
- [ ] Auditer les paiements et la gestion des abonnements.
- [ ] Auditer les données personnelles et les emails.
- [ ] Auditer les webhooks, fichiers et tâches asynchrones.
- [ ] Auditer les secrets et la configuration de déploiement.
- [ ] Corriger, tester et documenter chaque vulnérabilité.

## Règles de travail pendant les phases fonctionnalité/design/UX

- Ne pas supprimer les designs existants du head et du portfolio : les conserver dans leurs numéros historiques dédiés.
- Ne pas modifier les fetchs, routes, IDs ou callbacks backend pour un changement purement visuel.
- Ne pas confondre conservation de la mécanique et conservation du rendu : le DOM de présentation, la mise en page, la navigation et le modèle d’interaction peuvent être refondus.
- Ne jamais imposer au dashboard une architecture horizontale, quatre cards, des listes répétitives ou un dock d’icônes si le design choisi appelle une autre solution.
- Chaque design doit être évalué sur sa propre logique UX, pas comme une variation de couleurs du dashboard précédent.
- Conserver le choix global et le choix bloc par bloc.
- Toujours retirer les anciennes classes de design avant d’ajouter les nouvelles.
- Utiliser les variables dynamiques du thème ( --c-one et --c-two) plutôt que des couleurs fixes.
- Travailler mobile-first avant les ajustements desktop.
- Éviter les `overflow: hidden` inutiles, la 3D permanente et le blur GPU massif.
- Incrémenter les versions de cache-busting après une modification importante d’un fichier chargé par URL versionnée.
- Préserver les modales, confirmations et callbacks dans leur fonction métier ; leur composition visuelle et leur mode d’ouverture peuvent changer.
- Utiliser des vérifications statiques pendant les phases de construction ; le test navigateur complet intervient dans la phase de validation prévue.

## Critère de fin

Le SaaS est considéré comme prêt pour le chantier sécurité lorsque :

- les designs head et portfolio 1 à 5 sont terminés ;
- les designs historiques du head et du portfolio sont conservés et fonctionnels ;
- tous les détails visuels des designs ont été corrigés ;
- le responsive est validé ;
- toutes les fonctionnalités principales ont été testées ;
- les erreurs fonctionnelles identifiées ont été corrigées ;
- les tests ont été rejoués après correction.
