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
