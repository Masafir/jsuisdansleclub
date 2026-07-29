# Décisions techniques — jsuisdansleclub

Jeu de rythme multijoueur en ligne dans le navigateur (voir CONTEXT.MD pour la vision).

## Stack retenue (27 juil. 2026)

| Domaine | Choix | Pourquoi |
|---|---|---|
| Backend temps réel | **Go** | Perf/frustration optimal, goroutines = 1 room ou 1 connexion par goroutine, maintenance simple |
| Netcode | **Protocole binaire maison sur WebSocket brut** | La partie instructive du netcode (sérialisation, ticks, synchro d'horloge) sans réinventer le transport |
| Front | **React** (lobby, menus) + **PixiJS** (rendu du jeu en WebGL) | React suffit pour l'UI, le gameplay doit être en canvas/WebGL |
| Audio client | **Web Audio API** — `AudioContext.currentTime` est l'horloge maîtresse du gameplay | Seule horloge assez précise ; jamais `Date.now()`/`requestAnimationFrame` pour juger les hits |
| Pipeline partitions | **Service Python** : `yt-dlp` (téléchargement audio YouTube) + `librosa` (beat tracking / détection d'onsets) → génère la partition (JSON) | Expérience cible dès le MVP : coller une URL YouTube |

## Gameplay retenu (27 juil. 2026)

**Format Taiko** : une seule lane horizontale, les notes défilent de droite à gauche vers une ligne de jugement fixe. Deux types de notes : `DON` (centre, touches F/J) et `KA` (bord, touches D/K).

Pourquoi plutôt que 4 lanes verticales (DDR/osu!mania) ou un chemin façon *A Dance of Fire and Ice* :
- Une bande horizontale libère tout l'écran pour les **danseurs**, qui sont le cœur social du jeu. Des lanes verticales mangent l'espace, surtout à plusieurs joueurs.
- Rendu le plus simple : un seul axe, un seul point de jugement.
- La **génération auto** s'y prête : un onset = une note, le type se déduit d'une heuristique simple (accent/downbeat vs contretemps). ADOFAI repose sur des partitions dessinées à la main → incompatible avec la génération depuis un MP3, qui est la feature signature du projet.
- Deux touches restent accessibles à des joueurs non initiés.

Fenêtres de jugement : ±40 ms `PERFECT`, ±90 ms `GOOD`, au-delà `MISS`.

## Scénario du MVP

1. Écran d'accueil : champ pour coller une **URL YouTube**, ou choix d'un morceau dans la **bibliothèque** locale.
2. Chargement : téléchargement + décodage de l'audio, génération de la partition.
3. **Décompte 3 / 2 / 1**, puis lancement du son.
4. Le joueur joue.
5. **Règle de survie** (« danse mortelle ») : le ratio de réussite doit rester ≥ 50 %. La vérification est **continue mais activée seulement après le premier tiers du morceau** (période de grâce : sans elle, un raté sur les premières notes tuerait immédiatement).
   - Ratio < seuil après la grâce → **Game over**, le morceau s'arrête.
   - Ratio ≥ seuil jusqu'au bout → **« Bravo, vous avez survécu à la danse mortelle »**.
6. Écran de stats, avec possibilité de rejouer le morceau ou d'en choisir un autre.

## Règles de code

- **AUCUN magic number.** Toutes les valeurs de gameplay (fenêtres de jugement, points, combo, seuil de survie, période de grâce, vitesse de défilement, durées d'animation, décompte) sont centralisées dans `client/src/config/gameplay.ts`. Les couleurs et gradients dans `client/src/config/theme.ts`. Aucune constante numérique en dur ailleurs dans le code.

## Feedback joueur (MVP)

- **Pulsations lumineuses** à chaque appui : rouge = échec, vert = réussite, arc-en-ciel = parfait.
- **3 SFX courts** : réussite, échec, parfait (fournis par amiral, déposés dans `client/public/audio/`).
- Direction artistique : **ambiance disco**, gradients rose / orange / rouge / violet / bleu.

## Décisions de gameplay et d'UI (28 juil. 2026)

- **Les notes ratées continuent de défiler** jusqu'à sortir de l'écran par la gauche ; seules les notes réussies disparaissent à la ligne de jugement. Sans ça, réussite et échec produisaient la même disparition et le joueur ne savait pas ce qu'il venait de faire — surtout quand deux notes proches s'effaçaient ensemble. La disparition devient donc la récompense.
- **Rappel des touches dans l'ordre physique du clavier** (D F | J K), un disque par touche rempli de la couleur de sa note. Grouper par type de note (F/J d'un côté, D/K de l'autre) masquait l'entrelacement réel des doigts. L'ordre est décrit par `KEY_LAYOUT` dans la config, car il ne se déduit pas de `KEY_BINDINGS`.
- **Volumes centralisés dans une table de mixage** (`MIX`) : volume général, musique, et un volume par effet sonore. La musique passe par un `GainNode` au lieu d'attaquer la sortie en direct, ce qui la rend réglable et ouvre la voie aux automations (fondu au game over, atténuation pendant un taunt).
- **La partition de test est du code, pas un JSON** (`client/src/chart/testChart.ts`) : elle génère les notes procéduralement. Le format JSON n'apparaîtra qu'avec le pipeline, quand il faudra transporter des partitions générées.
- **Un prototype d'estimation de tempo est conservé** dans `pipeline/prototype/` : sans dépendance (ffmpeg seul), il donne BPM et offset d'un morceau. Il ne remplace pas librosa — il travaille sur l'énergie totale, pas sur le flux spectral — mais il documente la méthode et dépanne pour caler une partition à la main.

## Générateur expérimental `--new-gen` (29 juil. 2026)

Une seconde piste de génération, **isolée derrière un drapeau CLI**, pour tester des techniques plus fines sans toucher à la génération en service. Issue d'une analyse comparative avec une beatmap osu! taiko de *Haruka Kanata*.

**Principe d'isolation, non négociable** : toutes les constantes `--new-gen` valent `False` par défaut, et c'est la CLI qui les lève. Un défaut à `True` suffit à modifier le mode legacy dès qu'un appel oublie de vérifier le mode — c'est exactement ce qui s'est produit avec HPSS, appliqué inconditionnellement, qui divisait par deux le nombre de notes de l'ancienne génération. Critère de non-régression : `--legacy` doit produire un fichier **bit-à-bit identique** à l'existant (vérifié sur Haruka Kanata).

Techniques ajoutées, toutes sous drapeau :
- **HPSS** (`USE_HPSS`) : sépare harmonique et percussif, pour que la guitare et les synthés ne produisent plus d'onsets.
- **Backtracking d'onsets** (`USE_ONSET_BACKTRACK`) : recale le pic du flux spectral sur le minimum d'énergie qui le précède, c'est-à-dire sur l'attaque réelle plutôt que sur son sommet.
- **Grille adaptative** (`USE_ADAPTIVE_GRID`) : subdivisions 2/3/4/6/8/12 choisies localement selon la densité d'onsets, au lieu du couple fixe croches/doubles. Permet les triolets et les roulements.
- **Segmentation structurelle** (`USE_STRUCTURE_GUIDANCE`) : MFCC + clustering agglomératif → couplet/refrain/pont, qui oriente le choix du lead.
- **Forçage KA sur caisse claire** (`SNARE_KA_BOOST`, `SNARE_BEAT_TOLERANCE_S`) : les temps 2 et 4 portant une attaque médium deviennent des KA.
- **Finishes** (`DETECT_FINISHES`) : grosses notes sur crêtes spectrales larges (cymbales, crashes).

### La règle d'alternance, mesurée sur des maps humaines

Les beatmaps osu!taiko officielles de *Haruka Kanata* (quatre difficultés, mappeur Tachibana_) donnent une convention **identique à tous les niveaux** : longueur médiane d'une série d'une même couleur = **1**, maximum = **4 ou 5**, ratio DON/KA entre **45 et 52 %**. Seule la densité varie (1,76 à 5,10 notes/s) — c'est elle le levier de difficulté, pas l'alternance.

Notre générateur produisait des séries de **37 notes** de la même couleur. Cause structurelle : trois pistes sur quatre sont monochromes à la source — `bass` fournit 229 DON et 0 KA, `vocals` 0 DON et 256 KA, `other` 1 DON et 253 KA. Seule la batterie porte les deux couleurs (kick → DON, caisse claire → KA). Une phrase menée par la basse ou la voix était donc monochrome par construction.

Trois mécanismes, tous sous drapeau, corrigent cela :
- `USE_RUN_CAP` / `MAX_SAME_TYPE_RUN` : plafonne les séries, en basculant la couleur d'une note dès que la série dépasserait la limite. C'est la traduction directe de la convention relevée.
- `USE_RELATIVE_NOTE_TYPE` : la couleur suit le **contour de sa propre piste** — chaque note est comparée à la brillance médiane de sa piste plutôt qu'à un seuil absolu. Une ligne de chant alterne alors selon qu'elle monte ou descend, comme le fait un charter humain sur une mélodie.
- `USE_DRUM_BACKBONE_SHARE` : réserve une part du budget à la batterie et lui rend ses **deux** couleurs, là où l'ossature était filtrée aux seuls DON et ne recevait que les miettes du budget.

### Le décalage temporel était systématique

Symptôme rapporté : « ça ne hit pas toujours au bon moment ». La mesure note à note contre la beatmap humaine a montré un **biais constant de ~65 ms** — nos notes tombaient tard — et non une imprécision aléatoire. Un décalage constant est bien plus perceptible qu'une gigue : il fausse chaque note dans le même sens.

Cause : le flux spectral **culmine après le début de l'attaque**. La fenêtre d'analyse fait 2048 échantillons (~93 ms à 22 050 Hz) et le pic tombe une à deux trames plus loin. `USE_ONSET_LATENCY_COMPENSATION` retranche cette latence **en sortie de chaîne** : appliquée à la détection, la quantification la réabsorbait aussitôt en recollant les notes sur la grille.

Deux découvertes en chemin :
- **Le backtracking dégrade nettement** (concordance de 87 % → 54 %). Censé recaler l'onset sur l'attaque réelle, il sur-corrige et place les notes en avance. Retiré de `NEW_GEN_FLAGS`.
- **Le tempo constant** (`USE_CONSTANT_TEMPO`) supprime la gigue de ±25 ms que `beat_track` laisse sur chaque temps, et qui dérivait jusqu'à 539 ms en fin de morceau. Un mappeur time un morceau avec un BPM et un offset, pas une position par temps.

### Résultats mesurés (Haruka Kanata, comparaison note à note)

| | legacy | `--new-gen` | cible humaine |
|---|---|---|---|
| Écart médian à la note humaine | 64 ms | **11 ms** | — |
| Notes à moins de 25 ms | 13 % | **85 %** | — |
| DON % | 55 | **52** | 45-52 |
| Séries : médiane / max | 2 / 37 | **1 / 4** | 1 / 4-5 |
| Slides | 4 | 5 | — |

Le seuil des tenues a aussi dû être assoupli (`USE_RELAXED_HOLDS`) : à 2,0 attaques/s, 9 des 13 envolées détectées étaient rejetées comme du chant scandé, alors qu'une envolée compte naturellement 2 à 3 syllabes par seconde.

**Leçon de méthode** : une mesure contre une grille théorique peut être circulaire — comparer nos notes à une grille dont nous fixons nous-mêmes les paramètres validait notre propre grille, pas la musique. Seule la comparaison **note à note avec une partition humaine** a révélé le biais de 65 ms. Et la beatmap de référence utilise plus de 250 points de timing, donc aucune grille à BPM unique ne la décrit.

### Densité rapprochée de Futsuu, trous de densité éliminés

Deux retours supplémentaires : il manquait des notes, et il fallait viser Futsuu (normal) plutôt que Courage (extrême) — la comparaison précédente se faisait contre la mauvaise référence.

**Cause des trous de densité** trouvée par instrumentation : 20 des 32 phrases de Haruka Kanata étaient « affamées » — le budget demandait plus de notes que le lead (+ ossature) n'en avait en stock localement, alors que d'autres pistes avaient de la matière au même instant. Le mécanisme d'attention (un seul lead par phrase) créait donc ses propres angles morts. `USE_POOL_SPILLOVER` complète le budget avec les événements les plus forts des pistes non retenues, sans jamais rogner ce que le lead a déjà obtenu.

**La grille adaptative dégradait aussi la densité**, en plus du timing déjà documenté : 2,6 notes/s avec elle contre 3,3 sans, à réglage identique. Deuxième raison de la retirer de `NEW_GEN_FLAGS`, en plus de la dégradation du timing (4 → 15-29 ms).

`TARGET_NOTES_PER_SECOND` passe de 1,8 à 4,0. Point important : ce réglage n'a **jamais été isolé** derrière `--new-gen` — c'est un paramètre de densité partagé par les deux modes, pas une technique expérimentale — donc son changement est actif même sans le drapeau, et la non-régression bit-à-bit ne s'applique pas à lui (elle reste valide pour les techniques réellement gatées).

**Résultats sur Haruka Kanata** :

| | avant | après |
|---|---|---|
| Densité | 1,60/s | **3,11/s** (Futsuu : 3,12/s) |
| Tranches de 5 s à ≤ 2 notes | plusieurs | **0/18** |
| Séries : médiane / max | 2 / 37 | 1 / 4 |

Reste ouvert : les finishes qui ne produisent rien (le champ `finish` n'existe même pas côté client), et le ratio DON/KA légèrement haut (56 % contre 45-52 % visés) à cette densité plus élevée.

Deux fonctionnalités restent inopérantes : les **finishes** ne produisent aucune note et le champ `finish` n'existe pas côté client, et les **tenues disparaissent** en `--new-gen` (3 → 0 sur My Hero Academia), probablement parce que le backtracking rend davantage d'onsets sur la voix, ce qui fait classer les envolées comme du chant scandé.

**Repère de durée, qui sert de test de bon fonctionnement** : sur 90 s avec pistes en cache, legacy ≈ 6 s et `--new-gen` ≈ 24 s, l'écart venant presque entièrement de HPSS. Une génération `--new-gen` revenant en 6 s signale qu'une étape ne tourne pas. C'est ainsi qu'on a détecté que `USE_HPSS` manquait dans la liste d'activation de la CLI. La liste des drapeaux vit désormais dans `config.NEW_GEN_FLAGS` et la CLI itère dessus, pour qu'un ajout ne puisse plus être oublié.

À retenir sur la méthode : le rapport d'analyse à l'origine de ces travaux annonçait 612 notes et 85 % de DON pour la partition générée, là où le fichier du dépôt en contient 144 avec un ratio 55/45 — déjà conforme à la référence osu! citée. **Seul le diagnostic des longues séries s'est vérifié.** D'où la règle : mesurer sur le fichier réel avant de calibrer un correctif, et vérifier qu'une étape coûteuse coûte effectivement du temps.

## Hybride Guitar Hero / taiko : deux lanes et notes tenues (29 juil. 2026)

Refonte du format de jeu, validée sur trois choix :

- **Deux lanes distinctes**, une par couleur : KA (aigu) en haut, DON (grave) en bas — comme les fréquences. Chaque lane est une **file de jugement indépendante** (un Judge par lane) : l'erreur « mauvaise couleur » disparaît, appuyer dans le vide ne coûte rien (convention Guitar Hero/DDR). C'est ce qui rend possible le parallèle tenue + frappes.
- **Notes tenues** (champ `durationMs`, optionnel donc rétrocompatible) : le début se juge comme un tap, la tenue crédite des points au prorata du temps tenu, **hors combo et hors ratio de survie**. Règle indulgente : relâcher tôt arrête les points, sans punir. Une tenue menée au bout déclenche le feedback maximal. Au clavier, le hold survit tant qu'une des deux touches de la lane reste enfoncée ; sur mobile, l'appui et le relâchement des boutons sont transmis avec capture de pointeur.
- **Détection des envolées** sur la piste de voix isolée : un long plateau d'énergie RMS (≥ 1,2 s), fusionné par-dessus les respirations courtes, et **rejeté si truffé d'attaques** (chant scandé ≠ tenue). Le début est recalé sur la grille. Pendant une tenue, les taps de la même lane sont purgés ; l'autre lane garde les siens. Mesuré sur Kassie Krut : 6 envolées de 2 à 6 s, 0 collision même lane, 11 taps DON en parallèle sous les tenues.

## Séparation de pistes et couche « charter » (28 juil. 2026)

Sur la pop/house (kick sur chaque temps), l'analyse par bandes produisait 700 notes ininterrompues : le problème n'était plus l'irrégularité mais l'absence de contraste et d'attention. Décision : passer à la séparation de sources (demucs) surmontée d'une couche « charter » qui *choisit* au lieu de tout garder.

**Les principes du groove qui fondent cette couche** (littérature : Witek et al. 2014, Margulis) :
1. le corps danse sur une grille prévisible (entraînement) ;
2. l'envie de bouger est maximale à syncope *moyenne* — tension dosée entre grille prédite et accents entendus ;
3. la répétition transforme l'écoute en participation (boucles de 2-4 mesures) ;
4. le contraste fabrique les pics — un morceau qui tape tout le temps ne tape jamais ;
5. le drop est une prédiction à longue portée récompensée.

**Architecture retenue** :
- demucs sépare le morceau en batterie / basse / voix / reste, avec cache disque (`data/stems/`, indexé par empreinte du fichier) : on paie les minutes de calcul une fois par morceau. On attend pendant l'analyse — pas de pipeline deux vitesses pour l'instant.
- Par phrase de 8 temps, chaque piste reçoit une **saillance = activité × nouveauté** ; la nouveauté d'un motif se mesure par similarité de Jaccard avec les phrases récentes. La piste la plus saillante devient le **lead** que le joueur incarne — c'est le geste du charter humain (« quelle partie de la musique le joueur va incarner ») et le mécanisme de l'attention auditive (elle va vers ce qui change).
- **Hystérésis** sur le lead : un prétendant doit dépasser le lead en place de 30 % pour le détrôner. L'attention est stable par phrases ; un chart qui zappe est illisible.
- **Budget de notes par phrase**, proportionnel à l'intensité relative de la phrase dans le morceau (borné 0.4×–1.7×). `TARGET_NOTES_PER_SECOND` devient LE levier de difficulté.
- **Ossature** : quand le lead n'est pas la batterie, les kicks les plus forts complètent le budget — la pulsation ne disparaît jamais (principe 1). En cas de collision, le lead gagne toujours.
- La batterie isolée repasse par l'analyse par bandes (kick→DON, snare→KA), la basse donne des DON, la voix des KA, le « reste » est classé note par note (la fonction `classify_note_type` de l'analyse large bande retrouve un usage).
- **Repli automatique** sur l'analyse par bandes si demucs est absent ou échoue — le pipeline ne casse jamais pour ça.

Coût assumé : ~1,5 Go de venv (PyTorch CPU), modèle téléchargé au premier usage, minutes de CPU par morceau non caché.

## Moments forts et arbitrage par intensité (28 juil. 2026)

Le passage en croches avait réglé la difficulté mais rendu les partitions un peu vides : les roulements de batterie et les relances de guitare, ceux qui donnent l'impression de *jouer* le morceau, passaient à la trappe. Une subdivision fixe plafonne partout, y compris là où la musique s'emballe.

- **Grille à finesse variable.** On mesure le nombre d'attaques par temps, on le compare à la médiane locale, et les temps qui dépassent nettement passent en doubles-croches ; le reste demeure en croches. C'est ce que fait un charter humain : couplet en croches, roulement en doubles au moment du fill. Résultat mesuré : 9 % des temps deviennent des moments forts, avec 3 à 4 notes/s dedans contre 2,2 ailleurs, sans perdre la régularité (85 % de motif dominant).
- **Compter les attaques, pas sommer l'énergie.** Première version fausse : sommer l'énergie par temps ne détectait qu'un seul moment fort sur 225 dans un morceau de rock. Une batterie qui joue en continu délivre la même énergie à chaque temps — un roulement ne frappe pas plus fort, il frappe **plus souvent**.
- **Comparaison locale, par médiane glissante.** Un seuil global marquerait tout le refrain comme un long moment fort et laisserait les couplets plats. La médiane plutôt que la moyenne, pour qu'un pic isolé ne masque pas les accents voisins.
- **L'arbitrage des collisions se fait à l'intensité**, plus par priorité de bande fixe. Une caisse claire qui claque l'emporte sur un kick discret : les accents ressortent au lieu d'être écrasés. Les intensités sont normalisées par bande, sinon une bande globalement plus énergique gagnerait tout.

Sur l'ergonomie : la règle « ne pas taper trois fois avec le même doigt » ne s'applique pas à notre disposition. Chaque type ayant deux touches (DON = F et J), une suite de notes identiques se joue en alternant les mains — c'est précisément pourquoi le taiko fonctionne ainsi.

Vitesse de défilement : elle reste **constante**, délibérément. La faire varier casserait la relation apprise entre distance et temps, qui est ce sur quoi le joueur fonde son anticipation. L'espacement des notes reflète déjà l'intensité.

## La régularité prime sur la densité (28 juil. 2026)

Après les bandes de fréquences, le jeu restait difficile et « ne suivait pas la musique ». La mesure a écarté les explications attendues : la densité était modérée (2,4 notes/s), la répartition DON/KA équilibrée, le tempo correct, et 70 % des notes tombaient bien sur la grille.

Le vrai problème était la **répétition des motifs**. En doubles-croches, l'écart le plus fréquent entre deux notes ne représentait que 29 % des écarts : les notes étaient sur la grille, mais à des positions arbitraires (1, puis 3, puis 2, puis 4 subdivisions). La main ne peut jamais prendre le pli, et chaque note demande une réaction plutôt qu'une anticipation — d'où la difficulté.

- **`BEAT_SUBDIVISIONS` passe de 4 à 2.** Mesuré sur deux morceaux : la part du motif dominant monte de 29 % à 71 %, à nombre de notes identique. Ce n'est pas la densité qui fatiguait, c'est l'irrégularité.
- **Monter `ONSET_SENSITIVITY` est contre-productif** pour alléger : ça retire des notes au milieu de suites régulières et casse les motifs (71 % → 53 % en passant de 1.2 à 1.8). Pour alléger, baisser la subdivision.

Leçon générale : sur ce jeu, la **prévisibilité** compte plus que le nombre de notes. On mesure la part du motif dominant, pas seulement les notes par seconde.

## Analyse par bandes de fréquences (28 juil. 2026)

La première génération suivait mal la musique : `onset_strength` travaille sur tout le spectre à la fois, donc un kick, un charleston, une syllabe chantée et une queue de réverbération produisent tous un pic indistinct. La partition suivait la moyenne de tout ce qui bouge — ce qui perceptivement ne suit rien.

- **Trois détections séparées** (grave < 150 Hz, médium 150–2000 Hz, aigu > 2000 Hz). Le type de note découle de l'instrument qui a frappé au lieu d'être deviné après coup : grave → DON, médium → KA.
- **L'aigu est ignoré par défaut.** Le charleston est ce qui joue le plus vite dans un morceau ; il inondait la partition. C'est le levier de densité le plus efficace, et il reste activable dans `BAND_NOTE_TYPE`.
- **Recalage sur une grille de doubles-croches** déduite du beat tracking. Les onsets loin de toute subdivision sont jetés (ornements, bruit). Les motifs deviennent réguliers donc anticipables — c'est ce qui rend une partition satisfaisante, plus que la justesse de chaque note prise isolément.
- **Sélection de la note la plus forte** d'un groupe, et non la plus précoce comme le faisait `enforce_min_gap` : sinon une pré-écho ou une réverbération évince la vraie frappe.
- **L'ancienne analyse est conservée** derrière `USE_BAND_ANALYSIS`, pour comparer les deux sur un même morceau plutôt que de juger de mémoire.

La séparation de pistes (demucs) reste l'étape suivante si les bandes ne suffisent pas sur un mix dense — elle seule permettrait de suivre la voix. On mesure d'abord le gain des bandes.

## Difficulté et calibration (28 juil. 2026)

Le jeu était trop dur avec les fenêtres d'origine (±40 / ±90 ms). Deux causes distinctes, traitées séparément :

- **Fenêtres élargies** à ±55 ms (PERFECT) et ±130 ms (GOOD), fenêtre candidate à 220 ms. Plus généreux qu'un jeu charté à la main, et c'est justifié : les notes générées par détection d'onsets ont une imprécision propre de ~23 ms (la résolution d'analyse) et tombent légèrement après l'attaque réelle.
- **La calibration se mesure en jouant**, pas au métronome. L'écran de fin affiche l'écart moyen des appuis et propose de le corriger d'un clic. Un joueur imprécis se trompe dans les deux sens et sa moyenne reste proche de zéro ; une moyenne franchement décalée trahit la latence du matériel ou des notes tardives. Cette mesure est plus fidèle qu'un test au métronome puisqu'elle intègre toute la chaîne, y compris le biais du générateur de partitions.

Élargir les fenêtres et corriger un décalage systématique ne sont pas interchangeables : le second se voit dans la moyenne, le premier dans la dispersion.

## Génération de partitions (28 juil. 2026)

La partition métronome (une note par temps) n'est pas amusante, et aucun réglage ne la sauvera : elle ne dépend pas de la musique et serait identique sur tout morceau au même tempo. Décisions prises :

- **Les notes suivent les onsets, pas une grille.** Le tempo n'est plus qu'une information affichée. C'est la seule façon de jouer *la chanson* plutôt que de taper sur une horloge.
- **Détection par flux spectral** (`librosa.onset.onset_strength`), pas par énergie. Une caisse claire par-dessus une nappe de synthé ne change presque pas le volume global mais bouleverse la répartition des fréquences — l'énergie seule la rate.
- **DON/KA déduits du contenu fréquentiel** de l'attaque, avec une frontière à 400 Hz : grave (kick, basse) → DON, aigu (caisse claire, charleston) → KA. C'est la logique du vrai taiko (centre grave / bord claquant), et elle produit des motifs musicaux gratuitement puisque le morceau alterne déjà kick et snare. Le seuil favorise le DON en cas d'égalité, pour que les KA restent des accents.
- **Deux filtrages de densité** : un juste après la détection (une frappe s'étale sur plusieurs trames), un sur la partition finale (jouabilité à deux mains).
- **Les partitions générées sont des artefacts non versionnés**, régénérables depuis l'audio. Le pipeline maintient un `client/public/charts/index.json`, sans lequel le navigateur ne pourrait pas savoir quelles partitions existent — on ne liste pas un dossier en HTTP.
- **La partition métronome est conservée** comme point de comparaison : c'est elle qui dira si la génération apporte vraiment quelque chose.

## Principes d'architecture (découlent de la nature du jeu)

1. **La détection de hit est 100 % locale.** Le client juge chaque hit contre son horloge audio et envoie le résultat (score/combo) au serveur. Le serveur ne valide pas les hits en temps réel (anticheat = problème post-MVP).
2. **Le serveur ne relaie que du lent** : scores, % de réussite, état des danseurs, taunts. Fréquence faible (événementiel ou ~5-10 Hz). C'est ce qui permet beaucoup de joueurs par room.
3. **Synchro musicale** — c'est le cœur de l'expérience « écouter ensemble », protocole détaillé :
   - Chaque client possède le fichier audio complet avant le départ (téléchargé + décodé), on ne streame rien en live.
   - Au join : synchro d'horloge style NTP (~10 pings, offset = médiane de `temps_serveur - temps_local - RTT/2`). Précision ~5-20 ms même avec du ping élevé.
   - Ready-check : le serveur attend le « prêt » de toute la room, puis annonce « lecture à T » (T = +2-3 s, le délai sert de compte à rebours 3-2-1 à l'écran).
   - Le client convertit T → temps local → temps `AudioContext` et appelle `source.start(when)` (précision à l'échantillon près).
   - Retardataire : rejoint en cours via `source.start(when, offset_dans_le_morceau)` — synchro dès sa première seconde.
   - Pas de pause solo en multi (une pause serait globale ou rien).
   - Écran de calibration (métronome « tape en rythme ») pour mesurer l'offset perso de chaque joueur — indispensable à cause des casques Bluetooth (100-300 ms de latence de sortie invisibles) ; l'offset décale les fenêtres de jugement.
4. **Broadcast borné** : ne jamais relayer l'état de N joueurs à N joueurs naïvement. Relayer un agrégat + top N si les rooms grossissent.
5. **Partition = JSON versionné** : liste de notes `{ time_ms, lane, type }` + métadonnées (BPM, offset, durée). Générée par le service Python, servie en statique, jouée par le client.

## Architecture cible

```
[Client React+PixiJS] ⇄ WebSocket (protocole binaire maison) ⇄ [Serveur Go : rooms, scores, synchro]
                                                                        │
[Service Python FastAPI : yt-dlp + librosa] ── audio (mp3/ogg) + partition (JSON) ──> stockage/CDN
```

- Le serveur Go orchestre : création de room, demande de map au service Python, distribution de l'URL audio + partition aux clients, top départ synchronisé.
- L'audio téléchargé est servi par notre backend (pas de lecture YouTube embarquée : CORS + pas de contrôle précis du timing).
- ⚠️ yt-dlp : zone grise vis-à-vis des ToS YouTube — OK projet perso, prévoir l'import de fichier MP3 comme fallback (quasi gratuit à ajouter, même pipeline sans l'étape téléchargement).

## Roadmap MVP (ordre de dev)

1. **Cœur de gameplay solo** (le plus risqué en ressenti) : PixiJS + Web Audio, une partition JSON codée à la main, hit detection avec fenêtres de timing (perfect/good/miss), score/combo, écran de calibration d'offset (utile dès le solo, indispensable en multi). Critère : « c'est satisfaisant à jouer ».
2. **Pipeline partitions** : service Python yt-dlp + librosa → partition auto. Critère : une URL YouTube devient jouable en < 1 min.
3. **Multijoueur** : serveur Go, protocole binaire, rooms, synchro d'horloge + start simultané, scores partagés en live.
4. **Fun social** : danseurs (MVP = visage content/moyen/triste selon le % de réussite), taunts, écran de fin de partie.

## Choix restants (à trancher plus tard, pas bloquants)

- Format de sérialisation binaire : maison pur, ou FlatBuffers/protobuf en référence pour comparer
- Nombre de lanes/touches du gameplay (4 façon osu!mania semble un bon départ)
- Stockage des maps générées : disque local au début, S3-compatible ensuite
- Déploiement (un seul VPS suffit largement pour le MVP)
