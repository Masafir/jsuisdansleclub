"""Tests de top_up : combler le budget d'une phrase avec un pool de secours."""

from chartgen.phrases import top_up


class TestTopUp:
    def test_budget_deja_atteint_pool_ignore(self):
        picked = [(0.0, 1.0, "DON"), (0.5, 1.0, "KA")]
        pool = [(0.25, 5.0, "KA")]
        assert top_up(picked, pool, budget=2, min_gap_s=0.1) == picked

    def test_pool_vide_ne_change_rien(self):
        picked = [(0.0, 1.0, "DON")]
        assert top_up(picked, [], budget=5, min_gap_s=0.1) == picked

    def test_complete_avec_les_plus_forts_du_pool(self):
        picked = [(0.0, 1.0, "DON")]
        pool = [(1.0, 2.0, "KA"), (2.0, 5.0, "KA"), (3.0, 1.0, "DON")]
        result = top_up(picked, pool, budget=3, min_gap_s=0.1)
        assert (0.0, 1.0, "DON") in result
        assert (2.0, 5.0, "KA") in result  # le plus fort du pool
        assert (1.0, 2.0, "KA") in result
        assert (3.0, 1.0, "DON") not in result  # budget atteint avant

    def test_picked_jamais_rogne_meme_si_le_pool_est_plus_fort(self):
        picked = [(0.0, 1.0, "DON")]
        pool = [(5.0, 99.0, "KA")]
        result = top_up(picked, pool, budget=1, min_gap_s=0.1)
        assert (0.0, 1.0, "DON") in result

    def test_collision_avec_picked_le_complement_cede(self):
        picked = [(1.0, 1.0, "DON")]
        pool = [(1.02, 5.0, "KA")]  # trop pres de la note deja retenue
        result = top_up(picked, pool, budget=5, min_gap_s=0.1)
        assert result == picked

    def test_resultat_chronologique(self):
        picked = [(3.0, 1.0, "DON")]
        pool = [(1.0, 2.0, "KA")]
        result = top_up(picked, pool, budget=2, min_gap_s=0.1)
        assert result == sorted(result)
