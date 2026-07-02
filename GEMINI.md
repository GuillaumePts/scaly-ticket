# Projet Scaly-Ticket - La Ferme des Peupliers

## 1. MISSION & CONTEXTE
- **Client** : La Ferme des Peupliers.
- **Objectif** : Remplacer NiceLabel par un moteur Python autonome.
- **Hardware** : Toshiba B-FV4D (203 DPI) et Zebra ZE511/512 (300 DPI).

## 2. DÉVELOPPEMENTS RÉALISÉS
- **Modularité DPI** : Calcul dynamique des coordonnées (8 dots/mm pour 203 DPI, 11.81 dots/mm pour 300 DPI).
- **Moteur Hybride** : Support du **ZPL II** (Zebra) et du **TPCL** (Toshiba).
- **Interface Web** : FastAPI avec gestion des imprimantes (IP, DPI, Langage) et interface de suppression massive.

## 3. RÈGLES MÉTIER
- **Impression Batch** : Traitement de fichiers CSV avec séparateurs visuels automatiques.
- **Transition de Minuit** : DLC et Lot incrémentés dynamiquement pendant le job.

## 4. JOURNAL DES TESTS - TOSHIBA B-FV4D (EXPÉDITION)

### Session du 12 juin 2026 : Le Mystère du Raster XPML
- **Percée Majeure** : L'envoi direct d'une capture binaire driver (`.prn`) via Python (Socket 9100) **fonctionne parfaitement**. Cela valide la connectivité et le port.
- **Analyse du Flux Driver** :
    - Utilise des balises "sentinelles" `<xpml><page...></xpml>` (immédiatement fermées) pour signaler les changements de contexte.
    - Utilise la commande `{D0763,1016,0743|}` où les dimensions sont en **1/10ème de mm** (76.3mm de large).
    - **Hypothèse "Raster Only"** : Toutes les tentatives d'envoi de texte (`PC`) ou de commandes TPCL standard provoquent un **Voyant Rouge**. Le driver, lui, envoie uniquement des commandes `{SG;...}` (Set Graphic) en mode de compression `3`.
- **Conclusion Technique** : L'imprimante (firmware spécifique Ferme des Peupliers) semble verrouillée en mode "GDI / Raster". Elle ne traite pas le langage TPCL de haut niveau.
- **Stratégie pour la suite** :
    1. Implémenter un moteur de rendu graphique (via `Pillow`) pour transformer les étiquettes en bitmaps.
    2. Porter l'algorithme de compression RLE Toshiba (Mode 3) pour réduire la taille des flux `SG`.
    3. Utiliser les balises XPML sentinelles identifiées pour encapsuler ces blocs graphiques.

### Session du 15 juin 2026 : Résolution et Rendu 100% Opérationnel
- **Découvertes Clés** :
    - **Compression TOPIX (Mode 3)** : Notre implémentation de l'algorithme de compression XOR-RLE (Mode 3) correspond désormais à 100% au pilote Seagull officiel octet par octet.
    - **Tronquage des zéros de fin (RLE)** : Le pilote officiel tronque systématiquement tous les octets `0x00` de fin de flux (correspondant aux lignes vides en fin de bloc graphique). Si ces zéros de fin ne sont pas retirés, l'imprimante peut rejeter le job.
    - **Gestion Réseau TCP (Le mystère du job ignoré)** : L'imprimante a besoin de temps pour traiter et stocker le flux graphique. Si la connexion socket est fermée brutalement après l'envoi, le buffer est jeté par la carte réseau de l'imprimante. Pour résoudre ce problème :
        1. Envoyer le flux avec `s.sendall(job)`.
        2. Effectuer une fermeture propre de la moitié d'écriture avec `s.shutdown(socket.SHUT_WR)`.
        3. Attendre au moins `2.0` secondes (`time.sleep(2.0)`) avant de fermer définitivement le socket.
- **Résultat des Tests** : Le test graphique avec rectangle noir et le test complet d'étiquette avec code-barres GS1-128 ont tous les deux fonctionné parfaitement et ont été imprimés sans erreur !

### Session du 18 juin 2026 : Le triomphe sur la limite matérielle et le format usine
- **Découverte Majeure (Le vrai format physique)** : L'imprimante n'a jamais été configurée pour un rouleau continu de 30x115mm. L'analyse du fichier binaire d'usine généré par NiceLabel (`exemplePrn.prn`) a prouvé que la configuration matérielle de l'imprimante (le capteur Gap) est verrouillée sur une **hauteur de 120.1 mm (Pitch 122.1 mm)** et une **largeur de 97.5 mm**. L'étiquette est en réalité une matrice 3-up imprimée en paysage (orientée portrait logiciellement). L'en-tête TPCL strict doit être `{D1221,0975,1201|}`.
- **Contournement de la limite RAM (Le découpage SG)** : La commande `{SG}` de Toshiba provoque un crash mémoire (voyant rouge) si on lui envoie une image trop haute d'un seul bloc. **Règle absolue** : Il faut trancher l'image horizontalement en blocs de maximum **300 dots de hauteur**.
- **Crash des chunks vides** : Si la compression d'un bloc de 300 de haut retourne un payload de 0 octet (bloc totalement blanc), l'envoi d'une commande `{SG}` avec une taille de `0000` octets fait crasher l'imprimante. **Règle absolue** : Ne jamais envoyer de commande `{SG}` vide.
- **Bug du décalage de bits (Gribouillis Pillow)** : La fonction `Image.tobytes()` de Pillow arrondit la taille des lignes à un multiple de 8 bits (1 octet). Si la largeur du canevas en dots n'est pas un **multiple parfait de 8**, la fonction `compress_topix` décale les pixels à chaque ligne de l'image. Cela corrompt la compression XOR et génère du "gribouillis". **Règle absolue** : La largeur `CANVAS_W` doit TOUJOURS être un multiple de 8 (ex: 800 dots pour 100mm au lieu de 780 dots).
- **Fichier de référence final** : `toshiba_test34_alignment.py` contient l'architecture de rendu parfaite : 3 étiquettes de front alignées, découpées en `H=300`, sans chunks vides, alignement multiple de 8 sur 800x1200 dots, avec attente réseau de 2 secondes. Il ne reste plus qu'à ajuster les tailles de police et les espacements pour calquer visuellement sur le rendu usine (`but.jpg`).

### Session du 19 juin 2026 : Le "Holy Grail" Trick, Centrage Absolu et Rafale Réseau
- **Le "Holy Grail" Trick (Fin de la découpe)** : La limite des blocs de `H=300` créait un problème insoluble de "texte mangé" aux bordures de découpe à cause d'une perte de bits matérielle. La solution finale trouvée : l'imprimante refuse les commandes `{SG}` dont l'en-tête dépasse `H=0300`, mais **elle ne vérifie pas la taille réelle du payload**. Le code génère maintenant l'intégralité de la matrice (1200 lignes) en une seule fois et l'envoie dans une unique commande `{SG}` maquillée avec `H=0300`. Résultat : impression fluide, 0 ligne blanche, 0 coupure.
- **Vitesse d'impression (Mode Rafale)** : Le délai obligatoire de 2.0 secondes pour la fermeture propre du socket TCP ralentissait considérablement la production (2 secondes par ticket). Le moteur assemble désormais l'intégralité du lot (séparateurs + toutes les étiquettes) en une seule énorme chaîne binaire et l'envoie via une seule ouverture/fermeture de socket. L'impression se fait désormais en continu (zéro temps mort).
- **Calage Physique (Bavure Droite)** : L'imprimante générait une "bavure d'encre" sur le côté droit de la 3ème étiquette. Cause : le canevas de 800 dots dépassait la largeur physique réelle du rouleau (96mm / 768 dots), forçant la tête à chauffer dans le vide et à faire fondre le ruban sur le cylindre d'entraînement. **Solution** : Largeur du canevas réduite à la constante stricte `TOSHIBA_CANVAS_W = 768`.
- **Centrage Parfait** : Les étiquettes ont été redécalées pour s'aligner de manière chirurgicale dans leurs couloirs de coupe respectifs (Coordonnées : `X=[12, 268, 524]`).
- **Ajustements UX/UI** :
    - Réduction de la taille de la police du Lot à 20 pour éviter l'écrasement.
    - Le texte du haut ("6 Yaourt entier...") a été rapproché de 15 points (Y=25) vers le code-barres.
    - Fix d'un comportement indésirable de l'UI Web : la Dropzone ne se vide plus automatiquement après une impression, permettant de garder sa commande à l'écran. Ajout d'un cache-buster `?v=2` pour forcer la mise à jour JS des navigateurs.

### Session du 22 juin 2026 : Intégration du Format 4-up et Formulaire UI
- **Implémentation du format 4-up** : Le rouleau 4-up est pris en charge avec succès. L'algorithme a été adapté pour générer un canevas de 100mm (800 dots) pour éviter les coupures sur le bord droit.
- **Calage Millimétré** : L'espacement physique de 3mm entre les étiquettes a été parfaitement répliqué (sauts de 200 dots) avec un décalage global à gauche pour contrer l'alignement mécanique de l'imprimante. Résultat : Centrage absolu.
- **Rendu graphique affiné** : Ajustement de la largeur des codes-barres (`module_width=0.40`), réduction de la police à 22 pour éviter les dépassements, et formatage standardisé du texte EAN-13 (avec les espaces) calculé manuellement sous les barres via Pillow.
- **Création dynamique (UI)** : Ajout d'un formulaire pour créer de nouveaux parfums directement depuis l'interface Web avec un aperçu visuel en direct généré par le backend.

### Session du 25 juin 2026 : Intégration Ligne 1 (Zebra 1-up) et Calibrage Visuel
- **Intégration Zebra (1-up)** : Support total du format 1-up pour l'imprimante Zebra ZE511 (Ligne 1). Désactivation du séparateur `>>> PARFUM <<<` (spécifique à la Toshiba).
- **Calibrage Pixel-Perfect (Interface)** : Création d'une interface de "Calibrage Visuel" directement dans le navigateur. L'utilisateur peut déplacer l'aperçu de l'étiquette pixel par pixel, traduisant le déplacement CSS (`left`/`top`) en offsets ZPL natifs (`offset_x`, `offset_y`). 
- **Rotation de rendu (Orientation Web vs Hardware)** : Le moteur graphique ZPL de la Zebra retourne par défaut l'image en portrait matériel (352x1144). Pour l'afficher correctement en paysage sur l'interface Web (1144x352), une transposition `Image.ROTATE_270` a été ajoutée sur la route de prévisualisation API (`/api/preview-zebra-1up`).
- **Pydantic Validation Fix** : La route de prévisualisation API a été sécurisée en injectant des "dummy variables" (`Client`, `Commande`, etc.) pour satisfaire la validation stricte de `TicketData` et éviter l'Erreur 500.
- **Prochaines Étapes** : Étendre l'API pour la création personnalisée de formats d'étiquettes, et développer des options de calibrage encore plus poussées (orientations, marges avancées).
### Session du 2 juillet 2026 : Intégration de la Toshiba B-EV4 (Gravigny) et Ajustements de Précision
- **Le Mystère du Pitch XPML (B-EV4 vs B-FV4D)** : La B-FV4D (Prépa commande) exige l'attribut `pitch='120.1 mm'` dans la balise d'ouverture `<xpml><page...`. À l'inverse, la **B-EV4 (Gravigny)** rejette strictement cet attribut (elle passe au rouge). Le code détecte désormais le secteur "Gravigny" dans le `printers.json` pour omettre dynamiquement le pitch.
- **La Sécurité Matérielle du Pixel 0** : La B-EV4 refuse d'imprimer (et n'avance même pas le papier) si l'image générée dans la commande `{SG}` contient des pixels noirs positionnés exactement sur le premier pixel du bord gauche (`X=0`). Il est impératif de conserver une marge physique de départ (actuellement fixée à `X=12`) pour éviter de déclencher cette sécurité.
- **Calibrage du Pitch (Entraxe) au Pixel-Perfect** : Le décalage progressif de l'impression (ex: +1mm sur l'étiquette 2, +2mm sur la 3) était dû à un écart numérique par rapport à la mécanique. L'entraxe physique de la bande (30mm d'étiquette + 3mm de gap) fait très exactement 33mm, soit **264 dots** à 203 DPI. L'algorithme place désormais les étiquettes rigoureusement tous les 264 points (`x_offsets = [12, 276, 540]`). Pour que la dernière étiquette ne déborde pas de la limite matérielle des 768 dots de la tête d'impression, la zone virtuelle de dessin a été rétrécie de 240 à 224 dots (28mm). Résultat : un centrage absolu sur les 3 couloirs.
- **Fermeture Réseau Asynchrone (Le crash des grosses quantités)** : Lors d'impressions de grosses quantités (ex: 30 étiquettes = 10 bandes), la B-EV4 a besoin d'environ 15 secondes pour terminer physiquement le job. La fermeture de la connexion TCP (Socket) après le délai fixe de 2.0 secondes interrompait la communication réseau, ce qui provoquait une annulation matérielle immédiate par le firmware.
    - **Solution** : L'envoi TCP est désormais délégué à une tâche de fond asynchrone (`BackgroundTasks` de FastAPI). Le serveur calcule dynamiquement un temps de maintien de connexion TCP (`total_rows * 1.5s`) pour laisser l'imprimante finir sereinement, tout en répondant instantanément à l'interface Web (zéro temps d'attente pour l'utilisateur).

## 5. PENSE-BÊTES & CONCEPTS CLÉS
- **Hydration (State Injection)** : Injecter l'état initial depuis le backend directement dans le code source HTML (via `{{ variable|tojson }}` en Jinja2, ou `<%- JSON.stringify(var) %>` en EJS/Node.js). Cela permet d'éviter les requêtes `fetch()` asynchrones au premier chargement et d'obtenir un affichage instantané des données (excellent pour optimiser l'ouverture d'un SaaS).
