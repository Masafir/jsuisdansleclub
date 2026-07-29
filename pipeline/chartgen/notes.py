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


def select_strongest(
    times: list[float], strengths: list[float], min_gap_s: float
) -> list[float]:
    """Ne garde qu'une attaque par groupe : la plus forte.

    A IMPLEMENTER (amiral). Fonction pure.

    Remplace `enforce_min_gap` pour la selection finale. La difference est
    importante : `enforce_min_gap` garde la plus *precoce* d'un groupe, ce qui
    laisse une pre-echo ou une queue de reverberation evincer la vraie frappe.
    Ici on garde la plus *forte*, donc l'attaque reelle.

    Marche a suivre — c'est un algorithme glouton classique :

    1. Verifier que `times` et `strengths` ont la meme longueur, sinon lever une
       ValueError.

    2. Parcourir les instants **du plus fort au plus faible**. Pour trier les
       indices par force decroissante :

           ordre = sorted(range(len(times)), key=lambda i: strengths[i], reverse=True)

    3. Accepter un instant seulement s'il est distant d'au moins `min_gap_s` de
       **tous** ceux deja acceptes. Comme on traite les plus forts d'abord, un
       instant rejete l'est forcement au profit d'un plus fort : c'est ce qui
       garantit qu'on garde le bon.

    4. Renvoyer la liste des instants acceptes, **triee par ordre croissant**
       (l'ordre de traitement est celui des forces, pas celui du temps).

    Cas limites : listes vides -> liste vide ; un ecart exactement egal a
    `min_gap_s` est accepte.

    Tests : `test_notes.py::TestSelectStrongest`
    """
    if len(times) != len(strengths):
        raise ValueError("Oups times et strengths non pas la même longueur")

    ordre = sorted(range(len(times)), key=lambda i: strengths[i], reverse=True)
    result = []
    for o in ordre:
        t = times[o]
        if all(abs(t - accepted) >= min_gap_s for accepted in result):
            result.append(t)
    return sorted(result)




def merge_bands(
    band_times: dict[str, list[float]],
    band_strengths: dict[str, list[float]],
    min_gap_s: float,
    beats: list[float] | None = None,
    use_new_gen: bool = False,
) -> tuple[list[float], list[NoteType]]:
    """Fusionne les detections par bande en une seule suite de notes typees.

    Chaque bande a produit ses instants ; il faut en faire une partition unique,
    ou chaque note porte le type de la bande dont elle vient.

    **L'arbitrage se fait a l'intensite.** Quand deux bandes frappent trop pres
    l'une de l'autre pour etre jouees toutes les deux, on garde la plus forte,
    et non celle d'une bande privilegiee d'avance. Une caisse claire qui claque
    l'emporte donc sur un kick discret, ce qui est ce que l'oreille attend : les
    accents ressortent au lieu d'etre ecrases par une regle fixe. L'ordre de
    `config.BANDS` ne sert plus qu'a departager les egalites parfaites.

    Les intensites doivent avoir ete **normalisees par bande** en amont, sinon
    une bande globalement plus energique gagnerait systematiquement.
    """
    entries: list[tuple[float, float, int, NoteType]] = []

    for index, band_name in enumerate(config.BANDS):
        note_type = config.BAND_NOTE_TYPE.get(band_name)
        if note_type is None or band_name not in band_times:
            continue  # bande volontairement ignoree, ou absente de l'analyse

        times = band_times[band_name]
        strengths = band_strengths.get(band_name, [])
        if len(strengths) != len(times):
            raise ValueError(
                f"bande {band_name} : {len(times)} instants pour "
                f"{len(strengths)} intensites"
            )
        entries.extend(
            (time_s, strength, index, note_type)
            for time_s, strength in zip(times, strengths)
        )

    # Detection snare (MID band reguliere sur beats 2/4) pour nouveau generateur
    is_snare_beat: set[float] = set()
    if use_new_gen and beats and len(beats) >= 4:
        mid_times = band_times.get("MID", [])
        if mid_times:
            for beat_idx, beat in enumerate(beats[:-1]):
                # beats 2 et 4 d'une mesure 4/4 (index 1 et 3 dans le groupe de 4)
                if beat_idx % 4 in (1, 3):
                    nearest = min(mid_times, key=lambda t: abs(t - beat))
                    if abs(nearest - beat) < config.SNARE_BEAT_TOLERANCE_S:
                        is_snare_beat.add(beat)

    # Du plus fort au plus faible : chaque note rejetee l'est au profit d'une
    # plus intense, jamais l'inverse.
    entries.sort(key=lambda entry: (-entry[1], entry[2], entry[0]))

    kept: list[tuple[float, NoteType]] = []
    for time_s, _strength, _priority, note_type in entries:
        if all(abs(time_s - other) >= min_gap_s for other, _ in kept):
            # Sur nouveau gen : snare sur beats 2/4 force KA
            if use_new_gen and any(
                abs(time_s - b) < config.SNARE_BEAT_TOLERANCE_S for b in is_snare_beat
            ):
                note_type = "KA" if note_type == "DON" else note_type
            kept.append((time_s, note_type))

    kept.sort(key=lambda pair: pair[0])
    return [time_s for time_s, _ in kept], [note_type for _, note_type in kept]


def types_from_contour(
    band_energies: list[tuple[float, float]],
) -> list[NoteType]:
    """Couleur de chaque note, relative au contour de sa propre piste.

    Fonction pure.

    `classify_note_type` compare grave et aigu dans l'absolu : sur une piste
    homogene, elle rend donc toujours la meme reponse — la basse est grave, la
    voix est aigue. Ici on compare chaque note a la brillance MEDIANE de sa
    piste : les notes plus brillantes que la moyenne de la ligne deviennent des
    KA, les plus sombres des DON.

    Une ligne de chant alterne alors selon qu'elle monte ou descend, ce qui est
    exactement la facon dont un charter humain colore une melodie en taiko.
    """
    if not band_energies:
        return []

    # Part d'aigu dans chaque note, entre 0 et 1.
    brightness = [
        high / (low + high) if (low + high) > 0 else 0.0 for low, high in band_energies
    ]
    ordered = sorted(brightness)
    middle = len(ordered) // 2
    median = (
        ordered[middle]
        if len(ordered) % 2
        else (ordered[middle - 1] + ordered[middle]) / 2
    )
    return ["KA" if value > median else "DON" for value in brightness]


def cap_same_type_runs(
    types: list[NoteType], max_run: int = config.MAX_SAME_TYPE_RUN
) -> list[NoteType]:
    """Brise les longues series d'une meme couleur, en alternant la couleur.

    Fonction pure.

    Les quatre difficultes officielles de « Haruka Kanata » en osu!taiko ont
    toutes une serie mediane de 1 et un maximum de 4 a 5. Notre generateur
    produisait des series de 40 : trois pistes sur quatre etant monochromes
    (bass n'emet que des DON, vocals et other que des KA), une phrase menee par
    l'une d'elles l'etait aussi.

    On parcourt la suite en comptant la serie courante ; des qu'une note la
    ferait depasser `max_run`, on bascule sa couleur et la serie repart. Le
    resultat garantit qu'aucune serie ne depasse la limite.
    """
    if max_run < 1 or not types:
        return list(types)

    result: list[NoteType] = []
    run = 0
    for note_type in types:
        if result and note_type == result[-1]:
            run += 1
        else:
            run = 1
        if run > max_run:
            note_type = "KA" if note_type == "DON" else "DON"
            run = 1
        result.append(note_type)
    return result


def filter_hold_segments(
    segments: list[tuple[float, float]],
    onset_times: list[float],
    max_onsets_per_s: float,
    max_duration_s: float,
) -> list[tuple[float, float]]:
    """Ne garde que les segments qui sont de vraies tenues.

    Fonction pure. Un segment energique mais truffe d'attaques est une phrase
    rythmique (chant scande, rap) : le jouer en tenue serait a contretemps de
    ce qu'on entend. Les segments trop longs sont tronques, pas jetes — le
    debut de l'envolee reste le moment fort.
    """
    holds: list[tuple[float, float]] = []
    for start, end in segments:
        duration = end - start
        if duration <= 0:
            continue
        onsets = sum(1 for t in onset_times if start < t < end)
        if onsets / duration > max_onsets_per_s:
            continue
        holds.append((start, min(end, start + max_duration_s)))
    return holds


def carve_taps_for_holds(
    events: list[tuple[float, float, str]],
    holds: list[tuple[float, float]],
    note_type: str,
    margin_s: float,
) -> list[tuple[float, float, str]]:
    """Retire les frappes du type donne qui chevauchent une tenue.

    Fonction pure. Pendant qu'une lane tient, elle ne peut pas aussi frapper :
    ses taps dans l'intervalle (elargi d'une marge) disparaissent. Les taps de
    l'autre lane restent — c'est tout l'interet du format deux lanes.
    """
    def clashes(time_s: float) -> bool:
        return any(start - margin_s <= time_s <= end + margin_s for start, end in holds)

    return [
        event
        for event in events
        if event[2] != note_type or not clashes(event[0])
    ]


def classify_note_type(
    low_energy: float,
    high_energy: float,
    ka_ratio: float = config.KA_ENERGY_RATIO,
    is_snare_candidate: bool = False,
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

    Si `is_snare_candidate` est True, retourne "KA" (caisse claire = bord de peau).

    Tests : `test_notes.py::TestClassifyNoteType`
    """
    if is_snare_candidate:
        return "KA"
    if high_energy > low_energy * ka_ratio:
        return "KA"
    else:
        return "DON"


def times_to_notes(
    times: list[float],
    types: list[NoteType],
    offset_ms: int = 0,
    durations_s: list[float] | None = None,
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
    if durations_s is not None and len(durations_s) != len(times):
        raise ValueError(
            f"durations_s doit suivre times : {len(durations_s)} != {len(times)}"
        )

    notes = []
    for index, (t, note_type) in enumerate(zip(times, types)):
        times_ms = round(t * 1000) + offset_ms
        note = {"timeMs": times_ms, "type": note_type}
        # Une duree non nulle fait de la note un hold ; zero ou absent = tap.
        duration = durations_s[index] if durations_s is not None else 0.0
        if duration > 0:
            note["durationMs"] = round(duration * 1000)
        notes.append(note)
    return sorted(notes, key=lambda note: note["timeMs"])  
