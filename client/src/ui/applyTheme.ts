/**
 * Injecte la palette de `config/theme.ts` dans le DOM sous forme de variables
 * CSS, pour que la feuille de style n'ait aucune couleur en dur : la config
 * reste la source unique de vérité.
 */

import { GRADIENTS, PALETTE, toCss, toCssGradient } from '../config/theme';
import { FEEDBACK_COLORS } from '../config/theme';

/** Angle des gradients décoratifs, en degrés. */
const GRADIENT_ANGLE_DEG = 135;

export function applyTheme(root: HTMLElement = document.documentElement): void {
  for (const [name, color] of Object.entries(PALETTE)) {
    root.style.setProperty(`--color-${name.toLowerCase()}`, toCss(color));
  }
  for (const [judgement, color] of Object.entries(FEEDBACK_COLORS)) {
    root.style.setProperty(`--judgement-${judgement.toLowerCase()}`, toCss(color));
  }
  for (const [name, colors] of Object.entries(GRADIENTS)) {
    root.style.setProperty(
      `--gradient-${name.toLowerCase()}`,
      toCssGradient(colors, GRADIENT_ANGLE_DEG),
    );
  }
}
