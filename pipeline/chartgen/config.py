"""Source unique de verite pour les reglages de generation de partition.

Meme regle que cote client : aucun magic number ailleurs dans le code. C'est ce
fichier qu'on touche pour equilibrer une partition, pas les algorithmes.
"""

from pathlib import Path

#: Racine du depot, deduite de l'emplacement de ce fichier :
#: chartgen/config.py -> chartgen -> pipeline -> racine.
REPO_ROOT = Path(__file__).resolve().parents[2]

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
#: passent.
#:
#: ATTENTION : ce n'est PAS le bon bouton pour alleger une partition. Monter la
#: sensibilite retire des notes au milieu de suites regulieres et casse les
#: motifs : mesure sur deux morceaux, passer de 1.2 a 1.8 fait tomber la part du
#: motif dominant de 71 % a 53 %. Pour alleger, baisser BEAT_SUBDIVISIONS.
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

# --- Separation de sources (demucs) ----------------------------------------

#: Analyse par pistes separees : le morceau est decompose en batterie, basse,
#: voix et « le reste », et une couche « charter » choisit quelle piste le
#: joueur incarne a chaque phrase. Si demucs n'est pas installe ou echoue, le
#: pipeline se rabat automatiquement sur l'analyse par bandes.
USE_STEM_ANALYSIS = True

#: Modele demucs. htdemucs est le defaut actuel du projet demucs, bon
#: compromis qualite/temps sur CPU.
DEMUCS_MODEL = "htdemucs"

#: Les quatre pistes produites par demucs, dans un ordre stable.
STEMS = ("drums", "bass", "vocals", "other")

#: Type de note produit par les pistes homogenes. La batterie n'y figure pas
#: (elle repasse par l'analyse par bandes : kick -> DON, caisse claire -> KA),
#: ni « other » (classe note par note selon son contenu grave/aigu).
STEM_NOTE_TYPE = {"bass": "DON", "vocals": "KA"}

#: Cache des pistes separees. La separation coute des minutes de CPU : on ne la
#: paie qu'une fois par morceau. data/ est deja hors du depot git.
STEMS_CACHE_DIR = REPO_ROOT / "data" / "stems"

# --- Phrases, attention et budget -------------------------------------------

#: Longueur d'une phrase, en temps. 8 temps = 2 mesures en 4/4 : l'unite de
#: pensee des charters humains et de la dance music.
PHRASE_BEATS = 8

#: Densite moyenne visee, en notes par seconde. C'est LE levier principal de
#: difficulte : le budget de chaque phrase en decoule.
TARGET_NOTES_PER_SECOND = 1.8

#: Bornes du multiplicateur de budget selon l'intensite relative de la phrase.
#: Une phrase calme peut descendre a 40 % de la densite cible, une phrase
#: intense monter a 170 % : c'est le contraste qui fabrique les pics.
BUDGET_MIN_MULTIPLIER = 0.4
BUDGET_MAX_MULTIPLIER = 1.7

#: Resolution du motif rythmique d'une phrase, en cases. 16 cases sur 8 temps
#: = la croche, notre subdivision de base.
PATTERN_SLOTS_PER_PHRASE = 16

#: Nombre de phrases passees contre lesquelles la nouveaute d'un motif est
#: evaluee. Au-dela, un motif oublie redevient interessant — comme pour
#: l'auditeur.
NOVELTY_HISTORY_PHRASES = 8

#: Plancher de saillance d'une piste active mais repetitive : elle doit rester
#: devant une piste silencieuse.
NOVELTY_FLOOR = 0.25

#: Un pretendant doit depasser le lead en place de ce facteur pour le detroner.
#: L'attention humaine est stable par phrases ; un chart qui zappe est
#: illisible.
LEAD_HYSTERESIS = 1.3

# --- Notes tenues (holds) ---------------------------------------------------

#: Pistes sondees pour les tenues, et le type de note produit. La voix tenue
#: (envolee lyrique) donne un hold KA ; ajouter {"bass": "DON"} pour tenir les
#: nappes de basse.
HOLD_STEM_NOTE_TYPE = {"vocals": "KA"}

#: Duree minimale d'une tenue, en secondes. En dessous, c'est une syllabe
#: longue, pas une envolee.
HOLD_MIN_DURATION_S = 1.2

#: Duree maximale, en secondes : au-dela on tronque — tenir plus longtemps
#: n'est plus du jeu, c'est de l'attente.
HOLD_MAX_DURATION_S = 6.0

#: Deux segments tenus separes par un trou plus court que ceci fusionnent :
#: une respiration au milieu d'une envolee n'en fait pas deux.
HOLD_MERGE_GAP_S = 0.3

#: Seuil d'activite : fraction du percentile d'energie de la piste. La voix
#: isolee est silencieuse entre les phrases, ce qui rend ce seuil tres net.
HOLD_RMS_RATIO = 0.35
HOLD_RMS_PERCENTILE = 90

#: Au-dela de cette densite d'attaques (par seconde) dans le segment, ce n'est
#: pas une tenue mais une phrase rythmique (du chant scande, du rap).
HOLD_MAX_ONSETS_PER_S = 2.0

# --- Grille rythmique ------------------------------------------------------

#: Subdivisions par temps en regime normal. 2 = croches.
#:
#: Mesure a l'appui : en doubles-croches partout, l'ecart le plus frequent entre
#: deux notes ne represente que 29 % des ecarts — les notes tombent sur la
#: grille mais a des positions arbitraires, et la main ne prend jamais le pli.
#: En croches, ce chiffre monte a 71 % pour un nombre de notes identique.
#: C'est la regularite qui rend une partition agreable, pas la densite.
BEAT_SUBDIVISIONS = 2

#: Subdivisions sur les temps marques comme moments forts. 4 = doubles-croches.
#: C'est ce qui permet aux roulements de batterie et aux relances de guitare
#: d'exister, sans transformer tout le morceau en soupe.
ACCENT_SUBDIVISIONS = 4

#: Un temps est un moment fort si son intensite depasse la mediane locale de ce
#: facteur. Monter la valeur rend les moments forts plus rares et plus marques.
ACCENT_RATIO = 1.6

#: Nombre de temps sur lesquels la mediane locale est calculee. Une fenetre
#: large compare un temps a la section entiere, une fenetre etroite a son
#: voisinage immediat. 16 temps valent environ 4 mesures.
ACCENT_WINDOW_BEATS = 16

#: Recalage sur la grille rythmique. A desactiver si `beat_track` se trompe de
#: tempo sur un morceau : la grille serait alors fausse, et recaler dessus ferait
#: plus de mal que de bien. Le tempo estime est affiche a chaque generation,
#: c'est lui qui permet de s'en rendre compte.
USE_GRID_QUANTIZATION = True

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

#: Dossier ou le client va chercher les partitions generees.
#: Chemin absolu, et pas relatif : la CLI doit ecrire au bon endroit quel que
#: soit le dossier depuis lequel on la lance.
CLIENT_CHARTS_DIR = REPO_ROOT / "client" / "public" / "charts"
