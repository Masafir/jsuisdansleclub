/**
 * Format de partition. C'est le contrat entre le pipeline Python (qui les
 * génère depuis un MP3) et le client (qui les joue).
 *
 * Le champ `version` permet de faire évoluer le format sans casser les
 * partitions déjà générées et stockées.
 */

import type { NoteType } from '../config/gameplay';

export const CHART_FORMAT_VERSION = 1;

export interface Note {
  /** Instant du hit, en millisecondes depuis le début du morceau. */
  timeMs: number;
  type: NoteType;
  /**
   * Note appartenant à un moment fort du morceau — roulement, relance. Le rendu
   * les auréole pour que le joueur voie la montée arriver.
   *
   * Optionnel : les partitions générées avant cette notion n'en ont pas, et
   * l'absence vaut `false`.
   */
  accent?: boolean;
}

export interface Chart {
  version: number;
  /** Titre affiché. */
  title: string;
  /** URL de l'audio décodable par le navigateur (mp3, ogg…). */
  audioUrl: string;
  /** Durée totale du morceau, en millisecondes. */
  durationMs: number;
  /** Tempo estimé, informatif (affichage, futurs effets visuels). */
  bpm: number;
  /**
   * Décalage entre le début du fichier audio et le premier temps de la mesure,
   * en millisecondes. Produit par le pipeline, appliqué aux `timeMs`.
   */
  offsetMs: number;
  /** Notes triées par `timeMs` croissant. C'est un invariant du format. */
  notes: Note[];
}

/** Erreur de validation d'une partition. */
export class InvalidChartError extends Error {}

/**
 * Valide une partition venant de l'extérieur (pipeline, fichier importé) et
 * garantit les invariants dont le reste du code dépend — en particulier que
 * les notes sont triées, ce que le moteur de jugement suppose.
 */
export function parseChart(raw: unknown): Chart {
  if (typeof raw !== 'object' || raw === null) {
    throw new InvalidChartError('La partition doit être un objet.');
  }
  const chart = raw as Chart;

  if (chart.version !== CHART_FORMAT_VERSION) {
    throw new InvalidChartError(
      `Version de partition non supportée : ${chart.version} (attendu ${CHART_FORMAT_VERSION}).`,
    );
  }
  if (!Array.isArray(chart.notes)) {
    throw new InvalidChartError('La partition doit contenir un tableau `notes`.');
  }

  const sorted = [...chart.notes].sort((a, b) => a.timeMs - b.timeMs);
  return { ...chart, notes: sorted };
}
