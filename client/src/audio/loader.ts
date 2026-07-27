/**
 * Chargement et décodage de l'audio.
 *
 * Principe d'architecture (voir DECISIONS.md) : on télécharge et décode le
 * morceau **en entier** avant de jouer. On ne streame jamais — c'est ce qui
 * permet le démarrage à l'échantillon près, et plus tard le départ simultané
 * entre tous les joueurs d'une room.
 */

export class AudioLoadError extends Error {}

/** Contexte audio partagé. Un seul par page : les navigateurs les limitent. */
let sharedContext: AudioContext | null = null;

export function getAudioContext(): AudioContext {
  sharedContext ??= new AudioContext();
  return sharedContext;
}

/**
 * Les navigateurs démarrent l'AudioContext en état « suspended » tant que
 * l'utilisateur n'a pas interagi avec la page. À appeler depuis un gestionnaire
 * de clic, sinon rien ne sortira des enceintes.
 */
export async function unlockAudioContext(): Promise<void> {
  const ctx = getAudioContext();
  if (ctx.state === 'suspended') {
    await ctx.resume();
  }
}

/** Télécharge puis décode un fichier audio en mémoire. */
export async function loadAudioBuffer(url: string): Promise<AudioBuffer> {
  let response: Response;
  try {
    response = await fetch(url);
  } catch (cause) {
    throw new AudioLoadError(`Impossible de télécharger l'audio : ${url}`, {
      cause,
    });
  }
  if (!response.ok) {
    throw new AudioLoadError(
      `Impossible de télécharger l'audio (${response.status}) : ${url}`,
    );
  }

  const encoded = await response.arrayBuffer();
  try {
    return await getAudioContext().decodeAudioData(encoded);
  } catch (cause) {
    throw new AudioLoadError(`Format audio non décodable : ${url}`, { cause });
  }
}

/**
 * Charge les effets sonores. Un SFX manquant n'est pas bloquant : le jeu doit
 * rester jouable sans, on renvoie simplement `null` pour celui-ci.
 */
export async function loadOptionalAudioBuffer(
  url: string,
): Promise<AudioBuffer | null> {
  try {
    return await loadAudioBuffer(url);
  } catch {
    return null;
  }
}
