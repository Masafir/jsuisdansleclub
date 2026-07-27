import { describe, expect, it } from 'vitest';
import { ClockNotStartedError, SongClock } from './clock';

/** Horloge simulée : on pilote le temps à la main, en secondes. */
function fakeClock(calibrationOffsetMs = 0) {
  let nowSec = 0;
  const clock = new SongClock({
    now: () => nowSec,
    calibrationOffsetMs,
  });
  return {
    clock,
    setNowSec: (value: number) => {
      nowSec = value;
    },
  };
}

describe('SongClock', () => {
  it("lève une erreur tant que le départ n'a pas été programmé", () => {
    const { clock } = fakeClock();
    expect(clock.isStarted).toBe(false);
    expect(() => clock.getSongTimeMs()).toThrow(ClockNotStartedError);
  });

  it('vaut 0 à l’instant exact du départ', () => {
    const { clock, setNowSec } = fakeClock();
    setNowSec(10);
    clock.start(10);
    expect(clock.isStarted).toBe(true);
    expect(clock.getSongTimeMs()).toBe(0);
  });

  it('convertit les secondes écoulées en millisecondes', () => {
    const { clock, setNowSec } = fakeClock();
    setNowSec(10);
    clock.start(10);

    setNowSec(10.5);
    expect(clock.getSongTimeMs()).toBe(500);

    setNowSec(13.25);
    expect(clock.getSongTimeMs()).toBe(3250);
  });

  it('renvoie un temps négatif pendant le décompte (départ dans le futur)', () => {
    const { clock, setNowSec } = fakeClock();
    setNowSec(10);
    clock.start(13); // départ programmé 3 s plus tard

    expect(clock.getSongTimeMs()).toBe(-3000);
    setNowSec(12);
    expect(clock.getSongTimeMs()).toBe(-1000);
    setNowSec(13);
    expect(clock.getSongTimeMs()).toBe(0);
  });

  it('applique le décalage de départ pour un joueur qui rejoint en cours', () => {
    const { clock, setNowSec } = fakeClock();
    setNowSec(10);
    clock.start(10, 42_000); // le morceau en est déjà à 42 s

    expect(clock.getSongTimeMs()).toBe(42_000);
    setNowSec(11);
    expect(clock.getSongTimeMs()).toBe(43_000);
  });

  it('retire la latence de sortie du joueur pour juger ses appuis', () => {
    const { clock, setNowSec } = fakeClock(200); // casque Bluetooth : 200 ms
    setNowSec(10);
    clock.start(10);
    setNowSec(10.5);

    expect(clock.getSongTimeMs()).toBe(500);
    expect(clock.getInputTimeMs()).toBe(300);
  });

  it('laisse le temps de jeu inchangé quand la calibration est nulle', () => {
    const { clock, setNowSec } = fakeClock(0);
    setNowSec(0);
    clock.start(0);
    setNowSec(2);

    expect(clock.getInputTimeMs()).toBe(clock.getSongTimeMs());
  });

  it('redevient non démarrée après reset()', () => {
    const { clock, setNowSec } = fakeClock();
    setNowSec(5);
    clock.start(5);
    clock.reset();

    expect(clock.isStarted).toBe(false);
    expect(() => clock.getSongTimeMs()).toThrow(ClockNotStartedError);
  });
});
