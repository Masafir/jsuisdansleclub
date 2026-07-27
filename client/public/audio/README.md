# Fichiers audio à déposer ici

Ces fichiers ne sont pas versionnés (voir `.gitignore` à la racine). À déposer
manuellement pour tester le jeu :

| Fichier | Rôle |
|---|---|
| `test-song.mp3` | Morceau de test, référencé par `src/chart/testChart.ts`. Idéalement à 120 BPM avec un beat marqué, ou alors ajuster `TEST_BPM` dans ce fichier. |
| `sfx-perfect.mp3` | Son court joué sur un PERFECT |
| `sfx-good.mp3` | Son court joué sur un GOOD |
| `sfx-miss.mp3` | Son court joué sur un MISS |

Les trois SFX sont **optionnels** : s'ils manquent, le jeu reste jouable, il est
seulement silencieux sur les appuis (voir `loadOptionalAudioBuffer`).
`test-song.mp3` est en revanche nécessaire pour lancer une partie.
