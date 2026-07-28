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


def generate_chart(audio_path: str, title: str, audio_url: str) -> dict:
    """Chaine complete : un fichier audio en entree, une partition en sortie.

    C'est le seul endroit qui orchestre les etapes ; chacune reste testable
    isolement.
    """
    samples, sample_rate = analysis.load_audio(audio_path)

    envelope = analysis.onset_envelope(samples, sample_rate)
    onset_times = analysis.detect_onset_times(envelope, sample_rate)
    playable_times = notes.enforce_min_gap(onset_times, config.MIN_NOTE_GAP_S)

    note_types = [
        notes.classify_note_type(
            *analysis.band_energies(samples, sample_rate, time_s)
        )
        for time_s in playable_times
    ]

    return build_chart(
        title=title,
        audio_url=audio_url,
        duration_ms=analysis.duration_ms(samples, sample_rate),
        bpm=analysis.estimate_tempo(samples, sample_rate),
        note_list=notes.times_to_notes(playable_times, note_types),
    )
