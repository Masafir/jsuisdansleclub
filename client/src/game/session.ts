/**
 * Orchestration d'une partie : câble ensemble l'horloge, le jugement, le score
 * et le rendu, et fait tourner la boucle de jeu.
 *
 * C'est ici que se joue la séquence décrite dans DECISIONS.md : décompte 3/2/1,
 * lancement du son, jeu, puis game over ou victoire.
 */

import { Judge } from './judge';
import { HoldManager, type HoldRelease } from './holds';
import { ScoreTracker, isPlayerDead, type ScoreState } from './scoring';
import { SongClock } from '../audio/clock';
import { SfxPlayer } from '../audio/sfx';
import { getAudioContext, loadAudioBuffer, unlockAudioContext } from '../audio/loader';
import { HighwayRenderer } from '../render/highway';
import type { Chart, Note } from '../chart/types';
import {
  COUNTDOWN,
  HIGHWAY,
  NOTE_TYPES,
  RESULTS_TRANSITION,
  missedNoteLingerMs,
  musicVolume,
  noteTypeForKey,
  type Judgement,
  type NoteType,
} from '../config/gameplay';

/**
 * `ending` : la partie est jouée (gagnée ou perdue) mais l'écran de résultats
 * n'est pas encore montré — le temps du battement de `RESULTS_TRANSITION`.
 * Les entrées du joueur sont ignorées (elles ne testent que `=== 'playing'`),
 * le rendu continue de tourner pour que la dernière pulsation ait le temps de
 * s'éteindre au lieu de se figer.
 */
export type SessionStatus =
  | 'idle'
  | 'countdown'
  | 'playing'
  | 'ending'
  | 'dead'
  | 'survived';

export interface SessionSnapshot {
  status: SessionStatus;
  score: ScoreState;
  successRatio: number;
  /** Palier de décompte restant (3, 2, 1), ou null hors décompte. */
  countdownStep: number | null;
  lastJudgement: Judgement | null;
  songTimeMs: number;
  /**
   * Écart moyen des appuis, en ms : positif = le joueur frappe en retard.
   * `null` tant qu'aucune touche n'a visé une note.
   *
   * Un écart moyen important révèle un décalage systématique (latence audio,
   * notes générées légèrement tardives) plutôt qu'un manque de précision : il
   * se corrige par la calibration, pas en élargissant les fenêtres.
   */
  meanDeltaMs: number | null;
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

  private readonly judges: Record<NoteType, Judge>;
  private readonly holds = new HoldManager();
  private readonly tracker = new ScoreTracker();
  private readonly clock: SongClock;
  private readonly sfx = new SfxPlayer();

  private source: AudioBufferSourceNode | null = null;
  private musicGain: GainNode | null = null;
  private frameHandle: number | null = null;
  private status: SessionStatus = 'idle';
  /** Instant (temps morceau) où le battement de fin a commencé. */
  private endingStartedAtMs = 0;
  /** Résultat final, connu dès le début du battement mais annoncé après lui. */
  private endingResult: 'dead' | 'survived' | null = null;
  private lastJudgement: Judgement | null = null;
  /**
   * Notes ratées encore à l'écran. Elles ont quitté le champ du Judge (le
   * curseur est passé) mais continuent d'être dessinées jusqu'à sortir par la
   * gauche : c'est ce qui distingue visuellement un échec d'une réussite.
   */
  private missedNotes: Note[] = [];
  /** Somme et nombre des écarts mesurés, pour en tirer une moyenne. */
  private deltaSumMs = 0;
  private deltaCount = 0;
  /** Passe à true dès `stop()` : empêche un démarrage tardif après démontage. */
  private disposed = false;

  constructor(options: GameSessionOptions) {
    this.chart = options.chart;
    this.renderer = options.renderer;
    this.onSnapshot = options.onSnapshot;
    // Un Judge par lane : chaque couleur est une file indépendante. Frapper le
    // rouge ne peut pas consommer une note bleue, et réciproquement.
    this.judges = {
      DON: new Judge(options.chart.notes.filter((note) => note.type === 'DON')),
      KA: new Judge(options.chart.notes.filter((note) => note.type === 'KA')),
    };
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
    // direct : c'est ce qui rend son volume réglable, et l'automatise au
    // battement de fin (fondu, voir beginEnding).
    this.musicGain = ctx.createGain();
    this.musicGain.gain.value = musicVolume();
    this.source.connect(this.musicGain).connect(ctx.destination);

    this.source.start(startAtSec);

    this.clock.start(startAtSec);
    this.status = 'countdown';
    this.loop();
  }

  /** Enfoncement d'une touche clavier. */
  handleKeyDown(key: string): void {
    const type = noteTypeForKey(key);
    if (type) this.handleNoteDown(type, `key:${key.toLowerCase()}`);
  }

  /** Relâchement d'une touche clavier. */
  handleKeyUp(key: string): void {
    const type = noteTypeForKey(key);
    if (type) this.handleNoteUp(type, `key:${key.toLowerCase()}`);
  }

  /**
   * Le joueur frappe une lane, quelle que soit la source : touche clavier ou
   * doigt sur mobile. `source` identifie qui appuie, pour que le hold survive
   * tant qu'une des deux touches de la lane reste enfoncée.
   */
  handleNoteDown(type: NoteType, source: string): void {
    if (this.status !== 'playing') return;
    this.holds.press(type, source);

    const result = this.judges[type].hit(this.clock.getInputTimeMs());
    if (!result) return;

    // Tout appui ayant vise une note compte, y compris raté : c'est justement
    // un décalage systématique qui produit des ratés.
    this.deltaSumMs += result.deltaMs;
    this.deltaCount++;

    this.tracker.register(result.judgement);
    this.lastJudgement = result.judgement;
    this.sfx.play(result.judgement);
    this.renderer.spawnPulse(result.judgement, this.clock.getSongTimeMs(), type);

    if (result.judgement === 'MISS') {
      // Une note frappée trop tôt ou trop tard reste visible : le joueur voit
      // passer ce qu'il a manqué.
      this.missedNotes.push(result.note);
    } else if (result.note.durationMs) {
      // Hit réussi sur une note à durée : la tenue commence.
      this.holds.begin(result.note);
    }
  }

  /** Le joueur relâche une lane. */
  handleNoteUp(type: NoteType, source: string): void {
    if (this.status !== 'playing') {
      this.holds.release(type, source, 0);
      return;
    }
    const release = this.holds.release(type, source, this.clock.getSongTimeMs());
    if (release) this.settleHold(release);
  }

  /** Crédite une tenue terminée, complète ou non. */
  private settleHold(release: HoldRelease): void {
    this.tracker.registerHold(release.heldMs);
    if (release.completed) {
      // Une tenue menée au bout mérite le feedback maximal.
      this.sfx.play('PERFECT');
      this.renderer.spawnPulse('PERFECT', this.clock.getSongTimeMs(), release.note.type);
    }
  }

  private loop = (): void => {
    this.frameHandle = requestAnimationFrame(this.loop);

    const songTimeMs = this.clock.getSongTimeMs();

    if (this.status === 'countdown' && songTimeMs >= 0) {
      this.status = 'playing';
    }

    if (this.status === 'playing') {
      for (const type of NOTE_TYPES) {
        for (const missed of this.judges[type].update(songTimeMs)) {
          this.tracker.register('MISS');
          this.lastJudgement = 'MISS';
          this.renderer.spawnPulse('MISS', songTimeMs, type);
          this.missedNotes.push(missed);
        }
      }

      // Tenues arrivées naturellement à leur terme.
      for (const release of this.holds.update(songTimeMs)) {
        this.settleHold(release);
      }

      const chartDone =
        this.judges.DON.isFinished &&
        this.judges.KA.isFinished &&
        this.holds.activeHolds.length === 0;

      if (isPlayerDead(this.tracker, songTimeMs, this.chart.durationMs)) {
        this.beginEnding('dead', songTimeMs);
      } else if (songTimeMs >= this.chart.durationMs || chartDone) {
        this.beginEnding('survived', songTimeMs);
      }
    } else if (
      this.status === 'ending' &&
      songTimeMs - this.endingStartedAtMs >= RESULTS_TRANSITION.DELAY_MS
    ) {
      this.finish();
    }

    // Oublier les notes ratées une fois sorties de l'écran, sinon elles
    // s'accumuleraient pendant tout le morceau.
    const lingerMs = missedNoteLingerMs();
    this.missedNotes = this.missedNotes.filter(
      (note) => songTimeMs - note.timeMs <= lingerMs,
    );

    this.renderer.renderNotes(
      [
        ...this.missedNotes,
        ...this.judges.DON.visibleNotes(songTimeMs, HIGHWAY.APPROACH_TIME_MS),
        ...this.judges.KA.visibleNotes(songTimeMs, HIGHWAY.APPROACH_TIME_MS),
      ],
      songTimeMs,
    );
    this.renderer.renderActiveHolds(this.holds.activeHolds, songTimeMs);
    this.renderer.updatePulses(songTimeMs);
    this.renderer.updateJudgeCircle(songTimeMs);
    this.emit(songTimeMs);
  };

  /**
   * La partie vient de se décider (gagnée ou perdue), mais l'écran de
   * résultats attend `RESULTS_TRANSITION.DELAY_MS` avant de s'afficher — le
   * temps que la dernière pulsation s'éteigne à l'écran plutôt que de couper
   * net. Le résultat est déjà acquis, `this.status` reste `'ending'` jusque-là
   * (voir la boucle), ce qui bloque à la fois les entrées et une nouvelle
   * détection de fin de partie.
   */
  private beginEnding(result: 'dead' | 'survived', songTimeMs: number): void {
    this.status = 'ending';
    this.endingResult = result;
    this.endingStartedAtMs = songTimeMs;

    // Le fondu commence tout de suite, pour que le silence soit déjà installé
    // à l'affichage des résultats plutôt qu'une coupure nette au dernier instant.
    if (this.musicGain) {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      this.musicGain.gain.cancelScheduledValues(now);
      this.musicGain.gain.setValueAtTime(this.musicGain.gain.value, now);
      this.musicGain.gain.linearRampToValueAtTime(
        0,
        now + RESULTS_TRANSITION.FADE_OUT_MS / 1000,
      );
    }
  }

  /** Le battement de fin est écoulé : on bascule vers l'écran de résultats. */
  private finish(): void {
    if (!this.endingResult) return;
    this.status = this.endingResult;
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
    this.musicGain = null;
    this.status = 'idle';
    this.endingResult = null;
    this.missedNotes = [];
    this.deltaSumMs = 0;
    this.deltaCount = 0;
    this.holds.reset();
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
      meanDeltaMs: this.deltaCount === 0 ? null : this.deltaSumMs / this.deltaCount,
    });
  }
}
