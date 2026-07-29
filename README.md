# jsuisdansleclub

Jeu de rythme multijoueur en ligne : écouter de la musique avec ses potes et jouer ensemble, chacun avec son danseur qui réagit à ses performances.

- **Vision produit** : [CONTEXT.MD](CONTEXT.MD)
- **Décisions techniques** : [DECISIONS.md](DECISIONS.md)
- **Contrat de collaboration humain/agent** : [AGENTS.md](AGENTS.md)

## Structure

```
client/     React + PixiJS + Web Audio (Vite, TypeScript)
server/     Go — rooms, scores, synchro d'horloge, protocole binaire sur WebSocket
pipeline/   Python — yt-dlp + librosa : URL YouTube → audio + partition JSON
```

## Prérequis

Go ≥ 1.25, Node ≥ 20, Python ≥ 3.12, ffmpeg.

## Démarrage

Client :

```bash
cd client && npm install && npm run dev
```

Tests client :

```bash
cd client && npm test
```

Serveur (une fois implémenté) :

```bash
cd server && go run ./cmd/server
```

Pipeline (génération de partition) :

```bash
cd pipeline && .venv/bin/python -m chartgen "chemin/vers/morceau.mp3"
```

Voir [pipeline/README.md](pipeline/README.md) pour l'installation (librosa,
puis demucs en option) et le mode expérimental `--new-gen`.

## Où en est-on (29 juil. 2026)

**Gameplay solo (étape 1) : fait.** Format hybride Guitar Hero / taiko à deux
lanes (KA en haut, DON en bas), notes tenues, décompte, règle de survie
(« danse mortelle »), calibration mesurée en jouant, commandes tactiles sur
mobile, battement avant l'écran de résultats. Détails et raisons dans
[DECISIONS.md](DECISIONS.md).

**Pipeline de génération (étape 2) : fonctionnel, en calibrage continu.** Trois
analyses en cascade selon ce qui est disponible : séparation de pistes
(demucs) avec couche « charter » (choix du lead, budget par phrase) en mode
normal, repli automatique sur l'analyse par bandes de fréquences si demucs est
absent, et un mode expérimental `--new-gen` calibré contre des beatmaps
osu!taiko humaines (timing, alternance des couleurs, densité). Le
téléchargement YouTube (`yt-dlp`) n'est **pas encore implémenté** : le
pipeline ne traite aujourd'hui que des fichiers audio locaux.

**Multijoueur (étape 3) : pas commencé.** `server/` ne contient qu'un
`go.mod` vide. Les principes d'architecture (synchro d'horloge, protocole
binaire, broadcast borné) sont posés dans DECISIONS.md mais aucun code n'existe.

**Fun social (étape 4) : pas commencé.** Danseurs, taunts — juste des idées
pour l'instant.

## Conseil de dev

Développer avec un **casque filaire**. En Bluetooth, 100 à 300 ms de latence de sortie faussent complètement le ressenti d'un jeu de rythme.
