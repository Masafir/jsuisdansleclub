import { useEffect, useState } from 'react';

/**
 * Le joueur dispose-t-il d'un pointeur grossier (doigt) plutôt que d'une souris ?
 *
 * On interroge `pointer: coarse` et non la largeur de l'écran : un téléphone en
 * paysage est large, et une petite fenêtre sur un ordinateur portable est
 * étroite. Ce qui décide de l'interface, c'est de quoi le joueur dispose pour
 * jouer, pas la place dont il dispose.
 */
export function useTouchDevice(): boolean {
  const [isTouch, setIsTouch] = useState(
    () => window.matchMedia('(pointer: coarse)').matches,
  );

  useEffect(() => {
    const query = window.matchMedia('(pointer: coarse)');
    const update = () => setIsTouch(query.matches);
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);

  return isTouch;
}
