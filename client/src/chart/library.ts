/**
 * Bibliothèque de morceaux : la partition métronome codée en dur, plus les
 * partitions générées par le pipeline.
 *
 * On ne peut pas lister un dossier en HTTP, donc le pipeline maintient un
 * `index.json` que l'on lit ici.
 */

import { parseChart, type Chart } from './types';
import { TEST_CHART } from './testChart';

const CHARTS_DIR = '/charts';
const INDEX_URL = `${CHARTS_DIR}/index.json`;

interface IndexEntry {
  title: string;
  file: string;
}

/**
 * Charge les partitions générées. Un pipeline pas encore lancé — donc pas
 * d'index — n'est pas une erreur : on renvoie simplement une liste vide.
 */
async function loadGeneratedCharts(): Promise<Chart[]> {
  let entries: IndexEntry[];
  try {
    const response = await fetch(INDEX_URL);
    if (!response.ok) return [];
    entries = await response.json();
  } catch {
    return [];
  }

  const charts = await Promise.all(
    entries.map(async ({ file }) => {
      try {
        const response = await fetch(`${CHARTS_DIR}/${file}`);
        if (!response.ok) return null;
        return parseChart(await response.json());
      } catch {
        // Une partition illisible ne doit pas priver le joueur des autres.
        return null;
      }
    }),
  );

  return charts.filter((chart): chart is Chart => chart !== null);
}

/** Toutes les partitions jouables, la partition de test en tête. */
export async function loadLibrary(): Promise<Chart[]> {
  return [TEST_CHART, ...(await loadGeneratedCharts())];
}
