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
 * Fenêtres de jugement, en millisecondes autour du timing idéal de la note.
 * Un écart absolu <= PERFECT_WINDOW_MS vaut PERFECT, sinon <= GOOD_WINDOW_MS
 * vaut GOOD, au-delà c'est MISS.
 */
export const TIMING = {
  PERFECT_WINDOW_MS: 40,
  GOOD_WINDOW_MS: 90,
  /**
   * Au-delà de cet écart, une note n'est plus candidate à un appui : le joueur
   * visait forcément une autre note. Doit être >= GOOD_WINDOW_MS.
   */
  CANDIDATE_WINDOW_MS: 150,
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
  /** Position verticale de la lane, en fraction de la hauteur. */
  LANE_Y_RATIO: 0.78,
  /** Hauteur de la bande de jeu, en fraction de la hauteur. */
  LANE_HEIGHT_RATIO: 0.16,
  /** Rayon d'une note, en pixels. */
  NOTE_RADIUS_PX: 28,
  /** Rayon du cercle de la ligne de jugement, en pixels. */
  JUDGE_CIRCLE_RADIUS_PX: 34,
  /** Marge hors écran avant de cesser d'afficher une note, en pixels. */
  CULL_MARGIN_PX: 80,
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
} as const;

/** Volumes des effets sonores, entre 0 et 1. */
export const SFX = {
  VOLUME: {
    PERFECT: 0.8,
    GOOD: 0.6,
    MISS: 0.5,
  } satisfies Record<Judgement, number>,
} as const;
