"""Decoupage en phrases, attention par nouveaute, budget de notes.

C'est la couche « charter » du pipeline : elle ne detecte rien, elle CHOISIT.
Quelle piste le joueur incarne sur chaque phrase (le lead), combien de notes la
phrase a le droit de porter (le budget), et lesquelles survivent (les plus
fortes). Les principes viennent droit du groove :

- l'attention va vers ce qui change -> le lead suit la nouveaute ;
- le contraste fabrique les pics -> le budget suit l'intensite relative ;
- la pulsation ne doit jamais disparaitre -> une ossature de kicks accompagne
  le lead quand il n'est pas la batterie.

Tout ici est fonction pure : memes entrees, memes sorties, aucun fichier.
"""

from __future__ import annotations

import librosa
import numpy as np

from . import config

#: Un evenement musical : (instant en secondes, intensite normalisee, type de
#: note). L'intensite est normalisee par piste en amont, pour que deux pistes
#: puissent etre comparees.
Event = tuple[float, float, str]


def phrase_spans(
    beats: list[float], phrase_beats: int = config.PHRASE_BEATS
) -> list[tuple[float, float]]:
    """Decoupe la liste des temps en phrases de `phrase_beats` temps.

    La derniere phrase, souvent incomplete, est conservee : mieux vaut une
    phrase courte que des notes orphelines jamais traitees.
    """
    if len(beats) < 2:
        return []

    spans: list[tuple[float, float]] = []
    for start in range(0, len(beats) - 1, phrase_beats):
        end = min(start + phrase_beats, len(beats) - 1)
        spans.append((beats[start], beats[end]))
    return spans


def snap_events(
    events: list[Event], grid: list[float], tolerance_s: float
) -> list[Event]:
    """Recale chaque evenement sur le point de grille le plus proche.

    Ceux qui n'ont aucun point a portee sont des ornements ou du bruit : jetes.
    Contrairement a `quantize_to_grid`, on conserve l'intensite et le type
    attaches a chaque instant.
    """
    if not grid:
        return []

    snapped: list[Event] = []
    for time_s, strength, note_type in events:
        nearest = min(grid, key=lambda point: abs(point - time_s))
        if abs(nearest - time_s) <= tolerance_s:
            snapped.append((nearest, strength, note_type))
    return sorted(snapped)


def dedupe_events(events: list[Event], min_gap_s: float) -> list[Event]:
    """Resout les collisions d'un meme flux : la plus forte gagne."""
    ordered = sorted(events, key=lambda event: (-event[1], event[0]))
    kept: list[Event] = []
    for event in ordered:
        if all(abs(event[0] - other[0]) >= min_gap_s for other in kept):
            kept.append(event)
    return sorted(kept)


def events_in_span(events: list[Event], start: float, end: float) -> list[Event]:
    """Evenements tombant dans [start, end[."""
    return [event for event in events if start <= event[0] < end]


def pattern_signature(
    events: list[Event],
    start: float,
    end: float,
    slots: int = config.PATTERN_SLOTS_PER_PHRASE,
) -> tuple[int, ...]:
    """Motif rythmique d'une phrase : les cases occupees d'une grille de
    `slots` positions.

    Deux phrases jouant le meme motif donnent la meme signature quel que soit
    leur emplacement dans le morceau — c'est ce qui permet de reconnaitre la
    repetition.
    """
    if end <= start:
        return ()

    width = (end - start) / slots
    filled = {
        min(slots - 1, int((event[0] - start) / width))
        for event in events
        if start <= event[0] < end
    }
    return tuple(sorted(filled))


def novelty(
    signature: tuple[int, ...], history: list[tuple[int, ...]]
) -> float:
    """1 = motif jamais entendu, 0 = deja entendu tel quel.

    Similarite de Jaccard avec le motif passe le plus proche : robuste a une
    note pres, la ou une comparaison exacte verrait de la nouveaute dans le
    moindre accident de detection.
    """
    if not history:
        return 1.0

    current = set(signature)
    best_similarity = 0.0
    for past in history:
        past_set = set(past)
        if not current and not past_set:
            similarity = 1.0
        elif not current or not past_set:
            similarity = 0.0
        else:
            similarity = len(current & past_set) / len(current | past_set)
        best_similarity = max(best_similarity, similarity)
    return 1.0 - best_similarity


def salience(
    event_count: int,
    span_s: float,
    novelty_score: float,
    floor: float = config.NOVELTY_FLOOR,
) -> float:
    """Ce qui attire l'oreille : de l'activite, ponderee par la nouveaute.

    Le plancher garantit qu'une piste active mais repetitive garde un peu de
    saillance : elle doit toujours battre une piste silencieuse.
    """
    if span_s <= 0:
        return 0.0
    return (event_count / span_s) * (floor + novelty_score)


def detect_sections(
    samples: np.ndarray,
    sample_rate: int,
    beats: list[float],
    n_sections: int = config.STRUCTURE_SECTIONS,
) -> list[tuple[float, float, str]]:
    """Decoupe le morceau en sections (verse, chorus, bridge, etc.) par MFCC + agglomerative.

    Retourne une liste de (start_s, end_s, label) pour chaque section detectee.
    Les labels sont guesses par profil spectral moyen:
      - bright + high centroid -> "chorus"
      - lower energy -> "verse"
      - sparse -> "bridge"
      - first/last -> "intro" / "outro"
    """
    if len(samples) < sample_rate or len(beats) < 4:
        return [(beats[0], beats[-1], "unknown")]

    hop_length = config.HOP_LENGTH
    # MFCC comme descripteur de timbre
    mfcc = librosa.feature.mfcc(y=samples, sr=sample_rate, hop_length=hop_length)
    # Normaliser chaque coefficient
    mfcc = (mfcc - mfcc.mean(axis=1, keepdims=True)) / (mfcc.std(axis=1, keepdims=True) + 1e-10)

    # Agglomerative clustering sur les trames temporelles. `agglomerative` ne
    # prend pas de hop_length : elle rend des indices de trames, qu'on convertit
    # nous-memes.
    boundaries_frames = librosa.segment.agglomerative(mfcc, n_sections)
    frame_times = librosa.frames_to_time(
        boundaries_frames, sr=sample_rate, hop_length=hop_length
    )

    # Ajuster les frontieres aux temps les plus proches
    adjusted = [beats[0]]
    for t in frame_times[1:-1]:
        nearest = min(beats, key=lambda b: abs(b - t))
        if nearest > adjusted[-1]:
            adjusted.append(nearest)
    adjusted.append(beats[-1])

    # Caracteriser chaque section pour deviner un label
    spectrum = np.abs(librosa.stft(samples, hop_length=hop_length))
    centroid = librosa.feature.spectral_centroid(
        S=spectrum, sr=sample_rate, hop_length=hop_length
    )[0]
    rms = librosa.feature.rms(y=samples, hop_length=hop_length)[0]

    sections: list[tuple[float, float, str]] = []
    n = len(adjusted)

    for i in range(n - 1):
        start_s, end_s = adjusted[i], adjusted[i + 1]
        # Trame MFCC correspondante
        f_start = int(start_s * sample_rate / hop_length)
        f_end = int(end_s * sample_rate / hop_length) + 1

        if f_end <= f_start:
            label = "unknown"
        else:
            avg_centroid = float(centroid[f_start:f_end].mean())
            avg_energy = float(rms[f_start:f_end].mean())
            centroid_norm = avg_centroid / (sample_rate / 2)

            if i == 0:
                label = "intro"
            elif i == n - 2:
                label = "outro"
            elif (
                centroid_norm > config.STRUCTURE_CHORUS_CENTROID
                and avg_energy > config.STRUCTURE_CHORUS_ENERGY
            ):
                label = "chorus"
            elif avg_energy < config.STRUCTURE_BRIDGE_ENERGY:
                label = "bridge"
            else:
                label = "verse"

        sections.append((start_s, end_s, label))

    return sections


def select_lead(
    saliences: dict[str, float],
    previous: str | None,
    hysteresis: float = config.LEAD_HYSTERESIS,
    section_label: str | None = None,
) -> str | None:
    """Choisit la piste que le joueur incarne sur la phrase.

    Hysteresis : le lead en place n'est detrone que si un pretendant le depasse
    nettement. L'attention humaine est stable par phrases ; un chart qui zappe
    a chaque mesure est illisible. Renvoie None si tout est silencieux.

    Si `section_label` est fournie et que `USE_STRUCTURE_GUIDANCE` est actif,
    une preference de section peut surcharger le choix.
    """
    candidates = {stem: value for stem, value in saliences.items() if value > 0}
    if not candidates:
        return None

    best = max(candidates, key=lambda stem: candidates[stem])

    # Preference de section si activee
    if section_label and config.USE_STRUCTURE_GUIDANCE:
        preferred = config.SECTION_LEAD_PREFERENCE.get(section_label.lower())
        if preferred and preferred in candidates:
            candidates[preferred] *= config.STRUCTURE_LEAD_BOOST
            best = max(candidates, key=lambda stem: candidates[stem])

    if previous in candidates and candidates[previous] * hysteresis >= candidates[best]:
        return previous
    return best


def phrase_budget(
    intensity_nps: float,
    median_nps: float,
    span_s: float,
    target_nps: float = config.TARGET_NOTES_PER_SECOND,
    min_multiplier: float = config.BUDGET_MIN_MULTIPLIER,
    max_multiplier: float = config.BUDGET_MAX_MULTIPLIER,
) -> int:
    """Nombre de notes que la phrase a le droit de porter.

    Le budget suit l'intensite RELATIVE du morceau : une phrase deux fois plus
    chargee que la mediane recoit plus de notes, une phrase calme en recoit
    peu. C'est le contraste — un morceau qui tape tout le temps ne tape
    jamais.
    """
    multiplier = 1.0 if median_nps <= 0 else intensity_nps / median_nps
    multiplier = max(min_multiplier, min(max_multiplier, multiplier))
    return max(0, round(target_nps * span_s * multiplier))


def pick_top(events: list[Event], budget: int) -> list[Event]:
    """Garde les `budget` evenements les plus forts, rendus chronologiques."""
    if budget <= 0:
        return []
    strongest = sorted(events, key=lambda event: (-event[1], event[0]))[:budget]
    return sorted(strongest)


def combine_streams(
    primary: list[Event], secondary: list[Event], min_gap_s: float
) -> list[Event]:
    """Fusionne deux flux ; en cas de collision, le primaire gagne toujours.

    Sert a poser l'ossature de kicks autour du lead sans jamais l'evincer.
    """
    kept = list(primary)
    for event in sorted(secondary, key=lambda event: (-event[1], event[0])):
        if all(abs(event[0] - other[0]) >= min_gap_s for other in kept):
            kept.append(event)
    return sorted(kept)
