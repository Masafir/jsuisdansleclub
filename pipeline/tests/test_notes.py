"""Tests des fonctions pures de conversion en notes."""

import pytest

from chartgen.notes import (
    classify_note_type,
    enforce_min_gap,
    merge_bands,
    select_strongest,
    times_to_notes,
)


class TestEnforceMinGap:
    def test_liste_vide(self):
        assert enforce_min_gap([], 0.1) == []

    def test_un_seul_instant_toujours_conserve(self):
        assert enforce_min_gap([0.42], 0.1) == [0.42]

    def test_instants_suffisamment_espaces_tous_conserves(self):
        times = [0.0, 0.2, 0.4, 0.6]
        assert enforce_min_gap(times, 0.1) == times

    def test_ecart_exactement_egal_au_minimum_accepte(self):
        assert enforce_min_gap([0.0, 0.1], 0.1) == [0.0, 0.1]

    def test_instants_trop_proches_ecartes(self):
        assert enforce_min_gap([0.0, 0.05, 0.09, 0.30], 0.1) == [0.0, 0.30]

    def test_ecart_mesure_depuis_le_dernier_conserve(self):
        # Chaque instant est a 0.06 s du precedent, donc une comparaison de
        # proche en proche les garderait tous. Mesure depuis le dernier
        # conserve, seuls 0.0 et 0.12 passent.
        assert enforce_min_gap([0.0, 0.06, 0.12], 0.1) == [0.0, 0.12]

    def test_n_altere_pas_la_liste_d_entree(self):
        times = [0.0, 0.05, 0.30]
        enforce_min_gap(times, 0.1)
        assert times == [0.0, 0.05, 0.30]


class TestSelectStrongest:
    def test_listes_vides(self):
        assert select_strongest([], [], 0.1) == []

    def test_un_seul_instant_conserve(self):
        assert select_strongest([0.5], [3.0], 0.1) == [0.5]

    def test_instants_espaces_tous_conserves(self):
        times = [0.0, 0.5, 1.0]
        assert select_strongest(times, [1.0, 1.0, 1.0], 0.1) == times

    def test_garde_la_plus_forte_et_non_la_plus_precoce(self):
        # 0.00 arrive en premier mais 0.05 frappe deux fois plus fort :
        # c'est la vraie attaque, la premiere n'est qu'une pre-echo.
        assert select_strongest([0.00, 0.05], [1.0, 2.0], 0.1) == [0.05]

    def test_ecarte_tout_un_groupe_au_profit_du_maximum(self):
        times = [0.00, 0.04, 0.08, 0.50]
        strengths = [1.0, 5.0, 2.0, 1.0]
        assert select_strongest(times, strengths, 0.1) == [0.04, 0.50]

    def test_ecart_exactement_egal_au_minimum_accepte(self):
        assert select_strongest([0.0, 0.1], [1.0, 2.0], 0.1) == [0.0, 0.1]

    def test_resultat_trie_par_temps_croissant(self):
        # Les plus fortes sont traitees d'abord, mais la sortie est chronologique.
        times = [0.0, 0.5, 1.0]
        strengths = [1.0, 3.0, 2.0]
        assert select_strongest(times, strengths, 0.1) == [0.0, 0.5, 1.0]

    def test_longueurs_incoherentes_levent_une_erreur(self):
        with pytest.raises(ValueError):
            select_strongest([0.0, 1.0], [1.0], 0.1)


class TestMergeBands:
    def test_dictionnaire_vide(self):
        assert merge_bands({}, {}, 0.1) == ([], [])

    def test_bande_grave_donne_des_don(self):
        times, types = merge_bands({"LOW": [0.0, 0.5]}, {"LOW": [1.0, 1.0]}, 0.1)
        assert times == [0.0, 0.5]
        assert types == ["DON", "DON"]

    def test_bande_medium_donne_des_ka(self):
        times, types = merge_bands({"MID": [0.25]}, {"MID": [1.0]}, 0.1)
        assert types == ["KA"]

    def test_bande_ignoree_ne_produit_rien(self):
        # HIGH vaut None dans BAND_NOTE_TYPE : le charleston est ecarte.
        band_times = {"HIGH": [0.0, 0.1, 0.2]}
        band_strengths = {"HIGH": [5.0, 5.0, 5.0]}
        assert merge_bands(band_times, band_strengths, 0.1) == ([], [])

    def test_bandes_entrelacees_dans_l_ordre_chronologique(self):
        times, types = merge_bands(
            {"LOW": [0.0, 1.0], "MID": [0.5]},
            {"LOW": [1.0, 1.0], "MID": [1.0]},
            0.1,
        )
        assert times == [0.0, 0.5, 1.0]
        assert types == ["DON", "KA", "DON"]

    def test_collision_la_plus_forte_l_emporte(self):
        # Caisse claire qui claque contre kick discret : la snare gagne, meme
        # si le grave est prioritaire dans config.BANDS.
        times, types = merge_bands(
            {"LOW": [0.50], "MID": [0.52]},
            {"LOW": [1.0], "MID": [3.0]},
            0.1,
        )
        assert times == [0.52]
        assert types == ["KA"]

    def test_collision_le_grave_gagne_quand_il_est_plus_fort(self):
        times, types = merge_bands(
            {"LOW": [0.50], "MID": [0.52]},
            {"LOW": [4.0], "MID": [1.0]},
            0.1,
        )
        assert times == [0.50]
        assert types == ["DON"]

    def test_egalite_parfaite_departagee_par_l_ordre_des_bandes(self):
        times, types = merge_bands(
            {"LOW": [0.50], "MID": [0.52]},
            {"LOW": [2.0], "MID": [2.0]},
            0.1,
        )
        assert types == ["DON"]

    def test_resultat_independant_de_l_ordre_des_cles(self):
        arguments = ({"MID": [0.52], "LOW": [0.50]}, {"MID": [3.0], "LOW": [1.0]}, 0.1)
        assert merge_bands(*arguments) == ([0.52], ["KA"])

    def test_bande_vide_sans_effet(self):
        times, types = merge_bands({"LOW": [], "MID": [0.3]}, {"LOW": [], "MID": [1.0]}, 0.1)
        assert times == [0.3]
        assert types == ["KA"]

    def test_notes_suffisamment_espacees_toutes_conservees(self):
        times, types = merge_bands(
            {"LOW": [0.0], "MID": [0.5]}, {"LOW": [1.0], "MID": [1.0]}, 0.1
        )
        assert times == [0.0, 0.5]
        assert types == ["DON", "KA"]

    def test_intensites_incoherentes_levent_une_erreur(self):
        with pytest.raises(ValueError):
            merge_bands({"LOW": [0.0, 0.5]}, {"LOW": [1.0]}, 0.1)


class TestClassifyNoteType:
    def test_grave_dominant_donne_don(self):
        assert classify_note_type(low_energy=10.0, high_energy=1.0) == "DON"

    def test_aigu_franchement_dominant_donne_ka(self):
        assert classify_note_type(low_energy=1.0, high_energy=10.0) == "KA"

    def test_egalite_donne_don(self):
        # Le facteur etant > 1, le DON gagne les cas ambigus.
        assert classify_note_type(low_energy=5.0, high_energy=5.0) == "DON"

    def test_aigu_juste_sous_le_seuil_donne_don(self):
        assert classify_note_type(
            low_energy=10.0, high_energy=11.0, ka_ratio=1.15
        ) == "DON"

    def test_aigu_juste_au_dessus_du_seuil_donne_ka(self):
        assert classify_note_type(
            low_energy=10.0, high_energy=11.6, ka_ratio=1.15
        ) == "KA"

    def test_absence_de_grave_ne_leve_pas_d_erreur(self):
        # Passage sans basses : une division high/low planterait ici.
        assert classify_note_type(low_energy=0.0, high_energy=3.0) == "KA"

    def test_silence_complet_donne_don(self):
        assert classify_note_type(low_energy=0.0, high_energy=0.0) == "DON"


class TestTimesToNotes:
    def test_conversion_en_millisecondes_entieres(self):
        result = times_to_notes([0.0, 1.5], ["DON", "KA"])
        assert result == [
            {"timeMs": 0, "type": "DON"},
            {"timeMs": 1500, "type": "KA"},
        ]

    def test_arrondi_au_millieme_de_seconde(self):
        result = times_to_notes([0.2324], ["DON"])
        assert result[0]["timeMs"] == 232

    def test_offset_applique_a_toutes_les_notes(self):
        result = times_to_notes([0.0, 1.0], ["DON", "DON"], offset_ms=50)
        assert [note["timeMs"] for note in result] == [50, 1050]

    def test_resultat_trie_par_temps_croissant(self):
        result = times_to_notes([2.0, 0.5, 1.0], ["DON", "KA", "DON"])
        assert [note["timeMs"] for note in result] == [500, 1000, 2000]
        # Le type doit suivre son instant, pas rester a sa position d'origine.
        assert result[0]["type"] == "KA"

    def test_longueurs_incoherentes_levent_une_erreur(self):
        with pytest.raises(ValueError):
            times_to_notes([0.0, 1.0], ["DON"])

    def test_listes_vides(self):
        assert times_to_notes([], []) == []
