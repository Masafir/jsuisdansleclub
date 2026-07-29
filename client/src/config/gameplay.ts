/**
 * Source unique de vérité pour toutes les valeurs de gameplay.
 *
 * RÈGLE DU PROJET : aucun magic number ailleurs dans le code. Toute constante
 * numérique qui influence le jeu vit ici. Pour équilibrer le jeu, on ne touche
 * qu'à ce fichier.
 */

/** Les deux types de notes (format Taiko). */
export const NOTE_TYPES = ['DON', 'KA'] as const;
export type NoteType = (typeof NOTE_TYPES)[number];

/** Résultat du jugement d'une note. */
export const JUDGEMENTS = ['PERFECT', 'GOOD', 'MISS'] as const;
export type Judgement = (typeof JUDGEMENTS)[number];

/** Touches clavier associées à chaque type de note (minuscules). */
export const KEY_BINDINGS: Record<NoteType, readonly string[]> = {
  DON: ['f', 'j'],
  KA: ['d', 'k'],
};

/**
 * Disposition physique des touches sur le clavier, main par main et de gauche
 * à droite : D F  J K.
 *
 * Cet ordre ne se déduit pas de KEY_BINDINGS, qui groupe par type de note
 * (F et J d'un côté, D et K de l'autre) et masque donc le fait que les touches
 * s'entrelacent. Le rappel des touches à l'écran s'appuie sur cette table pour
 * refléter le vrai clavier.
 */
export const KEY_LAYOUT = [
  { hand: 'Main gauche', keys: ['d', 'f'] },
  { hand: 'Main droite', keys: ['j', 'k'] },
] as const;

/** Table inverse touche -> type de note, dérivée de KEY_BINDINGS. */
const KEY_TO_NOTE_TYPE = new Map<string, NoteType>(
  Object.entries(KEY_BINDINGS).flatMap(([type, keys]) =>
    keys.map((key) => [key, type as NoteType] as const),
  ),
);

/** Type de note déclenché par une touche, ou `undefined` si non assignée. */
export function noteTypeForKey(key: string): NoteType | undefined {
  return KEY_TO_NOTE_TYPE.get(key.toLowerCase());
}

/**
 * Fenêtres de jugement, en millisecondes autour du timing idéal de la note.
 * Un écart absolu <= PERFECT_WINDOW_MS vaut PERFECT, sinon <= GOOD_WINDOW_MS
 * vaut GOOD, au-delà c'est MISS.
 */
export const TIMING = {
  PERFECT_WINDOW_MS: 55,
  GOOD_WINDOW_MS: 130,
  /**
   * Au-delà de cet écart, une note n'est plus candidate à un appui : le joueur
   * visait forcément une autre note. Doit être >= GOOD_WINDOW_MS.
   */
  CANDIDATE_WINDOW_MS: 220,
} as const;

/** Points et combo. */
export const SCORING = {
  POINTS: {
    PERFECT: 300,
    GOOD: 100,
    MISS: 0,
  } satisfies Record<Judgement, number>,
  /** Le multiplicateur augmente d'un cran tous les N coups enchaînés. */
  COMBO_STEP: 10,
  /** Gain de multiplicateur par cran. */
  COMBO_BONUS_PER_STEP: 0.1,
  /** Plafond du multiplicateur. */
  MAX_MULTIPLIER: 4,
} as const;

/** Règle de survie : la « danse mortelle ». */
export const SURVIVAL = {
  /** Ratio de réussite minimum à tenir, entre 0 et 1. */
  MIN_SUCCESS_RATIO: 0.5,
  /**
   * Part du morceau pendant laquelle le joueur est immunisé (période de grâce).
   * 1/3 = la vérification ne commence qu'après le premier tiers du morceau.
   */
  GRACE_PERIOD_RATIO: 1 / 3,
  /** Sécurité : pas de game over tant que ce nombre de notes n'a pas été jugé. */
  MIN_JUDGED_NOTES: 10,
} as const;

/** Défilement des notes et rendu. */
export const HIGHWAY = {
  /**
   * Temps que met une note pour traverser l'écran jusqu'à la ligne de jugement.
   * Plus c'est court, plus le jeu paraît rapide et nerveux.
   */
  APPROACH_TIME_MS: 1800,
  /** Position horizontale de la ligne de jugement, en fraction de la largeur. */
  JUDGE_LINE_X_RATIO: 0.15,
  /**
   * Position verticale de chaque lane, en fraction de la hauteur. Format
   * hybride Guitar Hero / taiko : une lane par couleur. Le KA (aigu) est en
   * haut, le DON (grave) en bas — comme les fréquences.
   */
  LANE_Y_RATIOS: { KA: 0.62, DON: 0.84 } satisfies Record<NoteType, number>,
  /** Hauteur d'une bande de jeu, en fraction de la hauteur. */
  LANE_HEIGHT_RATIO: 0.14,
  /** Rayon d'une note, en pixels. */
  NOTE_RADIUS_PX: 28,
  /** Rayon du cercle de la ligne de jugement, en pixels. */
  JUDGE_CIRCLE_RADIUS_PX: 34,
  /** Marge hors écran avant de cesser d'afficher une note, en pixels. */
  CULL_MARGIN_PX: 80,
  /**
   * Halo des notes appartenant à un moment fort. Il rend la montée visible
   * avant qu'elle n'arrive : la difficulté est annoncée, donc préparable.
   */
  ACCENT_HALO_LAYERS: 3,
  /** Élargissement de chaque anneau de halo, en pixels. */
  ACCENT_HALO_STEP_PX: 6,
  /** Opacité de l'anneau le plus intérieur ; les suivants s'estompent. */
  ACCENT_HALO_ALPHA: 0.5,
  /**
   * Marge de sécurité sur la durée de survie d'une note ratée : 1 = elle
   * disparaît pile au bord gauche, 1.5 = elle continue un peu au-delà pour que
   * sa sortie ne se voie pas.
   */
  MISSED_NOTE_LINGER_SAFETY: 1.5,
} as const;

/**
 * Durée pendant laquelle une note ratée continue de défiler après la ligne de
 * jugement, en millisecondes.
 *
 * Déduite de la géométrie de la piste plutôt que fixée à la main : la note met
 * APPROACH_TIME_MS pour parcourir la distance du bord droit à la ligne de
 * jugement, donc proportionnellement moins pour couvrir les
 * JUDGE_LINE_X_RATIO restants jusqu'au bord gauche. Déplacer la ligne de
 * jugement ajuste automatiquement cette durée.
 */
export function missedNoteLingerMs(): number {
  const travelRatio =
    HIGHWAY.JUDGE_LINE_X_RATIO / (1 - HIGHWAY.JUDGE_LINE_X_RATIO);
  return (
    HIGHWAY.APPROACH_TIME_MS * travelRatio * HIGHWAY.MISSED_NOTE_LINGER_SAFETY
  );
}

/**
 * Adaptations tactiles. Sur mobile, le joueur n'a que deux pouces : les quatre
 * touches deviennent deux gros boutons, un par type de note.
 */
export const TOUCH = {
  /**
   * Les pistes remontent pour libérer le bas de l'écran, où se trouvent les
   * boutons — et où se trouvent les pouces.
   */
  LANE_Y_RATIOS: { KA: 0.24, DON: 0.46 } satisfies Record<NoteType, number>,
  /** Hauteur de la zone de boutons, en fraction de la hauteur de l'écran. */
  CONTROLS_HEIGHT_RATIO: 0.34,
} as const;

/**
 * Notes tenues (« slides ») : rester appuyé pendant une envolée du morceau.
 *
 * Règle indulgente, style Guitar Hero : le début se juge comme un tap normal,
 * la tenue rapporte des points au prorata du temps tenu, et relâcher tôt
 * arrête simplement les points — ni MISS, ni combo cassé.
 */
/**
 * Retour visuel d'une tenue en cours : étincelles qui remontent la traîne
 * vers le cercle de jugement (l'énergie se « collecte »), et halo pulsant sur
 * la tête. Sans ça, un hold actif ne se distingue pas d'une simple note
 * étirée — il faut qu'on VOIE que ça tient.
 */
export const HOLD_FX = {
  /** Délai entre deux étincelles générées sur une tenue, en millisecondes. */
  PARTICLE_SPAWN_INTERVAL_MS: 45,
  /**
   * Durée de vie maximale d'une étincelle. Une étincelle meurt avant si elle
   * atteint le cercle de jugement — elle ne le dépasse jamais.
   */
  PARTICLE_LIFETIME_MS: 500,
  /** Rayon d'une étincelle, en pixels. */
  PARTICLE_RADIUS_PX: 4,
  /** Amplitude du tremblement perpendiculaire à la traîne (effet électrique). */
  PARTICLE_JITTER_PX: 9,
  /** Période du tremblement, en millisecondes. */
  PARTICLE_JITTER_PERIOD_MS: 90,
  /**
   * Garde-fou : nombre max d'étincelles vivantes par tenue. Protège d'un
   * empilement si une image a mis longtemps à s'afficher.
   */
  MAX_PARTICLES_PER_HOLD: 20,
  /** Période de la pulsation de la tête pendant la tenue, en millisecondes. */
  HEAD_PULSE_PERIOD_MS: 260,
  /** Amplitude de la pulsation de la tête, en fraction du rayon. */
  HEAD_PULSE_AMPLITUDE: 0.16,
} as const;

export const HOLD = {
  /** Points par seconde de tenue, avant multiplicateur de combo. */
  POINTS_PER_SECOND: 150,
  /**
   * Relâcher dans les dernières millisecondes d'un hold compte comme une tenue
   * complète : exiger la milliseconde exacte serait injouable.
   */
  END_TOLERANCE_MS: 150,
} as const;

/** Retour visuel : pulsations lumineuses à chaque appui. */
export const FEEDBACK = {
  /** Durée d'une pulsation, en millisecondes. */
  PULSE_DURATION_MS: 320,
  /** Facteur d'agrandissement au pic de la pulsation. */
  PULSE_MAX_SCALE: 1.6,
  /** Opacité au départ de la pulsation. */
  PULSE_START_ALPHA: 0.9,
  /** Durée d'affichage du texte de jugement (PERFECT / GOOD / MISS). */
  JUDGEMENT_TEXT_DURATION_MS: 500,
  /**
   * Nombre d'anneaux d'une pulsation GOOD ou MISS. Comme pour le PERFECT, ce
   * sont des cercles évidés : un disque plein masque la note et la ligne de
   * jugement au moment précis où le joueur veut les voir.
   */
  PULSE_RINGS: 2,
  /** Épaisseur d'un anneau de pulsation, en pixels. */
  PULSE_RING_WIDTH_PX: 4,
  /** Écart entre deux anneaux successifs, en fraction du rayon de base. */
  PULSE_RING_SPACING_RATIO: 0.22,
} as const;

/** Style de la ligne de jugement : le cercle que le joueur vise. */
export const JUDGE_CIRCLE = {
  /**
   * Nombre de halos concentriques dessinés autour du cercle. Chacun est plus
   * large et plus transparent que le précédent, ce qui imite une lueur néon
   * sans le coût d'un filtre de flou.
   */
  GLOW_LAYERS: 4,
  /** Épaisseur du trait principal, en pixels. */
  STROKE_WIDTH_PX: 3,
  /** Élargissement de chaque halo successif, en pixels. */
  GLOW_STEP_PX: 5,
  /** Opacité du halo le plus intérieur ; les suivants s'estompent. */
  GLOW_ALPHA: 0.35,
  /** Période de la respiration au repos, en millisecondes. */
  IDLE_PERIOD_MS: 1600,
  /** Amplitude de la respiration, en fraction du rayon. */
  IDLE_SCALE_AMPLITUDE: 0.06,
  /** Grossissement instantané lors d'un appui réussi. */
  HIT_SCALE: 1.25,
  /** Temps de retour à la taille normale après un appui, en millisecondes. */
  HIT_RECOVERY_MS: 220,
} as const;

/** Séquence de démarrage. */
export const COUNTDOWN = {
  /** Nombre de paliers du décompte (3, 2, 1). */
  STEPS: 3,
  /** Durée d'un palier, en millisecondes. */
  STEP_DURATION_MS: 1000,
  /**
   * Marge de sécurité entre l'ordre de départ et le premier échantillon audio.
   * En multijoueur, c'est ce délai qui laisse à tous les clients le temps de
   * programmer leur lecture sur l'horloge partagée.
   */
  SCHEDULE_LEAD_MS: 200,
} as const;

/** Calibration de la latence de sortie audio (casques Bluetooth, etc.). */
export const CALIBRATION = {
  /** Offset par défaut, en millisecondes, tant que le joueur n'a pas calibré. */
  DEFAULT_OFFSET_MS: 0,
  /** Bornes acceptables pour un offset saisi ou mesuré. */
  MIN_OFFSET_MS: -200,
  MAX_OFFSET_MS: 500,
  /** Clé de stockage local de l'offset du joueur. */
  STORAGE_KEY: 'jsuisdansleclub.calibrationOffsetMs',
  /**
   * Écart moyen à partir duquel on propose une correction en fin de partie.
   * En dessous, le décalage se confond avec l'imprécision naturelle du joueur.
   */
  SUGGEST_THRESHOLD_MS: 20,
} as const;

/**
 * Table de mixage. Tous les volumes valent entre 0 (muet) et 1 (plein).
 *
 * Chaque son est multiplié par MASTER, puis par le volume de sa catégorie :
 * baisser MASTER baisse tout, sans toucher à l'équilibre entre la musique et
 * les effets.
 */
export const MIX = {
  /** Volume général, appliqué à tout ce qui sort du jeu. */
  MASTER: 1,
  /** Volume du morceau joué. */
  MUSIC: 0.8,
  /** Volume de chaque effet sonore, réglable indépendamment. */
  SFX: {
    PERFECT: 0.1,
    GOOD: 0.07,
    MISS: 0.1,
  } satisfies Record<Judgement, number>,
} as const;

/** Volume effectif de la musique, une fois le volume général appliqué. */
export function musicVolume(): number {
  return MIX.MASTER * MIX.MUSIC;
}

/** Volume effectif d'un effet sonore, une fois le volume général appliqué. */
export function sfxVolume(judgement: Judgement): number {
  return MIX.MASTER * MIX.SFX[judgement];
}
