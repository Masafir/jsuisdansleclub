"""Tests de la detection d'onsets.

On n'utilise aucun fichier audio : les signaux sont fabriques a la main, ce qui
rend les tests rapides et deterministes.
"""

import numpy as np

from chartgen import config
from chartgen.analysis import (
    detect_onset_times,
    find_accent_beats,
    onset_envelope,
    onset_envelopes_by_band,
    onsets_per_beat,
    quantize_to_grid,
    variable_grid,
)


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


def tone_burst(frequency_hz: float, at_s: float, duration_s: float = 2.0) -> np.ndarray:
    """Silence ponctue d'une breve note pure a la frequence demandee."""
    samples = np.zeros(int(duration_s * config.SAMPLE_RATE), dtype=np.float32)
    length = int(0.05 * config.SAMPLE_RATE)
    start = int(at_s * config.SAMPLE_RATE)

    t = np.arange(length) / config.SAMPLE_RATE
    # Enveloppe descendante : une attaque franche suivie d'une extinction.
    burst = np.sin(2 * np.pi * frequency_hz * t) * np.exp(-t * 30)
    samples[start:start + length] = burst.astype(np.float32)
    return samples


class TestOnsetEnvelopesByBand:
    def test_renvoie_une_enveloppe_par_bande(self):
        envelopes = onset_envelopes_by_band(click_track([0.5]), config.SAMPLE_RATE)

        assert set(envelopes) == set(config.BANDS)
        for envelope in envelopes.values():
            assert envelope.ndim == 1

    def test_un_grave_excite_la_bande_grave(self):
        # 60 Hz : un kick. La bande LOW doit reagir plus fort que la bande HIGH.
        envelopes = onset_envelopes_by_band(tone_burst(60, 1.0), config.SAMPLE_RATE)

        assert envelopes["LOW"].max() > envelopes["HIGH"].max()

    def test_un_aigu_excite_la_bande_aigue(self):
        # 6000 Hz : un charleston. C'est l'inverse.
        envelopes = onset_envelopes_by_band(tone_burst(6000, 1.0), config.SAMPLE_RATE)

        assert envelopes["HIGH"].max() > envelopes["LOW"].max()

    def test_le_pic_tombe_au_bon_instant(self):
        envelopes = onset_envelopes_by_band(tone_burst(60, 1.0), config.SAMPLE_RATE)

        peak_frame = int(np.argmax(envelopes["LOW"]))
        assert abs(frame_to_time(peak_frame) - 1.0) < 0.05


class TestQuantizeToGrid:
    #: Grille reguliere de 100 ms, comme des doubles-croches a 150 BPM.
    GRID = [round(0.1 * i, 3) for i in range(11)]

    def test_listes_vides(self):
        assert quantize_to_grid([], self.GRID, 0.03) == []

    def test_grille_vide_ne_retient_rien(self):
        assert quantize_to_grid([0.15, 0.42], [], 0.03) == []

    def test_instant_deja_sur_la_grille_inchange(self):
        assert quantize_to_grid([0.3], self.GRID, 0.03) == [0.3]

    def test_instant_proche_recale_sur_la_grille(self):
        # 0.317 s est a 17 ms de 0.3 : dans la tolerance, donc aligne.
        assert quantize_to_grid([0.317], self.GRID, 0.03) == [0.3]

    def test_instant_eloigne_rejete(self):
        # 0.35 s est a 50 ms des deux points voisins : c'est un ornement.
        assert quantize_to_grid([0.35], self.GRID, 0.03) == []

    def test_ecart_exactement_egal_a_la_tolerance_accepte(self):
        assert quantize_to_grid([0.33], self.GRID, 0.03) == [0.3]

    def test_deux_onsets_sur_le_meme_point_fusionnent(self):
        assert quantize_to_grid([0.29, 0.31], self.GRID, 0.03) == [0.3]

    def test_resultat_trie(self):
        assert quantize_to_grid([0.7, 0.1, 0.4], self.GRID, 0.03) == [0.1, 0.4, 0.7]

    def test_n_altere_pas_la_liste_d_entree(self):
        times = [0.317, 0.35]
        quantize_to_grid(times, self.GRID, 0.03)
        assert times == [0.317, 0.35]


class TestOnsetsPerBeat:
    BEATS = [0.0, 1.0, 2.0, 3.0]

    def test_moins_de_deux_temps(self):
        assert onsets_per_beat([0.5], []) == []
        assert onsets_per_beat([0.5], [0.0]) == [0.0]

    def test_compte_les_attaques_de_chaque_temps(self):
        onsets = [0.1, 0.5, 1.2, 2.1, 2.4, 2.7]
        counts = onsets_per_beat(onsets, self.BEATS)
        # 2 sur le premier temps, 1 sur le deuxieme, 3 sur le troisieme.
        assert counts[:3] == [2.0, 1.0, 3.0]

    def test_borne_basse_incluse_borne_haute_exclue(self):
        assert onsets_per_beat([1.0], self.BEATS)[:2] == [0.0, 1.0]

    def test_aucune_attaque(self):
        assert onsets_per_beat([], self.BEATS)[:3] == [0.0, 0.0, 0.0]

    def test_une_valeur_par_temps(self):
        assert len(onsets_per_beat([0.5, 1.5], self.BEATS)) == len(self.BEATS)


class TestFindAccentBeats:
    def test_liste_vide(self):
        assert find_accent_beats([]) == set()

    def test_intensite_uniforme_aucun_accent(self):
        assert find_accent_beats([5.0] * 32) == set()

    def test_un_pic_isole_est_un_accent(self):
        strengths = [5.0] * 32
        strengths[16] = 50.0
        assert 16 in find_accent_beats(strengths)

    def test_un_pic_modeste_n_est_pas_un_accent(self):
        # 1.2x la mediane, sous le ratio de 1.6 : c'est du bruit, pas un fill.
        strengths = [5.0] * 32
        strengths[16] = 6.0
        assert find_accent_beats(strengths) == set()

    def test_comparaison_locale_et_non_globale(self):
        # Un couplet faible puis un refrain fort. Le fill du couplet (indice 8)
        # est moins intense que le refrain, mais il ressort de SON voisinage :
        # il doit etre detecte, et le refrain ne doit pas l'etre en entier.
        strengths = [2.0] * 32 + [20.0] * 32
        strengths[8] = 8.0

        accents = find_accent_beats(strengths, window=16)

        assert 8 in accents
        assert 40 not in accents

    def test_ratio_eleve_rend_les_accents_plus_rares(self):
        strengths = [5.0] * 32
        for index in (8, 16, 24):
            strengths[index] = 9.0

        permissif = find_accent_beats(strengths, ratio=1.2)
        severe = find_accent_beats(strengths, ratio=3.0)

        assert len(severe) < len(permissif)


class TestVariableGrid:
    BEATS = [0.0, 0.5, 1.0, 1.5]

    def test_moins_de_deux_temps(self):
        assert variable_grid([], set()) == []
        assert variable_grid([0.4], set()) == [0.4]

    def test_sans_accent_grille_reguliere_en_croches(self):
        grid = variable_grid(self.BEATS, set(), base_subdivisions=2)
        assert grid == [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]

    def test_un_intervalle_accentue_est_subdivise_plus_finement(self):
        grid = variable_grid(
            self.BEATS, {1}, base_subdivisions=2, accent_subdivisions=4
        )
        # Intervalle 0 en croches, intervalle 1 en doubles, intervalle 2 en croches.
        assert grid == [0.0, 0.25, 0.5, 0.625, 0.75, 0.875, 1.0, 1.25, 1.5]

    def test_grille_toujours_croissante(self):
        grid = variable_grid(self.BEATS, {0, 2}, base_subdivisions=2)
        assert grid == sorted(grid)

    def test_le_dernier_temps_est_toujours_present(self):
        grid = variable_grid(self.BEATS, set())
        assert grid[-1] == self.BEATS[-1]


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
