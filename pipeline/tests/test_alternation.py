"""Tests de l'alternance des couleurs : contour de piste et plafond de series.

Reference mesuree sur les quatre difficultes officielles de « Haruka Kanata »
(osu!taiko) : serie mediane de 1, maximum de 4 a 5, ratio DON/KA entre 45 et
52 %. C'est la cible de ces deux mecanismes.
"""

from chartgen.notes import cap_same_type_runs, types_from_contour


class TestTypesFromContour:
    def test_liste_vide(self):
        assert types_from_contour([]) == []

    def test_piste_homogene_alterne_quand_meme(self):
        # Une ligne de basse : tout est grave, mais le contour varie. Une
        # comparaison absolue rendrait 100 % de DON.
        energies = [(10.0, 1.0), (10.0, 2.0), (10.0, 3.0), (10.0, 4.0)]
        types = types_from_contour(energies)
        assert set(types) == {"DON", "KA"}

    def test_les_plus_brillantes_deviennent_ka(self):
        energies = [(10.0, 1.0), (1.0, 10.0)]
        assert types_from_contour(energies) == ["DON", "KA"]

    def test_repartition_proche_de_la_moitie(self):
        energies = [(10.0, float(i)) for i in range(1, 21)]
        types = types_from_contour(energies)
        assert abs(types.count("DON") - types.count("KA")) <= 1

    def test_energie_nulle_ne_plante_pas(self):
        assert types_from_contour([(0.0, 0.0), (1.0, 1.0)]) == ["DON", "KA"]

    def test_une_seule_note(self):
        assert types_from_contour([(1.0, 1.0)]) == ["DON"]


class TestCapSameTypeRuns:
    def test_liste_vide(self):
        assert cap_same_type_runs([]) == []

    def test_serie_courte_intouchee(self):
        types = ["DON", "DON", "KA", "DON"]
        assert cap_same_type_runs(types, max_run=4) == types

    def test_serie_a_la_limite_intouchee(self):
        types = ["DON"] * 4
        assert cap_same_type_runs(types, max_run=4) == types

    def test_serie_trop_longue_brisee(self):
        result = cap_same_type_runs(["DON"] * 6, max_run=4)
        assert result == ["DON", "DON", "DON", "DON", "KA", "DON"]

    def test_aucune_serie_ne_depasse_le_plafond(self):
        for max_run in (1, 2, 4, 5):
            result = cap_same_type_runs(["KA"] * 40, max_run=max_run)
            run = best = 1
            for a, b in zip(result[:-1], result[1:]):
                run = run + 1 if a == b else 1
                best = max(best, run)
            assert best <= max_run

    def test_longueur_preservee(self):
        assert len(cap_same_type_runs(["DON"] * 37, max_run=4)) == 37

    def test_plafond_invalide_ne_change_rien(self):
        types = ["DON"] * 10
        assert cap_same_type_runs(types, max_run=0) == types

    def test_n_altere_pas_la_liste_d_entree(self):
        types = ["DON"] * 10
        cap_same_type_runs(types, max_run=2)
        assert types == ["DON"] * 10
