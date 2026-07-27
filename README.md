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

## Où en est-on — étape 1 (gameplay solo)

Le squelette est en place. Il reste **cinq fonctions à écrire**, repérées par
`TODO(amiral)`, chacune couverte par des tests qui servent de critère de
réussite. Le harnais est vert quand tout est implémenté.

Ordre conseillé (du plus simple au plus impliquant) :

| # | Fichier | À écrire | Tests |
|---|---|---|---|
| 1 | `client/src/audio/clock.ts` | `start`, `getSongTimeMs`, `getInputTimeMs` | `clock.test.ts` |
| 2 | `client/src/game/scoring.ts` | `multiplier`, `successRatio`, `register`, `isPlayerDead` | `scoring.test.ts` |
| 3 | `client/src/game/judge.ts` | `hit`, `update` | `judge.test.ts` |
| 4 | `client/src/render/highway.ts` | `noteX`, `updatePulses` | à l'œil, dans le jeu |

```bash
cd client && npm run test:watch
```

Une fois les quatre faits, déposer un `test-song.mp3` dans `client/public/audio/`
(voir le README de ce dossier) et `npm run dev` donne une partie jouable.

Note : `noUnusedLocals` / `noUnusedParameters` sont désactivés dans
`tsconfig.app.json` pour que le build ne casse pas tant que les TODO ne sont pas
remplis ; oxlint continue de les signaler en avertissement.

## Conseil de dev

Développer avec un **casque filaire**. En Bluetooth, 100 à 300 ms de latence de sortie faussent complètement le ressenti d'un jeu de rythme.
