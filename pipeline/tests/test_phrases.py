"""Tests de la couche « charter » : phrases, nouveaute, lead, budget.

Toutes les fonctions testees sont pures — aucun fichier audio, aucun demucs.
"""

from chartgen.phrases import (
    combine_streams,
    dedupe_events,
    events_in_span,
    novelty,
    pattern_signature,
    phrase_budget,
    phrase_spans,
    pick_top,
    salience,
    select_lead,
    snap_events,
)


def make_events(*times, strength=1.0, note_type="DON"):
    return [(t, strength, note_type) for t in times]


class TestPhraseSpans:
    def test_moins_de_deux_temps(self):
        assert phrase_spans([], 8) == []
        assert phrase_spans([1.0], 8) == []

    def test_decoupe_en_phrases_completes(self):
        beats = [float(i) for i in range(17)]  # 16 intervalles
        assert phrase_spans(beats, 8) == [(0.0, 8.0), (8.0, 16.0)]

    def test_la_derniere_phrase_incomplete_est_conservee(self):
        beats = [float(i) for i in range(12)]  # 11 intervalles
        assert phrase_spans(beats, 8) == [(0.0, 8.0), (8.0, 11.0)]


class TestSnapEvents:
    GRID = [0.0, 0.5, 1.0, 1.5]

    def test_grille_vide(self):
        assert snap_events(make_events(0.5), [], 0.1) == []

    def test_evenement_proche_recale_intensite_et_type_conserves(self):
        events = [(0.53, 2.5, "KA")]
        assert snap_events(events, self.GRID, 0.1) == [(0.5, 2.5, "KA")]

    def test_evenement_loin_de_tout_jete(self):
        assert snap_events(make_events(0.25), self.GRID, 0.1) == []

    def test_resultat_chronologique(self):
        events = [(1.02, 1.0, "DON"), (0.48, 2.0, "KA")]
        snapped = snap_events(events, self.GRID, 0.1)
        assert [event[0] for event in snapped] == [0.5, 1.0]


class TestDedupeEvents:
    def test_la_plus_forte_gagne(self):
        events = [(0.50, 1.0, "DON"), (0.52, 3.0, "KA")]
        assert dedupe_events(events, 0.1) == [(0.52, 3.0, "KA")]

    def test_evenements_espaces_tous_conserves(self):
        events = [(0.0, 1.0, "DON"), (0.5, 2.0, "KA")]
        assert dedupe_events(events, 0.1) == events


class TestPatternSignature:
    def test_phrase_vide(self):
        assert pattern_signature([], 0.0, 4.0, slots=8) == ()

    def test_position_relative_dans_la_phrase(self):
        # Meme motif joue dans deux phrases differentes -> meme signature.
        first = pattern_signature(make_events(0.0, 1.0), 0.0, 4.0, slots=8)
        second = pattern_signature(make_events(8.0, 9.0), 8.0, 12.0, slots=8)
        assert first == second == (0, 2)

    def test_ignore_les_evenements_hors_phrase(self):
        assert pattern_signature(make_events(5.0), 0.0, 4.0, slots=8) == ()


class TestNovelty:
    def test_sans_historique_tout_est_nouveau(self):
        assert novelty((0, 2, 4), []) == 1.0

    def test_motif_identique_novelty_nulle(self):
        assert novelty((0, 2, 4), [(0, 2, 4)]) == 0.0

    def test_motif_proche_novelty_faible(self):
        value = novelty((0, 2, 4), [(0, 2, 6)])
        assert 0.0 < value < 0.8

    def test_motif_disjoint_novelty_maximale(self):
        assert novelty((1, 3), [(0, 2)]) == 1.0

    def test_compare_au_plus_proche_de_l_historique(self):
        # Un motif identique dans l'historique suffit, meme entoure d'autres.
        assert novelty((0, 2), [(1, 3), (0, 2), (4, 6)]) == 0.0


class TestSalience:
    def test_piste_silencieuse_nulle(self):
        assert salience(0, 4.0, 1.0) == 0.0

    def test_active_et_repetitive_bat_le_silence(self):
        repetitive = salience(8, 4.0, 0.0, floor=0.25)
        assert repetitive > 0.0

    def test_la_nouveaute_amplifie(self):
        repetitive = salience(8, 4.0, 0.0, floor=0.25)
        novel = salience(8, 4.0, 1.0, floor=0.25)
        assert novel > repetitive


class TestSelectLead:
    def test_tout_silencieux_pas_de_lead(self):
        assert select_lead({"drums": 0.0, "vocals": 0.0}, None) is None

    def test_le_plus_saillant_gagne(self):
        assert select_lead({"drums": 1.0, "vocals": 3.0}, None) == "vocals"

    def test_hysteresis_le_lead_en_place_resiste(self):
        # vocals est devant, mais pas de 30 % : drums reste lead.
        saliences = {"drums": 1.0, "vocals": 1.2}
        assert select_lead(saliences, "drums", hysteresis=1.3) == "drums"

    def test_un_pretendant_nettement_devant_detrone(self):
        saliences = {"drums": 1.0, "vocals": 2.0}
        assert select_lead(saliences, "drums", hysteresis=1.3) == "vocals"

    def test_un_lead_devenu_silencieux_est_remplace(self):
        saliences = {"drums": 0.0, "vocals": 0.5}
        assert select_lead(saliences, "drums") == "vocals"


class TestPhraseBudget:
    def test_phrase_moyenne_recoit_la_densite_cible(self):
        # 4 s a 2 notes/s de cible = 8 notes.
        assert phrase_budget(3.0, 3.0, 4.0, target_nps=2.0) == 8

    def test_phrase_intense_recoit_plus(self):
        calm = phrase_budget(1.0, 3.0, 4.0, target_nps=2.0)
        intense = phrase_budget(6.0, 3.0, 4.0, target_nps=2.0)
        assert intense > calm

    def test_multiplicateur_borne_en_haut(self):
        budget = phrase_budget(300.0, 1.0, 4.0, target_nps=2.0, max_multiplier=1.5)
        assert budget == round(2.0 * 4.0 * 1.5)

    def test_multiplicateur_borne_en_bas(self):
        budget = phrase_budget(0.01, 10.0, 4.0, target_nps=2.0, min_multiplier=0.5)
        assert budget == round(2.0 * 4.0 * 0.5)

    def test_mediane_nulle_multiplicateur_neutre(self):
        assert phrase_budget(5.0, 0.0, 4.0, target_nps=2.0) == 8


class TestPickTop:
    EVENTS = [(0.0, 1.0, "DON"), (0.5, 3.0, "KA"), (1.0, 2.0, "DON")]

    def test_budget_nul(self):
        assert pick_top(self.EVENTS, 0) == []

    def test_garde_les_plus_forts(self):
        picked = pick_top(self.EVENTS, 2)
        assert [event[1] for event in picked] == [3.0, 2.0]

    def test_resultat_chronologique(self):
        picked = pick_top(self.EVENTS, 2)
        assert [event[0] for event in picked] == [0.5, 1.0]

    def test_budget_superieur_au_nombre_d_evenements(self):
        assert pick_top(self.EVENTS, 10) == sorted(self.EVENTS)


class TestCombineStreams:
    def test_le_primaire_gagne_les_collisions(self):
        lead = [(0.50, 1.0, "KA")]
        backbone = [(0.52, 9.0, "DON")]
        assert combine_streams(lead, backbone, 0.1) == lead

    def test_le_secondaire_comble_les_trous(self):
        lead = [(0.0, 1.0, "KA")]
        backbone = [(1.0, 1.0, "DON")]
        assert combine_streams(lead, backbone, 0.1) == [
            (0.0, 1.0, "KA"),
            (1.0, 1.0, "DON"),
        ]

    def test_events_in_span_bornes(self):
        events = make_events(0.0, 1.0, 2.0)
        assert events_in_span(events, 0.0, 2.0) == make_events(0.0, 1.0)
