"""Des instants d'attaque aux notes jouables.

Cette etape ne fait plus de traitement du signal : elle prend des nombres et
rend des nombres. C'est du game design pur, et c'est ce qui separe une
partition « correcte » d'une partition amusante.

Toutes les fonctions ici sont **pures** : meme entree, meme sortie, aucun
fichier, aucun etat. Leurs tests sont donc exacts et instantanes.
"""

from __future__ import annotations

from typing import Literal

from . import config

#: Les deux types de notes, alignes sur NOTE_TYPES cote client.
NoteType = Literal["DON", "KA"]


def enforce_min_gap(times: list[float], min_gap_s: float) -> list[float]:
    """Ecarte les instants trop rapproches.

    A IMPLEMENTER (amiral).

    Sert deux fois : dans `detect_onset_times` pour eviter qu'une frappe etalee
    sur plusieurs trames donne une rafale, puis sur la partition finale pour
    garantir qu'elle reste jouable a deux mains.

    Regle : on parcourt les instants dans l'ordre et on garde le premier ; on
    ne garde ensuite un instant que s'il est distant d'au moins `min_gap_s` du
    **dernier instant conserve** — surtout pas du precedent instant de la liste,
    sinon une longue rafale passerait entierement de proche en proche.

    Exemple avec min_gap_s = 0.1 :
        [0.00, 0.05, 0.09, 0.30]  ->  [0.00, 0.30]
        (0.05 et 0.09 sont tous deux a moins de 0.1 s du 0.00 conserve)

    Cas limites a respecter :
        - liste vide -> liste vide ;
        - un ecart exactement egal a min_gap_s est accepte ;
        - la liste d'entree n'est pas modifiee (on en construit une nouvelle).

    Tests : `test_notes.py::TestEnforceMinGap`
    """
    # Sortie immediate sur liste vide : le deballage ci-dessous echouerait
    # avant meme qu'un garde place apres lui puisse s'appliquer.
    if not times:
        return []

    first, *rest = times
    result = [first]
    for t in rest:
        if t - result[-1] >= min_gap_s:
            result.append(t)
    return result


def classify_note_type(
    low_energy: float,
    high_energy: float,
    ka_ratio: float = config.KA_ENERGY_RATIO,
) -> NoteType:
    """Decide si une attaque est un DON (grave) ou un KA (aigu).

    A IMPLEMENTER (amiral).

    On reprend la logique du vrai taiko : frapper le centre de la peau donne un
    son grave (DON), frapper le bord un son claquant (KA). Une attaque dominee
    par les graves — kick, basse — devient donc un DON, une attaque dominee par
    les aigus — caisse claire, charleston — devient un KA.

    Regle : c'est un KA si `high_energy` depasse `low_energy` d'un facteur
    `ka_ratio`, autrement dit si

        high_energy > low_energy * ka_ratio

    Sinon c'est un DON. Le facteur est superieur a 1, donc le DON gagne en cas
    d'egalite : les KA restent des accents et la partition reste lisible.

    Piege : `low_energy` peut valoir 0 sur un passage sans grave. Il ne faut
    donc pas ecrire la regle sous forme de division `high / low`, qui leverait
    une ZeroDivisionError — la forme multipliee ci-dessus n'a pas ce probleme.

    Tests : `test_notes.py::TestClassifyNoteType`
    """
    if high_energy > low_energy * ka_ratio:
        return "KA"
    else:
        return "DON"


def times_to_notes(
    times: list[float],
    types: list[NoteType],
    offset_ms: int = 0,
) -> list[dict]:
    """Assemble instants et types en notes du format de partition.

    A IMPLEMENTER (amiral).

    Chaque note est un dictionnaire de la forme :

        {"timeMs": <entier>, "type": "DON" | "KA"}

    Les cles sont en camelCase parce qu'elles voyagent en JSON vers le client
    TypeScript (voir `Note` dans client/src/chart/types.ts).

    Marche a suivre :
        1. Verifier que `times` et `types` ont la meme longueur ; sinon lever
           une ValueError avec un message clair — c'est une erreur de
           programmation, pas une entree utilisateur.
        2. Pour chaque paire, convertir les secondes en millisecondes entieres
           (`round(t * 1000)`) puis ajouter `offset_ms`.
        3. Renvoyer la liste, triee par timeMs croissant : c'est un invariant
           du format, le moteur de jugement du client en depend.

    Astuce : `zip(times, types)` parcourt les deux listes en parallele.

    Tests : `test_notes.py::TestTimesToNotes`
    """
    if len(times) != len(types):
        raise ValueError(f"Aie coup dur times et types ne sont pas de la même longueur: {len(times)} != {len(types)}")
    notes = []
    for t, note_type in zip(times, types):
        times_ms = round(t * 1000) + offset_ms
        notes.append({"timeMs": times_ms, "type": note_type})
    return sorted(notes, key=lambda note: note["timeMs"])  
