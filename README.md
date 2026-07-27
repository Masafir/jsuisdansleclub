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

## Conseil de dev

Développer avec un **casque filaire**. En Bluetooth, 100 à 300 ms de latence de sortie faussent complètement le ressenti d'un jeu de rythme.
