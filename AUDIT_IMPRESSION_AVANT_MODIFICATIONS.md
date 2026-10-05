# Référence d'impression avant modifications — 2026-10-01

Ce fichier fige **l'analyse de l'état actuel**, avant toute intervention sur les requêtes d'impression. Il ne modifie ni le moteur ni les réglages. Son objectif est de servir de carte de lecture et de référence de comparaison, en particulier pour les Toshiba sensibles au flux exact. Les structures ci-dessous décrivent le code présent à cette date, **pas une promesse de compatibilité avec tout firmware**.

## Point de restauration et intégrité

- Branche au moment de l'audit : `dev` ; commit : `72f6eb0d23ff48259e17d1e8687fcf373d94963b`.
- `src/main.py`, `src/zpl_engine.py`, `src/printer.py`, `src/models.py` et `src/config.py` étaient identiques à ce commit. `static/script.js`, `static/style.css` et `templates/index.html` avaient déjà des changements locaux d'interface ; **ne pas utiliser le commit seul pour restaurer l'interface**.
- La configuration `.env`, la base SQLite, les adresses d'imprimantes et le dossier `ScalyTicket/` sont des données locales : ils ne sont pas sauvegardés ici.
- Empreintes SHA-256 au moment de l'audit :

  | Fichier | SHA-256 |
  | --- | --- |
  | `src/main.py` | `ce4b35599e0ce4ba6b0c95262a61cc772996f12e259c7bdc9dc443e0736acdd9` |
  | `src/zpl_engine.py` | `4fda406b2105a0867c60b421edf3c9d9c56716e43f7faf3c84df8578b911b607` |
  | `src/printer.py` | `7aa586c16c609abc7d95a8ae499e4861a0a2d57724ef44d2a3c4404b65a24ca8` |
  | `src/models.py` | `025c931c6a3145c8b13c91f598dcf2659a9597220ca342a8012cdbcf822f6777` |
  | `src/config.py` | `79598eb2ba90b96177b083b15ee7e5452b3df7a3ed706ea565328990c2dd76f6` |
  | `static/script.js` (interface locale, non committée) | `7c8aa0b2e7efe603cff3a60280d2513d31ba6b73dbe31602838cc4da15a3c80a` |
  | `prn_file_exemple/TOSHIBA-BFV4.prn` | `4be845704d36bf65196b3bf4adfaa1a008c2017fac0e20c849c1fe74a6c9e064` |

Pour **consulter** une version antérieure du moteur sans changer le répertoire de travail : `git show 72f6eb0d23ff48259e17d1e8687fcf373d94963b:src/zpl_engine.py` (adapter le chemin pour les autres fichiers). Avant une éventuelle restauration, comparer avec `git diff` et sauvegarder tout nouveau travail : restaurer directement depuis Git écraserait les modifications intervenues depuis. Une empreinte seule permet de vérifier l'identité d'un fichier, pas de recréer son contenu ; la référence récupérable du moteur est le commit indiqué.

## Circuit commun

1. L'interface (`static/script.js`) envoie du JSON aux routes FastAPI de `src/main.py`.
2. `src/zpl_engine.py` produit le flux complet, TPCL binaire Toshiba ou ZPL Zebra.
3. Une file `asyncio.Queue` **en mémoire**, distincte par IP, sérialise les jobs (`enqueue_job` et `spooler_worker`, `src/main.py:72-128`). Elle disparaît au redémarrage.
4. `PrinterClient(host=ip)` ouvre un socket TCP **9100** par défaut. Même si la base mémorise un champ `port`, les routes observées ne le transmettent pas au client (`src/printer.py:9`, `src/main.py:86`).
5. `send_zpl` encode la chaîne en `latin-1` : c'est un aller-retour volontaire `bytes -> str -> bytes` pour préserver chaque octet binaire TPCL. Pour TPCL, `sendall`, délai de maintien, `shutdown(SHUT_WR)`, fermeture. Jusqu'à trois tentatives ; en cas d'envoi partiel suivi d'une erreur, une répétition d'étiquettes reste possible (`src/printer.py:74-126`).
6. Le HTTP 200 signifie **mis en file d'attente**, pas imprimé. Le WebSocket signale le résultat de l'envoi TCP, pas un acquittement d'impression matérielle. Le `XS` employé demande explicitement aucune réponse de statut.

Le statut `/printer-status` ouvre TCP puis envoie `~HS`, commande de statut Zebra. Sur Toshiba, un délai d'attente est interprété comme « connexion présente, statut inconnu » ; cela ne vérifie pas papier, capot ou succès d'impression (`src/printer.py:13-45`, `src/main.py:603-612`). En mode simulation, le dernier job seulement est écrit dans `data/last_simulation_output.prn` ; il est remplacé au job suivant.

## Syntaxe Toshiba TPCL graphique commune

Le constructeur de production est `_build_tpcl_job(images_and_qtys, xpml_pitch=True, d_param=None)` (`src/zpl_engine.py:211-252`). Chaque élément `images_and_qtys` est un couple `(bitmap Pillow, nombre de bandes)`. Le contenu exact, hors octets de l'image, est :

```text
<xpml><page quantity='0' pitch='120.1 mm'></xpml>{D1221,0975,1201|}\r\n
<xpml></page></xpml><xpml><page quantity='1' pitch='120.1 mm'></xpml>{C|}\r\n
{SG;0000,0000,0768,0300,3,[2 OCTETS DE LONGUEUR][PAYLOAD TOPIX BINAIRE]|}\r\n
{XS;I,0002,0002C5000|}\r\n
<xpml></page></xpml><xpml><end/></xpml>\r\n
```

Cet exemple correspond à **2 bandes 3-up B-FV4D**. Les retours à la ligne montrés comme `\r\n` sont réellement les octets CR LF ; il n'y a **pas** de CR LF entre la fermeture de page et la nouvelle ouverture XPML. Le flux est binaire : le payload peut contenir des octets arbitraires, donc ne pas parser un `.prn` par simple recherche de `|}`. Les 2 octets de longueur sont en ordre gros-boutiste. La compression n'a pas de garde explicite pour une longueur supérieure à 65535 octets.

### Signification des commandes

- Les balises `<xpml>...` sont les enveloppes/sentinelles recopiées du flux du pilote. Si `xpml_pitch=False`, **les deux** ouvertures de page deviennent `<xpml><page quantity='0'></xpml>` et `<xpml><page quantity='1'></xpml>` ; l'attribut `pitch` est supprimé, le reste inchangé. Le choix est fait par `sector == "Gravigny"` **ou** `name == "TOSHIBA FLIPOU"` ; toute IP non reconnue reçoit le mode avec pitch (`src/main.py:528-532`, `:360-369`). Les notes de terrain `GEMINI.md:71-76` attribuent à la B-EV4 un rejet du pitch ; cela n'a pas été revérifié physiquement pendant cet audit.
- `{D1221,0975,1201|}` : pas de 122,1 mm, largeur efficace de 97,5 mm, longueur efficace de 120,1 mm. Un autre `d_param` peut être fourni **uniquement pour le 4-up B-EV4** depuis `d_param_4up` en base ; sinon cette valeur est utilisée. Toshiba documente `D` en dixièmes de mm.
- `{C|}` efface le tampon graphique avant chaque image.
- `{SG;0000,0000,WWWW,0300,3,...|}` : coordonnées de départ X/Y ici `0000,0000` (unités Toshiba : dixièmes de mm), `WWWW` largeur du bitmap en **points**, `0300` = **résolution TOPIX 300 dpi**, `3` = mode TOPIX. Selon la spécification Toshiba B-FV4, `0300` n'est **pas** la hauteur du bitmap. La hauteur effective n'est pas écrite comme nombre dans cet en-tête ; le code compresse `img_h` lignes entières et insère le résultat après sa longueur binaire. Ne pas « corriger » `0300` en hauteur de canevas.
- Compression `compress_topix` (`src/zpl_engine.py:58-112`) : l'image Pillow monochrome est inversée bit à bit, chaque ligne est comparée à la précédente par XOR, et les octets changés sont signalés par trois niveaux de masques (blocs 512/64/8 points). Les zéros finaux sont retirés. La largeur du canevas doit rester multiple de 8 pour l'alignement des octets. La marge gauche de 12 points est forcée au blanc pour les bandes Toshiba.
- `{XS;I,NNNN,0002C5000|}` : `NNNN` = **nombre de bandes à imprimer**, sur quatre chiffres. Le suffixe se lit `000` sans coupe, `2` capteur transmissif, `C` batch, `5` vitesse sélectionnée, `0` sans ruban, `0` orientation normale, `0` sans réponse de statut (spécification Toshiba B-FV4). Ce suffixe est codé en dur et partagé par les formats graphiques Toshiba.

La spécification primaire de ces champs est [Toshiba B-FV4 External Equipment Interface Specification](https://business.toshiba.com/downloads/KB/f1Ulds/12666/B-FV4_IF_Spec_2nd.pdf), sections `D`, `C`, `SG` TOPIX et `XS`. Le fichier `prn_file_exemple/TOSHIBA-BFV4.prn` est une référence de pilote différente du générateur actuel : il contient **13 commandes SG** (première : `{SG;0024,0095,0440,0300,3,...}`), puis `{XS;I,0001,0002C5000|}`. Le générateur actuel emploie **une seule SG par image**, origine `0000,0000`, et compresse tout le canevas. Ne pas confondre la capture du pilote avec le flux généré aujourd'hui.

### Incohérences apparentes à préserver avant validation matérielle

Les notes historiques `GEMINI.md:42-47` évoquent un découpage en blocs de 300 points et un risque de crash avec une grande `SG` ; **le code actuel ne découpe pas** les bandes graphiques : il compresse par exemple 768 × 1200 points dans une seule `SG`. Le champ `0300` était assimilé à une hauteur dans certains commentaires, mais la documentation Toshiba le définit comme une résolution TOPIX. De même, le canevas 3-up fait 1200 points de long alors que `D` annonce 120,1 mm de longueur efficace. Ce sont des observations exactes du code ; l'incidence physique de ces écarts dépend de l'imprimante, du pilote et du support. **Ne pas normaliser ces valeurs à l'aveugle.**

## Formats et requêtes API actuels

### 1. Toshiba 3-up standard — `/print-json`

Requête HTTP JSON type (les autres options `title_size`, `title_bold`, `gs1_size`, `gs1_bold`, `lot_size`, `lot_bold` sont facultatives) :

```json
{
  "printer_ip": "192.0.2.10",
  "printer_dpi": 203,
  "printer_language": "TPCL",
  "offset_x": 0,
  "offset_y": 0,
  "items": [{
    "Client": "EXEMPLE",
    "Commande": "C-001",
    "DateLivraison": "2026-10-01",
    "Libelle": "Produit test",
    "CodeBarre01": "01234567890123",
    "CodeBarre17": "261231",
    "CodeBarre10": "LOT1",
    "Numlot": "LOT1",
    "Quantite": 5
  }]
}
```

`TicketData` accepte ces alias CSV ou les noms Python (`client`, `commande`, `date_livraison`, `libelle`, `gtin`, `date_expiration`, `lot`, `num_lot_display`, `quantite`), sans validation métier forte du GTIN/date (`src/models.py`). Le moteur dessine une étiquette de 920 × 224 points, avec libellé, GS1-128 composé de `01{GTIN}17{AAMMJJ}10{LOT}`, texte lisible et lot/DLC ; rotation à 224 × 920, puis trois copies aux X **12, 276, 540** sur un canevas **768 × 1200**. `offset_x/y` décale les images avant compression (`src/zpl_engine.py:123-209`).

Le nombre de bandes est `ceil(Quantite / 3)` ; ainsi 5 demandées donnent `XS;I,0002,...`, soit 6 positions imprimées, sans masquage de la dernière. Au-delà de 2000 bandes, plusieurs flux TPCL complets sont concaténés dans un même job TCP (`src/main.py:562-570`). Délai de maintien TCP : `max(2, total_bands × 1,5)` secondes. Un séparateur graphique est prévu entre produits, mais **il est cassé actuellement** : `generate_separator_tpcl` passe une `Image` au lieu de `[(Image, 1)]` à `_build_tpcl_job`, ce qui produit `TypeError: 'Image' object is not subscriptable` avant la mise en file pour deux produits ou plus (`src/zpl_engine.py:282-313`, `src/main.py:541-544`). Le calcul `days_offset` de cette route n'est pas appliqué aux données imprimées.

### 2. Toshiba 4-up parfums — `/print-4up`

Requête type :

```json
{
  "printer_ip": "192.0.2.10",
  "printer_dpi": 203,
  "printer_language": "TPCL",
  "items": [{"parfum_id": "ID_EN_BASE", "quantity": 5}],
  "offset_x": 0,
  "offset_y": 0
}
```

L'ancien couple `parfum_id`/`quantity` à la racine est aussi accepté si `items` est vide (`src/main.py:350-354`). Chaque parfum est recherché en SQLite ; `nom`, `ean13` et parfois `nom_impression` servent à dessiner le bitmap. Pour les RGF, certains visuels sont extraits des fichiers ZPL `fichierprn/*.prn` ; la Figue RGF a un QR Code particulier (`src/zpl_engine.py:493-611`).

Une bande contient 4 copies. B-FV4D : canevas **800 × 344**, étiquette source 344 × 176, X `0,200,400,600` puis blanc forcé sur X `0..11`. B-EV4 : canevas **768 × 360**, source 344 × 168, mêmes X et même marge. En B-EV4, les `offset_x_4up`, `offset_y_4up`, `d_param_4up` enregistrés en base prennent le pas sur les décalages envoyés dans le JSON (`src/main.py:360-373`, `src/zpl_engine.py:613-637`).

`ceil(quantity / 4)` bandes par parfum ; 5 demandées donnent 2 bandes donc 8 positions. Le flux contient **un seul en-tête `D`**, puis pour chaque parfum une nouvelle page XPML, `{C|}`, une `{SG;0000,0000,0800,0300,3,...|}` sur B-FV4D ou largeur `0768` sur B-EV4, et `{XS;I,NNNN,0002C5000|}`. Un seul footer clôt le lot. Délai TCP : `max(2, total_bands × 0,5)` secondes (`src/main.py:384-405`, `src/zpl_engine.py:254-270`). `generate_separator_4up_tpcl` existe mais n'est pas appelé ici et est également cassé (argument `quantity` inexistant).

Squelette exact d'un lot de **deux parfums B-FV4D**, hors octets variables. `page_1` et la fermeture précédente sont directement accolés ; la deuxième image n'a ni nouveau `D` ni nouveau footer :

```text
<xpml><page quantity='0' pitch='120.1 mm'></xpml>{D1221,0975,1201|}\r\n
<xpml></page></xpml><xpml><page quantity='1' pitch='120.1 mm'></xpml>{C|}\r\n
{SG;0000,0000,0800,0300,3,[2 OCTETS][TOPIX PARFUM A]|}\r\n
{XS;I,0002,0002C5000|}\r\n
<xpml></page></xpml><xpml><page quantity='1' pitch='120.1 mm'></xpml>{C|}\r\n
{SG;0000,0000,0800,0300,3,[2 OCTETS][TOPIX PARFUM B]|}\r\n
{XS;I,0001,0002C5000|}\r\n
<xpml></page></xpml><xpml><end/></xpml>\r\n
```

En B-EV4, enlever ` pitch='120.1 mm'` des trois ouvertures de page, remplacer la largeur `0800` par `0768` et substituer éventuellement le `D` configuré en base.

### 3. Toshiba Fromis 3-up — `/api/fromis/print`

```json
{"printer_ip": "192.0.2.10", "label_name": "NOM_DANS_LABELS_JSON", "quantity": 5}
```

Le texte vient de `etiquette_allemand/labels.json`; `label_name` doit y exister. Le canevas fait **768 × 400**, trois exemplaires d'une étiquette **400 × 240** pivotée, X `12,276,540`, marge X `0..11` blanche. Le flux est propre à Fromis : XPML **sans pitch**, `{D0520,0975,0500|}`, `{C|}`, `{SG;0000,0000,0768,0300,3,...|}`, `{XS;I,NNNN,0002C5000|}`, footer identique. `NNNN = ceil(quantity/3)` ; 5 demandées donnent 6 positions. Délai TCP fixe de 2 s ; contrôle de quantité 1 à 9999 **avant** arrondi (`src/main.py:445-477`, `src/zpl_engine.py:925-1053`).

```text
<xpml><page quantity='0'></xpml>{D0520,0975,0500|}\r\n
<xpml></page></xpml><xpml><page quantity='1'></xpml>{C|}\r\n
{SG;0000,0000,0768,0300,3,[2 OCTETS][TOPIX FROMIS]|}\r\n
{XS;I,0002,0002C5000|}\r\n
<xpml></page></xpml><xpml><end/></xpml>\r\n
```

### 4. Nature 4-up historique — `/print-nature`

```json
{"printer_ip": "192.0.2.10", "printer_dpi": 203, "printer_language": "TPCL", "quantity": 5}
```

Cette route emploie **un autre générateur** que le 4-up parfums : commandes TPCL/ESC textuelles, démarrant exactement par `\x1bAX\x1bAY\x1b{D0430,1000,0380|}\x1bC`. Chaque ligne ajoute `\x1bL`, des champs `\x1bPC001;...` et `\x1bB00;...` pour « Yaourt Nature », « 2 x 125gr » et l'EAN codé en dur `3412345678901`, puis `\x1bXS\x1bI` (`src/zpl_engine.py:401-426`). Les X sont `0,192,384,576`. La dernière ligne ne dessine que le nombre restant : 5 donne 4 + 1, **sans surimpression jusqu'à 8**. Le comportement réel sur les Toshiba sensibles au raster n'a pas été revalidé ici. Cette route accepte aussi `printer_language != "TPCL"` et produit alors le ZPL Nature ci-dessous (`src/main.py:199-223`).

Schéma d'une bande (ici la première position) ; `\x1b` désigne l'octet ESC, pas quatre caractères visibles :

```text
\x1bAX\x1bAY\x1b{D0430,1000,0380|}\x1bC
\x1bL
\x1bPC001;0020,0050,10,10,k,00,B=Yaourt Nature|
\x1bPC001;0035,0090,08,08,k,00,B=2 x 125gr|
\x1bB00;0025,0140,2,2,050,0,0,1,0,3412345678901|
... autres positions de la bande ...
\x1bXS\x1bI
```

### 5. Zebra 300 dpi, carton 1-up — `/print-json` avec `printer_language: "ZPL"`

Même schéma de `items` que le 3-up, mais une image individuelle **1144 × 352** avec GS1-128 est pivotée à **352 × 1144** puis émise comme ZPL graphique hexadécimal : `^XA\n^FO{offset_x},{offset_y}\n^GFA,{N},{N},{octets_par_ligne},{HEX}\n^PQ1,0,1,Y\n^XZ`. Une commande complète par unité demandée, concaténée dans le job (`src/main.py:585-589`, `src/zpl_engine.py:691-800`). La fonction `generate_ticket_zpl` en ZPL textuel 3-up existe dans le moteur, mais **ce n'est pas la branche utilisée** par cette route actuelle.

```text
^XA
^FO800,18
^GFA,50336,50336,44,[IMAGE HEXADÉCIMALE]
^PQ1,0,1,Y
^XZ
```

Ici `50336 = 352 / 8 × 1144` octets de bitmap brut ; chaque octet est représenté par deux caractères hexadécimaux. Les coordonnées `800,18` sont les valeurs par défaut du modèle API et peuvent être écrasées par l'interface.

### 6. Zebra 203 dpi, pots 2-up — `/print-json` avec `printer_language: "ZPL"`, `printer_dpi: 203`

Le serveur cherche un parfum correspondant au libellé, prend son EAN-13 et calcule `ceil(Quantite / 2)` lignes. Chaque ligne standard contient deux emplacements texte + EAN-13 dans `^XA ... ^PQ{nombre_de_lignes},0,1,Y ^XZ` (`src/main.py:572-584`, `src/zpl_engine.py:825-859`). Pour un nom contenant `RGF`, si `fichierprn/{nom_sans_RGF}.prn` existe, le flux **brut** de ce fichier est utilisé et tous ses motifs `^PQ` suivis de chiffres sont remplacés par la quantité calculée ; sinon repli sur le ZPL standard. Cette route peut donc envoyer des octets provenant d'un `.prn` préexistant, et non du moteur graphique Toshiba. Si quantité impaire, la dernière ligne standard a encore deux positions : 5 demandées deviennent 6 positions.

```text
^XA
^CI28
^FO92,16^A0N,25,25^FD{nom}^FS
^BY2,2,56^FT122,106^BEN,,Y,N^FD{ean13}^FS
^FO540,16^A0N,25,25^FD{nom}^FS
^BY2,2,56^FT565,106^BEN,,Y,N^FD{ean13}^FS
^PQ{nombre_de_lignes},0,1,Y
^XZ
```

### 7. Nature 4-up ZPL historique — `/print-nature` avec une autre langue

Une page `^XA ... ^XZ` par bande, largeur `^PW800` et longueur `^LL344` à 203 dpi, champs texte `^A0N` et code-barres `^BE` aux X `0,192,384,576`. Comme en TPCL Nature, la dernière bande ne dessine que les positions restantes (`src/zpl_engine.py:373-399`, `:428-447`).

### Entrée CSV historique — `/upload-csv`

Cette route accepte un fichier UTF-8 à séparateur `;` avec les neuf colonnes de `TicketData`, plus `printer_ip`, `printer_dpi`, `printer_language` en formulaire. Elle génère une bande TPCL par ligne physique, peut actualiser DLC/lot en cours d'impression, puis appelle **directement** `printer.send_zpl(full_flux)` au lieu de la file asynchrone (`src/main.py:636-706`). Plusieurs lignes produit TPCL rencontrent le même bug de séparateur que `/print-json`. La branche ZPL référence `offset_x` et `offset_y` sans les définir : elle échoue si elle est exécutée. À considérer comme chemin historique, non comme référence fiable du circuit moderne.

## Vérifications non matérielles effectuées pour cette référence

- Génération en mémoire, avec données fictives et **sans socket** : 3-up `D1221,0975,1201` / `SG` largeur `0768` / `XS` 2 ; 4-up B-FV4D `SG` largeur `0800` ; 4-up B-EV4 largeur `0768` sans attribut `pitch` ; Fromis `D0520,0975,0500` ; Nature historique démarre par la séquence ESC ci-dessus ; Zebra pots démarre par `^XA` ; Zebra carton contient `^GFA`.
- Comparaison structurelle avec `prn_file_exemple/TOSHIBA-BFV4.prn` : en-tête XPML + `D`, 13 blocs `SG` à longueur binaire cohérente, `XS`, footer.
- Reproduction du bug de séparateur 3-up : `TypeError: 'Image' object is not subscriptable`.
- Aucune impression physique, aucun appel aux IP de production, aucune modification du moteur pour constituer ce document.

## Règle pratique avant les prochaines modifications

Modifier **un seul paramètre du flux à la fois**, conserver un `.prn` généré avant/après et comparer les octets autour de XPML, `D`, `SG` (dont les deux octets de longueur), `XS` et du footer. Ne pas conclure d'un HTTP 200 que l'imprimante a effectivement sorti l'étiquette. Pour une marche arrière, revenir aux fichiers du commit cité après avoir examiné le diff ; pour l'interface locale non committée, prévoir une sauvegarde séparée si elle doit elle aussi être restaurable.
