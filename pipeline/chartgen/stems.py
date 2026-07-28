"""Separation de sources via demucs, avec cache.

demucs decompose un morceau en quatre pistes : batterie, basse, voix, et « le
reste » (synthes, guitares, bruits insolites). C'est lourd — PyTorch, un modele
telecharge au premier usage, des minutes de CPU par morceau — donc on ne le
paie qu'une fois : les pistes sont cachees sur disque, indexees par empreinte
du fichier audio.

Ce module n'importe pas demucs : il l'invoque en sous-processus. Le pipeline
reste donc importable (et testable) sans lui, et son absence se traduit par une
StemSeparationError que l'appelant rattrape pour se replier sur l'analyse par
bandes.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import config


class StemSeparationError(RuntimeError):
    """demucs indisponible ou en echec. L'appelant peut se replier."""


def audio_fingerprint(path: str | Path) -> str:
    """Empreinte rapide d'un fichier : taille + premier mega-octet.

    Suffisant pour identifier un morceau dans le cache sans lire des dizaines
    de Mo — deux fichiers audio differents qui partageraient taille ET premier
    Mo n'arrivent pas en pratique.
    """
    source = Path(path)
    digest = hashlib.sha256()
    digest.update(str(source.stat().st_size).encode())
    with open(source, "rb") as handle:
        digest.update(handle.read(1 << 20))
    return digest.hexdigest()[:16]


def cached_stem_paths(fingerprint: str) -> dict[str, Path] | None:
    """Pistes deja separees pour cette empreinte, ou None si incompletes."""
    directory = Path(config.STEMS_CACHE_DIR) / fingerprint
    paths = {stem: directory / f"{stem}.wav" for stem in config.STEMS}
    if all(path.exists() for path in paths.values()):
        return paths
    return None


def separate_stems(audio_path: str | Path) -> dict[str, Path]:
    """Separe un morceau en pistes, en passant par le cache.

    Premier appel sur un morceau : plusieurs minutes (et, au tout premier
    usage, le telechargement du modele). Appels suivants : instantane.
    """
    fingerprint = audio_fingerprint(audio_path)
    cached = cached_stem_paths(fingerprint)
    if cached is not None:
        return cached

    target = Path(config.STEMS_CACHE_DIR) / fingerprint

    with tempfile.TemporaryDirectory() as workdir:
        command = [
            sys.executable,
            "-m",
            "demucs",
            "-n",
            config.DEMUCS_MODEL,
            "-o",
            workdir,
            str(audio_path),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError as error:
            raise StemSeparationError("python introuvable pour lancer demucs") from error
        except subprocess.CalledProcessError as error:
            tail = (error.stderr or "").strip().splitlines()[-3:]
            raise StemSeparationError(
                "demucs a echoue : " + " | ".join(tail) if tail else "demucs a echoue"
            ) from error

        produced = Path(workdir) / config.DEMUCS_MODEL / Path(audio_path).stem
        target.mkdir(parents=True, exist_ok=True)
        for stem in config.STEMS:
            source = produced / f"{stem}.wav"
            if not source.exists():
                raise StemSeparationError(f"piste manquante en sortie de demucs : {stem}")
            shutil.move(str(source), target / f"{stem}.wav")

    return {stem: target / f"{stem}.wav" for stem in config.STEMS}
