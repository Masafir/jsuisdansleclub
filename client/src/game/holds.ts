/**
 * Suivi des notes tenues (« holds »).
 *
 * Sépare deux notions que le reste du code ne doit pas confondre :
 *   - les **sources** enfoncées : quelles touches physiques (ou quels doigts)
 *     maintiennent chaque lane. DON a deux touches (F et J) : le hold tient
 *     tant qu'au moins une source de la lane reste enfoncée ;
 *   - le **hold actif** : la note en cours de tenue sur une lane, au plus une
 *     par lane (le générateur garantit qu'ils ne se chevauchent pas).
 *
 * Classe pure : le temps est injecté, aucune dépendance audio ou DOM — donc
 * testable exactement.
 */

import { HOLD, type NoteType } from '../config/gameplay';
import type { Note } from '../chart/types';

export interface HoldRelease {
  note: Note;
  /** Temps effectivement tenu, borné à la durée de la note. */
  heldMs: number;
  /** Tenue complète (à la tolérance de fin près) ? */
  completed: boolean;
}

export class HoldManager {
  private readonly sources = new Map<NoteType, Set<string>>();
  private readonly active = new Map<NoteType, Note>();

  /** Une source (touche, doigt) vient d'appuyer sur cette lane. */
  press(type: NoteType, source: string): void {
    let set = this.sources.get(type);
    if (!set) {
      set = new Set();
      this.sources.set(type, set);
    }
    set.add(source);
  }

  /** Un hit réussi sur une note à durée : la tenue commence. */
  begin(note: Note): void {
    this.active.set(note.type, note);
  }

  /**
   * Une source relâche la lane. Si c'était la dernière et qu'un hold est en
   * cours, la tenue s'arrête là.
   */
  release(type: NoteType, source: string, songTimeMs: number): HoldRelease | null {
    const set = this.sources.get(type);
    set?.delete(source);
    if (set !== undefined && set.size > 0) {
      return null; // l'autre touche de la lane maintient toujours
    }
    return this.finish(type, songTimeMs);
  }

  /** Tenues arrivées naturellement à leur terme. À appeler chaque image. */
  update(songTimeMs: number): HoldRelease[] {
    const done: HoldRelease[] = [];
    for (const [type, note] of this.active) {
      if (songTimeMs >= note.timeMs + (note.durationMs ?? 0)) {
        const release = this.finish(type, songTimeMs);
        if (release) done.push(release);
      }
    }
    return done;
  }

  private finish(type: NoteType, songTimeMs: number): HoldRelease | null {
    const note = this.active.get(type);
    if (!note) return null;
    this.active.delete(type);

    const durationMs = note.durationMs ?? 0;
    const heldMs = Math.max(0, Math.min(songTimeMs - note.timeMs, durationMs));
    return {
      note,
      heldMs,
      completed: heldMs >= durationMs - HOLD.END_TOLERANCE_MS,
    };
  }

  /** Holds en cours, pour le rendu (traîne qui se consomme). */
  get activeHolds(): Note[] {
    return [...this.active.values()];
  }

  reset(): void {
    this.sources.clear();
    this.active.clear();
  }
}
