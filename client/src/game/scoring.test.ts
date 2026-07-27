import { describe, expect, it } from 'vitest';
import { ScoreTracker, isPlayerDead } from './scoring';
import { SCORING, SURVIVAL, type Judgement } from '../config/gameplay';

function trackerWith(...judgements: Judgement[]): ScoreTracker {
  const tracker = new ScoreTracker();
  for (const judgement of judgements) tracker.register(judgement);
  return tracker;
}

function repeat(judgement: Judgement, times: number): Judgement[] {
  return Array.from({ length: times }, () => judgement);
}

describe('ScoreTracker — état initial', () => {
  it('démarre à zéro, avec un ratio de 1 et un multiplicateur de 1', () => {
    const tracker = new ScoreTracker();
    expect(tracker.state.score).toBe(0);
    expect(tracker.state.combo).toBe(0);
    expect(tracker.judgedCount).toBe(0);
    expect(tracker.successRatio).toBe(1);
    expect(tracker.multiplier).toBe(1);
  });
});

describe('ScoreTracker — combo', () => {
  it('incrémente le combo sur PERFECT et GOOD', () => {
    expect(trackerWith('PERFECT', 'GOOD', 'PERFECT').state.combo).toBe(3);
  });

  it('remet le combo à zéro sur MISS', () => {
    expect(trackerWith('PERFECT', 'PERFECT', 'MISS').state.combo).toBe(0);
  });

  it('retient le meilleur combo atteint', () => {
    const tracker = trackerWith('PERFECT', 'PERFECT', 'PERFECT', 'MISS', 'GOOD');
    expect(tracker.state.combo).toBe(1);
    expect(tracker.state.maxCombo).toBe(3);
  });
});

describe('ScoreTracker — multiplicateur', () => {
  it('vaut 1 avant le premier palier', () => {
    const tracker = trackerWith(...repeat('PERFECT', SCORING.COMBO_STEP - 1));
    expect(tracker.multiplier).toBeCloseTo(1);
  });

  it('monte d’un cran à chaque palier franchi', () => {
    const oneStep = trackerWith(...repeat('PERFECT', SCORING.COMBO_STEP));
    expect(oneStep.multiplier).toBeCloseTo(1 + SCORING.COMBO_BONUS_PER_STEP);

    const twoSteps = trackerWith(...repeat('PERFECT', SCORING.COMBO_STEP * 2));
    expect(twoSteps.multiplier).toBeCloseTo(1 + SCORING.COMBO_BONUS_PER_STEP * 2);
  });

  it('ne dépasse jamais le plafond', () => {
    const tracker = trackerWith(...repeat('PERFECT', SCORING.COMBO_STEP * 1000));
    expect(tracker.multiplier).toBe(SCORING.MAX_MULTIPLIER);
  });

  it('retombe à 1 après un MISS', () => {
    const tracker = trackerWith(
      ...repeat('PERFECT', SCORING.COMBO_STEP * 3),
      'MISS',
    );
    expect(tracker.multiplier).toBeCloseTo(1);
  });
});

describe('ScoreTracker — score', () => {
  it('ajoute les points du jugement au multiplicateur courant', () => {
    expect(trackerWith('PERFECT').state.score).toBe(SCORING.POINTS.PERFECT);
    expect(trackerWith('GOOD').state.score).toBe(SCORING.POINTS.GOOD);
  });

  it('ne rapporte rien sur un MISS', () => {
    expect(trackerWith('MISS').state.score).toBe(SCORING.POINTS.MISS);
  });

  it('applique le multiplicateur obtenu APRÈS mise à jour du combo', () => {
    // Les COMBO_STEP premiers PERFECT font passer le combo à COMBO_STEP : le
    // dernier d'entre eux est donc déjà payé au multiplicateur du palier.
    const tracker = trackerWith(...repeat('PERFECT', SCORING.COMBO_STEP));
    const withoutBonus = SCORING.POINTS.PERFECT * SCORING.COMBO_STEP;
    expect(tracker.state.score).toBeGreaterThan(withoutBonus);
  });

  it('produit un score entier', () => {
    const tracker = trackerWith(...repeat('GOOD', SCORING.COMBO_STEP + 3));
    expect(Number.isInteger(tracker.state.score)).toBe(true);
  });
});

describe('ScoreTracker — ratio de réussite', () => {
  it('compte PERFECT et GOOD comme des réussites', () => {
    expect(trackerWith('PERFECT', 'GOOD').successRatio).toBe(1);
  });

  it('tombe à 0 quand tout est raté', () => {
    expect(trackerWith('MISS', 'MISS').successRatio).toBe(0);
  });

  it('vaut la proportion de notes réussies', () => {
    expect(trackerWith('PERFECT', 'MISS').successRatio).toBe(0.5);
    expect(trackerWith('PERFECT', 'GOOD', 'GOOD', 'MISS').successRatio).toBe(0.75);
  });
});

describe('ScoreTracker — reset', () => {
  it('remet tout à zéro', () => {
    const tracker = trackerWith('PERFECT', 'GOOD', 'MISS');
    tracker.reset();
    expect(tracker.state).toEqual({
      score: 0,
      combo: 0,
      maxCombo: 0,
      counts: { PERFECT: 0, GOOD: 0, MISS: 0 },
      judgedCount: 0,
    });
  });
});

describe('isPlayerDead — la danse mortelle', () => {
  const DURATION_MS = 60_000;
  /** Un instant confortablement après la période de grâce. */
  const AFTER_GRACE_MS = DURATION_MS * SURVIVAL.GRACE_PERIOD_RATIO + 1;
  /** Assez de notes jugées pour que la règle s'applique. */
  const ENOUGH = SURVIVAL.MIN_JUDGED_NOTES;

  it('épargne le joueur pendant la période de grâce, même à 0 %', () => {
    const tracker = trackerWith(...repeat('MISS', ENOUGH));
    expect(isPlayerDead(tracker, 0, DURATION_MS)).toBe(false);
    expect(
      isPlayerDead(tracker, DURATION_MS * SURVIVAL.GRACE_PERIOD_RATIO - 1, DURATION_MS),
    ).toBe(false);
  });

  it('tue le joueur sous le seuil une fois la grâce terminée', () => {
    const tracker = trackerWith(...repeat('MISS', ENOUGH));
    expect(isPlayerDead(tracker, AFTER_GRACE_MS, DURATION_MS)).toBe(true);
  });

  it('épargne le joueur au-dessus du seuil', () => {
    const tracker = trackerWith(...repeat('PERFECT', ENOUGH));
    expect(isPlayerDead(tracker, AFTER_GRACE_MS, DURATION_MS)).toBe(false);
  });

  it('épargne le joueur pile au seuil (il faut passer SOUS pour mourir)', () => {
    const half = Math.ceil(ENOUGH / 2);
    const tracker = trackerWith(...repeat('PERFECT', half), ...repeat('MISS', half));
    expect(tracker.successRatio).toBe(SURVIVAL.MIN_SUCCESS_RATIO);
    expect(isPlayerDead(tracker, AFTER_GRACE_MS, DURATION_MS)).toBe(false);
  });

  it('n’applique pas la règle avant assez de notes jugées', () => {
    const tracker = trackerWith(...repeat('MISS', SURVIVAL.MIN_JUDGED_NOTES - 1));
    expect(isPlayerDead(tracker, AFTER_GRACE_MS, DURATION_MS)).toBe(false);
  });

  it('épargne un joueur qui n’a encore rien joué', () => {
    expect(isPlayerDead(new ScoreTracker(), AFTER_GRACE_MS, DURATION_MS)).toBe(false);
  });
});
