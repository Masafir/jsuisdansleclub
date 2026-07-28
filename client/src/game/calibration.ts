/**
 * Offset de calibration du joueur : de combien son matériel retarde le son.
 *
 * Il est mesuré pendant une vraie partie plutôt que par un test au métronome :
 * l'écart moyen entre ses appuis et les notes est directement la quantité à
 * corriger, et elle intègre tout — latence du casque, du navigateur, et même le
 * léger retard des notes générées par détection d'onsets.
 */

import { CALIBRATION } from '../config/gameplay';

export function readCalibrationOffsetMs(): number {
  const stored = localStorage.getItem(CALIBRATION.STORAGE_KEY);
  const parsed = stored === null ? Number.NaN : Number(stored);
  return Number.isFinite(parsed) ? parsed : CALIBRATION.DEFAULT_OFFSET_MS;
}

/** Enregistre un offset, borné aux valeurs plausibles. */
export function writeCalibrationOffsetMs(offsetMs: number): number {
  const clamped = Math.round(
    Math.min(CALIBRATION.MAX_OFFSET_MS, Math.max(CALIBRATION.MIN_OFFSET_MS, offsetMs)),
  );
  localStorage.setItem(CALIBRATION.STORAGE_KEY, String(clamped));
  return clamped;
}
