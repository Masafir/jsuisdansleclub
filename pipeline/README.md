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

## À implémenter (amiral)

| Fonction | Fichier | Ce qu'elle décide |
|---|---|---|
| `onset_envelope` | `analysis.py` | appel librosa du flux spectral |
| `detect_onset_times` | `analysis.py` | seuillage : quelle attaque compte vraiment |
| `enforce_min_gap` | `notes.py` | densité jouable |
| `classify_note_type` | `notes.py` | grave → DON, aigu → KA |
| `times_to_notes` | `notes.py` | conversion au format de partition |

```bash
cd pipeline && .venv/bin/pytest
```

Les 27 tests passent au vert quand les cinq fonctions sont écrites. Ceux de
`test_notes.py` portent sur des fonctions pures et n'utilisent aucun fichier
audio ; ceux de `test_analysis.py` fabriquent leurs signaux à la main.

## Équilibrage

Une partition brute est rarement amusable du premier coup : c'est
`chartgen/config.py` qui fait la différence. `ONSET_SENSITIVITY` d'abord (monter
la valeur pour moins de notes), puis `MIN_NOTE_GAP_S` (densité maximale) et
`KA_ENERGY_RATIO` (proportion de KA). La CLI affiche après chaque génération le
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
