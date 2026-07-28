"""Tests de la detection d'onsets.

On n'utilise aucun fichier audio : les signaux sont fabriques a la main, ce qui
rend les tests rapides et deterministes.
"""

import numpy as np

from chartgen import config
from chartgen.analysis import detect_onset_times, onset_envelope


def click_track(click_times_s: list[float], duration_s: float = 2.0) -> np.ndarray:
    """Signal silencieux ponctue de breves salves de bruit."""
    rng = np.random.default_rng(seed=1234)
    samples = np.zeros(int(duration_s * config.SAMPLE_RATE), dtype=np.float32)
    burst_length = int(0.01 * config.SAMPLE_RATE)

    for time_s in click_times_s:
        start = int(time_s * config.SAMPLE_RATE)
        burst = rng.uniform(-1.0, 1.0, burst_length).astype(np.float32)
        samples[start:start + burst_length] = burst

    return samples


def frame_to_time(frame: int) -> float:
    return frame * config.HOP_LENGTH / config.SAMPLE_RATE


def test_onset_envelope_detecte_les_impulsions():
    click_times = [0.5, 1.0, 1.5]
    envelope = onset_envelope(click_track(click_times), config.SAMPLE_RATE)

    assert envelope.ndim == 1
    assert len(envelope) > 0

    # Les trois plus fortes valeurs doivent tomber sur les trois clics.
    strongest = sorted(np.argsort(envelope)[-3:])
    detected = [frame_to_time(int(frame)) for frame in strongest]

    for expected, actual in zip(click_times, detected):
        assert abs(actual - expected) < 0.05


class TestDetectOnsetTimes:
    def test_retient_les_pics_francs(self):
        envelope = np.zeros(100)
        for frame in (10, 50, 90):
            envelope[frame] = 10.0

        times = detect_onset_times(envelope, config.SAMPLE_RATE)

        assert len(times) == 3
        for expected_frame, actual in zip((10, 50, 90), times):
            assert abs(actual - frame_to_time(expected_frame)) < 1e-6

    def test_ignore_les_bosses_sous_le_seuil(self):
        envelope = np.zeros(100)
        envelope[10] = 10.0
        envelope[50] = 10.0
        envelope[30] = 0.2  # bruit de fond, tres en dessous du seuil

        times = detect_onset_times(envelope, config.SAMPLE_RATE)

        assert len(times) == 2
        assert all(abs(t - frame_to_time(30)) > 1e-3 for t in times)

    def test_sensibilite_haute_retient_moins_de_pics(self):
        envelope = np.zeros(200)
        for frame in range(10, 200, 10):
            envelope[frame] = 1.0
        envelope[100] = 20.0  # une attaque nettement plus forte

        permissif = detect_onset_times(envelope, config.SAMPLE_RATE, sensitivity=0.5)
        severe = detect_onset_times(envelope, config.SAMPLE_RATE, sensitivity=3.0)

        assert len(severe) < len(permissif)

    def test_pics_trop_rapproches_ecartes(self):
        envelope = np.zeros(100)
        envelope[10] = 10.0
        envelope[11] = 1.0   # creux, pour que 10 et 12 soient deux maxima
        envelope[12] = 10.0
        envelope[80] = 10.0

        # 10 et 12 sont distants de 2 trames, soit ~46 ms : moins que
        # ONSET_MIN_GAP_S, donc un seul des deux doit survivre.
        times = detect_onset_times(envelope, config.SAMPLE_RATE)

        assert len(times) == 2
        assert abs(times[0] - frame_to_time(10)) < 1e-6

    def test_resultat_croissant(self):
        envelope = np.zeros(100)
        for frame in (10, 40, 70):
            envelope[frame] = 10.0

        times = detect_onset_times(envelope, config.SAMPLE_RATE)

        assert times == sorted(times)

    def test_enveloppe_plate_ne_produit_aucune_note(self):
        envelope = np.full(100, 3.0)
        assert detect_onset_times(envelope, config.SAMPLE_RATE) == []
