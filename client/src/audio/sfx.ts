/**
 * Effets sonores joués à chaque appui du joueur.
 *
 * Ils passent par Web Audio (et non par des balises <audio>) pour être
 * déclenchés sans latence et pouvoir se superposer.
 */

import { SFX, type Judgement } from '../config/gameplay';
import { getAudioContext, loadOptionalAudioBuffer } from './loader';

const SFX_URLS: Record<Judgement, string> = {
  PERFECT: '/audio/sfx-perfect.mp3',
  GOOD: '/audio/sfx-good.mp3',
  MISS: '/audio/sfx-miss.mp3',
};

export class SfxPlayer {
  private buffers = new Map<Judgement, AudioBuffer>();

  /** Précharge les trois sons. Un fichier manquant est simplement ignoré. */
  async load(): Promise<void> {
    const entries = Object.entries(SFX_URLS) as [Judgement, string][];
    await Promise.all(
      entries.map(async ([judgement, url]) => {
        const buffer = await loadOptionalAudioBuffer(url);
        if (buffer) this.buffers.set(judgement, buffer);
      }),
    );
  }

  play(judgement: Judgement): void {
    const buffer = this.buffers.get(judgement);
    if (!buffer) return;

    const ctx = getAudioContext();
    const source = ctx.createBufferSource();
    source.buffer = buffer;

    const gain = ctx.createGain();
    gain.gain.value = SFX.VOLUME[judgement];

    source.connect(gain).connect(ctx.destination);
    source.start();
  }
}
