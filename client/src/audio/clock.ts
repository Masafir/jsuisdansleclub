/**
 * Horloge du morceau — la pièce la plus critique du jeu.
 *
 * Tout le timing du gameplay se dérive d'`AudioContext.currentTime`, jamais de
 * `Date.now()` ni de `requestAnimationFrame` : ce sont les seules millisecondes
 * fiables du navigateur, cadencées par la carte son elle-même.
 *
 * L'horloge ne lit pas directement l'AudioContext : elle reçoit une fonction
 * `now()`. Ça permet de la tester avec un temps simulé, et plus tard de lui
 * passer l'horloge synchronisée avec le serveur sans rien changer d'autre.
 */

import { CALIBRATION } from '../config/gameplay';

export class ClockNotStartedError extends Error {}

export interface SongClockOptions {
  /** Renvoie le temps courant en **secondes** (signature d'`AudioContext.currentTime`). */
  now: () => number;
  /**
   * Latence de sortie du joueur, en millisecondes, mesurée à la calibration.
   * Positive = le son arrive en retard aux oreilles (cas du Bluetooth).
   */
  calibrationOffsetMs?: number;
}

export class SongClock {
  private readonly now: () => number;
  private readonly calibrationOffsetMs: number;

  /** Instant (en secondes, échelle de `now()`) où le morceau démarre. */
  private startTimeSec: number | null = null;
  /** Position dans le morceau au démarrage, en ms (≠ 0 si on rejoint en cours). */
  private startOffsetMs = 0;

  constructor(options: SongClockOptions) {
    this.now = options.now;
    this.calibrationOffsetMs =
      options.calibrationOffsetMs ?? CALIBRATION.DEFAULT_OFFSET_MS;
  }

  /**
   * Programme le départ du morceau.
   *
   * @param atTimeSec Instant du départ, sur l'échelle de `now()` (secondes).
   *   Peut être dans le futur : c'est ainsi qu'on fait le décompte 3/2/1, et
   *   plus tard le départ simultané de toute une room.
   * @param startOffsetMs Position de départ dans le morceau (ms). Vaut 0 pour
   *   un départ normal ; sert au joueur qui rejoint une partie en cours.
   */
  start(atTimeSec: number, startOffsetMs = 0): void {
    // TODO(amiral): mémoriser `atTimeSec` et `startOffsetMs` dans les champs
    // `startTimeSec` et `startOffsetMs`. Deux lignes, c'est tout.
    throw new Error('TODO(amiral): SongClock.start');
  }

  /** L'horloge a-t-elle reçu un ordre de départ ? */
  get isStarted(): boolean {
    return this.startTimeSec !== null;
  }

  /**
   * Position courante dans le morceau, en millisecondes.
   *
   * Négative avant le départ — et c'est voulu : pendant le décompte 3/2/1, la
   * valeur monte de -3000 vers 0, ce qui permet d'afficher le décompte et de
   * faire déjà défiler les premières notes vers la ligne de jugement.
   *
   * @throws ClockNotStartedError si `start()` n'a pas été appelé.
   */
  getSongTimeMs(): number {
    // TODO(amiral):
    //   1. Si `this.startTimeSec` est null, lever une ClockNotStartedError.
    //   2. Sinon : temps écoulé = this.now() - this.startTimeSec  (en SECONDES,
    //      donc à convertir en millisecondes), auquel on ajoute startOffsetMs.
    throw new Error('TODO(amiral): SongClock.getSongTimeMs');
  }

  /**
   * Position à utiliser pour **juger un appui du joueur**, corrigée de sa
   * latence de sortie audio.
   *
   * Pourquoi soustraire l'offset : si le casque retarde le son de 200 ms, le
   * joueur entend le temps `p` alors que l'horloge en est déjà à `p + 200`.
   * Il appuie donc « à l'heure » à un moment que l'horloge date de `p + 200`.
   * Retirer les 200 ms rend à son appui l'instant qu'il visait réellement.
   *
   * @throws ClockNotStartedError si `start()` n'a pas été appelé.
   */
  getInputTimeMs(): number {
    // TODO(amiral): renvoyer getSongTimeMs() corrigé de this.calibrationOffsetMs
    // (relis le paragraphe ci-dessus pour le signe).
    throw new Error('TODO(amiral): SongClock.getInputTimeMs');
  }

  /** Remet l'horloge à l'état initial (retour au menu, rejouer). */
  reset(): void {
    this.startTimeSec = null;
    this.startOffsetMs = 0;
  }
}
