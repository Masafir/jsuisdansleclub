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
    envelope = librosa.onset.onset_strength(y=samples, sr=sample_rate, hop_length=config.HOP_LENGTH)
    print(envelope.shape, envelope.max(), envelope.mean())
    return envelope


def detect_onset_times(
    envelope: np.ndarray,
    sample_rate: int,
    sensitivity: float = config.ONSET_SENSITIVITY,
    min_gap_s: float = config.ONSET_MIN_GAP_S,
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
    seuil = envelope.mean() + sensitivity * envelope.std()
    frames = []
    for i in range(1, len(envelope) - 1):
        if envelope[i] > seuil and envelope[i] > envelope[i - 1] and envelope[i] > envelope[i + 1]:
            # C'est un pic au-dessus du seuil
            new_time = librosa.frames_to_time(i, sr=sample_rate, hop_length=config.HOP_LENGTH)
            frames.append(new_time)

    return enforce_min_gap(frames, min_gap_s)

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
    raise NotImplementedError("TODO(amiral): onset_envelopes_by_band")


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
    raise NotImplementedError("TODO(amiral): quantize_to_grid")


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
