/**
 * Orchestration d'une partie : câble ensemble l'horloge, le jugement, le score
 * et le rendu, et fait tourner la boucle de jeu.
 *
 * C'est ici que se joue la séquence décrite dans DECISIONS.md : décompte 3/2/1,
 * lancement du son, jeu, puis game over ou victoire.
 */

import { Judge } from './judge';
import { ScoreTracker, isPlayerDead, type ScoreState } from './scoring';
import { SongClock } from '../audio/clock';
import { SfxPlayer } from '../audio/sfx';
import { getAudioContext, loadAudioBuffer, unlockAudioContext } from '../audio/loader';
import { HighwayRenderer } from '../render/highway';
import type { Chart, Note } from '../chart/types';
import {
  COUNTDOWN,
  HIGHWAY,
  missedNoteLingerMs,
  musicVolume,
  noteTypeForKey,
  type Judgement,
} from '../config/gameplay';

export type SessionStatus = 'idle' | 'countdown' | 'playing' | 'dead' | 'survived';

export interface SessionSnapshot {
  status: SessionStatus;
  score: ScoreState;
  successRatio: number;
  /** Palier de décompte restant (3, 2, 1), ou null hors décompte. */
  countdownStep: number | null;
  lastJudgement: Judgement | null;
  songTimeMs: number;
}

export interface GameSessionOptions {
  chart: Chart;
  renderer: HighwayRenderer;
  calibrationOffsetMs: number;
  onSnapshot: (snapshot: SessionSnapshot) => void;
}

export class GameSession {
  private readonly chart: Chart;
  private readonly renderer: HighwayRenderer;
  private readonly onSnapshot: (snapshot: SessionSnapshot) => void;

  private readonly judge: Judge;
  private readonly tracker = new ScoreTracker();
  private readonly clock: SongClock;
  private readonly sfx = new SfxPlayer();

  private source: AudioBufferSourceNode | null = null;
  private frameHandle: number | null = null;
  private status: SessionStatus = 'idle';
  private lastJudgement: Judgement | null = null;
  /**
   * Notes ratées encore à l'écran. Elles ont quitté le champ du Judge (le
   * curseur est passé) mais continuent d'être dessinées jusqu'à sortir par la
   * gauche : c'est ce qui distingue visuellement un échec d'une réussite.
   */
  private missedNotes: Note[] = [];
  /** Passe à true dès `stop()` : empêche un démarrage tardif après démontage. */
  private disposed = false;

  constructor(options: GameSessionOptions) {
    this.chart = options.chart;
    this.renderer = options.renderer;
    this.onSnapshot = options.onSnapshot;
    this.judge = new Judge(options.chart.notes);
    this.clock = new SongClock({
      now: () => getAudioContext().currentTime,
      calibrationOffsetMs: options.calibrationOffsetMs,
    });
  }

  /**
   * Charge l'audio, programme le départ après le décompte, et lance la boucle.
   *
   * Le son n'est pas démarré « maintenant » mais à un instant futur précis :
   * c'est exactement le mécanisme qui servira, en multijoueur, à faire partir
   * toute la room sur le même top.
   */
  async start(): Promise<void> {
    await unlockAudioContext();
    const [buffer] = await Promise.all([
      loadAudioBuffer(this.chart.audioUrl),
      this.sfx.load(),
    ]);
    // La partie a pu être abandonnée pendant le chargement : sans ce garde, le
    // morceau se lancerait dans le vide après le retour au menu.
    if (this.disposed) return;

    const ctx = getAudioContext();
    const countdownMs = COUNTDOWN.STEPS * COUNTDOWN.STEP_DURATION_MS;
    const startAtSec = ctx.currentTime + (countdownMs + COUNTDOWN.SCHEDULE_LEAD_MS) / 1000;

    this.source = ctx.createBufferSource();
    this.source.buffer = buffer;

    // Le morceau passe par un GainNode plutôt que d'attaquer la sortie en
    // direct : c'est ce qui rend son volume réglable, et plus tard automatisable
    // (fondu à la mort du joueur, atténuation pendant un taunt…).
    const musicGain = ctx.createGain();
    musicGain.gain.value = musicVolume();
    this.source.connect(musicGain).connect(ctx.destination);

    this.source.start(startAtSec);

    this.clock.start(startAtSec);
    this.status = 'countdown';
    this.loop();
  }

  /** Un appui clavier du joueur. */
  handleKey(key: string): void {
    if (this.status !== 'playing') return;

    const type = noteTypeForKey(key);
    if (!type) return;

    const result = this.judge.hit(this.clock.getInputTimeMs(), type);
    if (!result) return;

    this.tracker.register(result.judgement);
    this.lastJudgement = result.judgement;
    this.sfx.play(result.judgement);
    this.renderer.spawnPulse(result.judgement, this.clock.getSongTimeMs());

    // Une note frappée trop tôt, trop tard ou avec la mauvaise touche reste
    // visible : le joueur voit passer ce qu'il a manqué.
    if (result.judgement === 'MISS') this.missedNotes.push(result.note);
  }

  private loop = (): void => {
    this.frameHandle = requestAnimationFrame(this.loop);

    const songTimeMs = this.clock.getSongTimeMs();

    if (this.status === 'countdown' && songTimeMs >= 0) {
      this.status = 'playing';
    }

    if (this.status === 'playing') {
      for (const missed of this.judge.update(songTimeMs)) {
        this.tracker.register('MISS');
        this.lastJudgement = 'MISS';
        this.renderer.spawnPulse('MISS', songTimeMs);
        this.missedNotes.push(missed);
      }

      if (isPlayerDead(this.tracker, songTimeMs, this.chart.durationMs)) {
        this.finish('dead');
      } else if (songTimeMs >= this.chart.durationMs || this.judge.isFinished) {
        this.finish('survived');
      }
    }

    // Oublier les notes ratées une fois sorties de l'écran, sinon elles
    // s'accumuleraient pendant tout le morceau.
    const lingerMs = missedNoteLingerMs();
    this.missedNotes = this.missedNotes.filter(
      (note) => songTimeMs - note.timeMs <= lingerMs,
    );

    this.renderer.renderNotes(
      [...this.missedNotes, ...this.judge.visibleNotes(songTimeMs, HIGHWAY.APPROACH_TIME_MS)],
      songTimeMs,
    );
    this.renderer.updatePulses(songTimeMs);
    this.emit(songTimeMs);
  };

  private finish(status: 'dead' | 'survived'): void {
    this.status = status;
    this.source?.stop();
    this.source = null;
    if (this.frameHandle !== null) {
      cancelAnimationFrame(this.frameHandle);
      this.frameHandle = null;
    }
    this.emit(this.chart.durationMs);
  }

  stop(): void {
    this.disposed = true;
    if (this.frameHandle !== null) cancelAnimationFrame(this.frameHandle);
    this.frameHandle = null;
    try {
      this.source?.stop();
    } catch {
      // Déjà arrêtée : rien à faire.
    }
    this.source = null;
    this.status = 'idle';
    this.missedNotes = [];
    this.renderer.clear();
  }

  private emit(songTimeMs: number): void {
    const countdownStep =
      this.status === 'countdown'
        ? Math.ceil(-songTimeMs / COUNTDOWN.STEP_DURATION_MS)
        : null;

    this.onSnapshot({
      status: this.status,
      score: this.tracker.state,
      successRatio: this.tracker.successRatio,
      countdownStep,
      lastJudgement: this.lastJudgement,
      songTimeMs,
    });
  }
}
