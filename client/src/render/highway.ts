/**
 * Rendu de la piste (format Taiko) : une lane horizontale, les notes défilent
 * de droite à gauche vers la ligne de jugement fixe.
 *
 * L'initialisation de PixiJS et le décor statique sont faits. Ce qui reste à
 * écrire, c'est la partie qui donne le ressenti : où se trouve une note à un
 * instant donné, et comment pulse le feedback.
 */

import { Application, Container, Graphics } from 'pixi.js';
import { FEEDBACK, HIGHWAY, type Judgement, type NoteType } from '../config/gameplay';
import { HIGHWAY_COLORS, NOTE_COLORS, FEEDBACK_COLORS, GRADIENTS } from '../config/theme';
import type { Note } from '../chart/types';

interface Pulse {
  /** Position dans le morceau au déclenchement, en ms. */
  startedAtMs: number;
  judgement: Judgement;
  graphic: Graphics;
}

export class HighwayRenderer {
  private readonly app = new Application();
  private readonly decor = new Container();
  private readonly noteLayer = new Container();
  private readonly pulseLayer = new Container();
  private readonly noteGraphics = new Map<Note, Graphics>();
  private pulses: Pulse[] = [];

  /** Prépare le canvas et l'attache au DOM. */
  async init(container: HTMLElement): Promise<void> {
    await this.app.init({
      background: HIGHWAY_COLORS.BACKGROUND,
      resizeTo: container,
      antialias: true,
    });
    container.appendChild(this.app.canvas);

    this.app.stage.addChild(this.decor, this.noteLayer, this.pulseLayer);
    this.drawDecor();
    this.app.renderer.on('resize', () => this.drawDecor());
  }

  destroy(): void {
    this.app.destroy(true, { children: true });
  }

  private get width(): number {
    return this.app.renderer.width;
  }

  private get height(): number {
    return this.app.renderer.height;
  }

  /** Abscisse de la ligne de jugement, en pixels. */
  get judgeLineX(): number {
    return this.width * HIGHWAY.JUDGE_LINE_X_RATIO;
  }

  /** Ordonnée du centre de la lane, en pixels. */
  get laneY(): number {
    return this.height * HIGHWAY.LANE_Y_RATIO;
  }

  /** Décor statique : la bande de jeu et le cercle de jugement. */
  private drawDecor(): void {
    this.decor.removeChildren();

    const laneHeight = this.height * HIGHWAY.LANE_HEIGHT_RATIO;
    const lane = new Graphics()
      .rect(0, this.laneY - laneHeight / 2, this.width, laneHeight)
      .fill({ color: HIGHWAY_COLORS.LANE_BACKGROUND })
      .stroke({ color: HIGHWAY_COLORS.LANE_BORDER, width: 2, alpha: 0.6 });

    const judgeCircle = new Graphics()
      .circle(this.judgeLineX, this.laneY, HIGHWAY.JUDGE_CIRCLE_RADIUS_PX)
      .stroke({ color: HIGHWAY_COLORS.JUDGE_CIRCLE, width: 3, alpha: 0.9 });

    this.decor.addChild(lane, judgeCircle);
  }

  /**
   * Abscisse d'une note à l'écran, en pixels.
   *
   * Repères : la note doit être exactement sur `judgeLineX` quand
   * `songTimeMs === note.timeMs`, et se trouver au bord droit de l'écran
   * `HIGHWAY.APPROACH_TIME_MS` millisecondes plus tôt.
   */
  noteX(note: Note, songTimeMs: number): number {
    // TODO(amiral): calculer la position horizontale de la note.
    //
    //   1. Temps restant avant le hit : remainingMs = note.timeMs - songTimeMs
    //      (positif = la note arrive, négatif = elle est passée à gauche).
    //
    //   2. Vitesse de défilement, en pixels par milliseconde : la note parcourt
    //      la distance (this.width - this.judgeLineX) en HIGHWAY.APPROACH_TIME_MS.
    //
    //   3. x = this.judgeLineX + remainingMs * vitesse
    //
    //   Vérifie mentalement : remainingMs = 0 doit donner judgeLineX, et
    //   remainingMs = APPROACH_TIME_MS doit donner this.width.
    const remainingMs = note.timeMs - songTimeMs;
    const speed = (this.width - this.judgeLineX) / HIGHWAY.APPROACH_TIME_MS;
    return this.judgeLineX + remainingMs * speed;
  }

  /** Dessine les notes visibles à leur position courante. */
  renderNotes(notes: readonly Note[], songTimeMs: number): void {
    const visible = new Set(notes);

    for (const [note, graphic] of this.noteGraphics) {
      if (!visible.has(note)) {
        graphic.destroy();
        this.noteGraphics.delete(note);
      }
    }

    for (const note of notes) {
      let graphic = this.noteGraphics.get(note);
      if (!graphic) {
        graphic = this.createNoteGraphic(note.type);
        this.noteGraphics.set(note, graphic);
        this.noteLayer.addChild(graphic);
      }
      graphic.x = this.noteX(note, songTimeMs);
      graphic.y = this.laneY;
      graphic.visible =
        graphic.x > -HIGHWAY.CULL_MARGIN_PX &&
        graphic.x < this.width + HIGHWAY.CULL_MARGIN_PX;
    }
  }

  private createNoteGraphic(type: NoteType): Graphics {
    return new Graphics()
      .circle(0, 0, HIGHWAY.NOTE_RADIUS_PX)
      .fill({ color: NOTE_COLORS[type] })
      .stroke({ color: HIGHWAY_COLORS.JUDGE_CIRCLE, width: 2, alpha: 0.8 });
  }

  /**
   * Déclenche une pulsation lumineuse sur la ligne de jugement :
   * rouge en cas d'échec, vert en cas de réussite, arc-en-ciel pour un PERFECT.
   */
  spawnPulse(judgement: Judgement, songTimeMs: number): void {
    const graphic =
      judgement === 'PERFECT'
        ? this.createRainbowPulse()
        : new Graphics()
            .circle(0, 0, HIGHWAY.JUDGE_CIRCLE_RADIUS_PX)
            .fill({ color: FEEDBACK_COLORS[judgement] });

    graphic.x = this.judgeLineX;
    graphic.y = this.laneY;
    this.pulseLayer.addChild(graphic);
    this.pulses.push({ startedAtMs: songTimeMs, judgement, graphic });
  }

  /** Halo arc-en-ciel : un anneau par couleur de la palette disco. */
  private createRainbowPulse(): Graphics {
    const graphic = new Graphics();
    GRADIENTS.RAINBOW.forEach((color, index) => {
      const radius =
        HIGHWAY.JUDGE_CIRCLE_RADIUS_PX * (1 + index / GRADIENTS.RAINBOW.length);
      graphic.circle(0, 0, radius).stroke({ color, width: 3, alpha: 0.9 });
    });
    return graphic;
  }

  /**
   * Fait vivre les pulsations : elles grossissent et s'effacent, puis
   * disparaissent au bout de FEEDBACK.PULSE_DURATION_MS.
   */
  updatePulses(songTimeMs: number): void {
    // TODO(amiral): animer puis nettoyer les pulsations.
    //
    //   Pour chaque pulsation de this.pulses :
    //     1. progress = (songTimeMs - pulse.startedAtMs) / FEEDBACK.PULSE_DURATION_MS
    //        — une valeur qui va de 0 (naissance) à 1 (fin de vie).
    //     2. Si progress >= 1 : détruire pulse.graphic et retirer la pulsation
    //        de la liste.
    //     3. Sinon :
    //        - échelle : de 1 à FEEDBACK.PULSE_MAX_SCALE au fil du progress
    //          (pulse.graphic.scale.set(...))
    //        - opacité : de FEEDBACK.PULSE_START_ALPHA vers 0
    //          (pulse.graphic.alpha = ...)
    //
    //   Astuce : le plus simple est de reconstruire this.pulses avec un filter,
    //   en détruisant au passage les graphics des pulsations expirées.
    const remainingPulses = this.pulses.filter((pulse) => {
      const progress = (songTimeMs - pulse.startedAtMs) / FEEDBACK.PULSE_DURATION_MS;
      
      if (progress >= 1) {
        pulse.graphic.destroy();
        return false;
      }

      const scale = 1 + progress * (FEEDBACK.PULSE_MAX_SCALE - 1);
      pulse.graphic.scale.set(scale);
      pulse.graphic.alpha =FEEDBACK.PULSE_START_ALPHA * (1 - progress);
      
        return true;
    });
    
    this.pulses = remainingPulses;
  }

  /** Vide la scène entre deux parties. */
  clear(): void {
    for (const graphic of this.noteGraphics.values()) graphic.destroy();
    this.noteGraphics.clear();
    for (const pulse of this.pulses) pulse.graphic.destroy();
    this.pulses = [];
  }
}
