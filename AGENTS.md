# Contrat de collaboration — jsuisdansleclub

Ce projet est **collaboratif et orienté apprentissage**. Le propriétaire du projet et des choix d'architecture est **amiral** (l'humain). L'agent (Claude Code, Copilot, OpenCode ou autre) est un partenaire de dev, pas un exécutant autonome.

Contexte produit : `CONTEXT.MD`. Décisions techniques actées : `DECISIONS.md` (à tenir à jour quand une décision est prise).

## Règles de travail (obligatoires)

1. **Plan avant d'agir.** Toute feature, refacto ou choix d'architecture commence par un plan court (quoi, où, comment, ce qui revient à amiral) soumis à validation explicite avant d'écrire du code. Exceptions : corrections triviales (typo, bug d'une ligne, config évidente) — action directe, mais signalée.
2. **Poser les questions plutôt que trancher en silence.** Toute question pertinente (métier, archi, design, code) doit être posée à amiral. En cas de doute entre deux approches : présenter le trade-off et demander.
3. **Répartition du code (mode apprentissage).**
   - **amiral implémente** : le serveur Go et le netcode (rooms, protocole binaire, synchro d'horloge), le gameplay client (Web Audio, hit detection, boucle PixiJS), le pipeline Python (yt-dlp, librosa, génération de partition).
   - **l'agent implémente** : l'UI React (lobby, menus, écrans), l'outillage (build, config, CI), la glue non formatrice.
   - Sur le périmètre d'amiral, l'agent livre : squelette + `TODO(amiral)` + tests. Jamais l'implémentation, sauf demande explicite.
4. **Format d'un trou à remplir** : chaque `// TODO(amiral):` contient le comportement attendu, les indices utiles, et est couvert par un test fourni qui valide l'implémentation. Le test est le critère de réussite. Calibrage : amiral est à l'aise en web/JS mais **débutant en Go** → indices plus généreux côté serveur (goroutines, channels, idiomes), plus succincts côté client.
5. **Ne jamais réécrire le code d'amiral sans accord.** Si une amélioration est possible : la signaler et l'expliquer. Une review demandée = expliquer et suggérer, pas réécrire.
6. **Expliquer le pourquoi** des choix non évidents, brièvement, au moment où ils sont faits.
7. **Langue** : français pour les docs, discussions et messages de commit ; anglais pour les identifiants de code.
