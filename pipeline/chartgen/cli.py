"""Point d'entree en ligne de commande.

    python -m chartgen client/public/audio/test-song.mp3 --title "Mon morceau"

Ecrit la partition dans client/public/charts/ et affiche un resume : nombre de
notes, densite, repartition DON / KA. Ces trois chiffres suffisent en general a
savoir si un reglage de config.py va dans le bon sens.

Utilise --new-gen pour tester la nouvelle pipeline (HPSS, grille adaptive, structure).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import quote

from . import chart as chart_module
from . import config


def slugify(name: str) -> str:
    """Nom de fichier sur, derive d'un titre.

    Les titres viennent souvent de noms de fichiers du genre
    « Cody Currie - No Ice », donc pleins d'espaces et de tirets : on ecrase
    toute suite de caracteres non alphanumeriques en un seul tiret.
    """
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def summarize(chart: dict) -> str:
    """Resume lisible d'une partition generee."""
    note_list = chart["notes"]
    if not note_list:
        return "Aucune note generee — la sensibilite est probablement trop haute."

    duration_s = chart["durationMs"] / 1000
    don = sum(1 for note in note_list if note["type"] == "DON")
    ka = len(note_list) - don

    return (
        f"{len(note_list)} notes sur {duration_s:.0f} s "
        f"({len(note_list) / duration_s:.1f} par seconde)\n"
        f"  DON {don} · KA {ka}\n"
        f"  tempo estime {chart['bpm']} BPM"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", help="fichier audio a analyser")
    parser.add_argument("--title", help="titre affiche en jeu")
    parser.add_argument(
        "--out",
        help=f"chemin du JSON produit (defaut : {config.CLIENT_CHARTS_DIR}/<titre>.json)",
    )
    parser.add_argument(
        "--new-gen",
        action="store_true",
        help="utilise la nouvelle pipeline (HPSS, grille adaptive, structure guidee)",
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="force l'ancienne pipeline (defaut si --new-gen absent)",
    )
    args = parser.parse_args(argv)

    # Mode generation
    if args.new_gen and args.legacy:
        print("Erreur : --new-gen et --legacy sont mutuellement exclusifs", file=sys.stderr)
        return 1
    use_new_gen = args.new_gen

    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"Fichier introuvable : {audio_path}", file=sys.stderr)
        return 1

    # Sans --title, le nom du fichier fait le titre : "Cody Currie - No Ice.mp3"
    # donne "Cody Currie - No Ice".
    title = args.title or audio_path.stem

    # Le client sert public/ a la racine : public/audio/x.mp3 devient /audio/x.mp3.
    # `quote` encode les espaces et accents des noms de fichiers, sans quoi l'URL
    # serait invalide.
    audio_url = f"/audio/{quote(audio_path.name)}"

    # Applique la config selon le mode
    if use_new_gen:
        # Active les nouveaux parametres
        config.USE_BAND_ANALYSIS = True
        config.USE_STEM_ANALYSIS = True
        config.USE_GRID_QUANTIZATION = True
        # La liste vit dans config.NEW_GEN_FLAGS : la recopier ici exposait a
        # en oublier une, et une etape manquante ne se voit nulle part.
        for flag in config.NEW_GEN_FLAGS:
            setattr(config, flag, True)
        suffix = "-newgen"
    else:
        suffix = ""

    debug: list[str] = []
    chart = chart_module.generate_chart(
        str(audio_path), title, audio_url, debug=debug, use_new_gen=use_new_gen
    )

    filename = f"{slugify(title)}{suffix}.json"
    destination = Path(args.out) if args.out else Path(config.CLIENT_CHARTS_DIR) / filename
    written = chart_module.write_chart(chart, destination)

    print(summarize(chart))
    for line in debug:
        print(f"  {line}")
    print(f"\nPartition ecrite : {written}")

    # L'index n'a de sens que dans le dossier servi par le client.
    if args.out is None:
        chart_module.update_index(config.CLIENT_CHARTS_DIR, title, filename)
        print("Index de la bibliotheque mis a jour.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
