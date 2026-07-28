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
    raise NotImplementedError("TODO(amiral): onset_envelope")


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
    raise NotImplementedError("TODO(amiral): detect_onset_times")


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
