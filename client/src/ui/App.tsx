import { useCallback, useEffect, useState } from 'react';
import { HomeScreen } from './HomeScreen';
import { GameScreen } from './GameScreen';
import { ResultScreen } from './ResultScreen';
import { loadLibrary } from '../chart/library';
import { TEST_CHART } from '../chart/testChart';
import type { Chart } from '../chart/types';
import type { SessionSnapshot } from '../game/session';

type Screen =
  | { name: 'home' }
  | { name: 'game'; chart: Chart }
  | { name: 'result'; chart: Chart; snapshot: SessionSnapshot };

export function App() {
  const [screen, setScreen] = useState<Screen>({ name: 'home' });
  const [library, setLibrary] = useState<Chart[]>([TEST_CHART]);

  useEffect(() => {
    let cancelled = false;
    void loadLibrary().then((charts) => {
      if (!cancelled) setLibrary(charts);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const play = useCallback((chart: Chart) => {
    setScreen({ name: 'game', chart });
  }, []);

  const finish = useCallback((chart: Chart, snapshot: SessionSnapshot) => {
    setScreen({ name: 'result', chart, snapshot });
  }, []);

  const goHome = useCallback(() => setScreen({ name: 'home' }), []);

  switch (screen.name) {
    case 'home':
      return <HomeScreen library={library} onPlay={play} />;
    case 'game':
      return (
        <GameScreen
          chart={screen.chart}
          onFinished={(snapshot) => finish(screen.chart, snapshot)}
          onQuit={goHome}
        />
      );
    case 'result':
      return (
        <ResultScreen
          chart={screen.chart}
          snapshot={screen.snapshot}
          onRetry={() => play(screen.chart)}
          onAnotherSong={goHome}
        />
      );
  }
}
