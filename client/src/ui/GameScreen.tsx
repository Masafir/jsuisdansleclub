import { useEffect, useRef, useState } from 'react';
import { HighwayRenderer } from '../render/highway';
import { GameSession, type SessionSnapshot } from '../game/session';
import { CALIBRATION, SURVIVAL } from '../config/gameplay';
import type { Chart } from '../chart/types';
import { Hud } from './Hud';

interface GameScreenProps {
  chart: Chart;
  onFinished: (snapshot: SessionSnapshot) => void;
  onQuit: () => void;
}

function readCalibrationOffsetMs(): number {
  const stored = localStorage.getItem(CALIBRATION.STORAGE_KEY);
  const parsed = stored === null ? Number.NaN : Number(stored);
  return Number.isFinite(parsed) ? parsed : CALIBRATION.DEFAULT_OFFSET_MS;
}

export function GameScreen({ chart, onFinished, onQuit }: GameScreenProps) {
  const canvasHost = useRef<HTMLDivElement>(null);
  const [snapshot, setSnapshot] = useState<SessionSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

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

    (async () => {
      try {
        renderer = new HighwayRenderer();
        await renderer.init(host);
        if (cancelled) return;

        session = new GameSession({
          chart,
          renderer,
          calibrationOffsetMs: readCalibrationOffsetMs(),
          onSnapshot: (next) => {
            setSnapshot(next);
            if (!finished && (next.status === 'dead' || next.status === 'survived')) {
              finished = true;
              onFinished(next);
            }
          },
        });

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
      renderer?.destroy();
    };
  }, [chart, onFinished]);

  return (
    <main className="screen screen--game">
      <div className="canvas-host" ref={canvasHost} />

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
