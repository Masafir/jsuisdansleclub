"""Assemblage et export d'une partition, au format attendu par le client.

Le contrat est le type `Chart` de client/src/chart/types.ts. Toute evolution
doit rester synchronisee des deux cotes, via CHART_FORMAT_VERSION.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from . import analysis, config, notes, phrases, stems


def build_chart(
    title: str,
    audio_url: str,
    duration_ms: int,
    bpm: float,
    note_list: list[dict],
    offset_ms: int = 0,
) -> dict:
    """Construit le dictionnaire de partition, pret a serialiser."""
    return {
        "version": config.CHART_FORMAT_VERSION,
        "title": title,
        "audioUrl": audio_url,
        "durationMs": duration_ms,
        "bpm": round(bpm, 1),
        "offsetMs": offset_ms,
        "notes": note_list,
    }


def write_chart(chart: dict, path: str | Path) -> Path:
    """Ecrit la partition en JSON et renvoie le chemin du fichier."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(chart, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return destination


def update_index(charts_dir: str | Path, title: str, filename: str) -> Path:
    """Tient a jour l'index que le client lit pour peupler sa bibliotheque.

    Sans lui, le navigateur n'aurait aucun moyen de savoir quelles partitions
    existent : on ne peut pas lister un dossier en HTTP.
    """
    directory = Path(charts_dir)
    directory.mkdir(parents=True, exist_ok=True)
    index_path = directory / "index.json"

    entries = []
    if index_path.exists():
        entries = json.loads(index_path.read_text(encoding="utf-8"))

    entries = [entry for entry in entries if entry["file"] != filename]
    entries.append({"title": title, "file": filename})
    entries.sort(key=lambda entry: entry["title"])

    index_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return index_path


def mark_accent_notes(
    note_list: list[dict], accent_spans_s: list[tuple[float, float]]
) -> list[dict]:
    """Marque les notes tombant dans un moment fort.

    Le client s'en sert pour les auréoler : le joueur voit la relance arriver
    avant de devoir la jouer, ce qui transforme une difficulte subie en montee
    annoncee.
    """
    for note in note_list:
        time_s = note["timeMs"] / 1000
        if any(start <= time_s < end for start, end in accent_spans_s):
            note["accent"] = True
    return note_list


def stem_streams(stem_paths: dict[str, Path]) -> dict[str, list[phrases.Event]]:
    """Un flux d'evenements (instant, intensite, type) par piste separee.

    La batterie isolee repasse par l'analyse par bandes — kick -> DON, caisse
    claire -> KA — qui devient tres propre sans le reste du mix. La basse est
    du DON, la voix du KA, et « le reste » (synthes, guitares, bruits
    insolites) est classe note par note selon son contenu grave/aigu, par la
    fonction ecrite pour l'analyse large bande qui retrouve ici un usage.

    Les intensites sont normalisees par piste : c'est ce qui permet ensuite de
    comparer une note de voix a une note de batterie.
    """
    streams: dict[str, list[phrases.Event]] = {}

    for stem, path in stem_paths.items():
        samples, sample_rate = analysis.load_audio(str(path))
        events: list[phrases.Event] = []

        if stem == "drums":
            envelopes = analysis.onset_envelopes_by_band(samples, sample_rate)
            for band, note_type in (("LOW", "DON"), ("MID", "KA")):
                envelope = envelopes[band]
                times = analysis.detect_onset_times(envelope, sample_rate)
                times = notes.select_strongest(
                    times,
                    analysis.strength_at(envelope, times, sample_rate),
                    config.MIN_NOTE_GAP_S,
                )
                strengths = analysis.normalized_strength_at(envelope, times, sample_rate)
                events += [
                    (time_s, strength, note_type)
                    for time_s, strength in zip(times, strengths)
                ]
        else:
            envelope = analysis.onset_envelope(samples, sample_rate)
            times = analysis.detect_onset_times(envelope, sample_rate)
            times = notes.select_strongest(
                times,
                analysis.strength_at(envelope, times, sample_rate),
                config.MIN_NOTE_GAP_S,
            )
            strengths = analysis.normalized_strength_at(envelope, times, sample_rate)
            if stem == "other":
                types = [
                    notes.classify_note_type(low, high)
                    for low, high in analysis.band_energies_bulk(
                        samples, sample_rate, times
                    )
                ]
            else:
                types = [config.STEM_NOTE_TYPE[stem]] * len(times)
            events = [
                (time_s, strength, note_type)
                for time_s, strength, note_type in zip(times, strengths, types)
            ]

        streams[stem] = sorted(events)

    return streams


def detect_holds(
    stem_paths: dict[str, Path], grid: list[float], tolerance: float
) -> list[tuple[float, float, str]]:
    """Notes tenues : (debut, duree, type), depuis les pistes configurees.

    Une envolee lyrique est un long plateau d'energie sur la piste de voix
    isolee, sans rafale d'attaques dedans (sinon c'est du chant scande). Le
    debut est recale sur la grille rythmique quand elle existe : on part de la
    tenue en rythme.
    """
    holds: list[tuple[float, float, str]] = []

    for stem, note_type in config.HOLD_STEM_NOTE_TYPE.items():
        path = stem_paths.get(stem)
        if path is None:
            continue
        samples, sample_rate = analysis.load_audio(str(path))

        rms = analysis.rms_envelope(samples)
        positive = rms[rms > 0]
        if positive.size == 0:
            continue  # piste muette (instrumental) : rien a tenir
        threshold = float(
            np.percentile(positive, config.HOLD_RMS_PERCENTILE) * config.HOLD_RMS_RATIO
        )

        segments = analysis.sustained_segments(
            rms,
            sample_rate,
            threshold,
            config.HOLD_MIN_DURATION_S,
            config.HOLD_MERGE_GAP_S,
        )

        envelope = analysis.onset_envelope(samples, sample_rate)
        onsets = analysis.detect_onset_times(envelope, sample_rate)
        segments = notes.filter_hold_segments(
            segments, onsets, config.HOLD_MAX_ONSETS_PER_S, config.HOLD_MAX_DURATION_S
        )

        for start, end in segments:
            snapped = analysis.quantize_to_grid([start], grid, tolerance) if grid else []
            begin = snapped[0] if snapped else start
            holds.append((begin, end - begin, note_type))

    return sorted(holds)


def notes_from_stems(
    audio_path: str,
    samples,
    sample_rate: int,
    debug: list[str] | None = None,
) -> tuple[list[float], list[notes.NoteType], list[float], list[tuple[float, float]]]:
    """Analyse « charter » : pistes separees, attention par nouveaute, budget.

    Phrase par phrase (8 temps) :
      1. chaque piste recoit une saillance = activite x nouveaute de son motif ;
      2. la plus saillante devient le lead — ce que le joueur incarne — avec de
         l'hysteresis pour que l'attention ne zappe pas ;
      3. la phrase recoit un budget de notes proportionnel a son intensite
         relative dans le morceau (le contraste) ;
      4. le lead remplit le budget avec ses notes les plus fortes, et une
         ossature de kicks complete si la batterie n'est pas le lead — la
         pulsation ne disparait jamais.
    """
    stem_paths = stems.separate_stems(audio_path)
    streams = stem_streams(stem_paths)

    # Le beat tracking se fait sur le mix complet : plus fiable que sur une
    # piste isolee.
    beats = analysis.beat_times(samples, sample_rate)
    all_onsets = sorted(t for events in streams.values() for t, _, _ in events)
    density = analysis.onsets_per_beat(all_onsets, beats)
    accents = analysis.find_accent_beats(density)
    grid = analysis.variable_grid(beats, accents)
    tolerance = analysis.grid_tolerance_s(grid)

    snapped = {
        stem: phrases.dedupe_events(
            phrases.snap_events(events, grid, tolerance), config.MIN_NOTE_GAP_S
        )
        for stem, events in streams.items()
    }

    spans = phrases.phrase_spans(beats)
    intensities = [
        sum(1 for t in all_onsets if start <= t < end) / (end - start)
        for start, end in spans
    ]
    positive = [value for value in intensities if value > 0]
    median_intensity = float(np.median(positive)) if positive else 0.0

    history: dict[str, list[tuple[int, ...]]] = {stem: [] for stem in snapped}
    lead: str | None = None
    lead_counts: Counter[str] = Counter()
    picked: list[phrases.Event] = []

    for (start, end), intensity in zip(spans, intensities):
        span_s = end - start
        in_span = {
            stem: phrases.events_in_span(events, start, end)
            for stem, events in snapped.items()
        }

        signatures = {
            stem: phrases.pattern_signature(events, start, end)
            for stem, events in in_span.items()
        }
        saliences = {
            stem: phrases.salience(
                len(in_span[stem]), span_s, phrases.novelty(signatures[stem], history[stem])
            )
            for stem in in_span
        }

        lead = phrases.select_lead(saliences, lead)
        budget = phrases.phrase_budget(intensity, median_intensity, span_s)

        lead_events = phrases.pick_top(in_span[lead], budget) if lead else []
        remaining = budget - len(lead_events)
        backbone_pool = (
            []
            if lead == "drums"
            else [event for event in in_span.get("drums", []) if event[2] == "DON"]
        )
        backbone = phrases.pick_top(backbone_pool, remaining)
        picked += phrases.combine_streams(lead_events, backbone, config.MIN_NOTE_GAP_S)

        for stem in history:
            history[stem].append(signatures[stem])
            del history[stem][: -config.NOVELTY_HISTORY_PHRASES]
        if lead is not None:
            lead_counts[lead] += 1

    picked.sort()

    # Notes tenues : les envolees detectees chassent les taps de leur lane sur
    # leur duree (on ne peut pas tenir et frapper de la meme main), puis
    # s'inserent comme notes a duree. L'autre lane garde ses taps : c'est le
    # parallele tenue + frappes du format deux lanes.
    holds = detect_holds(stem_paths, grid, tolerance)
    for _, hold_type in config.HOLD_STEM_NOTE_TYPE.items():
        spans = [(start, start + duration) for start, duration, t in holds if t == hold_type]
        if spans:
            picked = notes.carve_taps_for_holds(
                picked, spans, hold_type, config.MIN_NOTE_GAP_S
            )

    times = [time_s for time_s, _, _ in picked]
    note_types = [note_type for _, _, note_type in picked]
    durations = [0.0] * len(times)
    for start, duration, note_type in holds:
        times.append(start)
        note_types.append(note_type)
        durations.append(duration)

    # Retrier les trois listes ensemble par instant croissant.
    order = sorted(range(len(times)), key=lambda index: times[index])
    times = [times[index] for index in order]
    note_types = [note_types[index] for index in order]
    durations = [durations[index] for index in order]

    accent_spans = [
        (beats[index], beats[index + 1])
        for index in sorted(accents)
        if index + 1 < len(beats)
    ]

    if debug is not None:
        if lead_counts:
            summary = " · ".join(
                f"{stem} {count}" for stem, count in lead_counts.most_common()
            )
            debug.append(
                f"lead par phrase ({sum(lead_counts.values())} phrases) : {summary}"
            )
        debug.append(f"notes tenues : {len(holds)}")

    return times, note_types, durations, accent_spans


def notes_from_bands(
    samples, sample_rate: int
) -> tuple[list[float], list[notes.NoteType], list[tuple[float, float]]]:
    """Analyse par bandes : chaque registre produit son propre type de note."""
    envelopes = analysis.onset_envelopes_by_band(samples, sample_rate)

    # 1. Detecter d'abord, sans grille : c'est le nombre d'attaques par temps
    #    qui va reveler ou se trouvent les moments forts.
    detected: dict[str, list[float]] = {}
    for band, envelope in envelopes.items():
        if config.BAND_NOTE_TYPE.get(band) is None:
            continue  # bande volontairement ignoree (le charleston, par defaut)

        times = analysis.detect_onset_times(envelope, sample_rate)
        raw_strengths = analysis.strength_at(envelope, times, sample_rate)
        detected[band] = notes.select_strongest(
            times, raw_strengths, config.MIN_NOTE_GAP_S
        )

    # 2. Grille a finesse variable : croches en regime normal, doubles-croches
    #    la ou la musique s'emballe. C'est ce qui laisse exister les roulements
    #    sans transformer tout le morceau en soupe.
    grid: list[float] = []
    tolerance = 0.0
    accent_spans: list[tuple[float, float]] = []
    if config.USE_GRID_QUANTIZATION:
        beats = analysis.beat_times(samples, sample_rate)
        all_onsets = sorted(t for times in detected.values() for t in times)
        density = analysis.onsets_per_beat(all_onsets, beats)
        accents = analysis.find_accent_beats(density)
        grid = analysis.variable_grid(beats, accents)
        tolerance = analysis.grid_tolerance_s(grid)
        accent_spans = [
            (beats[index], beats[index + 1])
            for index in sorted(accents)
            if index + 1 < len(beats)
        ]

    # 3. Recaler, puis arbitrer les collisions a l'intensite.
    band_times: dict[str, list[float]] = {}
    band_strengths: dict[str, list[float]] = {}

    for band, times in detected.items():
        final = (
            analysis.quantize_to_grid(times, grid, tolerance)
            if config.USE_GRID_QUANTIZATION
            else times
        )
        band_times[band] = final
        # Normalisees par bande : sans ca, une bande globalement plus energique
        # remporterait tous les arbitrages.
        band_strengths[band] = analysis.normalized_strength_at(
            envelopes[band], final, sample_rate
        )

    times, types = notes.merge_bands(
        band_times, band_strengths, config.MIN_NOTE_GAP_S
    )
    return times, types, accent_spans


def notes_from_full_spectrum(
    samples, sample_rate: int
) -> tuple[list[float], list[notes.NoteType]]:
    """Analyse large bande : une seule detection, type devine note par note.

    Conservee pour comparaison, via config.USE_BAND_ANALYSIS.
    """
    envelope = analysis.onset_envelope(samples, sample_rate)
    onset_times = analysis.detect_onset_times(envelope, sample_rate)
    playable_times = notes.enforce_min_gap(onset_times, config.MIN_NOTE_GAP_S)

    note_types = [
        notes.classify_note_type(*analysis.band_energies(samples, sample_rate, time_s))
        for time_s in playable_times
    ]
    return playable_times, note_types


def generate_chart(
    audio_path: str, title: str, audio_url: str, debug: list[str] | None = None
) -> dict:
    """Chaine complete : un fichier audio en entree, une partition en sortie.

    C'est le seul endroit qui orchestre les etapes ; chacune reste testable
    isolement. L'analyse par pistes separees est preferee ; si demucs manque ou
    echoue, on se replie sur l'analyse par bandes plutot que d'echouer.
    """
    samples, sample_rate = analysis.load_audio(audio_path)

    times: list[float] | None = None
    durations: list[float] | None = None
    if config.USE_STEM_ANALYSIS:
        try:
            times, note_types, durations, accent_spans = notes_from_stems(
                audio_path, samples, sample_rate, debug
            )
        except stems.StemSeparationError as error:
            print(
                f"Separation de pistes indisponible ({error}) : "
                "repli sur l'analyse par bandes.",
                file=sys.stderr,
            )

    if times is None:
        # Les analyses de repli ne produisent pas de notes tenues.
        if config.USE_BAND_ANALYSIS:
            times, note_types, accent_spans = notes_from_bands(samples, sample_rate)
        else:
            times, note_types = notes_from_full_spectrum(samples, sample_rate)
            accent_spans = []

    note_list = mark_accent_notes(
        notes.times_to_notes(times, note_types, durations_s=durations), accent_spans
    )

    return build_chart(
        title=title,
        audio_url=audio_url,
        duration_ms=analysis.duration_ms(samples, sample_rate),
        bpm=analysis.estimate_tempo(samples, sample_rate),
        note_list=note_list,
    )
