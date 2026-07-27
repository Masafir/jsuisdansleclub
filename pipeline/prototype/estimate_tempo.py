"""Estimation du tempo et de la phase d'un morceau, sans aucune dependance.

Prototype jetable, ecrit pour caler la partition de test du client sur le
`test-song.mp3` avant que le vrai pipeline n'existe. Le pipeline de l'etape 2
fera ce travail avec librosa, bien mieux et sur des morceaux quelconques.

Il est garde ici pour deux raisons : il documente la methode (autocorrelation
d'une fonction d'onset), et il depanne quand on veut caler une partition a la
main sans installer quoi que ce soit. Seul ffmpeg est requis.

Limites connues : l'enveloppe d'energie brute confond facilement un tempo avec
son double ou sa moitie, et un morceau sans percussions marquees donne
n'importe quoi. Un vrai detecteur travaille sur le flux spectral, pas sur
l'energie totale.

Usage :
    python3 estimate_tempo.py ../../client/public/audio/test-song.mp3
"""

import argparse
import array
import subprocess
import sys

SAMPLE_RATE = 8000
FRAME_MS = 10
FRAME_SIZE = SAMPLE_RATE * FRAME_MS // 1000
MIN_BPM = 60
MAX_BPM = 200
# Plage ou l'oreille situe spontanement le tempo d'un morceau dansant. Sert a
# corriger les erreurs d'octave : l'autocorrelation repond aussi fort a la
# moitie et au double du vrai tempo (sur test-song.mp3, elle propose 67.5 BPM
# la ou un humain compte 135).
PREFERRED_MIN_BPM = 90
PREFERRED_MAX_BPM = 180
# Balayage fin autour du candidat grossier : +/- 3 BPM par pas de 0.1.
REFINE_RANGE_BPM = 3.0
REFINE_STEP_BPM = 0.1


def decode_mono_pcm(path: str) -> array.array:
    """Decode un fichier audio en PCM 16 bits mono via ffmpeg."""
    try:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", path,
             "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-"],
            capture_output=True, check=True).stdout
    except FileNotFoundError:
        sys.exit("ffmpeg est introuvable : installe-le (apt install ffmpeg).")
    except subprocess.CalledProcessError as error:
        sys.exit(f"ffmpeg n'a pas pu lire le fichier :\n{error.stderr.decode()}")

    samples = array.array("h")
    samples.frombytes(raw[: len(raw) // 2 * 2])
    return samples


def onset_envelope(samples: array.array) -> list[float]:
    """Fonction d'onset : seules les montees d'energie signalent une attaque."""
    energy = []
    for start in range(0, len(samples) - FRAME_SIZE, FRAME_SIZE):
        total = 0
        for sample in samples[start:start + FRAME_SIZE]:
            total += sample * sample
        energy.append((total / FRAME_SIZE) ** 0.5)

    onset = [max(0.0, energy[i] - energy[i - 1]) for i in range(1, len(energy))]
    mean = sum(onset) / len(onset)
    # Centrer sur zero : sinon l'autocorrelation est dominee par la moyenne et
    # tous les tempos obtiennent a peu pres le meme score.
    return [value - mean for value in onset]


def coarse_tempo(onset: list[float]) -> float:
    """Tempo approximatif, par autocorrelation de la fonction d'onset."""
    frames_per_min = 60_000 / FRAME_MS
    best_score, best_bpm = None, 0.0

    for lag in range(int(frames_per_min / MAX_BPM), int(frames_per_min / MIN_BPM) + 1):
        total = 0.0
        for i in range(len(onset) - lag):
            total += onset[i] * onset[i + lag]
        score = total / (len(onset) - lag)
        if best_score is None or score > best_score:
            best_score, best_bpm = score, frames_per_min / lag

    return fold_into_preferred_range(best_bpm)


def fold_into_preferred_range(bpm: float) -> float:
    """Ramene un tempo dans la plage usuelle en le doublant ou le divisant."""
    while bpm < PREFERRED_MIN_BPM:
        bpm *= 2
    while bpm > PREFERRED_MAX_BPM:
        bpm /= 2
    return bpm


def refine_tempo_and_phase(onset: list[float], bpm_hint: float) -> tuple[float, int]:
    """Affine le tempo et trouve la phase : l'instant du premier temps."""
    steps = int(REFINE_RANGE_BPM / REFINE_STEP_BPM)
    best = None

    for bpm_step in range(-steps, steps + 1):
        bpm = bpm_hint + bpm_step * REFINE_STEP_BPM
        period = 60_000 / bpm / FRAME_MS

        for phase in range(int(period)):
            total = 0.0
            position = float(phase)
            while position < len(onset):
                total += onset[int(position)]
                position += period
            # Normaliser par le nombre de temps, sinon les tempos rapides
            # gagnent mecaniquement (ils cumulent plus de termes).
            beat_count = (len(onset) - phase) / period
            score = total / beat_count
            if best is None or score > best[0]:
                best = (score, bpm, phase * FRAME_MS)

    _, bpm, offset_ms = best
    return bpm, offset_ms


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", help="fichier audio a analyser")
    parser.add_argument("--bpm-hint", type=float,
                        help="tempo suppose, court-circuite la detection grossiere")
    args = parser.parse_args()

    samples = decode_mono_pcm(args.audio)
    onset = onset_envelope(samples)
    duration_ms = (len(onset) + 1) * FRAME_MS

    hint = args.bpm_hint or coarse_tempo(onset)
    bpm, offset_ms = refine_tempo_and_phase(onset, hint)

    print(f"duree  : {duration_ms / 1000:.1f} s")
    print(f"tempo  : {bpm:.1f} BPM")
    print(f"offset : {offset_ms} ms (premier temps)")
    print()
    print("A reporter dans client/src/chart/testChart.ts :")
    print(f"  const TEST_BPM = {round(bpm, 1)};")
    print(f"  const TEST_DURATION_MS = {duration_ms:_};")
    print(f"  const TEST_OFFSET_MS = {offset_ms};")


if __name__ == "__main__":
    main()
