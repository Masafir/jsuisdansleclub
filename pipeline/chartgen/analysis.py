"""Analyse audio : de la forme d'onde aux instants ou quelque chose frappe.

Vocabulaire utile avant de lire le code :

- **trame** (*frame*) : l'audio est decoupe en petits blocs se chevauchant, un
  toutes les HOP_LENGTH echantillons. Tout le traitement raisonne en indices de
  trames, qu'on reconvertit en secondes a la fin.
- **flux spectral** : de combien le contenu frequentiel a change entre deux
  trames. C'est la mesure qui detecte une attaque, la ou le simple volume
  echoue : une caisse claire par-dessus une nappe de synthe ne fait pas monter
  le volume, mais bouleverse la repartition des frequences.
- **enveloppe d'onsets** : la courbe du flux spectral au fil du temps. Ses pics
  sont les attaques.
"""

from __future__ import annotations

import librosa
import numpy as np
from .notes import enforce_min_gap

from . import config


def load_audio(path: str) -> tuple[np.ndarray, int]:
    """Charge un fichier audio en mono, re-echantillonne a SAMPLE_RATE.

    Renvoie (echantillons, frequence). librosa accepte tout ce que ffmpeg sait
    lire, donc mp3, ogg, wav, m4a.
    """
    samples, sample_rate = librosa.load(path, sr=config.SAMPLE_RATE, mono=True)
    return samples, sample_rate


def duration_ms(samples: np.ndarray, sample_rate: int) -> int:
    """Duree totale du morceau, en millisecondes."""
    return int(len(samples) / sample_rate * 1000)


def onset_envelope(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    """Enveloppe d'onsets : la courbe dont les pics sont les attaques.

    A IMPLEMENTER (amiral).

    Outil : `librosa.onset.onset_strength`.

    Arguments a lui passer :
        y=samples, sr=sample_rate, hop_length=config.HOP_LENGTH

    Ce qu'il fait sous le capot : il calcule un spectrogramme (l'energie par
    bande de frequence, trame par trame), puis pour chaque trame la somme des
    *augmentations* d'energie par rapport a la trame precedente. Les baisses
    sont ignorees : une note qui s'eteint n'est pas une attaque.

    Retour attendu : un tableau numpy a une dimension, une valeur par trame.

    Test : `test_analysis.py::test_onset_envelope_detecte_les_impulsions`
    verifie que sur un signal fait de clics espaces, l'enveloppe presente bien
    un pic a chaque clic.
    """
    # HPSS : isole la partie percussive pour que la guitare et les synthes ne
    # produisent plus d'onsets. Sous drapeau : applique inconditionnellement,
    # il changeait aussi l'ancienne generation (mesure sur Haruka Kanata : la
    # moitie des notes en moins).
    source = samples
    if config.USE_HPSS:
        _, source = librosa.effects.hpss(samples, margin=config.HPSS_MARGIN)

    return librosa.onset.onset_strength(
        y=source, sr=sample_rate, hop_length=config.HOP_LENGTH
    )


def detect_onset_times(
    envelope: np.ndarray,
    sample_rate: int,
    sensitivity: float = config.ONSET_SENSITIVITY,
    min_gap_s: float = config.ONSET_MIN_GAP_S,
    samples: np.ndarray | None = None,
) -> list[float]:
    """Choisit les pics de l'enveloppe qui comptent vraiment comme des attaques.

    A IMPLEMENTER (amiral).

    C'est ici que se joue la densite de la partition : trop permissif, chaque
    frisson du morceau devient une note ; trop severe, il ne reste que les
    temps forts.

    Marche a suivre :

    1. Seuil adaptatif. Un seuil fixe ne marche pas : un morceau fort a une
       enveloppe globalement plus haute qu'un morceau doux. On le calcule donc
       depuis l'enveloppe elle-meme :

           seuil = envelope.mean() + sensitivity * envelope.std()

       (`mean` = moyenne, `std` = ecart-type ; ce sont des methodes numpy
       directement disponibles sur le tableau.)

    2. Reperer les pics au-dessus de ce seuil. Un pic est une trame dont la
       valeur est superieure a celle d'avant ET a celle d'apres — un maximum
       local. Attention aux bords du tableau : la premiere et la derniere trame
       n'ont pas de voisine des deux cotes.

    3. Convertir les indices de trames en secondes. Deux options :
            librosa.frames_to_time(indices, sr=sample_rate,
                                   hop_length=config.HOP_LENGTH)
       ou, a la main : indice * config.HOP_LENGTH / sample_rate

    4. Espacer : appliquer `enforce_min_gap` (dans notes.py) avec min_gap_s,
       pour qu'une seule frappe etalee sur plusieurs trames ne donne pas une
       rafale.

    Retour attendu : une liste de temps en secondes, croissante.

    Tests : `test_analysis.py::TestDetectOnsetTimes`
    """
    # Si backtrack actif et samples fourni, utilise librosa.onset_detect
    if config.USE_ONSET_BACKTRACK and samples is not None:
        rms_envelope = librosa.feature.rms(y=samples, hop_length=config.HOP_LENGTH)[0]
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=envelope,
            sr=sample_rate,
            hop_length=config.HOP_LENGTH,
            backtrack=True,
            energy=rms_envelope,
            units='frames'
        )
        times = librosa.frames_to_time(onset_frames, sr=sample_rate, hop_length=config.HOP_LENGTH)
        times_list = list(times)
    else:
        # Peak picking manuel (code original)
        seuil = envelope.mean() + sensitivity * envelope.std()
        frames = []
        for i in range(1, len(envelope) - 1):
            if envelope[i] > seuil and envelope[i] > envelope[i - 1] and envelope[i] > envelope[i + 1]:
                new_time = librosa.frames_to_time(i, sr=sample_rate, hop_length=config.HOP_LENGTH)
                frames.append(new_time)
        times_list = frames

    return enforce_min_gap(times_list, min_gap_s)

def mel_bin_boundaries(n_mels: int, sample_rate: int) -> list[int]:
    """Frontieres de config.BANDS traduites en indices de bandes mel.

    `onset_strength_multi` ne raisonne pas en Hertz mais en numeros de bandes du
    spectrogramme : cette fonction fait la conversion. Elle renvoie une liste de
    N+1 indices pour N bandes, comme attendu par `channels`.
    """
    mel_frequencies = librosa.mel_frequencies(n_mels=n_mels, fmax=sample_rate / 2)
    names = list(config.BANDS)
    edges = [config.BANDS[name][0] for name in names]
    edges.append(config.BANDS[names[-1]][1])
    return [int(np.searchsorted(mel_frequencies, edge)) for edge in edges]


def onset_envelopes_by_band(
    samples: np.ndarray, sample_rate: int
) -> dict[str, np.ndarray]:
    """Une enveloppe d'onsets par bande de frequences.

    A IMPLEMENTER (amiral).

    C'est le cœur du changement : au lieu d'une seule enveloppe melangeant tous
    les instruments, on en obtient une par registre. Le grave suit le kick, le
    medium la caisse claire — le type de note decoule donc de l'instrument, au
    lieu d'etre devine apres coup.

    Marche a suivre :

    1. Spectrogramme mel (l'energie par bande de frequence, trame par trame) :

           spectrogram = librosa.feature.melspectrogram(
               y=samples, sr=sample_rate, hop_length=config.HOP_LENGTH)

    2. Frontieres des bandes, deja calculees pour toi :

           channels = mel_bin_boundaries(spectrogram.shape[0], sample_rate)

    3. Une enveloppe par bande. `onset_strength_multi` attend un spectrogramme
       en decibels, d'ou le passage par `librosa.power_to_db` :

           envelopes = librosa.onset.onset_strength_multi(
               S=librosa.power_to_db(spectrogram),
               sr=sample_rate,
               hop_length=config.HOP_LENGTH,
               channels=channels)

       Le resultat est un tableau a deux dimensions : une ligne par bande.

    4. Renvoyer un dictionnaire {nom de bande: enveloppe}. Les noms sont les
       cles de `config.BANDS`, dans le meme ordre que les lignes du resultat —
       `enumerate(config.BANDS)` fait le lien.

    Retour attendu : dict[str, np.ndarray], une entree par bande.

    Tests : `test_analysis.py::TestOnsetEnvelopesByBand`
    """
    spectrogram = librosa.feature.melspectrogram(
        y=samples, sr=sample_rate, hop_length=config.HOP_LENGTH
    )
    channels = mel_bin_boundaries(spectrogram.shape[0], sample_rate)
    envelopes = librosa.onset.onset_strength_multi(
        S=librosa.power_to_db(spectrogram),
        sr=sample_rate,
        hop_length=config.HOP_LENGTH,
        channels=channels
    )
    return {name: envelopes[i] for i, name in enumerate(config.BANDS)}

def quantize_to_grid(
    times: list[float], grid: list[float], tolerance_s: float
) -> list[float]:
    """Recale les onsets sur la grille rythmique, et jette ceux qui en sont loin.

    A IMPLEMENTER (amiral). Fonction pure : ni audio, ni librosa.

    C'est ce qui rend les motifs anticipables. Un onset proche d'une subdivision
    y est aligne — la main joue alors des croches franches plutot que des
    instants legerement irreguliers. Un onset eloigne de toute subdivision est
    un ornement ou du bruit : on le jette, ce qui allege aussi la partition.

    Marche a suivre :

    1. Pour chaque instant de `times`, trouver le point de `grid` le plus
       proche. `grid` est triee et croissante ; en Python simple,
       `min(grid, key=lambda g: abs(g - t))` suffit largement ici.

    2. Si l'ecart absolu a ce point est <= `tolerance_s`, retenir **le point de
       grille** (pas l'instant d'origine : tout l'interet est de l'aligner).
       Sinon, ne rien retenir pour cet onset.

    3. Dedoublonner : deux onsets proches peuvent tomber sur le meme point de
       grille, il ne doit en rester qu'un.

    4. Renvoyer la liste triee par ordre croissant.

    Cas limites : une grille vide renvoie une liste vide ; la liste d'entree ne
    doit pas etre modifiee.

    Astuce : `sorted(set(resultats))` regle d'un coup le dedoublonnage et le tri.

    Tests : `test_analysis.py::TestQuantizeToGrid`
    """
    if(not grid):
        return []
    closest_points = []
    eps = 1e-9
    for t in times:
        closest = min(grid, key=lambda g: abs(g - t))
        if abs(closest - t) <= tolerance_s + eps:
            closest_points.append(closest)
    return sorted(set(closest_points))


def beat_grid(
    samples: np.ndarray,
    sample_rate: int,
    subdivisions: int = config.BEAT_SUBDIVISIONS,
) -> list[float]:
    """Grille rythmique du morceau : les temps, et leurs subdivisions.

    `beat_track` donne la position des temps ; on interpole ensuite
    `subdivisions` points entre chaque paire de temps consecutifs.
    """
    _tempo, beat_times = librosa.beat.beat_track(
        y=samples, sr=sample_rate, hop_length=config.HOP_LENGTH, units="time"
    )
    if len(beat_times) < 2:
        return [float(t) for t in beat_times]

    grid: list[float] = []
    for start, end in zip(beat_times[:-1], beat_times[1:]):
        step = (end - start) / subdivisions
        grid.extend(float(start + i * step) for i in range(subdivisions))
    grid.append(float(beat_times[-1]))
    return grid


def beat_times(samples: np.ndarray, sample_rate: int) -> list[float]:
    """Position des temps du morceau, en secondes."""
    _tempo, times = librosa.beat.beat_track(
        y=samples, sr=sample_rate, hop_length=config.HOP_LENGTH, units="time"
    )
    return [float(t) for t in times]


def fit_constant_tempo(
    beats: list[float],
    search_ratio: float = config.TEMPO_FIT_SEARCH_RATIO,
    steps: int = config.TEMPO_FIT_STEPS,
) -> tuple[float, float]:
    """Ajuste une periode et une phase constantes sur les temps detectes.

    Renvoie (periode en secondes, phase en secondes).

    Pourquoi : `beat_track` trouve les bons temps mais avec ~25 ms de gigue sur
    chacun. Mesure sur Haruka Kanata — intervalles de 325 a 395 ms autour d'un
    vrai tempo de 342.86 ms, sans aucun temps saute ni ajoute. Construire la
    grille en interpolant entre ces temps propage la gigue dans les notes, qui
    tombent alors a cote : la derive atteignait 539 ms en fin de morceau.
    Ajuster un tempo constant retrouve 174.8 BPM contre 175.0 reels.

    C'est ainsi qu'un mappeur time un morceau : un BPM et un offset, pas une
    position par temps. La limite est assumee — un morceau qui change vraiment
    de tempo serait moins bien servi.

    Methode : pour chaque periode candidate, la phase optimale est la moyenne
    circulaire des temps modulo la periode. La concentration de cette moyenne
    mesure la qualite de l'ajustement ; on garde la meilleure.
    """
    if len(beats) < 2:
        return 0.0, 0.0

    times = np.asarray(beats)
    median_period = float(np.median(np.diff(times)))
    candidates = np.linspace(
        median_period * (1 - search_ratio), median_period * (1 + search_ratio), steps
    )

    best_strength, best_period, best_phase = -1.0, median_period, 0.0
    for period in candidates:
        angles = 2 * np.pi * (times % period) / period
        mean_vector = np.exp(1j * angles).mean()
        strength = float(np.abs(mean_vector))
        if strength > best_strength:
            best_strength = strength
            best_period = float(period)
            best_phase = float(
                (np.angle(mean_vector) % (2 * np.pi)) / (2 * np.pi) * period
            )

    return best_period, best_phase


def regular_beats(beats: list[float]) -> list[float]:
    """Temps regeneres sur un tempo constant, couvrant la meme plage."""
    if len(beats) < 2:
        return list(beats)

    period, phase = fit_constant_tempo(beats)
    if period <= 0:
        return list(beats)

    first = int(np.floor((beats[0] - phase) / period))
    last = int(np.ceil((beats[-1] - phase) / period))
    return [phase + index * period for index in range(first, last + 1)]


def onsets_per_beat(onset_times: list[float], beats: list[float]) -> list[float]:
    """Nombre d'attaques detectees sur chaque temps.

    C'est **le compte** qui revele un moment fort, et non l'energie. Mesure a
    l'appui : sommer l'energie par temps ne detectait qu'un seul moment fort sur
    225 dans un morceau de rock, parce qu'une batterie qui joue en continu
    delivre a peu pres la meme energie a chaque temps. Un roulement, lui, ne
    frappe pas plus fort : il frappe plus souvent.
    """
    if len(beats) < 2:
        return [0.0] * len(beats)

    counts: list[float] = []
    for start, end in zip(beats[:-1], beats[1:]):
        counts.append(float(sum(1 for t in onset_times if start <= t < end)))

    # Le dernier temps n'a pas de suivant : on lui prete le compte du precedent.
    counts.append(counts[-1])
    return counts


def find_accent_beats(
    strengths: list[float],
    ratio: float = config.ACCENT_RATIO,
    window: int = config.ACCENT_WINDOW_BEATS,
) -> set[int]:
    """Indices des temps qui sortent du lot : roulements, relances, refrains.

    La comparaison est **locale** et non globale. Un seuil global marquerait tout
    le refrain comme un long moment fort et laisserait les couplets entierement
    plats, alors qu'on veut des accents dans les deux — un fill de couplet doit
    ressortir de son couplet.

    On compare donc chaque temps a la mediane de son voisinage. La mediane, et
    non la moyenne : un seul pic tres fort tirerait la moyenne vers le haut et
    masquerait les accents voisins, alors que la mediane ignore les extremes.
    """
    if not strengths:
        return set()

    half = max(1, window // 2)
    accents: set[int] = set()

    for index, strength in enumerate(strengths):
        start = max(0, index - half)
        end = min(len(strengths), index + half + 1)
        local_median = float(np.median(strengths[start:end]))
        if local_median > 0 and strength > local_median * ratio:
            accents.add(index)

    return accents


def variable_grid(
    beats: list[float],
    accent_beats: set[int],
    base_subdivisions: int = config.BEAT_SUBDIVISIONS,
    accent_subdivisions: int = config.ACCENT_SUBDIVISIONS,
) -> list[float]:
    """Grille dont la finesse varie : croches en regime normal, doubles sur les
    moments forts.

    C'est la traduction directe de ce que fait un charter humain : couplet en
    croches, roulement en doubles-croches au moment du fill. Le groove reste
    anticipable et les relances redeviennent jouables.
    """
    if len(beats) < 2:
        return list(beats)

    grid: list[float] = []
    for index, (start, end) in enumerate(zip(beats[:-1], beats[1:])):
        subdivisions = (
            accent_subdivisions if index in accent_beats else base_subdivisions
        )
        step = (end - start) / subdivisions
        grid.extend(start + i * step for i in range(subdivisions))

    grid.append(beats[-1])
    return grid


def adaptive_grid(
    beats: list[float],
    onset_times: list[float],
    window_beats: int = config.ADAPTIVE_GRID_WINDOW_BEATS,
    density_ratio: float = config.ADAPTIVE_GRID_DENSITY_RATIO,
) -> list[float]:
    """Grille a subdivision adaptive : choisit 2/3/4/6/8/12 selon densite locale d'onsets.

    Pour chaque intervalle entre deux temps consecutifs, compte le nombre d'onsets
    et compare a la mediane locale. Si densite > mediane * ratio, monte en subdivision.
    """
    if len(beats) < 2:
        return list(beats)
    
    candidates = config.SUBDIVISION_CANDIDATES
    grid: list[float] = []
    
    # Pre-calcule densite par temps
    onset_counts = []
    for start, end in zip(beats[:-1], beats[1:]):
        count = sum(1 for t in onset_times if start <= t < end)
        onset_counts.append(count)
    
    # Mediane glissante sur window_beats
    half = max(1, window_beats // 2)
    
    for index, (start, end) in enumerate(zip(beats[:-1], beats[1:])):
        # Mediane locale
        lo = max(0, index - half)
        hi = min(len(onset_counts), index + half + 1)
        local_median = np.median(onset_counts[lo:hi]) if hi > lo else 0
        
        count = onset_counts[index]
        beat_dur = end - start
        density = count / beat_dur if beat_dur > 0 else 0
        
        # Choisit subdivision selon densite relative
        if local_median > 0 and density > local_median * density_ratio:
            # Monte en subdivision (prochain candidat superieur a base=2)
            base_idx = candidates.index(config.BEAT_SUBDIVISIONS) if config.BEAT_SUBDIVISIONS in candidates else 0
            sub_idx = min(base_idx + 1, len(candidates) - 1)
            subdivisions = candidates[sub_idx]
        else:
            subdivisions = config.BEAT_SUBDIVISIONS
        
        step = (end - start) / subdivisions
        grid.extend(start + i * step for i in range(subdivisions))
    
    grid.append(beats[-1])
    return grid


def grid_tolerance_s(
    grid: list[float], ratio: float = config.QUANTIZE_TOLERANCE_RATIO
) -> float:
    """Tolerance de recalage, en secondes, deduite du pas de la grille."""
    if len(grid) < 2:
        return 0.0
    steps = np.diff(grid)
    return float(np.median(steps) * ratio)


def strength_at(
    envelope: np.ndarray, times: list[float], sample_rate: int
) -> list[float]:
    """Valeur de l'enveloppe aux instants donnes, pour comparer leurs forces."""
    last = len(envelope) - 1
    frames = [
        min(last, max(0, int(round(time_s * sample_rate / config.HOP_LENGTH))))
        for time_s in times
    ]
    return [float(envelope[frame]) for frame in frames]


def rms_envelope(samples: np.ndarray) -> np.ndarray:
    """Energie RMS par trame : le volume au fil du temps, version lissee."""
    return librosa.feature.rms(y=samples, hop_length=config.HOP_LENGTH)[0]


def sustained_segments(
    rms: np.ndarray,
    sample_rate: int,
    threshold: float,
    min_duration_s: float,
    merge_gap_s: float,
) -> list[tuple[float, float]]:
    """Plages ou l'energie reste au-dessus du seuil assez longtemps.

    C'est la matiere premiere des notes tenues : sur une piste de voix isolee,
    une envolee lyrique est un long plateau d'energie, la ou du chant scande
    fait des pics brefs. Les trous plus courts que `merge_gap_s` (une
    respiration) sont fusionnes, puis seuls les segments d'au moins
    `min_duration_s` survivent.
    """
    frame_s = config.HOP_LENGTH / sample_rate
    active = rms > threshold

    # Plages contigues actives, en secondes.
    segments: list[tuple[float, float]] = []
    start: int | None = None
    for index, is_active in enumerate(active):
        if is_active and start is None:
            start = index
        elif not is_active and start is not None:
            segments.append((start * frame_s, index * frame_s))
            start = None
    if start is not None:
        segments.append((start * frame_s, len(active) * frame_s))

    # Fusion des respirations.
    merged: list[tuple[float, float]] = []
    for segment in segments:
        if merged and segment[0] - merged[-1][1] < merge_gap_s:
            merged[-1] = (merged[-1][0], segment[1])
        else:
            merged.append(segment)

    return [(s, e) for s, e in merged if e - s >= min_duration_s]


def band_energies_bulk(
    samples: np.ndarray,
    sample_rate: int,
    times: list[float],
    split_hz: float = config.FREQUENCY_SPLIT_HZ,
) -> list[tuple[float, float]]:
    """Comme `band_energies`, mais pour une liste d'instants d'un coup.

    `band_energies` recalcule le spectrogramme entier a chaque appel — tenable
    pour quelques notes, ruineux pour des centaines. Ici le spectrogramme n'est
    calcule qu'une fois.
    """
    if not times:
        return []

    spectrum = np.abs(librosa.stft(samples, hop_length=config.HOP_LENGTH))
    frequencies = librosa.fft_frequencies(sr=sample_rate)
    is_low = frequencies < split_hz
    last = spectrum.shape[1] - 1

    energies: list[tuple[float, float]] = []
    for time_s in times:
        frame = min(last, max(0, int(time_s * sample_rate / config.HOP_LENGTH)))
        column = spectrum[:, frame]
        energies.append((float(column[is_low].sum()), float(column[~is_low].sum())))
    return energies


def normalized_strength_at(
    envelope: np.ndarray, times: list[float], sample_rate: int
) -> list[float]:
    """Intensites ramenees a l'echelle propre de leur bande.

    Chaque bande a son niveau habituel : le grave d'un morceau peut etre deux
    fois plus energique que l'aigu sans qu'aucun de ses coups ne soit un accent.
    Diviser par l'ecart-type de la bande repond a la seule question qui compte
    pour arbitrer : « ce coup est-il exceptionnel *pour cette bande* ? »
    """
    scale = float(envelope.std()) or 1.0
    return [value / scale for value in strength_at(envelope, times, sample_rate)]


def estimate_tempo(samples: np.ndarray, sample_rate: int) -> float:
    """Tempo du morceau en BPM, purement informatif (affichage, effets visuels).

    Contrairement au prototype de `pipeline/prototype/`, on ne s'en sert pas
    pour placer les notes : elles suivent les onsets, pas une grille.
    """
    tempo, _beats = librosa.beat.beat_track(
        y=samples, sr=sample_rate, hop_length=config.HOP_LENGTH
    )
    return float(np.atleast_1d(tempo)[0])


def band_energies(
    samples: np.ndarray,
    sample_rate: int,
    time_s: float,
    split_hz: float = config.FREQUENCY_SPLIT_HZ,
) -> tuple[float, float]:
    """Energie grave et energie aigue a un instant donne.

    Renvoie (energie_grave, energie_aigue) pour la trame contenant `time_s`,
    en separant le spectre a `split_hz`. C'est la matiere premiere de la
    classification DON / KA.
    """
    frame = int(time_s * sample_rate / config.HOP_LENGTH)
    spectrum = np.abs(
        librosa.stft(samples, hop_length=config.HOP_LENGTH)
    )
    frame = min(frame, spectrum.shape[1] - 1)

    frequencies = librosa.fft_frequencies(sr=sample_rate)
    is_low = frequencies < split_hz

    column = spectrum[:, frame]
    return float(column[is_low].sum()), float(column[~is_low].sum())


def detect_finishes(
    samples: np.ndarray,
    sample_rate: int,
    grid: list[float],
    energy_percentile: float = 95.0,
    min_gap_ms: float = 500.0,
) -> list[tuple[float, str]]:
    """Detecte les finishes (grosses notes) : crêtes spectrales larges (cymbales/crashes).

    Retourne liste de (time_s, note_type) pour les finishes detectees.
    """
    if not grid or len(grid) < 2:
        return []
    
    # Spectral centroid et energy sur toute la duree
    centroid = librosa.feature.spectral_centroid(
        y=samples, sr=sample_rate, hop_length=config.HOP_LENGTH
    )[0]
    rms = librosa.feature.rms(y=samples, hop_length=config.HOP_LENGTH)[0]
    times = librosa.times_like(centroid, sr=sample_rate, hop_length=config.HOP_LENGTH)
    
    # Seuils basés sur percentiles
    centroid_thresh = np.percentile(centroid, energy_percentile)
    energy_thresh = np.percentile(rms, energy_percentile)
    
    finishes = []
    last_finish_time = -min_gap_ms / 1000.0
    
    for g in grid:
        idx = np.argmin(np.abs(times - g))
        if idx >= len(centroid):
            continue
            
        # Crest factor : centroid haut + energy haute = crash/cymbale
        if centroid[idx] > centroid_thresh and rms[idx] > energy_thresh:
            if g - last_finish_time >= min_gap_ms / 1000.0:
                # Type de note : alterne DON/KA selon position dans la mesure
                # (approximation simple)
                note_type = "DON" if int(g * 2) % 2 == 0 else "KA"
                finishes.append((g, note_type))
                last_finish_time = g
    
    return finishes
