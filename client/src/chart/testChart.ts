/**
 * Partition de test écrite à la main, pour valider le gameplay avant que le
 * pipeline Python n'existe.
 *
 * Motif simple et lisible : une note sur chaque temps, avec des KA sur les
 * contretemps toutes les deux mesures pour varier un peu.
 */

import { CHART_FORMAT_VERSION, type Chart, type Note } from './types';

const TEST_BPM = 120;
const TEST_DURATION_MS = 60_000;
const TEST_OFFSET_MS = 0;
/** Nombre de temps par mesure (4/4). */
const BEATS_PER_BAR = 4;
/** Une mesure sur deux reçoit des contretemps. */
const SYNCOPATED_BAR_INTERVAL = 2;

function buildTestNotes(): Note[] {
  const msPerBeat = 60_000 / TEST_BPM;
  const beatCount = Math.floor(TEST_DURATION_MS / msPerBeat);
  const notes: Note[] = [];

  for (let beat = 0; beat < beatCount; beat++) {
    const bar = Math.floor(beat / BEATS_PER_BAR);
    notes.push({ timeMs: TEST_OFFSET_MS + beat * msPerBeat, type: 'DON' });

    if (bar % SYNCOPATED_BAR_INTERVAL === 1) {
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
  title: 'Test — 120 BPM',
  audioUrl: '/audio/test-song.mp3',
  durationMs: TEST_DURATION_MS,
  bpm: TEST_BPM,
  offsetMs: TEST_OFFSET_MS,
  notes: buildTestNotes(),
};
