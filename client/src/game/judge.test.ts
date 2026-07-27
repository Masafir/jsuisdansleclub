import { describe, expect, it } from 'vitest';
import { Judge } from './judge';
import { TIMING } from '../config/gameplay';
import type { Note } from '../chart/types';

const notes: Note[] = [
  { timeMs: 1000, type: 'DON' },
  { timeMs: 2000, type: 'KA' },
  { timeMs: 3000, type: 'DON' },
];

const makeJudge = () => new Judge(notes);

describe('Judge.hit', () => {
  it('juge PERFECT un appui pile sur la note', () => {
    const result = makeJudge().hit(1000, 'DON');
    expect(result?.judgement).toBe('PERFECT');
    expect(result?.deltaMs).toBe(0);
    expect(result?.note).toBe(notes[0]);
  });

  it('juge PERFECT jusqu’au bord de la fenêtre parfaite', () => {
    expect(makeJudge().hit(1000 + TIMING.PERFECT_WINDOW_MS, 'DON')?.judgement).toBe(
      'PERFECT',
    );
    expect(makeJudge().hit(1000 - TIMING.PERFECT_WINDOW_MS, 'DON')?.judgement).toBe(
      'PERFECT',
    );
  });

  it('juge GOOD au-delà de la fenêtre parfaite, en avance comme en retard', () => {
    const late = makeJudge().hit(1000 + TIMING.PERFECT_WINDOW_MS + 1, 'DON');
    expect(late?.judgement).toBe('GOOD');

    const early = makeJudge().hit(1000 - TIMING.GOOD_WINDOW_MS, 'DON');
    expect(early?.judgement).toBe('GOOD');
    expect(early?.deltaMs).toBe(-TIMING.GOOD_WINDOW_MS);
  });

  it('juge MISS un appui dans la fenêtre candidate mais hors de la fenêtre GOOD', () => {
    const result = makeJudge().hit(1000 + TIMING.GOOD_WINDOW_MS + 1, 'DON');
    expect(result?.judgement).toBe('MISS');
  });

  it('juge MISS un appui bien timé mais sur la mauvaise touche', () => {
    const result = makeJudge().hit(1000, 'KA'); // la note est un DON
    expect(result?.judgement).toBe('MISS');
  });

  it('ignore un appui hors de toute fenêtre candidate, sans consommer la note', () => {
    const judge = makeJudge();
    expect(judge.hit(1000 - TIMING.CANDIDATE_WINDOW_MS - 1, 'DON')).toBeNull();

    // La note doit rester jouable juste après.
    expect(judge.hit(1000, 'DON')?.judgement).toBe('PERFECT');
  });

  it('consomme les notes une par une, dans l’ordre', () => {
    const judge = makeJudge();
    expect(judge.hit(1000, 'DON')?.note).toBe(notes[0]);
    expect(judge.hit(2000, 'KA')?.note).toBe(notes[1]);
    expect(judge.hit(3000, 'DON')?.note).toBe(notes[2]);
    expect(judge.isFinished).toBe(true);
  });

  it('ne rejuge pas une note déjà consommée', () => {
    const judge = makeJudge();
    judge.hit(1000, 'DON');
    // Un second appui au même instant ne vise plus rien : la note suivante
    // est à 2000 ms, bien au-delà de la fenêtre candidate.
    expect(judge.hit(1000, 'DON')).toBeNull();
  });

  it('renvoie null quand toutes les notes ont été jouées', () => {
    const judge = makeJudge();
    judge.hit(1000, 'DON');
    judge.hit(2000, 'KA');
    judge.hit(3000, 'DON');
    expect(judge.hit(3000, 'DON')).toBeNull();
  });
});

describe('Judge.update', () => {
  it('ne rate rien tant que la fenêtre GOOD n’est pas dépassée', () => {
    const judge = makeJudge();
    expect(judge.update(1000 + TIMING.GOOD_WINDOW_MS)).toEqual([]);
  });

  it('rate une note dès que la fenêtre GOOD est dépassée', () => {
    const judge = makeJudge();
    expect(judge.update(1000 + TIMING.GOOD_WINDOW_MS + 1)).toEqual([notes[0]]);
  });

  it('rate plusieurs notes d’un coup si le temps a beaucoup avancé', () => {
    const judge = makeJudge();
    expect(judge.update(5000)).toEqual(notes);
    expect(judge.isFinished).toBe(true);
  });

  it('ne rate pas une note déjà frappée', () => {
    const judge = makeJudge();
    judge.hit(1000, 'DON');
    expect(judge.update(1500)).toEqual([]);
  });

  it('ne rate pas deux fois la même note', () => {
    const judge = makeJudge();
    expect(judge.update(2000)).toEqual([notes[0]]);
    expect(judge.update(2000)).toEqual([]);
  });
});

describe('Judge.visibleNotes', () => {
  it('ne renvoie que les notes à venir dans la fenêtre demandée', () => {
    const judge = makeJudge();
    expect(judge.visibleNotes(0, 1500)).toEqual([notes[0]]);
    expect(judge.visibleNotes(0, 2500)).toEqual([notes[0], notes[1]]);
  });

  it('n’affiche plus les notes déjà jugées', () => {
    const judge = makeJudge();
    judge.hit(1000, 'DON');
    expect(judge.visibleNotes(1000, 1500)).toEqual([notes[1]]);
  });
});

describe('Judge.reset', () => {
  it('rend toutes les notes rejouables', () => {
    const judge = makeJudge();
    judge.update(5000);
    judge.reset();

    expect(judge.isFinished).toBe(false);
    expect(judge.hit(1000, 'DON')?.judgement).toBe('PERFECT');
  });
});
