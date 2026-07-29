import { useCallback, useEffect, useRef, useState, type CSSProperties } from 'react';
import { HighwayRenderer } from '../render/highway';
import { GameSession, type SessionSnapshot } from '../game/session';
import { HIGHWAY, SURVIVAL, TOUCH, type NoteType } from '../config/gameplay';
import { readCalibrationOffsetMs } from '../game/calibration';
import type { Chart } from '../chart/types';
import { Hud } from './Hud';
import { KeyLegend } from './KeyLegend';
import { TouchControls } from './TouchControls';
import { useTouchDevice } from './useTouchDevice';

interface GameScreenProps {
  chart: Chart;
  onFinished: (snapshot: SessionSnapshot) => void;
  onQuit: () => void;
}

export function GameScreen({ chart, onFinished, onQuit }: GameScreenProps) {
  const canvasHost = useRef<HTMLDivElement>(null);
  const [snapshot, setSnapshot] = useState<SessionSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isTouch = useTouchDevice();
  const laneYRatio = isTouch ? TOUCH.LANE_Y_RATIO : HIGHWAY.LANE_Y_RATIO;

  // Les boutons tactiles passent par la session sans passer par un faux
  // événement clavier : la source de l'appui ne regarde pas le gameplay.
  const sessionRef = useRef<GameSession | null>(null);
  const hit = useCallback((type: NoteType) => sessionRef.current?.handleNote(type), []);

  // Passer par une ref évite que l'effet ne dépende de l'identité du callback :
  // sans ça, un simple re-rendu du parent relancerait la partie depuis le début.
  const onFinishedRef = useRef(onFinished);
  onFinishedRef.current = onFinished;

  useEffect(() => {
    const host = canvasHost.current;
    if (!host) return;

    let session: GameSession | null = null;
    let renderer: HighwayRenderer | null = null;
    let cancelled = false;
    let finished = false;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.repeat) return;
      session?.handleKey(event.key);
    };

    void (async () => {
      try {
        const created = new HighwayRenderer();
        await created.init(host, laneYRatio);
        // React StrictMode démonte puis remonte systématiquement les composants
        // en développement : l'initialisation de Pixi peut donc se terminer
        // alors que l'écran n'existe plus. Sans ce garde, un second canvas
        // resterait accroché au DOM.
        if (cancelled) {
          created.destroy();
          return;
        }
        renderer = created;

        session = new GameSession({
          chart,
          renderer: created,
          calibrationOffsetMs: readCalibrationOffsetMs(),
          onSnapshot: (next) => {
            setSnapshot(next);
            if (!finished && (next.status === 'dead' || next.status === 'survived')) {
              finished = true;
              onFinishedRef.current(next);
            }
          },
        });

        sessionRef.current = session;
        window.addEventListener('keydown', onKeyDown);
        await session.start();
      } catch (cause) {
        if (!cancelled) setError(cause instanceof Error ? cause.message : String(cause));
      }
    })();

    return () => {
      cancelled = true;
      window.removeEventListener('keydown', onKeyDown);
      session?.stop();
      sessionRef.current = null;
      renderer?.destroy();
    };
  }, [chart, laneYRatio]);

  // Hauteur du bord supérieur de la piste, mesurée depuis le bas de l'écran :
  // la légende s'y accroche pour ne jamais recouvrir les notes, quelle que soit
  // la taille de la fenêtre.
  const laneTopFromBottom = `${(1 - laneYRatio + HIGHWAY.LANE_HEIGHT_RATIO / 2) * 100}%`;

  return (
    <main
      className="screen screen--game"
      style={
        {
          '--lane-top-from-bottom': laneTopFromBottom,
          '--touch-controls-height': `${TOUCH.CONTROLS_HEIGHT_RATIO * 100}%`,
        } as CSSProperties
      }
    >
      <div className="canvas-host" ref={canvasHost} />

      {/* Au clavier, un rappel discret ; au doigt, les boutons sont eux-mêmes
          le rappel — inutile de dupliquer. */}
      {isTouch ? <TouchControls onHit={hit} /> : <KeyLegend variant="floating" />}

      {snapshot && snapshot.status !== 'countdown' && (
        <Hud
          snapshot={snapshot}
          survivalThreshold={SURVIVAL.MIN_SUCCESS_RATIO}
          title={chart.title}
        />
      )}

      {snapshot?.status === 'countdown' && snapshot.countdownStep !== null && (
        <div className="countdown" key={snapshot.countdownStep}>
          {snapshot.countdownStep}
        </div>
      )}

      {error && (
        <div className="overlay">
          <div className="panel">
            <h2 className="panel__title">Impossible de lancer le morceau</h2>
            <p className="hint">{error}</p>
            <button className="button" onClick={onQuit}>
              Retour
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
