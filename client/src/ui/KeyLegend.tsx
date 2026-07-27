import { KEY_BINDINGS, NOTE_TYPES } from '../config/gameplay';
import { NOTE_COLORS, toCss } from '../config/theme';

interface KeyLegendProps {
  /**
   * `inline` pour l'intégrer dans le flux d'une page, `floating` pour l'épingler
   * dans un coin de l'écran de jeu.
   */
  variant?: 'inline' | 'floating';
}

/**
 * Rappel des touches : un disque par type de note, rempli de la couleur exacte
 * des notes qui défilent, avec les touches correspondantes écrites dedans.
 */
export function KeyLegend({ variant = 'inline' }: KeyLegendProps) {
  return (
    <div className={`key-legend key-legend--${variant}`}>
      {NOTE_TYPES.map((type) => (
        <div className="key-legend__item" key={type}>
          <div
            className="key-legend__disc"
            style={{ backgroundColor: toCss(NOTE_COLORS[type]) }}
          >
            {KEY_BINDINGS[type].join(' / ').toUpperCase()}
          </div>
          <span className="key-legend__name">{type}</span>
        </div>
      ))}
    </div>
  );
}
