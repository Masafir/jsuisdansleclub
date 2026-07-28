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

# --- Classification DON / KA ----------------------------------------------

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
