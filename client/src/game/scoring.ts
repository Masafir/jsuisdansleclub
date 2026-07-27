/**
 * Score, combo et règle de survie (la « danse mortelle »).
 *
 * Le ratio de réussite calculé ici est aussi ce qui pilotera l'humeur du
 * danseur, puis ce que le serveur diffusera aux autres joueurs. C'est donc la
 * valeur centrale du jeu, bien au-delà du simple affichage du score.
 */

import { SCORING, SURVIVAL, type Judgement } from '../config/gameplay';

export interface ScoreState {
  score: number;
  combo: number;
  maxCombo: number;
  /** Nombre de notes jugées dans chaque catégorie. */
  counts: Record<Judgement, number>;
  /** Total de notes jugées. */
  judgedCount: number;
}

export class ScoreTracker {
  private _score = 0;
  private _combo = 0;
  private _maxCombo = 0;
  private readonly _counts: Record<Judgement, number> = {
    PERFECT: 0,
    GOOD: 0,
    MISS: 0,
  };

  /**
   * Multiplicateur courant : 1 au départ, +COMBO_BONUS_PER_STEP tous les
   * COMBO_STEP coups réussis d'affilée, plafonné à MAX_MULTIPLIER.
   *
   * Exemple avec les valeurs par défaut (palier 10, bonus 0.1) :
   * combo 0-9 -> ×1 ; combo 10-19 -> ×1.1 ; combo 20-29 -> ×1.2 …
   */
  get multiplier(): number {
    // TODO(amiral): calculer le multiplicateur à partir de this._combo.
    //   Utiliser Math.floor pour le nombre de paliers atteints, et Math.min
    //   contre SCORING.MAX_MULTIPLIER pour le plafond.
    throw new Error('TODO(amiral): ScoreTracker.multiplier');
  }

  /**
   * Ratio de réussite entre 0 et 1 : part des notes jugées qui ne sont pas des
   * MISS. Vaut 1 avant la première note jugée (on commence en vie).
   */
  get successRatio(): number {
    // TODO(amiral):
    //   - si aucune note n'a été jugée (this.judgedCount === 0), renvoyer 1 ;
    //   - sinon (PERFECT + GOOD) / judgedCount.
    throw new Error('TODO(amiral): ScoreTracker.successRatio');
  }

  get judgedCount(): number {
    return this._counts.PERFECT + this._counts.GOOD + this._counts.MISS;
  }

  /**
   * Enregistre le jugement d'une note et met à jour score, combo et compteurs.
   *
   * Ordre imposé (il change le score, donc à respecter) : on met d'abord le
   * combo à jour, puis on applique le multiplicateur qui en résulte.
   */
  register(judgement: Judgement): void {
    // TODO(amiral):
    //   1. Incrémenter this._counts[judgement].
    //   2. Mettre à jour le combo :
    //        - MISS remet this._combo à 0 ;
    //        - PERFECT et GOOD l'incrémentent, et mettent à jour this._maxCombo.
    //   3. Ajouter au score : SCORING.POINTS[judgement] * this.multiplier,
    //      arrondi avec Math.round (on veut un score entier).
    throw new Error('TODO(amiral): ScoreTracker.register');
  }

  get state(): ScoreState {
    return {
      score: this._score,
      combo: this._combo,
      maxCombo: this._maxCombo,
      counts: { ...this._counts },
      judgedCount: this.judgedCount,
    };
  }

  reset(): void {
    this._score = 0;
    this._combo = 0;
    this._maxCombo = 0;
    this._counts.PERFECT = 0;
    this._counts.GOOD = 0;
    this._counts.MISS = 0;
  }
}

/**
 * Règle de survie : le joueur est-il mort ?
 *
 * Le ratio de réussite doit rester au-dessus de SURVIVAL.MIN_SUCCESS_RATIO,
 * mais la vérification n'est active qu'après une période de grâce couvrant le
 * premier tiers du morceau — sans elle, un raté sur les premières notes
 * suffirait à tuer le joueur avant qu'il ait eu sa chance.
 *
 * @param tracker Score courant.
 * @param songTimeMs Position dans le morceau.
 * @param durationMs Durée totale du morceau.
 */
export function isPlayerDead(
  tracker: ScoreTracker,
  songTimeMs: number,
  durationMs: number,
): boolean {
  // TODO(amiral): renvoyer true seulement si les TROIS conditions sont réunies.
  //   1. Assez de notes jugées : tracker.judgedCount >= SURVIVAL.MIN_JUDGED_NOTES
  //   2. Période de grâce terminée :
  //      songTimeMs >= durationMs * SURVIVAL.GRACE_PERIOD_RATIO
  //   3. Ratio insuffisant :
  //      tracker.successRatio < SURVIVAL.MIN_SUCCESS_RATIO
  throw new Error('TODO(amiral): isPlayerDead');
}
