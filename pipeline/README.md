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
**implémenté par amiral**, validé par les tests. La couche « charter »
(`phrases.py`, `stems.py`) et l'orchestration ont été écrites par l'agent, à la
demande d'amiral.

## Générateur expérimental `--new-gen`

Une seconde piste de génération, isolée derrière un drapeau, pour tester sans
toucher à celle en service :

```bash
cd pipeline && .venv/bin/python -m chartgen "../client/public/audio/mon morceau.mp3" --new-gen
```

Le fichier produit porte le suffixe `-newgen`, donc les deux versions
**coexistent dans la bibliothèque** et se comparent en jouant.

Ce qu'il active (tout est à `False` par défaut dans `config.py`, seule la CLI
les lève) : **HPSS** avant la détection d'onsets, **backtracking** vers
l'attaque réelle, **grille adaptative** (2/3/4/6/8/12 selon la densité locale,
donc triolets et roulements possibles), **segmentation structurelle**
couplet/refrain/pont pour orienter le lead, **forçage KA** sur les caisses
claires des temps 2 et 4, et détection de **finishes**.

### État actuel : à régler avant adoption

Mesuré sur Haruka Kanata (90 s, 172 BPM) :

| | legacy | `--new-gen` |
|---|---|---|
| Notes | 144 (1,60/s) | 138 (1,53/s) |
| Ratio DON/KA | 55 / 45 | 25 / 75 |
| Plus long run de même type | 37 | 14 |
| Répartition du lead | drums 16 · bass 9 · vocals 6 | drums 30 · vocals 2 |

Le gain réel est sur les **longues séries d'une même couleur** (37 → 14). En
revanche deux réglages sur-corrigent :

- `SNARE_BEAT_TOLERANCE_S` (0,15 s) couvre presque la moitié d'un temps à
  172 BPM — ce n'est plus une détection de caisse claire mais un forçage du
  contretemps, d'où les 75 % de KA. Essayer 0,05 s.
- `STRUCTURE_LEAD_BOOST` (1,5) fige le lead sur la batterie, car couplet, intro
  et outro la préfèrent toutes dans `SECTION_LEAD_PREFERENCE`.

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
