/**
 * Rendu de la piste, format hybride Guitar Hero / taiko : une lane par couleur
 * (KA en haut, DON en bas), les notes défilent de droite à gauche vers le
 * cercle de jugement de leur lane. Les notes tenues traînent une queue qui se
 * consomme pendant la tenue.
 */

import { Application, Container, Graphics } from 'pixi.js';
import {
  FEEDBACK,
  HIGHWAY,
  JUDGE_CIRCLE,
  NOTE_TYPES,
  type Judgement,
  type NoteType,
} from '../config/gameplay';
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
  private readonly judgeCircles: Record<NoteType, Container> = {
    DON: new Container(),
    KA: new Container(),
  };
  private readonly noteLayer = new Container();
  private readonly pulseLayer = new Container();
  /** Traînes des holds en cours, redessinées chaque image. */
  private readonly activeHoldLayer = new Graphics();
  private readonly noteGraphics = new Map<Note, Graphics>();
  private pulses: Pulse[] = [];
  /** Instant du dernier appui réussi par lane, pilote la dilatation du cercle. */
  private lastHitAtMs: Record<NoteType, number> = {
    DON: Number.NEGATIVE_INFINITY,
    KA: Number.NEGATIVE_INFINITY,
  };

  /**
   * Hauteur de chaque lane, en fraction de l'écran. Surchargeable : sur
   * mobile, les pistes remontent pour laisser le bas aux boutons.
   */
  private laneYRatios: Record<NoteType, number> = HIGHWAY.LANE_Y_RATIOS;

  /** Prépare le canvas et l'attache au DOM. */
  async init(
    container: HTMLElement,
    laneYRatios?: Record<NoteType, number>,
  ): Promise<void> {
    if (laneYRatios !== undefined) this.laneYRatios = laneYRatios;
    await this.app.init({
      background: HIGHWAY_COLORS.BACKGROUND,
      resizeTo: container,
      antialias: true,
    });
    container.appendChild(this.app.canvas);

    this.app.stage.addChild(
      this.decor,
      this.judgeCircles.KA,
      this.judgeCircles.DON,
      this.activeHoldLayer,
      this.noteLayer,
      this.pulseLayer,
    );
    this.drawDecor();
    this.app.renderer.on('resize', () => {
      this.drawDecor();
      // Les traînes des holds sont dessinées à une vitesse en px/ms qui dépend
      // de la largeur : on jette les graphiques, ils renaîtront à la bonne
      // taille à l'image suivante.
      for (const graphic of this.noteGraphics.values()) graphic.destroy();
      this.noteGraphics.clear();
    });
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

  /** Ordonnée du centre d'une lane, en pixels. */
  laneY(type: NoteType): number {
    return this.height * this.laneYRatios[type];
  }

  /** Vitesse de défilement, en pixels par milliseconde. */
  private get pxPerMs(): number {
    return (this.width - this.judgeLineX) / HIGHWAY.APPROACH_TIME_MS;
  }

  /** Décor statique : les deux bandes de jeu et leurs cercles de jugement. */
  private drawDecor(): void {
    this.decor.removeChildren();

    const laneHeight = this.height * HIGHWAY.LANE_HEIGHT_RATIO;
    for (const type of NOTE_TYPES) {
      const lane = new Graphics()
        .rect(0, this.laneY(type) - laneHeight / 2, this.width, laneHeight)
        .fill({ color: HIGHWAY_COLORS.LANE_BACKGROUND })
        // Chaque bande est soulignée de la couleur de ses notes : on sait où
        // regarder avant même que la première note arrive.
        .stroke({ color: NOTE_COLORS[type], width: 2, alpha: 0.45 });
      this.decor.addChild(lane);
      this.drawJudgeCircle(type);
    }
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
        graphic = this.createNoteGraphic(note);
        this.noteGraphics.set(note, graphic);
        this.noteLayer.addChild(graphic);
      }
      graphic.x = this.noteX(note, songTimeMs);
      graphic.y = this.laneY(note.type);
      // La marge de droite tient compte de la traîne d'un hold, qui s'étend
      // au-delà de la tête.
      const tailPx = (note.durationMs ?? 0) * this.pxPerMs;
      graphic.visible =
        graphic.x > -HIGHWAY.CULL_MARGIN_PX - tailPx &&
        graphic.x < this.width + HIGHWAY.CULL_MARGIN_PX;
    }
  }

  /**
   * Traînes des holds en cours de tenue : ancrées au cercle de jugement, elles
   * rétrécissent à mesure que la fin approche — la tenue se « consomme ».
   */
  renderActiveHolds(holds: readonly Note[], songTimeMs: number): void {
    this.activeHoldLayer.clear();

    for (const note of holds) {
      const endMs = note.timeMs + (note.durationMs ?? 0);
      const endX = this.judgeLineX + Math.max(0, endMs - songTimeMs) * this.pxPerMs;
      const y = this.laneY(note.type);
      const color = NOTE_COLORS[note.type];
      const radius = HIGHWAY.NOTE_RADIUS_PX;

      this.activeHoldLayer
        .roundRect(
          this.judgeLineX,
          y - radius * 0.55,
          Math.max(radius, endX - this.judgeLineX),
          radius * 1.1,
          radius * 0.55,
        )
        .fill({ color, alpha: 0.45 })
        .stroke({ color, width: 2, alpha: 0.8 });

      // La tête reste vissée sur le cercle de jugement, bien pleine : le
      // joueur voit que sa tenue est « accrochée ».
      this.activeHoldLayer
        .circle(this.judgeLineX, y, radius)
        .fill({ color })
        .stroke({ color: HIGHWAY_COLORS.JUDGE_CIRCLE, width: 3, alpha: 0.9 });
    }
  }

  /**
   * Cercle de jugement en néon : un trait net, entouré de halos de plus en plus
   * larges et transparents. Empiler des traits coûte bien moins cher qu'un
   * filtre de flou, et donne le même effet de lueur.
   *
   * Il est dessiné centré sur (0, 0) puis positionné : c'est ce qui permet de
   * l'agrandir depuis son centre plutôt que depuis le coin de l'écran.
   */
  private drawJudgeCircle(type: NoteType): void {
    const container = this.judgeCircles[type];
    container.removeChildren();
    const graphic = new Graphics();

    for (let layer = JUDGE_CIRCLE.GLOW_LAYERS; layer > 0; layer--) {
      graphic.circle(0, 0, HIGHWAY.JUDGE_CIRCLE_RADIUS_PX).stroke({
        color: HIGHWAY_COLORS.JUDGE_CIRCLE,
        width: JUDGE_CIRCLE.STROKE_WIDTH_PX + layer * JUDGE_CIRCLE.GLOW_STEP_PX,
        alpha: JUDGE_CIRCLE.GLOW_ALPHA / layer,
      });
    }
    graphic.circle(0, 0, HIGHWAY.JUDGE_CIRCLE_RADIUS_PX).stroke({
      color: HIGHWAY_COLORS.JUDGE_CIRCLE,
      width: JUDGE_CIRCLE.STROKE_WIDTH_PX,
    });

    container.addChild(graphic);
    container.x = this.judgeLineX;
    container.y = this.laneY(type);
  }

  /**
   * Anime les cercles de jugement : une respiration lente au repos, et une
   * dilatation brève sur la lane touchée.
   *
   * La respiration donne de la vie à l'écran pendant les silences ; la
   * dilatation confirme l'appui même quand le joueur regarde les notes arriver
   * plutôt que le cercle lui-même.
   */
  updateJudgeCircle(songTimeMs: number): void {
    const breath =
      1 +
      JUDGE_CIRCLE.IDLE_SCALE_AMPLITUDE *
        Math.sin((songTimeMs / JUDGE_CIRCLE.IDLE_PERIOD_MS) * Math.PI * 2);

    for (const type of NOTE_TYPES) {
      const sinceHit = songTimeMs - this.lastHitAtMs[type];
      const recovering = sinceHit >= 0 && sinceHit < JUDGE_CIRCLE.HIT_RECOVERY_MS;
      const impact = recovering
        ? (JUDGE_CIRCLE.HIT_SCALE - 1) * (1 - sinceHit / JUDGE_CIRCLE.HIT_RECOVERY_MS)
        : 0;

      this.judgeCircles[type].scale.set(breath + impact);
    }
  }

  private createNoteGraphic(note: Note): Graphics {
    const graphic = new Graphics();
    const color = NOTE_COLORS[note.type];

    // Les notes des moments forts portent un halo de leur propre couleur : la
    // relance se voit venir de loin, au lieu de surprendre à l'arrivée.
    if (note.accent) {
      for (let layer = HIGHWAY.ACCENT_HALO_LAYERS; layer > 0; layer--) {
        graphic
          .circle(0, 0, HIGHWAY.NOTE_RADIUS_PX + layer * HIGHWAY.ACCENT_HALO_STEP_PX)
          .stroke({
            color,
            width: HIGHWAY.ACCENT_HALO_STEP_PX,
            alpha: HIGHWAY.ACCENT_HALO_ALPHA / layer,
          });
      }
    }

    // La traîne d'un hold : une capsule qui part de la tête et couvre toute la
    // durée de tenue. Dessinée AVANT la tête pour passer dessous.
    const durationMs = note.durationMs ?? 0;
    if (durationMs > 0) {
      const length = durationMs * this.pxPerMs;
      const radius = HIGHWAY.NOTE_RADIUS_PX;
      graphic
        .roundRect(0, -radius * 0.55, length, radius * 1.1, radius * 0.55)
        .fill({ color, alpha: 0.3 })
        .stroke({ color, width: 2, alpha: 0.6 });
    }

    return graphic
      .circle(0, 0, HIGHWAY.NOTE_RADIUS_PX)
      .fill({ color })
      .stroke({ color: HIGHWAY_COLORS.JUDGE_CIRCLE, width: 2, alpha: 0.8 });
  }

  /**
   * Déclenche une pulsation lumineuse sur la ligne de jugement :
   * rouge en cas d'échec, vert en cas de réussite, arc-en-ciel pour un PERFECT.
   */
  spawnPulse(judgement: Judgement, songTimeMs: number, type: NoteType): void {
    const graphic =
      judgement === 'PERFECT'
        ? this.createRainbowPulse()
        : this.createRingPulse(FEEDBACK_COLORS[judgement]);

    graphic.x = this.judgeLineX;
    graphic.y = this.laneY(type);
    this.pulseLayer.addChild(graphic);
    this.pulses.push({ startedAtMs: songTimeMs, judgement, graphic });

    // Le cercle de la lane encaisse le coup : il enfle puis se rétracte.
    if (judgement !== 'MISS') this.lastHitAtMs[type] = songTimeMs;
  }

  /**
   * Onde concentrique évidée, pour les GOOD et les MISS.
   *
   * Un disque plein recouvrait la ligne de jugement et la note suivante au
   * moment précis où le joueur en a besoin. Des anneaux laissent voir au
   * travers tout en marquant l'impact.
   */
  private createRingPulse(color: number): Graphics {
    const graphic = new Graphics();
    for (let ring = 0; ring < FEEDBACK.PULSE_RINGS; ring++) {
      const radius =
        HIGHWAY.JUDGE_CIRCLE_RADIUS_PX *
        (1 + ring * FEEDBACK.PULSE_RING_SPACING_RATIO);
      graphic.circle(0, 0, radius).stroke({
        color,
        width: FEEDBACK.PULSE_RING_WIDTH_PX,
        // Les anneaux extérieurs s'estompent : l'onde paraît se dissiper.
        alpha: 1 - ring / FEEDBACK.PULSE_RINGS,
      });
    }
    return graphic;
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
    this.activeHoldLayer.clear();
  }
}
