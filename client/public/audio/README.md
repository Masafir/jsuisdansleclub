# Fichiers audio du client

| Fichier | Rôle | Versionné ? |
|---|---|---|
| `sfx-perfect.mp3` | Son court joué sur un PERFECT | **Oui** |
| `sfx-good.mp3` | Son court joué sur un GOOD | **Oui** |
| `sfx-miss.mp3` | Son court joué sur un MISS | **Oui** |
| `test-song.mp3` | Morceau de test, référencé par `src/chart/testChart.ts` | Non |

Les **SFX sont versionnés** : ce sont de vrais assets du jeu, ils pèsent quelques
kilo-octets, et sans eux un clone du dépôt serait muet. Ils restent techniquement
optionnels côté code (voir `loadOptionalAudioBuffer`) : leur absence ne casse
rien, elle rend seulement les appuis silencieux.

Le **morceau de test n'est pas versionné** : plusieurs mégaoctets de musique
probablement sous droits, que Git conserverait pour toujours à chaque version.
À déposer manuellement pour lancer une partie — idéalement à 120 BPM avec un
beat marqué, sinon ajuster `TEST_BPM` dans `src/chart/testChart.ts`.

C'est la même logique qui s'appliquera aux morceaux téléchargés par le pipeline :
l'audio se régénère, il ne se versionne pas.
