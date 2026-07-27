/**
 * Direction artistique : ambiance disco, gradients rose / orange / rouge /
 * violet / bleu.
 *
 * RÈGLE DU PROJET : aucune couleur en dur ailleurs dans le code.
 * Les couleurs sont écrites en hexadécimal numérique (0x…) pour être utilisables
 * directement par PixiJS ; `toCss()` les convertit pour le CSS et le DOM.
 */

import type { Judgement, NoteType } from './gameplay';

/** Palette disco de base. */
export const PALETTE = {
  PINK: 0xff2e88,
  ORANGE: 0xff8a3d,
  RED: 0xff3b3b,
  PURPLE: 0x9b30ff,
  BLUE: 0x2ec4ff,
  DEEP_SPACE: 0x140021,
  NIGHT: 0x0a0012,
  WHITE: 0xfff4fb,
} as const;

/** Gradients, du premier au dernier arrêt de couleur. */
export const GRADIENTS = {
  /** Fond général de l'application. */
  BACKDROP: [PALETTE.NIGHT, PALETTE.DEEP_SPACE, PALETTE.PURPLE],
  /** Accent principal (titres, boutons). */
  DISCO: [PALETTE.PINK, PALETTE.ORANGE, PALETTE.PURPLE],
  /** Pulsation « parfait » : arc-en-ciel. */
  RAINBOW: [
    PALETTE.RED,
    PALETTE.ORANGE,
    PALETTE.PINK,
    PALETTE.PURPLE,
    PALETTE.BLUE,
  ],
} as const;

/** Couleur de la pulsation lumineuse selon le jugement. */
export const FEEDBACK_COLORS: Record<Judgement, number> = {
  PERFECT: PALETTE.PINK, // accompagné du halo arc-en-ciel
  GOOD: 0x3ddc84, // vert réussite
  MISS: PALETTE.RED,
};

/** Couleur de chaque type de note. */
export const NOTE_COLORS: Record<NoteType, number> = {
  DON: PALETTE.RED,
  KA: PALETTE.BLUE,
};

/** Couleurs de la piste de jeu. */
export const HIGHWAY_COLORS = {
  LANE_BACKGROUND: 0x1b0430,
  LANE_BORDER: PALETTE.PURPLE,
  JUDGE_CIRCLE: PALETTE.WHITE,
  BACKGROUND: PALETTE.NIGHT,
} as const;

/** Convertit une couleur PixiJS (0xRRGGBB) en chaîne CSS `#rrggbb`. */
export function toCss(color: number): string {
  return `#${color.toString(16).padStart(6, '0')}`;
}

/** Construit un `linear-gradient` CSS à partir d'une liste de couleurs. */
export function toCssGradient(
  colors: readonly number[],
  angleDeg: number,
): string {
  const stops = colors.map(toCss).join(', ');
  return `linear-gradient(${angleDeg}deg, ${stops})`;
}
