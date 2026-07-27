import { KEY_LAYOUT, NOTE_TYPES, noteTypeForKey } from '../config/gameplay';
import { NOTE_COLORS, toCss } from '../config/theme';

interface KeyLegendProps {
  /**
   * `inline` pour l'intégrer dans le flux d'une page, `floating` pour l'épingler
   * dans un coin de l'écran de jeu — plus compact, sans les libellés.
   */
  variant?: 'inline' | 'floating';
}

/**
 * Rappel des touches, disposé comme le vrai clavier : D F puis J K, chaque
 * touche remplie de la couleur exacte des notes qu'elle frappe. Les touches
 * intérieures sont donc rouges (DON) et les extérieures bleues (KA), ce qui se
 * lit d'un coup d'œil — au contraire d'un regroupement par type de note, qui
 * obligeait à reconstruire mentalement la position des doigts.
 */
export function KeyLegend({ variant = 'inline' }: KeyLegendProps) {
  return (
    <div className={`key-legend key-legend--${variant}`}>
      <div className="key-legend__hands">
        {KEY_LAYOUT.map(({ hand, keys }) => (
          <div className="key-legend__hand" key={hand}>
            <div className="key-legend__keys">
              {keys.map((key) => {
                const type = noteTypeForKey(key);
                return (
                  <div
                    className="key-legend__disc"
                    key={key}
                    style={
                      type ? { backgroundColor: toCss(NOTE_COLORS[type]) } : undefined
                    }
                  >
                    {key.toUpperCase()}
                  </div>
                );
              })}
            </div>
            <span className="key-legend__hand-name">{hand}</span>
          </div>
        ))}
      </div>

      <div className="key-legend__types">
        {NOTE_TYPES.map((type) => (
          <span className="key-legend__type" key={type}>
            <span
              className="key-legend__dot"
              style={{ backgroundColor: toCss(NOTE_COLORS[type]) }}
            />
            {type}
          </span>
        ))}
      </div>
    </div>
  );
}
