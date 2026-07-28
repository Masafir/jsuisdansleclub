"""Assemblage et export d'une partition, au format attendu par le client.

Le contrat est le type `Chart` de client/src/chart/types.ts. Toute evolution
doit rester synchronisee des deux cotes, via CHART_FORMAT_VERSION.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import analysis, config, notes


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


def generate_chart(audio_path: str, title: str, audio_url: str) -> dict:
    """Chaine complete : un fichier audio en entree, une partition en sortie.

    C'est le seul endroit qui orchestre les etapes ; chacune reste testable
    isolement.
    """
    samples, sample_rate = analysis.load_audio(audio_path)

    if config.USE_BAND_ANALYSIS:
        times, note_types, accent_spans = notes_from_bands(samples, sample_rate)
    else:
        times, note_types = notes_from_full_spectrum(samples, sample_rate)
        accent_spans = []

    note_list = mark_accent_notes(
        notes.times_to_notes(times, note_types), accent_spans
    )

    return build_chart(
        title=title,
        audio_url=audio_url,
        duration_ms=analysis.duration_ms(samples, sample_rate),
        bpm=analysis.estimate_tempo(samples, sample_rate),
        note_list=note_list,
    )
