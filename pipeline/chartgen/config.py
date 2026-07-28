"""Source unique de verite pour les reglages de generation de partition.

Meme regle que cote client : aucun magic number ailleurs dans le code. C'est ce
fichier qu'on touche pour equilibrer une partition, pas les algorithmes.
"""

from pathlib import Path

# --- Analyse audio ---------------------------------------------------------

#: Frequence d'echantillonnage de travail. 22050 Hz suffit largement : on
#: cherche des attaques, pas de la fidelite. Deux fois moins d'echantillons que
#: 44100 Hz, donc deux fois moins de calcul.
SAMPLE_RATE = 22_050

#: Nombre d'echantillons entre deux trames d'analyse. A 22050 Hz, 512
#: echantillons valent ~23 ms : c'est la resolution temporelle de la detection.
#: Plus petit = plus precis mais plus lent et plus bruite.
HOP_LENGTH = 512

# --- Detection des onsets --------------------------------------------------

#: Sensibilite du seuillage, en nombre d'ecarts-types au-dessus de la moyenne
#: de l'enveloppe. Plus haut = moins de notes, seules les attaques franches
#: passent. C'est le premier bouton a tourner si la partition est trop chargee.
ONSET_SENSITIVITY = 1.2

#: Duree minimale entre deux onsets retenus, en secondes. Evite qu'une seule
#: frappe, dont l'energie s'etale sur plusieurs trames, ne produise une rafale
#: de notes.
ONSET_MIN_GAP_S = 0.09

# --- Analyse par bandes de frequences --------------------------------------

#: Bascule entre l'analyse par bandes (nouvelle) et la detection large bande
#: suivie d'une classification note par note (ancienne). Sert a comparer les
#: deux sur un meme morceau.
USE_BAND_ANALYSIS = True

#: Bandes analysees separement, bornes en Hertz. L'ordre compte : en cas de
#: collision entre deux bandes au meme instant, la premiere l'emporte — le kick
#: est l'ancre rythmique, il doit gagner sur la caisse claire.
BANDS = {
    "LOW": (0.0, 150.0),      # kick, basse
    "MID": (150.0, 2_000.0),  # caisse claire, clap, voix
    "HIGH": (2_000.0, SAMPLE_RATE / 2),  # charleston, cymbales
}

#: Type de note produit par chaque bande. `None` = bande ignoree.
#: Le charleston est ce qui joue le plus vite dans un morceau : le laisser
#: passer inonde la partition, d'ou HIGH ignore par defaut.
BAND_NOTE_TYPE = {"LOW": "DON", "MID": "KA", "HIGH": None}

# --- Grille rythmique ------------------------------------------------------

#: Subdivisions par temps. 4 = doubles-croches, 2 = croches.
#: Plus la valeur est basse, plus les motifs sont reguliers et lents.
BEAT_SUBDIVISIONS = 4

#: Distance maximale a un point de grille pour qu'un onset y soit recale,
#: exprimee en fraction d'un pas de grille. Au-dela, l'onset est jete : c'est
#: un ornement ou du bruit, pas un element de la pulsation.
QUANTIZE_TOLERANCE_RATIO = 0.35

# --- Classification DON / KA (analyse large bande uniquement) ---------------

#: Frontiere entre grave et aigu, en Hertz. En dessous : kick et basse (DON).
#: Au-dessus : caisse claire, charleston, attaques vocales (KA).
FREQUENCY_SPLIT_HZ = 400.0

#: Rapport energie_aigue / energie_grave a partir duquel une attaque est
#: classee KA. Au-dessus de 1, on privilegie le DON en cas d'egalite, ce qui
#: donne des partitions plus lisibles : les KA restent des accents.
KA_ENERGY_RATIO = 1.15

# --- Jouabilite ------------------------------------------------------------

#: Ecart minimum entre deux notes de la partition finale, en secondes.
#: 0.12 s = ~8 notes par seconde au maximum, deja tres soutenu a deux mains.
MIN_NOTE_GAP_S = 0.12

# --- Format de sortie ------------------------------------------------------

#: Doit rester aligne sur CHART_FORMAT_VERSION dans client/src/chart/types.ts.
CHART_FORMAT_VERSION = 1

#: Racine du depot, deduite de l'emplacement de ce fichier :
#: chartgen/config.py -> chartgen -> pipeline -> racine.
REPO_ROOT = Path(__file__).resolve().parents[2]

#: Dossier ou le client va chercher les partitions generees.
#: Chemin absolu, et pas relatif : la CLI doit ecrire au bon endroit quel que
#: soit le dossier depuis lequel on la lance.
CLIENT_CHARTS_DIR = REPO_ROOT / "client" / "public" / "charts"
