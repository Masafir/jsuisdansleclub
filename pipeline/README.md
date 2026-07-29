# pipeline — génération de partitions

Service Python de l'**étape 3** de la roadmap (voir [DECISIONS.md](../DECISIONS.md)) :
une URL YouTube ou un fichier audio entre, un MP3 et une partition JSON sortent.

Le téléchargement YouTube (`yt-dlp`) reste à faire. La **génération de partition
par détection d'onsets** est en place, avec cinq fonctions à implémenter.

## Installation

```bash
cd pipeline && python3 -m venv .venv && .venv/bin/pip install librosa pytest
```

Compter ~500 Mo : librosa tire numpy, scipy, numba et scikit-learn.

## Utilisation

```bash
cd pipeline && .venv/bin/python -m chartgen ../client/public/audio/test-song.mp3 --title "Mon morceau"
```

La partition atterrit dans `client/public/charts/` et apparaît dans la
bibliothèque du jeu au rechargement de la page.

## Qui a écrit quoi

Le cœur de détection (`onset_envelope`, `detect_onset_times`,
`enforce_min_gap`, `classify_note_type`, `times_to_notes`,
`onset_envelopes_by_band`, `quantize_to_grid`, `select_strongest`) est
**implémenté par amiral**, validé par les tests — c'est le seul code du
pipeline resté dans le format TODO + tests du contrat de collaboration.

Tout le reste (`phrases.py`, `stems.py`, l'orchestration de `chart.py`, et
l'intégralité du travail de calibrage `--new-gen` — timing, alternance,
densité, mesures contre les beatmaps osu!) a été **implémenté directement par
l'agent**, à la demande explicite d'amiral à chaque fois. Ce n'est pas le mode
par défaut du contrat (voir [AGENTS.md](../AGENTS.md), règle 3), mais le
pipeline s'y est prêté : les itérations de calibrage sont plus rapides que
d'apprentissage, sur du terrain déjà déblayé par le cœur de détection.

## Générateur expérimental `--new-gen`

Une seconde piste de génération, isolée derrière un drapeau, pour tester sans
toucher à celle en service :

```bash
cd pipeline && .venv/bin/python -m chartgen "../client/public/audio/mon morceau.mp3" --new-gen
```

Le fichier produit porte le suffixe `-newgen`, donc les deux versions
**coexistent dans la bibliothèque** et se comparent en jouant.

Ce qu'il active aujourd'hui (liste exacte dans `config.NEW_GEN_FLAGS`, tout à
`False` par défaut, seule la CLI les lève — la boucler dessus plutôt que la
recopier est volontaire, voir « Règle d'isolation ») :

| Drapeau | Effet |
|---|---|
| `USE_ONSET_LATENCY_COMPENSATION` | retranche ~65 ms aux instants détectés, appliqué en sortie de chaîne — voir « État actuel » |
| `USE_CONSTANT_TEMPO` | grille sur un tempo constant ajusté, au lieu des temps bruts de `beat_track` (gigue ±25 ms) |
| `USE_RUN_CAP` | plafonne les séries d'une même couleur (`MAX_SAME_TYPE_RUN`, 4 par défaut) |
| `USE_RELATIVE_NOTE_TYPE` | la couleur suit le contour de sa propre piste plutôt qu'un seuil absolu |
| `USE_DRUM_BACKBONE_SHARE` | l'ossature de batterie garde ses deux couleurs et une part réservée du budget |
| `USE_POOL_SPILLOVER` | complète le budget d'une phrase avec les pistes non retenues quand le lead n'a pas assez de matière |
| `USE_RELAXED_HOLDS` | seuil de densité d'attaques plus permissif pour qu'une tenue soit reconnue |
| `USE_HPSS` | sépare harmonique et percussif avant détection d'onsets |
| `USE_STRUCTURE_GUIDANCE` | segmentation couplet/refrain/pont (MFCC + clustering) pour orienter le lead |
| `DETECT_FINISHES` | grosses notes sur crêtes spectrales larges — **ne produit encore rien**, voir « État actuel » |

**`USE_ONSET_BACKTRACK` et `USE_ADAPTIVE_GRID` existent dans le code mais ne
sont plus dans `NEW_GEN_FLAGS`** : mesurés, tous deux dégradaient le résultat
(voir « État actuel »). Les drapeaux restent pour pouvoir les re-tester
isolément.

### Combien de temps ça doit prendre

Sur un morceau de 90 s dont les pistes sont **déjà en cache** : legacy ~6 s,
`--new-gen` ~24 s. L'écart vient presque entièrement de HPSS (~17 s pour quatre
appels). Une génération `--new-gen` qui reviendrait en 6 secondes est le signe
qu'une étape ne s'exécute pas — c'est arrivé, `USE_HPSS` manquait dans la liste
d'activation de la CLI, et rien ne le signalait.

Premier passage sur un morceau inconnu : ajouter les minutes de séparation
demucs, payées une seule fois (cache dans `data/stems/`).

### Référence : ce que fait un charter humain

Les quatre difficultés officielles de *Haruka Kanata* (osu!taiko, mappeur
Tachibana_) donnent une règle nette, **identique à tous les niveaux** :

| Difficulté | notes/s | DON % | séries : médiane / max |
|---|---|---|---|
| Kantan | 1,76 | 45 % | 1 / **4** |
| Futsuu | 3,12 | 52 % | 1 / **4** |
| Muzukashii | 3,91 | 49 % | 1 / **5** |
| Courage | 5,10 | 48 % | 1 / **5** |

**Jamais plus de 4 ou 5 notes consécutives de la même couleur**, et un ratio
DON/KA toujours entre 45 et 52 %. La densité, elle, varie du simple au triple
selon la difficulté : c'est le levier de difficulté, pas l'alternance.

Notre densité (~1,5/s) situe nos partitions au niveau **Kantan**.

### État actuel

Mesuré sur Haruka Kanata, comparaison **note à note** avec les beatmaps
humaines (Kantan = facile, Futsuu = normal, Courage = extrême) :

| | avant | `--new-gen` final | cible Futsuu |
|---|---|---|---|
| Densité | 1,60/s | **3,11/s** | 3,12/s |
| DON % | 55 | 56 | 45-52 |
| Séries : médiane / max | 2 / 37 | **1 / 4** | 1 / 4-5 |
| Slides | 4 | 5 | — |
| Tranches de 5 s à ≤ 2 notes | plusieurs | **0/18** | — |
| Écart médian vs Courage | 64 ms | 12 ms | — |

Cinq mesures ont amené ces résultats :

- **Le décalage était systématique**, pas aléatoire : nos notes tombaient ~65 ms
  trop tard, le flux spectral culminant après le début de l'attaque (fenêtre
  d'analyse de 2048 échantillons). `USE_ONSET_LATENCY_COMPENSATION` retranche
  cette latence **en sortie** — appliquée à la détection, la quantification
  l'absorbait.
- **Le backtracking dégradait fortement** : il fait tomber la concordance de
  87 % à 54 % en sur-corrigeant. Retiré de `NEW_GEN_FLAGS`.
- **Le seuil des tenues était trop strict** : à 2,0 attaques/s, 9 des 13
  envolées détectées étaient rejetées. `USE_RELAXED_HOLDS` porte le plafond à
  3,2.
- **Les phrases étaient « affamées »** : 20 des 32 phrases de Haruka Kanata
  demandaient plus de notes que le lead (+ ossature) n'en avait en stock,
  alors que d'autres pistes avaient de la matière au même instant — c'est ce
  qui créait les trous de densité pendant les passages intenses.
  `USE_POOL_SPILLOVER` complète le budget avec les événements les plus forts
  des pistes non retenues, sans jamais rogner le lead déjà choisi.
- **La grille adaptative dégradait aussi la densité**, en plus du timing déjà
  documenté : 2,6 notes/s avec elle contre 3,3 sans, sur le même réglage.
  Retirée de `NEW_GEN_FLAGS` pour cette seconde raison.

`TARGET_NOTES_PER_SECOND` est passé de 1,8 à **4,0** — ce réglage n'a jamais
été isolé derrière `--new-gen` (c'est un réglage de densité partagé par les
deux modes, pas une technique expérimentale), donc ce changement est actif
même sans le drapeau.

Reste ouvert : **les finishes** ne produisent toujours rien — `detect_finishes`
rend zéro note et le champ `finish` n'existe ni dans `Chart` côté client ni
dans le rendu.

Les maps de référence sont dans `F:\jsuisdansleclub\osumap\` (accessibles sous
`/mnt/f/...` depuis WSL) et se ré-analysent à tout moment pour recalibrer.

### Méthode de comparaison contre une map humaine

Toutes les mesures ci-dessus viennent de la même technique, reproductible sur
n'importe quelle map de `F:\jsuisdansleclub\osumap\` (`/mnt/f/...` sous WSL) :

1. **Parser le `.osu`** : section `[HitObjects]`, une ligne par note au format
   `x,y,temps_ms,type,hitsound,...`. `type & 8` = spinner (à ignorer,
   ça n'a pas d'équivalent chez nous). `hitsound & 2` ou `& 8` = whistle/clap
   → `KA` dans notre nomenclature, sinon → `DON`.
2. **Densité et alternance** : compter les notes, calculer `notes / durée`,
   et la longueur des séries consécutives d'une même couleur (médiane et max)
   — c'est ce qui a révélé la règle « jamais plus de 4-5 notes de la même
   couleur » citée plus haut.
3. **Concordance temporelle, note à note** : pour chaque note générée, la
   distance à la note humaine la plus proche (`|t_nous - t_humain|.min()`).
   Le pourcentage de notes à moins de 25 ms est le chiffre le plus parlant.
   **Piège évité** : comparer contre une grille théorique à BPM unique est
   circulaire (ça valide nos propres paramètres, pas la musique) — une
   beatmap réelle a souvent 250+ points de timing (tempo variable), la
   comparaison doit se faire note à note, jamais contre une grille recalculée.
4. **Quelle difficulté choisir comme référence** : comparer à la difficulté
   dont la densité est la plus proche de la nôtre, sinon le taux de
   concordance est mécaniquement tiré vers le haut par les difficultés les
   plus denses (plus de notes humaines = plus de chances d'en trouver une
   proche par pur hasard statistique, indépendamment de la justesse réelle).

Aucun script n'a été conservé dans le dépôt — chaque mesure a été refaite à la
volée. À écrire dans `pipeline/prototype/` si ce calibrage redevient fréquent.

### Règle d'isolation

Toute constante `--new-gen` doit valoir `False` par défaut. Un défaut à `True`
modifie la génération en service dès qu'un appel oublie de tester le mode : le
premier jet appliquait HPSS inconditionnellement et divisait par deux le nombre
de notes du mode legacy. Le test de non-régression est simple — regénérer sans
drapeau doit rendre un fichier identique à l'existant.

## Analyse par pistes séparées (le mode principal)

Le pipeline sépare le morceau en quatre pistes via **demucs** — batterie,
basse, voix, le reste — puis une couche « charter » choisit, phrase par phrase
de 8 temps, **quelle piste le joueur incarne** : la plus saillante, où
saillance = activité × nouveauté du motif. Une voix qui entre attire le lead ;
quand elle s'installe et se répète, le lead glisse vers ce qui bouge. De
l'hystérésis évite le zapping, un **budget de notes par phrase** (proportionnel
à l'intensité relative) crée le contraste, et une ossature de kicks maintient
la pulsation quand la batterie n'est pas le lead.

Installation (≈ 1,3 Go de dépendances, PyTorch CPU) :

```bash
cd pipeline && .venv/bin/pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu && .venv/bin/pip install demucs
```

Premier usage : le modèle (~300 Mo) se télécharge tout seul. Chaque morceau
coûte **quelques minutes de CPU la première fois** ; les pistes séparées sont
cachées dans `data/stems/` et les générations suivantes sont rapides. La CLI
affiche la répartition du lead (`lead par phrase : vocals 12 · drums 8 …`).

Sans demucs (ou s'il échoue), le pipeline **se replie automatiquement** sur
l'analyse par bandes ci-dessous.

Le levier de difficulté principal est `TARGET_NOTES_PER_SECOND` dans
`config.py` : le budget de chaque phrase en découle.

## Comment fonctionne l'analyse par bandes (le repli)

Trois détections séparées au lieu d'une seule sur tout le spectre. Le type de
note ne se devine plus après coup : il découle de **quel instrument a frappé**.

| Bande | Contenu | Devient |
|---|---|---|
| < 150 Hz | kick, basse | **DON** |
| 150–2000 Hz | caisse claire, clap, voix | **KA** |
| > 2000 Hz | charleston, cymbales | **ignoré** |

Le charleston est ce qui joue le plus vite dans un morceau : le laisser passer
inondait la partition. Il reste activable via `BAND_NOTE_TYPE` dans la config.

Les onsets sont ensuite **recalés sur une grille de doubles-croches** déduite du
beat tracking. Ceux qui tombent loin de toute subdivision sont jetés : ce sont
des ornements ou du bruit. Les motifs deviennent réguliers, donc anticipables —
c'est ce qui rend une partition satisfaisante à jouer.

`USE_BAND_ANALYSIS = False` rebascule sur l'ancienne analyse large bande, pour
comparer les deux sur un même morceau.

Les tests passent au vert quand les fonctions sont écrites. Ceux de
`test_notes.py` portent sur des fonctions pures et n'utilisent aucun fichier
audio ; ceux de `test_analysis.py` fabriquent leurs signaux à la main.

## Lancer les tests

Toute la suite :

```bash
cd pipeline && .venv/bin/pytest
```

**Un test précis** — le chemin du fichier, puis `::` entre chaque niveau
(fichier, classe, fonction) :

```bash
cd pipeline && .venv/bin/pytest tests/test_analysis.py::test_onset_envelope_detecte_les_impulsions -v
```

**Par motif de nom**, le plus pratique quand on travaille sur une fonction :
lance tout ce dont le nom contient le motif, sans avoir à taper le chemin.

```bash
cd pipeline && .venv/bin/pytest -k "enforce_min_gap" -v
```

Options utiles :

| Option | Effet |
|---|---|
| `-v` | une ligne par test, avec son nom — indispensable pour voir quel cas casse |
| `-s` | affiche les `print` du code testé (pytest capture la sortie par défaut et ne la restitue que sur un échec) |
| `-k "motif"` | ne garde que les tests dont le nom contient le motif |
| `-x` | s'arrête au premier échec, pour itérer vite |
| `--tb=short` | trace d'erreur compacte (`--tb=line` pour une seule ligne) |
| `-q` | sortie minimale, juste le compte final |
| `tests/test_notes.py::TestEnforceMinGap` | toute une classe d'un coup |

Côté client, vitest suit les mêmes principes : `npm test -- -t "motif"` filtre
par nom de test, `npm test src/game/judge.test.ts` ne lance qu'un fichier, et
`npm run test:watch` relance automatiquement à chaque sauvegarde.

## Pièges connus

**librosa exige des arguments nommés.** Depuis la version 0.10, presque toute
son API refuse les arguments positionnels :

```
TypeError: onset_strength() takes 0 positional arguments but 3 were given
```

Il faut écrire `librosa.onset.onset_strength(y=..., sr=..., hop_length=...)`.
C'est délibéré de leur part : les signatures ont beaucoup bougé au fil des
versions, et forcer les noms évite qu'un ordre d'arguments obsolète passe
silencieusement en donnant un résultat faux.

**Ne pas afficher l'enveloppe trame par trame** pour l'inspecter : il y en a une
toutes les 23 ms, soit ~7500 lignes pour trois minutes de musique, presque
toutes à zéro. Pour voir ce qui s'y passe vraiment, n'afficher que ce qui
dépasse le seuil :

```python
seuil = envelope.mean() + config.ONSET_SENSITIVITY * envelope.std()
print("forme", envelope.shape, "| max", envelope.max(), "| moyenne", envelope.mean())
for i in np.where(envelope > seuil)[0]:
    print(f"  trame {i}  t={i * config.HOP_LENGTH / config.SAMPLE_RATE:.3f}s  {envelope[i]:.2f}")
```

`np.where(condition)[0]` renvoie les indices où la condition est vraie : c'est
l'outil de base pour interroger un tableau numpy sans le parcourir à la main.

**Les valeurs par défaut des fonctions sont figées à l'import, pas à l'appel.**
Beaucoup de fonctions du pipeline ont la forme
`def f(..., sensitivity: float = config.ONSET_SENSITIVITY):` — c'est le cas de
`TARGET_NOTES_PER_SECOND`, `ONSET_SENSITIVITY`, `MIN_NOTE_GAP_S` et d'autres.
Python évalue ce défaut **une seule fois, à la définition de la fonction**
(donc au premier `import chartgen`), pas à chaque appel. Modifier
`config.TARGET_NOTES_PER_SECOND` en cours de script (pour balayer plusieurs
valeurs sans relancer Python, par exemple) n'a **aucun effet** sur les appels
qui utilisent ce défaut — piège rencontré en cherchant pourquoi une densité ne
bougeait pas quel que soit le réglage testé. Deux façons de le contourner :
relancer un process Python frais pour chaque valeur (ce que fait la CLI
normalement), ou passer la valeur explicitement en argument nommé plutôt que
compter sur le défaut. Les drapeaux booléens de `NEW_GEN_FLAGS` n'ont pas ce
problème : ils sont lus en direct dans le corps des fonctions (`if
config.USE_XXX:`), pas comme valeur par défaut.

## Équilibrage

Une partition brute est rarement amusable du premier coup : c'est
`chartgen/config.py` qui fait la différence. Par ordre d'impact :

| Constante | Effet |
|---|---|
| `BAND_NOTE_TYPE` | mettre une bande à `None` la supprime entièrement — le levier le plus fort sur la densité |
| `BEAT_SUBDIVISIONS` | 4 = doubles-croches, 2 = croches. Baisser ralentit et régularise |
| `ACCENT_RATIO` | monter rend les moments forts plus rares et plus marqués |
| `ACCENT_SUBDIVISIONS` | finesse de la grille dans les moments forts |
| `ACCENT_WINDOW_BEATS` | voisinage sur lequel un temps est jugé « exceptionnel » |
| `ONSET_SENSITIVITY` | monter pour ne garder que les attaques franches |
| `QUANTIZE_TOLERANCE_RATIO` | baisser jette plus d'onsets hors grille |
| `MIN_NOTE_GAP_S` | plafond absolu de densité |
| `BANDS` | déplacer les frontières si le kick ou la caisse claire est mal capté |
| `USE_GRID_QUANTIZATION` | désactiver si le tempo estimé est manifestement faux |

**Vérifier le tempo affiché après chaque génération.** C'est lui qui construit
la grille de quantification : s'il est faux, les notes sont recalées sur une
grille fausse et la partition empire. Un morceau qui donne un tempo aberrant se
traite en passant `USE_GRID_QUANTIZATION` à `False`.

La CLI affiche après chaque génération le
nombre de notes par seconde et la répartition DON/KA, les deux chiffres qui
disent si un réglage va dans le bon sens.

## `prototype/estimate_tempo.py`

Un prototype jetable, écrit pour caler la partition de test du client sur
`test-song.mp3` avant que le vrai pipeline n'existe. Il n'a **aucune dépendance**
autre que ffmpeg : il décode l'audio, construit une fonction d'onset à partir de
l'énergie par trames de 10 ms, et autocorrèle pour trouver le tempo, puis la
phase par balayage.

```bash
python3 pipeline/prototype/estimate_tempo.py client/public/audio/test-song.mp3
```

Il affiche le tempo, l'instant du premier temps, et les constantes prêtes à
coller dans `client/src/chart/testChart.ts`.

Il est conservé pour deux raisons : il documente la méthode de manière lisible,
et il dépanne quand on veut caler une partition à la main sans rien installer.

**Ses limites illustrent pourquoi librosa est nécessaire.** L'autocorrélation
répond aussi fort à la moitié et au double du vrai tempo : sur `test-song.mp3`
elle proposait 67,5 BPM là où un humain compte 135. Le script corrige ça en
repliant le résultat dans la plage 90–180 BPM, ce qui marche pour de la musique
dansante mais serait faux sur une ballade lente.

Plus fondamentalement, l'énergie totale ne détecte qu'un changement de volume :
un morceau sans percussions marquées donne n'importe quoi. Un vrai détecteur
travaille sur le **flux spectral** — l'énergie par bandes de fréquences — ce qui
lui permet d'entendre une attaque de caisse claire même quand le volume global
ne bouge pas. C'est là que librosa devient indispensable.

## Format de sortie attendu

La partition doit respecter le type `Chart` de
[`client/src/chart/types.ts`](../client/src/chart/types.ts) : `version`, `title`,
`audioUrl`, `durationMs`, `bpm`, `offsetMs`, et `notes` triées par `timeMs`
croissant, chacune avec un type `DON` ou `KA`.

Chaque note accepte aussi deux champs optionnels (absence = comportement par
défaut, donc rétrocompatible avec les anciennes partitions) :
- `durationMs` : note tenue (« slide »). Généré par `detect_holds` dans
  `chart.py`, à partir des envolées détectées sur la piste vocale isolée.
- `accent` : la note appartient à un moment fort (roulement, relance) — le
  client l'auréole. Posé par `mark_accent_notes`.
