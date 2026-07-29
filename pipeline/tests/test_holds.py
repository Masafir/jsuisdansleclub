"""Tests des notes tenues : segments soutenus, filtrage, purge des taps."""

import numpy as np

from chartgen import config
from chartgen.analysis import sustained_segments
from chartgen.notes import carve_taps_for_holds, filter_hold_segments, times_to_notes


def rms_with_plateau(start_s: float, end_s: float, total_s: float = 10.0) -> np.ndarray:
    """Enveloppe RMS synthetique : silence, un plateau, silence."""
    frame_s = config.HOP_LENGTH / config.SAMPLE_RATE
    frames = int(total_s / frame_s)
    rms = np.zeros(frames)
    rms[int(start_s / frame_s) : int(end_s / frame_s)] = 1.0
    return rms


class TestSustainedSegments:
    def test_un_plateau_donne_un_segment(self):
        rms = rms_with_plateau(2.0, 5.0)
        segments = sustained_segments(rms, config.SAMPLE_RATE, 0.5, 1.0, 0.2)

        assert len(segments) == 1
        start, end = segments[0]
        assert abs(start - 2.0) < 0.05
        assert abs(end - 5.0) < 0.05

    def test_un_plateau_trop_court_est_ignore(self):
        rms = rms_with_plateau(2.0, 2.5)
        assert sustained_segments(rms, config.SAMPLE_RATE, 0.5, 1.0, 0.2) == []

    def test_une_respiration_ne_coupe_pas_l_envolee(self):
        rms = rms_with_plateau(2.0, 4.0) + rms_with_plateau(4.1, 6.0)
        segments = sustained_segments(rms, config.SAMPLE_RATE, 0.5, 1.0, 0.2)

        assert len(segments) == 1
        assert abs(segments[0][1] - 6.0) < 0.05

    def test_deux_phrases_bien_separees_restent_distinctes(self):
        rms = rms_with_plateau(1.0, 3.0) + rms_with_plateau(6.0, 8.0)
        segments = sustained_segments(rms, config.SAMPLE_RATE, 0.5, 1.0, 0.2)
        assert len(segments) == 2

    def test_silence_total(self):
        rms = np.zeros(1000)
        assert sustained_segments(rms, config.SAMPLE_RATE, 0.5, 1.0, 0.2) == []

    def test_un_plateau_finissant_au_bord_est_ferme(self):
        rms = rms_with_plateau(8.0, 10.0)
        segments = sustained_segments(rms, config.SAMPLE_RATE, 0.5, 1.0, 0.2)
        assert len(segments) == 1


class TestFilterHoldSegments:
    def test_segment_calme_conserve(self):
        # Deux onsets en 4 s : bien en dessous du plafond.
        assert filter_hold_segments([(2.0, 6.0)], [2.0, 4.0], 2.0, 6.0) == [(2.0, 6.0)]

    def test_segment_scande_rejete(self):
        # Douze attaques en 4 s : du chant rythmique, pas une tenue.
        onsets = [2.0 + i * 0.33 for i in range(12)]
        assert filter_hold_segments([(2.0, 6.0)], onsets, 2.0, 6.0) == []

    def test_segment_trop_long_tronque(self):
        result = filter_hold_segments([(0.0, 10.0)], [], 2.0, 6.0)
        assert result == [(0.0, 6.0)]

    def test_les_bornes_du_segment_ne_comptent_pas_comme_attaques(self):
        # L'onset du debut de la tenue est l'attaque de la tenue elle-meme.
        assert filter_hold_segments([(2.0, 4.0)], [2.0, 4.0], 0.4, 6.0) == [(2.0, 4.0)]


class TestCarveTapsForHolds:
    EVENTS = [(1.0, 1.0, "KA"), (2.5, 1.0, "KA"), (2.5, 1.0, "DON"), (5.0, 1.0, "KA")]

    def test_purge_les_taps_du_type_dans_l_intervalle(self):
        result = carve_taps_for_holds(self.EVENTS, [(2.0, 4.0)], "KA", 0.1)
        assert result == [(1.0, 1.0, "KA"), (2.5, 1.0, "DON"), (5.0, 1.0, "KA")]

    def test_l_autre_lane_est_intouchee(self):
        result = carve_taps_for_holds(self.EVENTS, [(2.0, 4.0)], "KA", 0.1)
        assert (2.5, 1.0, "DON") in result

    def test_la_marge_elargit_l_intervalle(self):
        # 1.95 est hors de [2, 4] mais dans la marge de 0.1.
        events = [(1.95, 1.0, "KA")]
        assert carve_taps_for_holds(events, [(2.0, 4.0)], "KA", 0.1) == []

    def test_sans_hold_rien_ne_change(self):
        assert carve_taps_for_holds(self.EVENTS, [], "KA", 0.1) == self.EVENTS


class TestTimesToNotesDurations:
    def test_une_duree_produit_un_hold(self):
        result = times_to_notes([1.0], ["KA"], durations_s=[2.0])
        assert result == [{"timeMs": 1000, "type": "KA", "durationMs": 2000}]

    def test_une_duree_nulle_reste_un_tap(self):
        result = times_to_notes([1.0], ["KA"], durations_s=[0.0])
        assert result == [{"timeMs": 1000, "type": "KA"}]

    def test_sans_durations_comportement_inchange(self):
        result = times_to_notes([1.0], ["DON"])
        assert result == [{"timeMs": 1000, "type": "DON"}]

    def test_longueur_incoherente_leve_une_erreur(self):
        import pytest

        with pytest.raises(ValueError):
            times_to_notes([1.0, 2.0], ["KA", "KA"], durations_s=[1.0])
