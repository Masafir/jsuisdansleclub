import { describe, expect, it } from 'vitest';
import { HoldManager } from './holds';
import { HOLD } from '../config/gameplay';
import type { Note } from '../chart/types';

const holdNote: Note = { timeMs: 1000, type: 'KA', durationMs: 2000 };

function heldManager(): HoldManager {
  const manager = new HoldManager();
  manager.press('KA', 'd');
  manager.begin(holdNote);
  return manager;
}

describe('HoldManager — relâchement', () => {
  it('relâcher en cours de tenue crédite le prorata', () => {
    const release = heldManager().release('KA', 'd', 2000);
    expect(release?.heldMs).toBe(1000);
    expect(release?.completed).toBe(false);
  });

  it('relâcher à la fin exacte donne une tenue complète', () => {
    const release = heldManager().release('KA', 'd', 3000);
    expect(release?.heldMs).toBe(2000);
    expect(release?.completed).toBe(true);
  });

  it('relâcher dans la tolérance de fin compte comme complet', () => {
    const release = heldManager().release(
      'KA',
      'd',
      3000 - HOLD.END_TOLERANCE_MS,
    );
    expect(release?.completed).toBe(true);
  });

  it('le temps tenu est borné à la durée de la note', () => {
    const release = heldManager().release('KA', 'd', 9999);
    expect(release?.heldMs).toBe(2000);
  });

  it('relâcher sans hold actif ne produit rien', () => {
    const manager = new HoldManager();
    manager.press('KA', 'd');
    expect(manager.release('KA', 'd', 2000)).toBeNull();
  });
});

describe('HoldManager — deux touches par lane', () => {
  it('le hold survit tant qu’une touche de la lane reste enfoncée', () => {
    const manager = new HoldManager();
    manager.press('DON', 'f');
    manager.press('DON', 'j');
    manager.begin({ timeMs: 1000, type: 'DON', durationMs: 2000 });

    // F relâchée, mais J tient toujours : la tenue continue.
    expect(manager.release('DON', 'f', 1500)).toBeNull();
    expect(manager.activeHolds).toHaveLength(1);

    // J relâchée : fin de tenue.
    const release = manager.release('DON', 'j', 2000);
    expect(release?.heldMs).toBe(1000);
    expect(manager.activeHolds).toHaveLength(0);
  });

  it('les lanes sont indépendantes', () => {
    const manager = heldManager(); // hold KA en cours
    manager.press('DON', 'f');
    // Relâcher DON (sans hold) ne touche pas au hold KA.
    expect(manager.release('DON', 'f', 1500)).toBeNull();
    expect(manager.activeHolds).toHaveLength(1);
  });
});

describe('HoldManager — fin naturelle', () => {
  it('update libère un hold arrivé à son terme, complet', () => {
    const manager = heldManager();
    expect(manager.update(2999)).toEqual([]);

    const done = manager.update(3000);
    expect(done).toHaveLength(1);
    expect(done[0].heldMs).toBe(2000);
    expect(done[0].completed).toBe(true);
    expect(manager.activeHolds).toHaveLength(0);
  });

  it('un hold libéré par update ne l’est pas une seconde fois', () => {
    const manager = heldManager();
    manager.update(3000);
    expect(manager.update(3100)).toEqual([]);
    // Et le relâchement clavier qui suit ne re-crédite rien.
    expect(manager.release('KA', 'd', 3200)).toBeNull();
  });
});

describe('HoldManager — reset', () => {
  it('oublie sources et holds', () => {
    const manager = heldManager();
    manager.reset();
    expect(manager.activeHolds).toHaveLength(0);
    expect(manager.release('KA', 'd', 2000)).toBeNull();
  });
});
