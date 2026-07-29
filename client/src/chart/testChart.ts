/**
 * Partition de test écrite à la main, pour valider le gameplay avant que le
 * pipeline Python n'existe.
 *
 * Motif lisible : une note sur chaque temps, des KA sur les contretemps une
 * mesure sur deux, et toutes les quatre mesures une « envolée » — un hold KA
 * de deux temps pendant que les DON continuent en dessous. C'est le cas
 * d'usage exact du format deux lanes : tenir d'une main, frapper de l'autre.
 */

import { CHART_FORMAT_VERSION, type Chart, type Note } from './types';

/**
 * Valeurs calées sur le `test-song.mp3` actuel, estimées par autocorrélation de
 * l'enveloppe d'énergie (la méthode que le pipeline Python industrialisera).
 * À réajuster à l'oreille si la grille dérive, ou en changeant de morceau.
 */
const TEST_BPM = 135;
const TEST_DURATION_MS = 174_000;
const TEST_OFFSET_MS = 20;
/** Nombre de temps par mesure (4/4). */
const BEATS_PER_BAR = 4;
/** Une mesure sur deux reçoit des contretemps. */
const SYNCOPATED_BAR_INTERVAL = 2;
/** Une mesure sur quatre porte une envolée tenue. */
const HOLD_BAR_INTERVAL = 4;
/** Durée d'une envolée, en temps. */
const HOLD_BEATS = 2;

function buildTestNotes(): Note[] {
  const msPerBeat = 60_000 / TEST_BPM;
  const beatCount = Math.floor(TEST_DURATION_MS / msPerBeat);
  const notes: Note[] = [];

  for (let beat = 0; beat < beatCount; beat++) {
    const bar = Math.floor(beat / BEATS_PER_BAR);
    const beatInBar = beat % BEATS_PER_BAR;
    const holdBar = bar % HOLD_BAR_INTERVAL === HOLD_BAR_INTERVAL - 1;

    // Les DON tiennent la pulsation sur chaque temps, y compris sous les
    // envolées : c'est le parallèle tenue + frappes qu'on veut éprouver.
    notes.push({ timeMs: TEST_OFFSET_MS + beat * msPerBeat, type: 'DON' });

    if (holdBar) {
      if (beatInBar === 0) {
        notes.push({
          timeMs: TEST_OFFSET_MS + beat * msPerBeat,
          type: 'KA',
          durationMs: HOLD_BEATS * msPerBeat,
        });
      }
    } else if (bar % SYNCOPATED_BAR_INTERVAL === 1) {
      notes.push({
        timeMs: TEST_OFFSET_MS + (beat + 0.5) * msPerBeat,
        type: 'KA',
      });
    }
  }
  return notes;
}

export const TEST_CHART: Chart = {
  version: CHART_FORMAT_VERSION,
  title: `Morceau de test — ${TEST_BPM} BPM`,
  audioUrl: '/audio/test-song.mp3',
  durationMs: TEST_DURATION_MS,
  bpm: TEST_BPM,
  offsetMs: TEST_OFFSET_MS,
  notes: buildTestNotes(),
};
