/**
 * Moteur de jugement : décide si un appui du joueur est PERFECT, GOOD ou MISS.
 *
 * C'est le cœur du ressenti du jeu. Deux responsabilités :
 *   - `hit()`   : le joueur appuie, on cherche la note visée et on la juge ;
 *   - `update()`: le temps passe, les notes non frappées deviennent des MISS.
 *
 * Optimisation à connaître : les notes d'une partition sont **triées par
 * timeMs** (invariant garanti par `parseChart`). On garde donc un curseur
 * `cursor` sur la première note non encore jugée, au lieu de re-parcourir tout
 * le tableau à chaque appui. Une partition de 5 minutes contient facilement
 * un millier de notes, et cette boucle tourne à 60 images par seconde.
 */

import { TIMING, type Judgement, type NoteType } from '../config/gameplay';
import type { Note } from '../chart/types';

export interface JudgeResult {
  note: Note;
  judgement: Judgement;
  /** Écart signé en ms : négatif = en avance, positif = en retard. */
  deltaMs: number;
}

export class Judge {
  private readonly notes: readonly Note[];
  /** Index de la première note pas encore jugée. */
  private cursor = 0;

  constructor(notes: readonly Note[]) {
    this.notes = notes;
  }

  /** Toutes les notes ont-elles été jugées ? */
  get isFinished(): boolean {
    return this.cursor >= this.notes.length;
  }

  /** Nombre total de notes de la partition. */
  get totalNotes(): number {
    return this.notes.length;
  }

  /**
   * Le joueur vient d'appuyer sur une touche.
   *
   * @param inputTimeMs Instant de l'appui — utiliser `SongClock.getInputTimeMs()`,
   *   qui est corrigé de la latence du casque.
   * @param type Type de note correspondant à la touche pressée (DON ou KA).
   * @returns Le jugement, ou `null` si aucune note n'était visée : appuyer dans
   *   le silence ne doit rien coûter au joueur, c'est la convention du genre.
   */
  hit(inputTimeMs: number, type: NoteType): JudgeResult | null {
    // TODO(amiral): implémenter le jugement d'un appui.
    //
    //   1. Prendre la note candidate : `this.notes[this.cursor]`.
    //      S'il n'y en a plus (isFinished), renvoyer null.
    //
    //   2. Calculer l'écart signé : deltaMs = inputTimeMs - note.timeMs
    //      (négatif = le joueur est en avance).
    //
    //   3. Si Math.abs(deltaMs) > TIMING.CANDIDATE_WINDOW_MS, le joueur ne
    //      visait pas cette note : renvoyer null SANS avancer le curseur
    //      (la note reste jouable).
    //
    //   4. Sinon la note est consommée : avancer this.cursor d'un cran, puis
    //      déterminer le jugement :
    //        - mauvais type de touche (type !== note.type)      -> 'MISS'
    //        - |deltaMs| <= TIMING.PERFECT_WINDOW_MS            -> 'PERFECT'
    //        - |deltaMs| <= TIMING.GOOD_WINDOW_MS               -> 'GOOD'
    //        - sinon (dans la fenêtre candidate mais trop loin) -> 'MISS'
    //
    //   5. Renvoyer { note, judgement, deltaMs }.
    const candidateNote = this.notes[this.cursor];
    
    if(this.isFinished) {
      return null;
    }

    const deltaMs = inputTimeMs - candidateNote.timeMs;
    
    if(Math.abs(deltaMs) > TIMING.CANDIDATE_WINDOW_MS) {
      return null;
    }
    else {
      this.cursor++;
      let judgement: Judgement;

      if(type !== candidateNote.type) {
        judgement = 'MISS';
      }
      else if(Math.abs(deltaMs) <= TIMING.PERFECT_WINDOW_MS) {
        judgement = 'PERFECT';
      }
      else if(Math.abs(deltaMs) <= TIMING.GOOD_WINDOW_MS) {
        judgement = 'GOOD';
      }
      else {
        judgement = 'MISS';
      }

      return { note: candidateNote, judgement, deltaMs };
    }
  }

  /**
   * Appelée à chaque image : transforme en MISS les notes que le joueur a
   * laissé passer sans les frapper.
   *
   * @param songTimeMs Position courante — utiliser `SongClock.getSongTimeMs()`.
   * @returns Les notes ratées depuis le dernier appel (souvent vide).
   */
  update(songTimeMs: number): Note[] {
    // TODO(amiral): implémenter la détection des notes ratées.
    //
    //   Tant qu'il reste une note au curseur ET qu'elle est définitivement
    //   hors d'atteinte, la compter comme ratée et avancer le curseur.
    //
    //   « Hors d'atteinte » = songTimeMs - note.timeMs > TIMING.GOOD_WINDOW_MS
    //   (on a dépassé la note de plus que la fenêtre GOOD : plus aucun appui
    //   ne pourra lui valoir de points).
    //
    //   Attention : une boucle `while`, pas un `if` — plusieurs notes peuvent
    //   expirer dans la même image si le joueur lâche son clavier.
    //
    //   Renvoyer le tableau des notes ratées.
    const missedNotes: Note[] = [];
    
    while(!this.isFinished && (songTimeMs - this.notes[this.cursor].timeMs > TIMING.GOOD_WINDOW_MS)) {
      missedNotes.push(this.notes[this.cursor]);
      this.cursor++;
    }
    return missedNotes;
  }

  /**
   * Notes à afficher à l'écran : celles encore à venir, dans une fenêtre de
   * temps donnée. Utilisé par le rendu pour ne dessiner que le visible.
   */
  visibleNotes(songTimeMs: number, lookAheadMs: number): Note[] {
    const result: Note[] = [];
    for (let i = this.cursor; i < this.notes.length; i++) {
      const note = this.notes[i];
      if (note.timeMs > songTimeMs + lookAheadMs) break;
      result.push(note);
    }
    return result;
  }

  reset(): void {
    this.cursor = 0;
  }
}
