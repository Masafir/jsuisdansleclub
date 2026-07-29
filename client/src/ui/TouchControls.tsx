import type { PointerEvent } from 'react';
import { NOTE_TYPES, type NoteType } from '../config/gameplay';
import { NOTE_COLORS, toCss } from '../config/theme';

interface TouchControlsProps {
  onDown: (type: NoteType, pointerId: number) => void;
  onUp: (type: NoteType, pointerId: number) => void;
}

/**
 * Commandes tactiles : deux boutons, un par type de note, aux couleurs exactes
 * des notes qui défilent.
 *
 * Deux et non quatre : au clavier, les deux touches par type servent à alterner
 * les mains sur une suite rapide. Avec deux pouces, cette alternance n'existe
 * pas — quatre boutons ne feraient que réduire les cibles et multiplier les
 * erreurs.
 *
 * L'appui ET le relâchement sont transmis : les notes tenues (« holds »)
 * durent tant que le doigt reste posé. La capture de pointeur garantit que le
 * relâchement arrive même si le doigt a glissé hors du bouton.
 */
export function TouchControls({ onDown, onUp }: TouchControlsProps) {
  // `pointerdown` plutôt que `click` : un clic n'est émis qu'au relâchement,
  // ce qui ajouterait toute la durée de l'appui à la latence de jugement.
  const press = (type: NoteType) => (event: PointerEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    onDown(type, event.pointerId);
  };

  const release = (type: NoteType) => (event: PointerEvent<HTMLButtonElement>) => {
    onUp(type, event.pointerId);
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
          onPointerUp={release(type)}
          onPointerCancel={release(type)}
          aria-label={`Frapper ${type}`}
        >
          {type}
        </button>
      ))}
    </div>
  );
}
