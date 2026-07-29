import type { PointerEvent } from 'react';
import { NOTE_TYPES, type NoteType } from '../config/gameplay';
import { NOTE_COLORS, toCss } from '../config/theme';

interface TouchControlsProps {
  onHit: (type: NoteType) => void;
}

/**
 * Commandes tactiles : deux boutons, un par type de note, aux couleurs exactes
 * des notes qui défilent.
 *
 * Deux et non quatre : au clavier, les deux touches par type servent à alterner
 * les mains sur une suite rapide. Avec deux pouces, cette alternance n'existe
 * pas — quatre boutons ne feraient que réduire les cibles et multiplier les
 * erreurs.
 */
export function TouchControls({ onHit }: TouchControlsProps) {
  // `pointerdown` plutôt que `click` : un clic n'est émis qu'au relâchement,
  // ce qui ajouterait toute la durée de l'appui à la latence de jugement.
  const press = (type: NoteType) => (event: PointerEvent<HTMLButtonElement>) => {
    event.preventDefault();
    onHit(type);
  };

  return (
    <div className="touch-controls">
      {NOTE_TYPES.map((type) => (
        <button
          key={type}
          type="button"
          className="touch-controls__button"
          style={{ backgroundColor: toCss(NOTE_COLORS[type]) }}
          onPointerDown={press(type)}
          aria-label={`Frapper ${type}`}
        >
          {type}
        </button>
      ))}
    </div>
  );
}
